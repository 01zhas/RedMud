"""Validate current references/statuses without changing historical audit probes."""
from pathlib import Path
import json
initial=Path(__file__).resolve().parents[1]/'initial'/'plan-check.py'
context={'__file__':str(initial)}
exec(compile(initial.read_text().split("assert rows['T-010']")[0],str(initial),'exec'),context)
rows=context['rows']
for task in ('T-201','T-202','T-203'):
    assert rows[task][-1]=='VERIFIED'
    for dependency in context['graph'][task]:assert rows[dependency][-1]=='VERIFIED'
assert rows['T-205'][-1].startswith('BLOCKED')
assert all(rows[t][-1]=='TODO' for t in ('T-301','T-302','T-303','T-304'))
matrix=json.loads(Path('docs/evidence/m2/linux-package-matrix.json').read_text())
assert {d['version'].rsplit('.',1)[0] for d in matrix}=={'3.11','3.12','3.13'}
assert all(d['system']=='Linux' and d['machine']=='x86_64' and d['result'].startswith('PASS') for d in matrix)
rust=json.loads(Path('docs/evidence/m2/security/rust-advisories.json').read_text())
assert not rust['vulnerabilities']['found'] and not rust['warnings'] and not rust['settings']['ignore']
python=json.loads(Path('docs/evidence/m2/security/python-advisories.json').read_text())
assert all(not d['vulns'] and not d.get('skip_reason') for d in python['dependencies'])
print('PASS: 20 requirements, 24 tasks, acceptance/gate references and local links; acyclic task dependencies.')
print('PASS: T-201/T-202/T-203 verified; three Linux Python package versions verified; current advisory reports clean.')
print('PASS: T-205 explicitly BLOCKED on actual hosted/macOS execution; M3 not started, no unavailable check labelled PASS.')
