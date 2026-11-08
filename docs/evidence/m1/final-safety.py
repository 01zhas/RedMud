"""M1 safety rerun after PyO3 security remediation; depth policy enforcement is M2."""
from pathlib import Path
import re
import subprocess
import sys

for depth in (64,256,1000):
    code = f'''from redmud import Pipeline
raw=b'{{"x":'+b'['*{depth}+b'0'+b']'*{depth}+b'}}'
r=Pipeline().run_one(raw)
assert r.ok
print("depth probe {depth}: process survived")
'''
    subprocess.run([sys.executable,'-c',code],check=True,timeout=15)
code = '''from redmud import Pipeline
p=Pipeline()
assert p.run_one(b'{"x":18446744073709551617}').errors[0].code=='numeric_range'
assert p.run_one(b'{').errors[0].code=='invalid_json'
cycle={};cycle['x']=cycle
assert p.run_one(cycle).errors[0].code=='invalid_input'
assert p.run_one({'x':1}).ok
print('range, malformed, cycle and record isolation probes passed')
'''
subprocess.run([sys.executable,'-c',code],check=True,timeout=15)
for p in Path('crates').rglob('*.rs'):
    assert not re.search(r'\bunsafe\s*(?:\{|impl\b|fn\b|trait\b)',p.read_text()),str(p)
for p in Path('python/redmud').glob('*.py'):
    assert not re.search(r'\b(?:eval|exec)\s*\(',p.read_text()),str(p)
print('PASS: scoped subprocess safety/source checks; no claim of adversarial fuzz/depth-64 enforcement (M2).')
