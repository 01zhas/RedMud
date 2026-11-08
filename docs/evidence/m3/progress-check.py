"""Check current ledger, reference envelopes, source snapshots and links."""
import hashlib
import json
from pathlib import Path
import re
root=Path(__file__).resolve().parents[3]
initial=root/'docs/evidence/initial/plan-check.py'
context={'__file__':str(initial)}
exec(compile(initial.read_text().split("assert rows['T-010']")[0],str(initial),'exec'),context)
rows=context['rows'];graph=context['graph']
assert len(rows)==24
for task in ('T-301','T-302','T-303'):
    assert rows[task][-1]=='VERIFIED'
    assert all(rows[dep][-1]=='VERIFIED' for dep in graph[task])
assert all(rows[t][-1].startswith('BLOCKED') for t in ('T-205','T-304'))
assert all(rows[t][-1]=='TODO' for t in ('T-401','T-402','T-501','T-502'))
assert not any(row[-1]=='IN_PROGRESS' for row in rows.values())
folder=root/'docs/evidence/m3'
joined=json.loads((folder/'joined-summary.json').read_text())
budgets=json.loads((folder/'candidate-budgets.json').read_text())
assert len(joined)==len(budgets)==60
for baseline,budget in zip(joined,budgets):
    assert not budget['approved']
    for stat in ('min','median','max'):
        assert baseline['call_seconds_'+stat]==budget['reference_call_seconds_'+stat]
        assert baseline['rss_peak_bytes_'+stat]==budget['reference_rss_bytes_'+stat]
    assert baseline['process_samples']==5 and baseline['rss_process_samples']==3
components=json.loads((folder/'components/summary.json').read_text())
assert len(components)==6 and all(row['parity'] and row['samples']==5 for row in components)
for name in ('baseline','baseline-memory-corrected','stream','stream-corrected','components'):
    meta=json.loads((folder/name/'environment.json').read_text())
    for source,digest in meta['sources'].items():
        assert hashlib.sha256((folder/name/'source'/source).read_bytes()).hexdigest()==digest,(name,source)
for document in ('docs/benchmarks.md','docs/performance-proposal.md','docs/home-verification.ru.md'):
    p=root/document
    for link in re.findall(r'\[[^\]]*\]\(([^)]+)\)',p.read_text()):
        if '://' not in link:assert (p.parent/link.split('#')[0]).exists(),(document,link)
print('PASS: 20 requirements / 24 tasks, acyclic links; T-301/302/303 VERIFIED; T-205/304 BLOCKED; M4/M5 TODO.')
print('PASS: 60 timing/corrected-memory envelopes match, unapproved; six component fixtures have actual parity evidence.')
print('PASS: exact measured source snapshots match recorded hashes; methodology/proposal/home local links resolve.')
print('No CI, approval, portable speed or release completion inferred.')
