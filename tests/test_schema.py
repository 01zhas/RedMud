import unittest
from redmud import Pipeline

class TestSchema(unittest.TestCase):
    def test_ac102_invalid_schema_configuration(self):
        cases=['unknown',{},1,{'type':'int','mni':0},{'type':'int','nullable':1},
               {'type':'int','min':'x'},{'type':'int','min':1.0},
               {'type':'float','min':1},{'type':'int','min':3,'max':2},
               {'type':'number','min':0},{'type':'str','max':3},
               {'type':'int','allowed':[]},{'type':'int','allowed':[True]},
               {'type':'int','allowed':[None]}, {'type':'list','fields':{}},
               {'type':'int','items':'str'},{'fields':{},'items':'int'},
               {'fields':{'x':'unknown'}},{'items':{'type':'str','allowed':3}},
               {'type':'object','fields':{'a..b':'int'}}]
        for spec in cases:
            with self.subTest(spec=spec), self.assertRaises(ValueError):
                Pipeline().require({'x':spec}).prepare()
    def test_ac102_valid_nested_schema(self):
        p=Pipeline().require({'x':{'items':{'fields':{'n':{'type':'int','min':1,'max':2,'allowed':[1,2]}}}}})
        self.assertTrue(p.run_one({'x':[{'n':1}],'extra':1}).ok)
        for n in (0,3,None,True,1.0):
            with self.subTest(n=n):self.assertFalse(p.run_one({'x':[{'n':n}]}).ok)
        p=Pipeline().require({'x':{'type':'int','nullable':True,'allowed':[1,None]}})
        self.assertTrue(p.run_one({'x':None}).ok)
        self.assertFalse(p.run_one({}).ok)
    def test_ac102_bounds_and_allowed(self):
        for typ,good,bad in [('int',2,3),('float',2.0,3.0)]:
            p=Pipeline().require({'x':{'type':typ,'min':good,'max':good,'allowed':[good]}})
            self.assertTrue(p.run_one({'x':good}).ok)
            self.assertEqual(p.run_one({'x':bad}).errors[0].code,'numeric_constraint')
        self.assertEqual(Pipeline().require({'x':{'type':'str','allowed':['yes']}}).run_one({'x':'no'}).errors[0].code,'not_allowed')
