import unittest
from redmud import Pipeline, field as F, list_sum, when, ProcessingError

class TestNative(unittest.TestCase):
    def test_arithmetic_inputs(self):
        p=Pipeline().require({'x':'int'}).derive('v',F('x')*2)
        out=p.run_batch([{'x':3},b'{"x":4}','{"x":5}',b'{',{'x':True},{'x':None},{}])
        self.assertEqual([r.value['v'] for r in out[:3]],[6,8,10])
        self.assertEqual([r.errors[0].code for r in out[3:]],['invalid_json','invalid_type','null_value','missing_field'])
        self.assertEqual([r.index for r in out],list(range(7)))
    def test_nested(self):
        item=Pipeline().require({'quantity':{'type':'int','min':1}}).derive('total',F('price')*F('quantity'))
        p=Pipeline().map_list('orders',Pipeline().map_list('items',item).derive('total',list_sum('items','total'))).derive('total',list_sum('orders','total'))
        self.assertEqual(p.run_one({'orders':[{'items':[{'price':10,'quantity':2}]}]}).value['total'],20)
        self.assertEqual(p.run_one({'orders':[]}).value['total'],0)
        r=p.run_one({'orders':[{'items':[{'price':10,'quantity':0}]}]})
        self.assertEqual(r.errors[0].path,'orders[0].items[0].quantity')
    def test_overflow(self):
        p=Pipeline().derive('v',F('x')+1)
        self.assertEqual(p.run_one({'x':2**63-1}).errors[0].code,'overflow')
        self.assertTrue(p.run_one({'x':1}).ok)
    def test_policies(self):
        for policy in ('collect','skip','raise'):
            p=Pipeline(on_error=policy).check('positive',F('x')>0)
            if policy=='raise':
                with self.assertRaises(ProcessingError): p.run_one({'x':-1})
            else:
                self.assertEqual(len(p.run_batch([{'x':-1},{'x':1}])),1 if policy=='skip' else 2)
    def test_stream_and_metrics(self):
        seen=[]
        def rows():
            for i in range(100):
                seen.append(i)
                yield {'x':i}
        p=Pipeline(output_fields=('v','absent')).derive('v',F('x')*2)
        out=p.run_iter(rows(),batch_size=3)
        self.assertEqual(next(out).value['v'],0)
        self.assertEqual(len(seen),3)
        self.assertEqual(p.snapshot()['metrics']['processed'],3)
        self.assertEqual(p.snapshot()['quality']['fields']['absent']['missing'],3)
        self.assertEqual(p.profile([{'x':1}],max_records=1).records,1)
    def test_condition_and_snapshot(self):
        schema={'x':'int'}
        p=Pipeline().require(schema).derive('v',when(F('x')>0,1,0))
        schema['x']='str'
        self.assertEqual(p.run_one({'x':-1}).value['v'],0)
        self.assertEqual(p.run_one({'x':1}).value['v'],1)
        with self.assertRaises(TypeError): bool(F('x'))
