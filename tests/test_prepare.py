import unittest
from redmud import Pipeline, field as F, when
from redmud.pipeline import Expr

class TestPrepare(unittest.TestCase):
    def test_ac101_invalid_definitions(self):
        bad = [Pipeline().derive('', 1), Pipeline().derive('a.b', 1),
               Pipeline().derive('a[0]',1), Pipeline().derive('v', F('a..b')),
               Pipeline().map_list('',Pipeline()), Pipeline().check('bad name',F('x')>0),
               Pipeline().check('overflow',F('x')>0), Pipeline().check('é',F('x')>0),
               Pipeline().check('a',F('x')>0).check('a',F('x')>1),
               Pipeline().derive('v',Expr({'op':'wat'})),
               Pipeline().derive('v',when(F('x')>0,1,F('a..b')))]
        for p in bad:
            with self.subTest(steps=p._steps), self.assertRaises(ValueError): p.prepare()
    def test_ac101_prepare_before_consumption(self):
        seen=[]
        def records():
            seen.append(1)
            yield {}
        with self.assertRaises(ValueError):
            next(Pipeline().derive('',1).run_iter(records()))
        self.assertEqual(seen,[])
    def test_ac101_cached_independent_builders(self):
        base=Pipeline().derive('a',1)
        p=base.derive('b',F('a')+2)
        p.prepare(); cached=p._compiled
        self.assertIs(p.prepare(),p)
        self.assertIs(p._compiled,cached)
        self.assertEqual(p.run_one({}).value,{'a':1,'b':3})
        self.assertEqual(base.run_one({}).value,{'a':1})
        self.assertEqual(base._index,1)
        child=Pipeline().check('x',F('x')>0)
        parent=Pipeline().map_list('a',child).map_list('b',child)
        parent.prepare()
