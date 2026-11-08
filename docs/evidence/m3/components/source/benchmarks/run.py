"""Isolated, sequential, equivalent-work timing/RSS/tracemalloc experiments.

Run python -m benchmarks.run --profile smoke --output target/bench-smoke.
Production timing never runs with tracemalloc enabled. Inputs/results are streamed
in bounded batches; full latency samples are retained only in the timing pass.
"""
import argparse
from datetime import datetime, timezone
import hashlib
from itertools import islice
import json
import math
import os
from pathlib import Path
import platform
import resource
import statistics
import subprocess
import sys
import time
import tracemalloc
from .workloads import SEED, NAMES, Plain, rows, engine, call, signature, verify

ROOT=Path(__file__).resolve().parents[1]


def batches(iterator,size):
    iterator=iter(iterator)
    while batch:=list(islice(iterator,size)):
        yield batch


def consume(results,digest,index):
    counts={'ok':0,'rejected':0,'error':0}
    for result in results:
        i,status,value,errors=signature(result)
        assert i==index,(i,index)
        index+=1
        counts[status]+=1
        digest.update(json.dumps([status,value,errors],sort_keys=True,separators=(',',':'),allow_nan=False).encode())
        digest.update(b'\n')
    return index,counts


def peak_rss():
    """Post-exec Linux address-space high water; rusage can inherit launcher peak."""
    if sys.platform.startswith('linux'):
        for line in Path('/proc/self/status').read_text().splitlines():
            if line.startswith('VmHWM:'):
                return int(line.split()[1])*1024,'linux-proc-VmHWM'
        raise RuntimeError('VmHWM unavailable; do not substitute inherited rusage silently')
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*(1 if sys.platform=='darwin' else 1024),'rusage-platform-fallback-unverified'

def child(case,phase):
    if case.get('cpu') is not None:os.sched_setaffinity(0,{case['cpu']})
    name,kind,n,size=case['workload'],case['input'],case['records'],case['batch_size']
    # Parent verifies all modes. Each fresh child loads only its selected engine
    # plus the independent reference, avoiding cross-engine RSS high-water pollution.
    # A full-corpus untimed oracle pass can warm Python/CPU caches.
    expected=hashlib.sha256();reference=Plain(name)
    for batch in batches(rows(name,n,kind),size):
        consume(call(reference,batch),expected,reference.index-len(batch))
    begin=time.perf_counter_ns();processor=engine(case['engine'],name,size,case.get('tcore_source'))
    setup_ns=time.perf_counter_ns()-begin
    warm=min(n,1000)
    for batch in batches(rows(name,warm,kind),size):call(processor,batch)
    rss_before,rss_source=peak_rss()
    if phase=='traced':tracemalloc.start()
    duration_ns=0;latencies=[];index=warm;observed={'ok':0,'rejected':0,'error':0}
    digest=hashlib.sha256()
    wall_start=time.perf_counter_ns()
    for batch in batches(rows(name,n,kind),size):
        if phase=='timing':begin=time.perf_counter_ns()
        outcomes=call(processor,batch)
        if phase=='timing':
            elapsed=time.perf_counter_ns()-begin
            duration_ns+=elapsed;latencies.append(elapsed)
        index,counts=consume(outcomes,digest,index)
        for key,value in counts.items():observed[key]+=value
        del outcomes
    wall_ns=time.perf_counter_ns()-wall_start
    peak_python=None
    if phase=='traced':
        peak_python=tracemalloc.get_traced_memory()[1];tracemalloc.stop()
    rss_after,_=peak_rss()
    assert index==warm+n and digest.hexdigest()==expected.hexdigest(),'outcomes differ from independent reference'
    return dict(phase=phase,setup_ns=setup_ns,warmup_records=warm,call_ns=duration_ns if phase=='timing' else None,
                wall_ns=wall_ns,batch_ns=latencies if phase=='timing' else None,counts=observed,
                digest=digest.hexdigest(),rss_before_bytes=rss_before,rss_peak_bytes=rss_after,rss_source=rss_source,
                python_traced_peak_bytes=peak_python,affinity=sorted(os.sched_getaffinity(0)) if hasattr(os,'sched_getaffinity') else None)


