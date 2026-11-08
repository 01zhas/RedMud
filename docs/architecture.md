# Architecture and API reference

redmud-core depends on serde/serde_json (raw_value feature) and contains typed Expr/Step/Plan,
one-time plan/schema preparation, recursive record validation, checked arithmetic and per-record error isolation.
redmud-python uses PyO3, converts byte batches into owned Rust buffers and
releases the GIL during evaluation. No unsafe application code. NativePlan is
internal. python/redmud exposes the builder, compatible Python runtime, metrics,
quality and result types. Input JSON uses serde_json RawValue to inspect integral tokens before conversion;
this extra traversal prioritizes exactness over unmeasured speed. Borrowed values
are used for execution traversal; derived
values and record results are owned. No custom query optimizer is warranted.

Pipeline: require(schema), check(name, expr, message=...), derive(name, expr),
map_list(path, pipeline), prepare(), run_one(record), run_batch(records),
run_iter(records, batch_size=1000), snapshot(), profile(records,max_records=1000).
Expression API: field(path); +, -, *, >, >=, ==; list_sum(path, field);
when(condition, yes, no) evaluates only the chosen branch. Python boolean
coercion is forbidden. Fields use dotted object paths, no array-index syntax.
Derived names are literal top-level keys. Configuration is trusted developer
input, not a security boundary for executing arbitrary plans from users.

Runtime: process_one, process_batch, process_iter, snapshot, profile.
Processor: parse, transform, transform_batch, input_rules, output_rules.
Settings controls batching, fallback, policies, sampled timing, field profiling,
and explicit opt-in exception details. RecordResult additionally retains legacy
status/issues/error_stage/error_type/error_message. Error is an immutable
code/path/stage/message object. Python errors have empty paths unless specified
by developer rules. Failed results have no partially transformed value.

## Numeric and null semantics
Arithmetic, ordering and sums accept only signed i64, with checked intermediate
operations, in expression-tree order. No implicit float conversion, division,
or rounding. Equality compares JSON values (including null); other numeric
operations reject null/bool. `number` schema permits JSON numbers but arithmetic
still requires i64. Missing and explicit null are different errors. Null is
accepted in schema only with nullable=true. No coercion. Schema numeric bounds match the declared int/float type exactly; no mixed
comparisons, and no bounds for number. Input integers outside i64/u64 reject.

## Limitations and next work
1. Replace JSON output envelopes and dict serialization with a carefully tested
   direct PyO3 conversion; benchmark before accepting the added complexity.
2. Extend fuzz coverage and finish platform CI before production. M2 adds seeded
   arithmetic/nested invariants and depth-64 guards for data and definitions.
3. Add sampled native stage timing and memory/RSS benchmarks; currently only
   batch native duration is exposed. No per-expression production clocks.
4. Add parallel execution only after workload evidence supports a rayon threshold.
   Native work releases the GIL but is serial; callbacks always use Python.
5. Broaden numeric operations, optional schemas, and aggregate input-quality
   statistics. Selected output profiles currently cover accepted outputs only.

Streaming bounds records buffered, not bytes or expansion size of a single row.
run_batch intentionally materializes its supplied iterable. Metrics batch-size
histograms now have six fixed buckets and exact count/sum/min/max scalars. Profiles
use float summaries and are descriptive, not financial calculation outputs.


T-206 security update: PyO3 0.29.3 replaces vulnerable 0.23.5; the batch binding
uses Python.detach with owned buffers and gil_used=true on the module. This
retains the serial native execution/public Python API and does not introduce
free-threaded support. Original upstream Rust dependency notices are bundled
by maturin in wheel and sdist; security tooling remains outside runtime deps.


M2 depth enforcement: root JSON value has depth 1, scalar leaves count, maximum
64 for native inputs/outputs/literals/allowed values. Plan/expression/schema
semantic recursion uses a combined budget 64. Transport wrappers use preflight
264, then semantic prepare checks; see docs/contracts.md. serde_json RawValue
syntax skipping is iterative and conversion stops before constructing level 65.
Native oversized output rejects with depth_limit at transform. Arbitrary Python
callbacks remain responsible for their own recursion/data structures.

Type-profile labels are fixed builtins plus other. Storage cardinality is fixed
by plan, configured fields/rules and bucket set; no raw records are retained.
Byte width/output expansion are not capped, and float summaries are descriptive.
