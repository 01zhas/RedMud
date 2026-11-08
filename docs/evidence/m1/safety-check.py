"""Focused M1 safety checks; depth-limit enforcement and adversarial fuzzing are M2."""
import subprocess,sys
from pathlib import Path
for depth in (64,256,1000):
    code=f'''from redmud import Pipeline
raw=b'{{"x":'+b'['*{depth}+b'0'+b']'*{depth}+b'}}'
r=Pipeline().run_one(raw)
print("depth",{depth},"outcome",r.status)
'''
    p=subprocess.run([sys.executable,'-c',code],text=True,capture_output=True,timeout=15)
    print(p.stdout,p.stderr)
    assert p.returncode==0,p.returncode
core=Path('crates')
assert not any('unsafe {' in p.read_text() for p in core.rglob('*.rs'))
print('PASS: bounded subprocess fixtures terminate without process abort; no application unsafe block.')
print('NOT VERIFIED: specified depth-64 rejection boundary, unbounded-stream memory, fuzzing, advisory/platform gates (M2).')