def percentile(values,p):
    ordered=sorted(values)
    return ordered[max(0,math.ceil(p*len(ordered))-1)]


def summarize(case,samples):
    timing=[s for s in samples if s['phase']=='timing']
    rss=[s['rss_peak_bytes'] for s in samples if s['phase']=='rss']
    traced=[s['python_traced_peak_bytes'] for s in samples if s['phase']=='traced']
    times=[s['call_ns']/1e9 for s in timing]
    latencies=[n/1e6 for s in timing for n in s['batch_ns']]
    median=statistics.median(times) if times else None
    return dict(case=case,process_samples=len(timing),call_seconds_median=median,
                records_per_second=case['records']/median if median else None,
                call_seconds_min=min(times) if times else None,call_seconds_max=max(times) if times else None,
                relative_time_range=(max(times)-min(times))/median if median else None,
                batch_p50_ms=percentile(latencies,.5) if latencies else None,
                batch_p95_ms=percentile(latencies,.95) if latencies else None,
                batch_latency_samples=len(latencies),rss_process_samples=len(rss),
                rss_peak_bytes_median=statistics.median(rss) if rss else None,
                rss_peak_bytes_min=min(rss) if rss else None,rss_peak_bytes_max=max(rss) if rss else None,
                python_traced_peak_bytes=statistics.median(traced) if traced else None,
                counts=samples[0]['counts'],digest=samples[0]['digest'])


def configurations(profile,tcore_source):
    cases=[]
    def add(w,e,k,n,b,passes=('timing','rss','traced')):
        c=dict(workload=w,engine=e,input=k,records=n,batch_size=b,passes=list(passes),tcore_source=tcore_source)
        if c not in cases:cases.append(c)
    if profile=='smoke':
        for w in NAMES:
            for e in ('plain','native'):add(w,e,'bytes',128,64)
    elif profile=='stream':
        for n in (2000,100000):
            for e in ('runtime','native'):add('arithmetic',e,'bytes',n,64,('rss','traced'))
    elif profile=='full':
        for w in NAMES:
            for e in ['plain','runtime','native','native_off']+(['tcore'] if tcore_source else []):
                for k in ('bytes','dict'):
                    for n in (256,5000):
                        for b in (1,64,1000):add(w,e,k,n,b)
    else:
        for w in NAMES:
            for e in ['plain','runtime','native']+(['tcore'] if tcore_source else []):
                for k in ('bytes','dict'):add(w,e,k,5000,1000)
            add(w,'native','bytes',256,64)
        for w in ('arithmetic','nested_sums'):
            for b in (1,64):add(w,'native','bytes',5000,b)
            add(w,'native_off','bytes',5000,1000)
    return cases


def identity():
    import redmud,redmud._native
    paths=[p for folder in ('python','crates','benchmarks') for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    paths+=[ROOT/'Cargo.lock',ROOT/'Cargo.toml',ROOT/'pyproject.toml']
    clocks=[]
    for _ in range(1000):
        a=time.perf_counter_ns();b=time.perf_counter_ns();clocks.append(b-a)
    return dict(timestamp_utc=datetime.now(timezone.utc).isoformat(),python=sys.version,executable=sys.executable,
                platform=platform.platform(),processor=platform.processor(),cpu_count=os.cpu_count(),
                affinity=sorted(os.sched_getaffinity(0)) if hasattr(os,'sched_getaffinity') else None,
                rustc=subprocess.check_output(['rustc','-Vv'],text=True),seed=SEED,
                clock_pair_ns_median=statistics.median(clocks),module=redmud.__file__,extension=redmud._native.__file__,
                extension_sha256=hashlib.sha256(Path(redmud._native.__file__).read_bytes()).hexdigest(),
                sources={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)})


