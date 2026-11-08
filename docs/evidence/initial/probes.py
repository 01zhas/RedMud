import json
from redmud import Pipeline, Processor, Runtime, Settings, ProcessingError, field as F
for schema in ({"x":"unknown"},{"x":{"type":"int","min":"bad"}},{"x":{"type":"int","mni":1}}):
    try:
        p=Pipeline().require(schema).prepare()
        print("config",repr(schema),"prepare=ACCEPTED","result",p.run_one({"x":0}))
    except Exception as e: print("config rejected",type(e).__name__)
class Identity(Processor):
    def transform(self, row): return row
for engine,run in [(Pipeline(on_error="raise").require({"x":"int"}),"run_batch"),(Runtime(Identity(),Settings(on_error="raise")),"process_batch")]:
    try: getattr(engine,run)([b"{",{"x":1},{"x":2}])
    except ProcessingError: pass
    print(type(engine).__name__,"processed",engine.snapshot()["metrics"]["processed"],"next_index",getattr(engine,"_index"))
for raw in (b'{"n":18446744073709551616}',{"n":18446744073709551616}):
    r=Pipeline().run_one(raw)
    print("large_integer",type(raw).__name__,r.ok,repr(r.value))
for mode in ("native","python"):
    engine=Pipeline(on_error="skip") if mode=="native" else Runtime(Identity(),Settings(on_error="skip"))
    report=engine.profile([b"{",{"x":1}],max_records=2)
    print("profile_skip",mode,"report_records",report.records,"processed",engine.snapshot()["metrics"]["processed"])
r=Pipeline().derive("v",F("x")+1).run_one({"x":None})
print("expression_error",r.errors)
