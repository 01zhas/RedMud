import unittest
from redmud import Pipeline, Processor, Runtime, Settings, Rule, ProcessingError, field as F

class Identity(Processor):
    def transform(self,row):return row

def engines(policy):
    yield Pipeline(on_error=policy,output_fields=('x',)).check('positive',F('x')>0), 'run'
    yield Runtime(Identity(),Settings(on_error=policy,batch_size=3,output_fields=('x',)),input_rules=[Rule('positive',lambda row:row['x']>0)]),'process'

class TestPolicies(unittest.TestCase):
    def test_ac105_mixed_batches_account_before_raise(self):
        for policy in ('collect','raise','skip'):
            for e,api in engines(policy):
                with self.subTest(policy=policy,mode=api):
                    batch=getattr(e,api+'_batch')
                    self.assertEqual(batch([]),[])
                    if policy=='raise':
                        with self.assertRaises(ProcessingError) as caught:
                            batch([b'{',{'x':1},{'x':-1}])
                        self.assertEqual(caught.exception.result.index,0)
                    else:
                        out=batch([b'{',{'x':1},{'x':-1}])
                        self.assertEqual([r.index for r in out],[1] if policy=='skip' else [0,1,2])
                    self.assertEqual(e.metrics.processed,3)
                    self.assertEqual(sum(e.metrics.statuses.values()),3)
                    self.assertEqual(e.quality.snapshot()['fields']['x']['observed'],1)
                    self.assertEqual(getattr(e,api+'_one')({'x':1}).index,3)
    def test_ac105_scalar_and_iter_policies(self):
        for policy in ('collect','raise','skip'):
            for e,api in engines(policy):
                scalar=getattr(e,api+'_one')
                if policy=='raise':
                    with self.assertRaises(ProcessingError):scalar({'x':-1})
                else:self.assertFalse(scalar({'x':-1}).ok)
                self.assertEqual(scalar({'x':1}).index,1)
                stream=getattr(e,api+'_iter')([{'x':2},{'x':-1},{'x':3}])
                if policy=='raise':
                    with self.assertRaises(ProcessingError):list(stream)
                else:
                    self.assertEqual([r.index for r in stream],[2,4] if policy=='skip' else [2,3,4])
                self.assertEqual(e.metrics.processed,5)
    def test_ac105_source_failure_and_bad_sizes(self):
        def broken():
            raise LookupError('source')
            yield {}
        for e,api in engines('collect'):
            with self.assertRaises(LookupError):next(getattr(e,api+'_iter')(broken()))
            self.assertEqual(e.metrics.processed,0)
        for n in (0,-1,1.5,True):
            with self.assertRaises(ValueError):Settings(batch_size=n)
            seen=[]
            def rows():
                seen.append(1)
                yield {}
            with self.assertRaises(ValueError):next(Pipeline().run_iter(rows(),batch_size=n))
            self.assertEqual(seen,[])
