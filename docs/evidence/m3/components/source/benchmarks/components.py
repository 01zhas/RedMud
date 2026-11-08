"""Diagnostic core/FFI/public scopes on exactly the same finite fixture batch.

No public API, new dependency, or production instrumentation. Build once before
measurements; invoke release Rust test binary and CPython sequentially.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import statistics
import subprocess
import sys
import tempfile
import time
from .run import ROOT, identity
from .workloads import NAMES, Plain, native_plan, rows, signature
from redmud.pipeline import _validate_json_input


def timed(fn):
    start=time.perf_counter_ns();value=fn()
    return value,time.perf_counter_ns()-start


def marker(stdout):
    lines=[line.split('REDMUD_COMPONENTS ',1)[1] for line in stdout.splitlines() if 'REDMUD_COMPONENTS ' in line]
    if len(lines)!=1:raise ValueError('Expected exactly one Rust diagnostic result')
    data=json.loads(lines[0])
    if data['records']<=0 or any(data[key]<0 for key in ('full_ns','parse_ns','evaluate_ns','serialize_ns')):
        raise ValueError('Invalid diagnostic units/counts')
    return data


def child(case):
    if case['cpu'] is not None:os.sched_setaffinity(0,{case['cpu']})
    root=Path(case['fixture']);raw=root.joinpath('records.jsonl').read_bytes().splitlines()
    n=len(raw)
    with tempfile.TemporaryDirectory(prefix='redmud-components-') as temporary:
        output=Path(temporary)/'output.json'
        env=os.environ.copy();env.update(REDMUD_BENCH_FIXTURE_DIR=str(root),REDMUD_BENCH_OUTPUT=str(output))
        process=subprocess.run([case['binary'],'benchmark_probe::measure_fixture','--exact','--ignored','--nocapture'],
                               env=env,text=True,capture_output=True,check=True,timeout=120)
        core=marker(process.stdout)
        core_outputs=json.loads(output.read_text())
    p=native_plan(case['workload'],metrics=False).prepare()
    assert core['records']==n
    # Input bytes are identical across core, binding, decode and public paths.
    expected=Plain(case['workload']).run_batch(raw)
    binding=p._compiled.run_batch(raw)
    assert binding==core_outputs,'core/binding bytes differ'
    def normalize(data):
        errors=tuple((e['code'],e['path'],e['stage']) for e in data['errors'])
        return data['value'],errors
    assert [normalize(json.loads(s)) for s in binding]==[(r.value,signature(r)[3]) for r in expected]
    def encode(records):
        result=[]
        for row in records:
            if isinstance(row,bytes):result.append(row)
            else:
                _validate_json_input(row,set())
                result.append(json.dumps(row,allow_nan=False).encode('utf-8'))
        return result
    dictionaries=list(rows(case['workload'],n,'dict'))
    # Warm each observable scope; preparation and oracle are outside measurements.
    p.run_batch(raw);p.run_batch(dictionaries)
    encoded=encode(dictionaries)
    _,binding_ns=timed(lambda:p._compiled.run_batch(raw))
    decoded,decode_ns=timed(lambda:[json.loads(s) for s in binding])
    converted,encode_ns=timed(lambda:encode(dictionaries))
    assert converted==encoded and len(decoded)==n
    public_bytes,public_bytes_ns=timed(lambda:p.run_batch(raw))
    public_dict,public_dict_ns=timed(lambda:p.run_batch(dictionaries))
    assert [(r.value,signature(r)[3]) for r in public_bytes]==[(r.value,signature(r)[3]) for r in expected]
    assert [(r.value,signature(r)[3]) for r in public_dict]==[(r.value,signature(r)[3]) for r in expected]
    return dict(core=core,binding_ns=binding_ns,decode_ns=decode_ns,dict_validate_encode_ns=encode_ns,
                public_bytes_ns=public_bytes_ns,public_dict_ns=public_dict_ns,records=n,
                compact_input_bytes=sum(map(len,raw)),dict_encoded_bytes=sum(map(len,encoded)),
                parity=True)


def main():
    if sys.flags.optimize:raise RuntimeError('Correctness assertions require Python without -O')
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=Path('target/components'))
    parser.add_argument('--repeat',type=int,default=5)
    parser.add_argument('--records',type=int,default=1000)
    parser.add_argument('--pin-cpu',action='store_true')
    parser.add_argument('--child')
    args=parser.parse_args()
    if args.child:print(json.dumps(child(json.loads(args.child))));return
    if args.repeat<2 or args.records<1:parser.error('repeat>=2, records>=1')
    if args.pin_cpu and not hasattr(os,'sched_getaffinity'):parser.error('pin-cpu is Linux-only')
    out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    build=subprocess.run(['cargo','test','--release','-p','redmud-core','--locked','--no-run','--message-format=json'],
                         cwd=ROOT,text=True,capture_output=True,check=True)
    (out/'build.log').write_text(build.stdout+build.stderr)
    artifacts=[json.loads(line) for line in build.stdout.splitlines() if line.startswith('{')]
    binaries=[a['executable'] for a in artifacts if a.get('reason')=='compiler-artifact' and a.get('executable') and a['profile']['test']]
    if len(binaries)!=1:raise ValueError('Expected one core diagnostic test binary')
    binary=binaries[0];meta=identity()
    meta.update(command=sys.argv,binary=binary,binary_sha256=hashlib.sha256(Path(binary).read_bytes()).hexdigest(),
                repeat=args.repeat,records=args.records,method='same-batch independent observable scopes; not additive decomposition')
    (out/'environment.json').write_text(json.dumps(meta,indent=2)+'\n')
    from shutil import copyfile
    for name in meta['sources']:
        target=out/'source'/name;target.parent.mkdir(parents=True,exist_ok=True);copyfile(ROOT/name,target)
    cpu=min(os.sched_getaffinity(0)) if args.pin_cpu else None
    summaries=[]
    for name in NAMES:
        folder=out/name;folder.mkdir()
        (folder/'plan.json').write_text(json.dumps(dict(steps=native_plan(name)._steps)))
        (folder/'records.jsonl').write_bytes(b'\n'.join(rows(name,args.records,'bytes'))+b'\n')
        case=dict(workload=name,binary=binary,fixture=str(folder),cpu=cpu)
        samples=[]
        for repeat in range(args.repeat):
            result=subprocess.run([sys.executable,'-m','benchmarks.components','--child',json.dumps(case)],
                                  cwd=ROOT,text=True,capture_output=True,timeout=180)
            if result.returncode:
                (folder/f'FAILED-{repeat}.log').write_text(result.stdout+result.stderr)
                raise RuntimeError('component probe failed: '+name)
            sample=json.loads(result.stdout);samples.append(sample)
            (folder/f'sample-{repeat}.json').write_text(json.dumps(sample,indent=2)+'\n')
        scopes={k:statistics.median(s[k] for s in samples)/args.records for k in
                ('binding_ns','decode_ns','dict_validate_encode_ns','public_bytes_ns','public_dict_ns')}
        scopes.update({'core_'+k:statistics.median(s['core'][k] for s in samples)/args.records for k in
                       ('full_ns','parse_ns','evaluate_ns','serialize_ns')})
        summaries.append(dict(workload=name,records=args.records,samples=args.repeat,median_ns_per_record=scopes,
                              parity=all(s['parity'] for s in samples)))
        (out/'summary.json').write_text(json.dumps(summaries,indent=2)+'\n')
        print(name,scopes,flush=True)

if __name__=='__main__':main()