def main():
    if sys.flags.optimize:
        raise RuntimeError('Run benchmarks without -O: correctness assertions are required')
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile',choices=('smoke','baseline','stream','full'),default='smoke')
    parser.add_argument('--output',type=Path,default=Path('target/benchmark'))
    parser.add_argument('--repeat',type=int,default=5)
    parser.add_argument('--rss-repeat',type=int,default=3)
    parser.add_argument('--tcore-source')
    parser.add_argument('--pin-cpu',action='store_true')
    parser.add_argument('--record-scale',type=int,default=1,help='multiply profile record counts; keep raw sample counts visible')
    parser.add_argument('--passes',nargs='+',choices=('timing','rss','traced'),help='override passes, e.g. repeat only memory measurements')
    parser.add_argument('--child')
    parser.add_argument('--phase',choices=('timing','rss','traced'))
    args=parser.parse_args()
    if args.child:
        print(json.dumps(child(json.loads(args.child),args.phase)));return
    if args.pin_cpu and not hasattr(os,'sched_getaffinity'):parser.error('pin-cpu is Linux-only; omit it on other platforms')
    if args.record_scale<1:parser.error('record-scale must be positive')
    if args.repeat<2 or args.rss_repeat<1:parser.error('repeat>=2 and rss-repeat>=1 required')
    out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    meta=identity();meta.update(profile=args.profile,repeat=args.repeat,rss_repeat=args.rss_repeat,record_scale=args.record_scale,command=sys.argv)
    meta['method']='Sequential fresh processes; full untimed oracle/preflight; warmup excluded; call timings exclude input generation/digest; whole-process RSS and traced allocations separate.'
    cpu=min(os.sched_getaffinity(0)) if args.pin_cpu else None
    if args.tcore_source:
        source=Path(args.tcore_source).resolve()
        meta['tcore_sources']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in source.glob('tcore/*.py')}
        assert meta['tcore_sources'],'No legacy source supplied'
    meta['rss_source']='linux-proc-VmHWM' if sys.platform.startswith('linux') else 'unverified-platform-fallback'
    meta['passes_override']=args.passes
    (out/'environment.json').write_text(json.dumps(meta,indent=2)+'\n')
    from shutil import copyfile
    for name in meta['sources']:
        target=out/'source'/name;target.parent.mkdir(parents=True,exist_ok=True);copyfile(ROOT/name,target)
    summaries=[]
    cases=configurations(args.profile,args.tcore_source)
    for case in cases:
        case['records']*=args.record_scale
        if args.passes:case['passes']=args.passes
    verified=set()
    for number,case in enumerate(cases,1):
        key=(case['workload'],case['input'])
        if key not in verified:
            verify(*key,80,args.tcore_source)
            verified.add(key)
        case['cpu']=cpu
        cid=f'{case["workload"]}-{case["engine"]}-{case["input"]}-n{case["records"]}-b{case["batch_size"]}'
        folder=out/'raw'/cid;folder.mkdir(parents=True)
        samples=[]
        for phase in case['passes']:
            count=args.repeat if phase=='timing' else args.rss_repeat if phase=='rss' else 1
            for repeat in range(count):
                command=[sys.executable,'-m','benchmarks.run','--child',json.dumps(case),'--phase',phase]
                env=os.environ.copy();env['PYTHONHASHSEED']='0'
                result=subprocess.run(command,cwd=ROOT,env=env,text=True,capture_output=True,timeout=300)
                if result.returncode:
                    (folder/f'{phase}-{repeat}-FAILED.log').write_text(result.stdout+result.stderr)
                    raise RuntimeError(f'{cid}/{phase} failed; see raw log')
                sample=json.loads(result.stdout);samples.append(sample)
                (folder/f'{phase}-{repeat}.json').write_text(json.dumps(sample)+'\n')
                if result.stderr:(folder/f'{phase}-{repeat}.stderr').write_text(result.stderr)
        summaries.append(summarize(case,samples))
        (out/'summary.json').write_text(json.dumps(summaries,indent=2)+'\n')
        print(f'{number}/{len(cases)} {cid}: {summaries[-1]["records_per_second"]} records/s',flush=True)
    print('Measured data:',out)

if __name__=='__main__':main()
