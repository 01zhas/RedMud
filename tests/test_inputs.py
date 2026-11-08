import copy
import json
import unittest
from redmud import Pipeline

class TestInputs(unittest.TestCase):
    def test_ac103_exact_integer_domain(self):
        p=Pipeline()
        for n in (-2**63,-2**53-1,0,2**53+1,2**63-1,2**63,2**64-1):
            for raw in ({'n':n},json.dumps({'n':n}),json.dumps({'n':n}).encode()):
                r=p.run_one(raw)
                self.assertTrue(r.ok)
                self.assertIs(type(r.value['n']),int)
                self.assertEqual(r.value['n'],n)
        for n in (-2**63-1,2**64,2**64+1,10**100):
            for raw in ({'nested':[{'n':n}]},json.dumps({'nested':[{'n':n}]}).encode()):
                r=p.run_one(raw)
                self.assertFalse(r.ok)
                self.assertEqual(r.errors[0].code,'numeric_range')
                self.assertEqual(r.errors[0].path,'nested[0].n')
        self.assertTrue(p.run_one({'n':1}).ok)
    def test_ac103_reject_unsupported_without_mutation(self):
        cycle={};cycle['cycle']=cycle
        rows=[{1:'key'},{'nested':{False:1}},{'x':float('inf')},{'x':float('nan')},
              {'x':set()}, {'x':(1,2)},cycle,object(),None,[],123,b'\xff',b'{"n":NaN}',b'{"n":1e999}']
        p=Pipeline()
        out=p.run_batch(rows+[{'n':2}])
        self.assertTrue(all(not r.ok for r in out[:-1]))
        self.assertTrue(out[-1].ok)
        source={'a':[{'n':1}],'$serde_json::private::Number':'not a number'}
        before=copy.deepcopy(source)
        self.assertEqual(p.run_one(source).value,before)
        self.assertEqual(source,before)
    def test_ac103_invalid_literals_are_config_errors(self):
        for value in (2**64,-2**63-1):
            with self.assertRaises(ValueError): Pipeline().derive('v',value).prepare()
