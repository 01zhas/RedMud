"""Audit-only measurements of the unchanged implementation; not a regression gate."""
import json, math, os, resource, statistics, subprocess, sys, time
from redmud import Pipeline, Processor, Runtime, Settings, field as F

def transform(row):
    if type(row['price']) is not int or type(row['quantity']) is not int or row['quantity'] <= 0:
        raise ValueError
    return dict(row, total=row['price'] * row['quantity'])

class Compute(Processor):
    def transform(self, row):
        return transform(row)

if len(sys.argv) == 1:
    print(json.dumps({'platform':sys.platform, 'python':sys.version, 'records':20000,
                      'batch_size':1000, 'process_repeats':5, 'warmup_batches':1}))
    for mode in ('python', 'runtime', 'native_bytes', 'native_dict'):
        results=[]
        for _ in range(5):
            output=subprocess.check_output([sys.executable,__file__,mode],text=True)
            results.append(json.loads(output))
        rates=[r['records_per_second'] for r in results]
        times=[t for r in results for t in r['batch_ms']]
        print(json.dumps({'mode':mode,'throughput_median':statistics.median(rates),
                          'batch_p50_ms':statistics.median(times),
                          'batch_p95_ms':sorted(times)[math.ceil(.95*len(times))-1],
                          'rss_peak_kib_median':statistics.median(r['rss_peak_kib'] for r in results),
                          'raw_runs':results}))
    # This measures the unchanged internal call and envelope decoding separately,
    # not pure FFI overhead or pure Rust compute.
    from redmud._native import NativePlan
    spec={'steps':[{'op':'derive','name':'total','expr':{'op':'mul','left':{'op':'field','path':'price'},'right':{'op':'field','path':'quantity'}}}]}
    plan=NativePlan(json.dumps(spec)); batch=[b'{"price":10,"quantity":2}']*1000
    call=[]; decode=[]
    for _ in range(21):
        t=time.perf_counter_ns(); raw=plan.run_batch(batch); middle=time.perf_counter_ns()
        values=[json.loads(r) for r in raw]; end=time.perf_counter_ns()
        assert all(v['value']['total']==20 and not v['errors'] for v in values)
        call.append((middle-t)/1e6); decode.append((end-middle)/1e6)
    print(json.dumps({'boundary_scope':'internal_native_call_and_separate_envelope_decode',
                      'note':'derive only; differs from validated end-to-end workload; no exact overhead decomposition',
                      'call_median_ms':statistics.median(call[1:]),'decode_median_ms':statistics.median(decode[1:]),
                      'call_ms':call[1:],'decode_ms':decode[1:]}))
else:
    mode=sys.argv[1]
    decoded=[{'price':i,'quantity':2} for i in range(20000)]
    encoded=[json.dumps(r).encode() for r in decoded]
    pipeline=(Pipeline().require({'price':'int','quantity':'int'})
              .check('positive',F('quantity')>0).derive('total',F('price')*F('quantity')).prepare())
    runtime=Runtime(Compute(),Settings(timing_sample_every=0))
    rows=decoded if mode=='native_dict' else encoded
    def batch_run(batch):
        if mode=='python': return [transform(json.loads(r)) for r in batch]
        if mode=='runtime': return runtime.process_batch(batch)
        return pipeline.run_batch(batch)
    batch_run(rows[:1000])
    elapsed=[]; checksum=0
    for start in range(0,len(rows),1000):
        t=time.perf_counter_ns(); result=batch_run(rows[start:start+1000]); end=time.perf_counter_ns()
        elapsed.append((end-t)/1e6)
        for r in result:
            if mode!='python':
                assert r.ok
                r=r.value
            checksum+=r['total']
        del result
    assert checksum==2*sum(range(20000))
    print(json.dumps({'records_per_second':20000/(sum(elapsed)/1000),'batch_ms':elapsed,
                      'rss_peak_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                      'checksum':checksum}))
