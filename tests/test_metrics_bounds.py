import gc
import json
import unittest
import weakref
from unittest.mock import patch
from redmud import Pipeline, Processor, Runtime, Settings, Rule, ProcessingError, field as F
from redmud.metrics import Metrics
from redmud.quality import OutputProfiler

class Identity(Processor):
    def transform(self,item):return item

class TestMetricBounds(unittest.TestCase):
    def test_both_modes_batch_summary_and_error_policies(self):
        for policy in ('collect','skip','raise'):
            for engine,api in [(Pipeline(on_error=policy,output_fields=('x',)).check('positive',F('x')>0),'run'),
                               (Runtime(Identity(),Settings(on_error=policy,output_fields=('x',)),input_rules=[Rule('positive',lambda r:r['x']>0)]),'process')]:
                with self.subTest(policy=policy,api=api):
                    batch=getattr(engine,api+'_batch')
                    self.assertEqual(batch([]),[])
                    if policy=='raise':
                        with self.assertRaises(ProcessingError):batch([b'{',{'x':1},{'x':-1}])
                    else:batch([b'{',{'x':1},{'x':-1}])
                    m=engine.snapshot()['metrics']
                    self.assertEqual(m['processed'],3)
                    self.assertEqual(m['statuses'],{'ok':1,'error':1,'rejected':1})
                    self.assertEqual(m['errors_by_code'],{'invalid_json':1,'positive':1})
                    self.assertEqual(m['batch_sizes'],{'0':1,'2-63':1})
                    self.assertEqual(m['batch_size_summary'],{'count':2,'sum':3,'min':0,'max':3})
                    self.assertEqual(m['stages']['batch']['samples'],2)
                    self.assertEqual(engine.quality.snapshot()['fields']['x']['observed'],1)
    def test_histogram_has_fixed_cardinality(self):
        m=Metrics()
        for size in range(4000):m.batch(size,1)
        snapshot=m.snapshot()
        self.assertEqual(set(snapshot['batch_sizes']),{'0','1','2-63','64-255','256-999','1000+'})
        self.assertEqual(snapshot['batch_size_summary'],{'count':4000,'sum':sum(range(4000)),'min':0,'max':3999})
    def test_dynamic_types_are_other_and_not_retained(self):
        profile=OutputProfiler(('v',))
        refs=[]
        for i in range(500):
            cls=type(f'UniqueType{i}',(),{})
            value=cls();refs.append(weakref.ref(value))
            profile.observe({'v':value})
        del value,cls
        gc.collect()
        self.assertTrue(all(ref() is None for ref in refs))
        self.assertEqual(profile.snapshot()['fields']['v']['types'],{'other':500})
    def test_disabled_metrics_still_profiles_and_idle_clock(self):
        p=Pipeline(metrics=False,output_fields=('x','missing'))
        p.run_batch([{'x':None},{'x':2},{'x':4}])
        snapshot=p.snapshot()
        self.assertEqual(snapshot['metrics']['processed'],0)
        self.assertEqual(snapshot['metrics']['batch_size_summary']['count'],0)
        fields=snapshot['quality']['fields']
        self.assertEqual(fields['x']['nulls'],1)
        self.assertEqual(fields['x']['mean'],3)
        self.assertEqual(fields['missing']['missing'],3)
        m=Metrics()
        with patch('redmud.metrics.monotonic_ns',side_effect=[1_000_000_000,6_000_000_000]):
            m.start();m.processed=10;snapshot=m.snapshot()
        self.assertEqual(snapshot['throughput_per_second'],2)
        self.assertEqual(snapshot['elapsed_seconds'],5)
        json.dumps(p.snapshot(),allow_nan=False)
