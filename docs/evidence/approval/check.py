from pathlib import Path
initial=Path(__file__).resolve().parents[1]/"initial"/"plan-check.py"
context={"__file__":str(initial)}
source=initial.read_text().split("assert rows['T-010']")[0]
exec(compile(source,str(initial),"exec"),context)
assert context["rows"]["T-010"][-1].startswith("TODO")
assert all(cols[-1] != "IN_PROGRESS" for cols in context["rows"].values())
print("PASS: requirement/task/acceptance/gate references, dependency cycles and local links checked.")
print("PASS: M0 approval recorded; T-010 TODO, not prematurely VERIFIED; no implementation started.")
