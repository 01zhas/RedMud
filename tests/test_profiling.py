import gc
import tracemalloc
import unittest
import weakref
from redmud import Pipeline, Processor, Runtime, Settings

class Identity(Processor):
    def transform(self,item):return item

class TestProfiling(unittest.TestCase):
    def test_ac106_input_count_and_bounded_sample(self):
        for mode in ('native','python','disabled'):
            e=Runtime(Identity(),Settings(on_error='skip')) if mode=='python' else Pipeline(on_error='skip',metrics=mode!='disabled')
            seen=[]
            def rows():
                for raw in [b'{',{'x':1},b'{',{'x':2}]:
                    seen.append(raw)
                    yield raw
            report=e.profile(rows(),max_records=3)
            self.assertEqual(report.records,3)
            self.assertEqual(len(seen),3)
            self.assertIn('function calls',report.top_functions)
    def test_ac106_cleanup_and_existing_trace(self):
        started=not tracemalloc.is_tracing()
        if started:tracemalloc.start()
        try:
            for e in (Pipeline(),Runtime(Identity())):
                e.profile([{}],max_records=1)
                self.assertTrue(tracemalloc.is_tracing())
                def broken():
                    raise LookupError('source')
                    yield {}
                with self.assertRaises(LookupError):e.profile(broken())
                self.assertTrue(tracemalloc.is_tracing())
        finally:
            if started:tracemalloc.stop()
        if started:
            with self.assertRaises(LookupError):Pipeline().profile(broken())
            self.assertFalse(tracemalloc.is_tracing())
    def test_ac106_arguments_and_no_retention(self):
        for bad in (0,-1,True,1.5):
            with self.assertRaises(ValueError):Pipeline().profile([],max_records=bad)
            with self.assertRaises(ValueError):Pipeline().profile([],top=bad)
        refs=[]
        class Token:pass
        class Build(Processor):
            def transform(self,item):
                token=Token();refs.append(weakref.ref(token));return token
        Runtime(Build()).profile(range(5),max_records=5)
        gc.collect()
        self.assertTrue(all(ref() is None for ref in refs))
