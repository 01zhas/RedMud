"""Final structural/status validation after A-01 and T-206 remediation."""
from pathlib import Path
import json
initial=Path(__file__).resolve().parents[1]/'initial'/'plan-check.py'
context={'__file__':str(initial)}
exec(compile(initial.read_text().split("assert rows['T-010']")[0],str(initial),'exec'),context)
rows=context['rows']
m1=('T-010','T-011','T-101','T-102','T-103','T-104','T-105','T-106','T-107','T-206')
for t in m1:
    assert rows[t][-1]=='VERIFIED',t
    for dep in context['graph'][t]:assert rows[dep][-1]=='VERIFIED',(t,dep)
for t in ('T-201','T-202','T-203','T-205'):assert rows[t][-1]=='TODO'
report=json.loads(Path('docs/evidence/m1/security/rust-advisories.json').read_text())
assert not report['vulnerabilities']['found'] and not report['warnings']
assert not report['settings']['ignore']
python=json.loads(Path('docs/evidence/m1/security/python-advisories.json').read_text())
assert len(python['dependencies'])==2
assert all(not p['vulns'] and not p.get('skip_reason') for p in python['dependencies'])
print('PASS: 20 requirement IDs, 24 task IDs, AC/gate references and local artifact links resolve; task DAG acyclic.')
print('PASS: all 10 M1 tasks and their dependencies VERIFIED; A-01 removes the milestone safety dependency conflict.')
print('PASS: mandatory advisory reports exist with no findings/skips/ignores; M2 tasks remain TODO.')
print('Scope: local M1 acceptance only; platform/depth/cardinality/performance work remains as approved.')
