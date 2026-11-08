import itertools
import json
import subprocess
import sys
import unittest
from redmud import Pipeline, Processor, Runtime, Settings, field as F


def nested(depth):
    value=0
    for _ in range(depth-1):value={'x':value}
    return value


def expression(depth):
    value=F('x')
    for _ in range(depth-1):value=value+0
    return value


class TestLimits(unittest.TestCase):
    def test_data_boundary(self):
        for depth in (63,64,65):
            row=nested(depth)
            for raw in (row,json.dumps(row),json.dumps(row).encode()):
                with self.subTest(depth=depth,kind=type(raw).__name__):
                    r=Pipeline().run_one(raw)
                    self.assertEqual(r.ok,depth<=64)
                    if not r.ok:self.assertEqual((r.errors[0].code,r.errors[0].stage),('depth_limit','parse'))
    def test_plan_expression_and_combined_boundary(self):
        for depth in (63,64,65):
            if depth<=64:
                Pipeline().derive('v',expression(depth)).prepare()
            else:
                with self.assertRaises(ValueError):Pipeline().derive('v',expression(depth)).prepare()
        for plans,expr_depth,valid in [(64,1,True),(65,1,False),(32,33,True),(32,34,False)]:
            def prepare():
                p=Pipeline().derive('v',expression(expr_depth))
                for _ in range(plans-1):p=Pipeline().map_list('items',p)
                return p.prepare()
            if valid:prepare()
            else:
                with self.assertRaises(ValueError):prepare()
    def test_schema_and_literal_depth(self):
        for depth in (64,65):
            schema='int'
            for _ in range(depth-1):schema={'type':'object','fields':{'x':schema}}
            if depth<=64:Pipeline().require({'v':schema}).prepare()
            else:
                with self.assertRaises(ValueError):Pipeline().require({'v':schema}).prepare()
        with self.assertRaises(ValueError):
            Pipeline().require({'v':{'type':'object','allowed':[nested(65)]}}).prepare()
        # A legal literal can still make the output record too deep when inserted.
        r=Pipeline().derive('v',nested(64)).run_one({})
        self.assertEqual((r.status,r.errors[0].code,r.errors[0].stage),('error','depth_limit','transform'))
    def test_malicious_depth_in_bounded_subprocess(self):
        code='''from redmud import Pipeline, field as F
p=Pipeline()
for depth in (65,1000,20000):
 raw=b'{"x":'+b'['*depth+b'0'+b']'*depth+b'}'
 r=p.run_one(raw)
 assert not r.ok and r.errors[0].code=='depth_limit'
 assert p.run_one({'x':1}).ok
 r=p.run_one(b'['*depth)
 assert not r.ok
value=F('x')
for _ in range(5000):value=value+1
try: Pipeline().derive('x',value).prepare()
except ValueError: pass
else: raise AssertionError('deep plan accepted')
cycle={};cycle['x']=cycle
assert p.run_one(cycle).errors[0].code=='invalid_input'
print('adversarial subprocess completed')
'''
        p=subprocess.run([sys.executable,'-c',code],text=True,capture_output=True,timeout=20)
        self.assertEqual(p.returncode,0,p.stdout+p.stderr)
    def test_unbounded_source_lookahead(self):
        class Identity(Processor):
            def transform(self,item):return item
        for engine,method in [(Pipeline(),'run_iter'),(Runtime(Identity(),Settings(batch_size=5)),'process_iter')]:
            seen=[]
            def rows():
                for i in itertools.count():
                    seen.append(i)
                    yield {'x':i}
            iterator=getattr(engine,method)(rows(),**({'batch_size':5} if method=='run_iter' else {}))
            self.assertEqual(seen,[])
            self.assertEqual(next(iterator).index,0)
            self.assertEqual(len(seen),5)
            self.assertEqual([r.index for r in itertools.islice(iterator,6)],[1,2,3,4,5,6])
            self.assertEqual(len(seen),10)
            iterator.close()
