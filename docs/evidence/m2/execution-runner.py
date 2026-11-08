import subprocess,sys,json,hashlib,time
from pathlib import Path
root=Path('/workspace/redmud'); task=sys.argv[1];cmd=sys.argv[2]
folder=root/'docs/evidence/m2'; folder.mkdir(exist_ok=True)
seq=len(list(folder.glob('run-*.log')))+1
p=subprocess.run(['bash','-c','. "$HOME/.cargo/env"; '+cmd],cwd=root,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
log=folder/f'run-{seq:03d}-{task}.log'
log.write_text('$ '+cmd+'\n'+p.stdout+f'\nEXIT_CODE={p.returncode}\n')
files=[p for base in ('crates','python','tests','scripts') for p in (root/base).rglob('*') if p.is_file() and '__pycache__' not in p.parts]
identity=hashlib.sha256(''.join(str(p.relative_to(root))+hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files)).encode()).hexdigest()
with (folder/'runs.jsonl').open('a') as f:f.write(json.dumps(dict(task=task,command=cmd,exit_code=p.returncode,log=str(log.relative_to(root)),source_sha256=identity,time_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())))+'\n')
print(log.name,'EXIT',p.returncode);print(p.stdout[-7000:]);sys.exit(p.returncode)
