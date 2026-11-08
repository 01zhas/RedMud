import unittest
from redmud import Pipeline, field as F, when, list_sum

class TestExpressions(unittest.TestCase):
    def test_ac104_arithmetic_and_order(self):
        p=(Pipeline().derive('sum',F('x')+F('y')).derive('diff',F('x')-F('y'))
           .derive('product',F('x')*F('y')).derive('gt',F('x')>F('y'))
           .derive('ge',F('x')>=F('y')).derive('eq',F('x')==F('y')))
        r=p.run_one({'x':7,'y':2})
        self.assertEqual([r.value[k] for k in ('sum','diff','product','gt','ge','eq')],[9,5,14,True,True,False])
        for expr,raw in [(F('x')+1,{'x':2**63-1}),(F('x')-1,{'x':-2**63}),(F('x')*2,{'x':2**62})]:
            e=Pipeline().derive('v',expr).run_one(raw).errors[0]
            self.assertEqual((e.code,e.path,e.stage),('overflow','v','transform'))
    def test_ac104_paths_and_laziness(self):
        p=Pipeline().map_list('orders',Pipeline().derive('v',F('x')+F('missing')))
        for value,code in [(None,'null_value'),(True,'invalid_type'),(1.0,'invalid_type')]:
            e=p.run_one({'orders':[{'x':value}]}).errors[0]
            self.assertEqual((e.code,e.path,e.stage),(code,'orders[0].x','transform'))
        e=p.run_one({'orders':[{}]}).errors[0]
        self.assertEqual((e.code,e.path),('missing_field','orders[0].x'))
        self.assertEqual(Pipeline().derive('v',when(F('yes'),1,F('absent'))).run_one({'yes':True}).value['v'],1)
        for p in (Pipeline().check('rule',F('x')),Pipeline().derive('v',when(F('x'),1,2))):
            self.assertEqual(p.run_one({'x':1}).errors[0].code,'invalid_type')
    def test_ac104_nested_collection_errors(self):
        p=Pipeline().map_list('items',Pipeline().derive('v',1))
        for value,code in [(None,'null_value'),({},'invalid_type'),([1],'invalid_type')]:
            self.assertEqual(p.run_one({'items':value}).errors[0].code,code)
        for value,code in [(None,'null_value'),([], 'invalid_type')]:
            e=Pipeline().map_list('a.b',Pipeline()).run_one({'a':value}).errors[0]
            self.assertEqual((e.code,e.path),(code,'a'))
        p=Pipeline().derive('v',list_sum('items','x'))
        self.assertEqual(p.run_one({'items':[]}).value['v'],0)
        e=p.run_one({'items':[{'x':2**63-1},{'x':1}]}).errors[0]
        self.assertEqual((e.code,e.path),('overflow','items'))
        e=p.run_one({'items':[{'x':None}]}).errors[0]
        self.assertEqual((e.code,e.path),('null_value','items[0].x'))
    def test_ac104_structural_equality(self):
        p=Pipeline().derive('same',F('x')==F('y'))
        for x,y,same in [(1,1.0,False),(True,1,False),(None,None,True),({'a':[1]},{'a':[1]},True),([1],[1.0],False)]:
            self.assertEqual(p.run_one({'x':x,'y':y}).value['same'],same)
