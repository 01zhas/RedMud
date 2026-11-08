"""Local YAML/contract checks only; this does not simulate GitHub CI execution."""
import json
import re
from pathlib import Path
from importlib.metadata import distribution
import yaml

text=Path('.github/workflows/ci.yml').read_text()
workflow=yaml.safe_load(text)
assert set(workflow['on'])=={'push','pull_request','workflow_dispatch'}
assert workflow['permissions']=={'contents':'read'}
job=workflow['jobs']['verify']
matrix=job['strategy']['matrix']
assert matrix=={'os':['ubuntu-24.04','macos-15'],'python':['3.11','3.12','3.13']}
assert not job['strategy']['fail-fast']
assert 'platform.machine()' in text and 'arm64' in text
assert 'scripts/package_check.py' in text and 'scripts/security.sh' in text
pins={p['repository']:p['sha'] for p in json.loads(Path('docs/evidence/m2/ci-action-pins.json').read_text())}
for job in workflow['jobs'].values():
 for step in job['steps']:
  if 'uses' not in step:continue
  name,sha=step['uses'].split('@')
  assert re.fullmatch('[0-9a-f]{40}',sha) and pins[name]==sha
  if name=='actions/checkout':assert step['with']['persist-credentials'] is False
print('PASS: YAML parsed; six platform/Python jobs, read-only permissions, exact upstream commit pins, package/security commands present.')
print('NOT RUN: GitHub runner execution; local YAML checks do not establish platform support.')
d=distribution('PyYAML')
Path('docs/evidence/m2/ci-parser-tool.json').write_text(json.dumps({'name':'PyYAML','version':d.version,'license':d.metadata.get('License'),'scope':'preinstalled local YAML parser only; no new project dependency'},indent=2)+'\n')
for f in d.files:
 if 'license' in str(f).lower() and Path(d.locate_file(f)).is_file():
  Path('docs/evidence/m2/PyYAML-LICENSE.txt').write_bytes(Path(d.locate_file(f)).read_bytes())
