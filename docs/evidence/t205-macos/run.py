"""Record exact verification commands, output, timestamps and exit status."""
import datetime
import json
import os
from pathlib import Path
import subprocess
import sys
import time
root = Path(__file__).resolve().parents[3]
out = Path(__file__).resolve().parent
name, *command = sys.argv[1:]
start = datetime.datetime.now(datetime.timezone.utc).isoformat()
began = time.monotonic()
with (out / f'{name}.log').open('w') as log:
    log.write(f'UTC: {start}\nCWD: {root}\nCOMMAND: {json.dumps(command)}\n')
    log.flush()
    process = subprocess.run(command, cwd=root, stdout=log, stderr=subprocess.STDOUT)
    log.write(f'\nEXIT: {process.returncode}\n')
record = dict(name=name, command=command, cwd=str(root), utc=start,
              exit_code=process.returncode, seconds=time.monotonic()-began,
              log=f'{name}.log')
with (out / 'runs.jsonl').open('a') as index:
    index.write(json.dumps(record)+'\n')
print(json.dumps(record), flush=True)
sys.exit(process.returncode)
