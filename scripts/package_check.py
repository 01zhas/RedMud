"""G-PKG local runner: wheel and sdist installations in independent clean venvs.

Uses the current interpreter's pinned maturin to build for --python. Tests and
examples run outside the repository; imports must resolve inside each venv.
"""
import argparse
import email
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--python',default=sys.executable)
parser.add_argument('--output',type=Path,default=Path('target/package-check'))
args=parser.parse_args()
repo=Path(__file__).resolve().parents[1]
def run(command, **kwargs):
    print('+', ' '.join(map(str,command)),flush=True)
    subprocess.run(list(map(str,command)),check=True,**kwargs)
info=json.loads(subprocess.check_output([args.python,'-c',
    'import sys,platform,json; print(json.dumps(dict(version=platform.python_version(), system=platform.system(), machine=platform.machine())))'],text=True))
out=(repo/args.output/f'{info["system"]}-{info["machine"]}-{info["version"]}').resolve()
out.mkdir(parents=True,exist_ok=True)
run([sys.executable,'-m','maturin','build','--release','--locked','--interpreter',args.python,'--out',out/'wheel'],cwd=repo)
run([sys.executable,'-m','maturin','sdist','--out',out/'sdist'],cwd=repo)
artifacts=[next((out/'wheel').glob('*.whl')),next((out/'sdist').glob('*.tar.gz'))]
with zipfile.ZipFile(artifacts[0]) as archive:
    metadata=email.message_from_bytes(archive.read(next(n for n in archive.namelist() if n.endswith('/METADATA'))))
    assert not metadata.get_all('Requires-Dist'), 'Unexpected Python runtime dependency'
    assert any(n.endswith('THIRD_PARTY_NOTICES.md') for n in archive.namelist())
for artifact in artifacts:
    with tempfile.TemporaryDirectory(prefix='redmud-install-') as temporary:
        temp=Path(temporary)
        run([args.python,'-m','venv',temp/'venv'])
        python=temp/'venv'/'bin'/'python'
        work=temp/'work';work.mkdir()
        env=os.environ.copy();env.pop('PYTHONPATH',None)
        if artifact.name.endswith('.tar.gz'):
            run([python,'-m','pip','install','maturin==1.16.0'],cwd=work,env=env)
        run([python,'-m','pip','install','--no-deps','--no-build-isolation',artifact],cwd=work,env=env)
        run([python,'-I','-c',
             'import pathlib,sys,redmud,redmud._native; '
             'p=pathlib.Path(sys.prefix).resolve(); '
             'assert pathlib.Path(redmud.__file__).resolve().is_relative_to(p); '
             'assert pathlib.Path(redmud._native.__file__).resolve().is_relative_to(p); '
             'print(redmud.__file__);print(redmud._native.__file__)'],cwd=work,env=env)
        run([python,'-I','-m','unittest','discover','-s',repo/'tests','-t',repo,'-v'],cwd=work,env=env)
        for example in ('native_cart.py','cart.py'):
            run([python,'-I',repo/'examples'/example],cwd=work,env=env)
info['artifacts']=[str(a.relative_to(repo)) for a in artifacts]
info['result']='PASS: wheel and sdist installs, installed imports, full Python suite and examples'
(out/'result.json').write_text(json.dumps(info,indent=2)+'\n')
print(json.dumps(info,indent=2))
