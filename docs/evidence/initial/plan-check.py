"""Planning evidence validator; no product behavior is tested here."""
import hashlib, re
from pathlib import Path
root=Path(__file__).resolve().parents[3]
names=['SPEC.md','ROADMAP.md','TASKS.md','AGENTS.md','EVIDENCE.md']
texts={n:(root/n).read_text() for n in names}
spec=texts['SPEC.md'];tasks=texts['TASKS.md'];road=texts['ROADMAP.md']
requirements=re.findall(r'^\| ((?:FR|NFR)-\d{3}) \|',spec,re.M)+re.findall(r'^(GOV-\d{3}):',spec,re.M)
assert len(requirements)==len(set(requirements))==20, requirements
rows={}
for line in tasks.splitlines():
    parts=[p.strip() for p in line.split('|')]
    if len(parts)>3 and re.fullmatch(r'T-\d{3}',parts[1]):
        tid=parts[1];assert tid not in rows,tid
        rows[tid]=parts[2:-1]
        assert re.match(r'^(TODO|IN_PROGRESS|BLOCKED|VERIFIED)\b',rows[tid][-1]),tid
assert all(re.search(r'^\| '+rid+r' \|',tasks,re.M) for rid in requirements),'missing traceability row'
# Every referenced task/requirement resolves to a declaration.
for name,text in texts.items():
    for tid in re.findall(r'\bT-\d{3}\b',text): assert tid in rows,(name,tid)
    for rid in re.findall(r'\b(?:FR|NFR|GOV)-\d{3}\b',text): assert rid in requirements,(name,rid)
# Dependencies occupy the second content column in each task table.
graph={tid:set(re.findall(r'T-\d{3}',cols[1])) for tid,cols in rows.items()}
visiting=set();done=set()
def visit(tid):
    assert tid not in visiting,('cycle',tid)
    if tid in done:return
    visiting.add(tid)
    for dep in graph[tid]:visit(dep)
    visiting.remove(tid);done.add(tid)
for tid in graph:visit(tid)
# Planned acceptance labels all have owning task rows; no runnable test claim.
acceptance=set(re.findall(r'AC-\d{3}',tasks))
for ac in acceptance:
    assert 'T-'+ac[3:] in rows,ac
    assert ac in ' '.join(rows['T-'+ac[3:]]),(ac,'missing owner acceptance')
for text in texts.values():
    for ac in re.findall(r'AC-\d{3}',text): assert ac in acceptance,ac
milestones=set(re.findall(r'^\| (M\d) —',road,re.M))
assert milestones=={'M0','M1','M2','M3','M4','M5'}
gates=set(re.findall(r'\*\*(G-[A-Z]+):\*\*',road))
for text in texts.values():
    for gate in re.findall(r'\bG-[A-Z]+\b',text):assert gate in gates,gate
links=0
for name,text in texts.items():
    for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)',text):
        if '://' in target:continue
        path=root/target.split('#')[0]
        assert path.exists(),(name,target)
        links+=1
assert rows['T-010'][-1].startswith('BLOCKED')
assert [t for t,c in rows.items() if c[-1]=='VERIFIED']==['T-001','T-002']
assert 'IN_PROGRESS' not in [c[-1] for c in rows.values()]
print('PASS: 5 documents; 20 unique requirements; '+str(len(rows))+' unique tasks; 6 milestones; '+str(len(gates))+' gates.')
print('PASS: all requirement/task/AC/gate references resolve; all 20 requirements have traceability rows.')
print('PASS: task dependencies acyclic (explicit M4 deferral is a documented alternative dependency).')
print(f'PASS: {links} local document/artifact links resolve.')
print('PASS: only planning tasks VERIFIED; implementation approval BLOCKED; no implementation task IN_PROGRESS.')
print('NOTE: structural consistency is not proof of semantic correctness or implemented capabilities.')
