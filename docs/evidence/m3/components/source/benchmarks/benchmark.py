"""Equivalent parse, schema, check and derive work. Median of five warm runs."""
import json, statistics, time, platform, tracemalloc
from redmud import Pipeline, Processor, Runtime, Rule, Settings, field as F
N=10000
rows=[json.dumps({'price':i,'quantity':2}).encode() for i in range(N)]
def transform(r):
    if type(r['price']) is not int or type(r['quantity']) is not int or r['quantity']<=0: raise ValueError
    return dict(r,total=r['price']*r['quantity'])
class Compute(Processor):
    def transform(self,r): return transform(r)
p=Pipeline().require({'price':'int','quantity':'int'}).check('positive',F('quantity')>0).derive('total',F('price')*F('quantity')).prepare()
print(platform.platform(),platform.python_version())
for name,fn in [('python',lambda:[transform(json.loads(r)) for r in rows]),('fallback',lambda:list(Runtime(Compute(),Settings(timing_sample_every=0)).process_iter(rows))),('native',lambda:list(p.run_iter(rows))),('native_single',lambda:[p.run_one(r) for r in rows]),('native_dict',lambda:list(p.run_iter([json.loads(r) for r in rows])))]:
    result=fn()
    values=[r.value if hasattr(r,'value') else r for r in result]
    assert values==[transform(json.loads(r)) for r in rows]
    samples=[]
    for _ in range(5):
        start=time.perf_counter(); fn(); samples.append(time.perf_counter()-start)
    tracemalloc.start();fn();peak=tracemalloc.get_traced_memory()[1];tracemalloc.stop()
    sec=statistics.median(samples)
    print(f'{name}: {sec:.6f}s {N/sec:.0f} records/s Python_peak={peak} bytes')
# Conversion-only comparison uses predecoded rows outside timed execution.
decoded=[json.loads(r) for r in rows]
quiet=Pipeline(metrics=False).require({'price':'int','quantity':'int'}).check('positive',F('quantity')>0).derive('total',F('price')*F('quantity')).prepare()
for name,fn in [('native_metrics_off',lambda:list(quiet.run_iter(rows))),('native_predecoded',lambda:list(p.run_iter(decoded)))]:
    samples=[]
    for _ in range(5):
        start=time.perf_counter();result=fn();samples.append(time.perf_counter()-start)
        assert all(r.ok for r in result)
    sec=statistics.median(samples)
    print(f'{name}: {sec:.6f}s {N/sec:.0f} records/s')
