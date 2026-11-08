from pathlib import Path
initial=Path(__file__).resolve().parents[1]/'initial'/'plan-check.py'
context={'__file__':str(initial)}
exec(compile(initial.read_text().split("assert rows['T-010']")[0],str(initial),'exec'),context)
rows=context['rows']
for t in ('T-010','T-011','T-101','T-102','T-105','T-106'):assert rows[t][-1]=='VERIFIED'
for t in ('T-103','T-104','T-107'):assert rows[t][-1].startswith('BLOCKED')
for t in ('T-201','T-202','T-203','T-205','T-206'):assert rows[t][-1]=='TODO'
print('PASS: requirement/task/AC/gate references, local links, task-dependency DAG.')
print('PASS: M1 mandatory safety gate is explicitly BLOCKED; unavailable scan is not PASS; M2 not started.')
print('LIMIT: original task-only DAG does not resolve milestone-level T-206 safety-gate conflict; amendment is pending.')
