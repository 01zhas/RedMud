"""Join original timing with corrected memory; do not rewrite raw evidence."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def key(row):
    c=row['case']
    return tuple(c[k] for k in ('workload','engine','input','records','batch_size'))

def main():
    timing=json.loads((ROOT/'baseline/summary.json').read_text())
    memory={key(r):r for r in json.loads((ROOT/'baseline-memory-corrected/summary.json').read_text())}
    assert len(timing)==len(memory)==60
    result=[]
    for row in timing:
        corrected=memory[key(row)]
        assert row['digest']==corrected['digest'] and row['counts']==corrected['counts']
        merged=dict(row)
        for k,v in corrected.items():
            if k.startswith(('rss_','python_traced_')):merged[k]=v
        merged['timing_source']='baseline'
        merged['memory_source']='baseline-memory-corrected'
        result.append(merged)
    for filename in ('baseline-memory-corrected','stream-corrected'):
        for path in (ROOT/filename/'raw').glob('*/rss-*.json'):
            assert json.loads(path.read_text())['rss_source']=='linux-proc-VmHWM'
    (ROOT/'joined-summary.json').write_text(json.dumps(result,indent=2)+'\n')
    for r in result:
        c=r['case']
        if c['input']=='bytes' and c['records']==5000 and c['batch_size']==1000:
            print(c['workload'],c['engine'],round(r['records_per_second']),round(r['batch_p95_ms'],3),round(r['relative_time_range']*100,1),round(r['rss_peak_bytes_median']/1048576,2),round(r['python_traced_peak_bytes']/1024,1))
    print('PASS: 60 cases joined by identity and equivalent digest; corrected Linux memory source verified')

if __name__=='__main__':main()
