# RedMud specification — version 1

Status: APPROVED by user on 2026-11-07; see E-10 in EVIDENCE.md. This is a target contract, not a claim that the
current code satisfies it. Current facts and defects: [EVIDENCE.md](EVIDENCE.md).
Task/test traceability: [TASKS.md](TASKS.md). Approval and decisions: [ROADMAP.md](ROADMAP.md).

## Product and MVP boundary

RedMud performs only Transform: callers supply records and own extraction,
delivery, retries, transactions and orchestration. Polars is an architectural
reference for a Python API over native execution, not a dependency or feature checklist.

The next MVP is a hardened serial engine: existing native expressions, nested
objects/lists, schema/business checks, deterministic per-record results, Python
Processor compatibility, bounded iteration, basic quality/metrics/profiling,
reproducible installation and measurements. Native means Rust evaluates the
entire prepared batch without per-field Python callbacks. It does not mean
zero-copy, SIMD, parallel execution, or a guaranteed speed advantage.

Non-goals: connectors, network I/O, storage, ingestion, schedulers, distributed
execution, query optimizers, registries, automatic Python compilation. Deferred:
Rayon/parallel execution, Arrow/DataFusion/Polars integration, decimals and float
arithmetic, joins/group-by, dependency DAGs, optional schema fields, all-errors
collection in native records, input-wide quality scans, window statistics,
native per-stage/per-expression timings, native heap profiling, Windows wheels.
Preserve existing optional examples without adding their dependencies to runtime.

## Functional requirements and acceptance criteria

| ID | Contract | Objective acceptance (all clauses required) |
|---|---|---|
| FR-001 | Native input and output | bytes/str UTF-8 JSON objects and dicts with string keys produce equivalent values/errors within the defined numeric domain; scalars/arrays as records, malformed JSON/UTF-8, nonfinite values, cycles and unsupported Python objects reject safely; native input is not mutated; array-of-records uses batch API. |
| FR-002 | Prepared native plans | Builder calls produce independent pipelines; prepare is idempotent, cached, consumes no input; invalid schemas, paths, step names and expressions raise safe ValueError before iteration; valid steps run in declaration order in Rust; no eval or Python arithmetic callback. |
| FR-003 | Native expressions | field, literal operands, +, -, *, >, >=, ==, when, list_sum match the numeric/null contract; both conditional branches are validated but only the selected branch is evaluated; checks can surround derive; Python bool coercion of Expr raises TypeError. |
| FR-004 | Nested execution | map_list recursively transforms object elements; dotted paths traverse objects; empty maps/sums succeed; errors identify array indexes; nonobjects and missing/null/wrong-type targets reject only their containing record; no partial value escapes. |
| FR-005 | Schema quality | require implements int, float, number, str, bool, object, list, nullable, min/max, allowed, fields/items under the schema contract below; declared fields required, extra data preserved; configuration errors differ from record failures. |
| FR-006 | Python mode | Retain Processor parse/transform, pre/post Rule, warn/reject and custom transform_batch; dataclass parsing works; custom batch order/length checked; scalar fallback is configurable and requires pure hooks; callback failures are isolated; callbacks are never marketed as native. |
| FR-007 | Results and errors | Every consumed record has a classified internal outcome; collect returns one result per record in order with stable index; errors carry code/path/stage/message, failed value=None; warnings may coexist with ok; messages omit payloads and exception text by default. |
| FR-008 | Error policies | collect/raise/skip conform across execution modes as specified below, including counters, input indexes, scalar calls, empty and mixed batches, and callback exceptions. |
| FR-009 | Batching and streaming | Batch APIs materialize only the supplied finite batch; iterator APIs buffer at most configured batch_size records, yield before exhaustion, keep global indexes and do not retain past results; invalid batch size fails before input consumption. |
| FR-010 | Metrics and quality | snapshot reports processed/status/error counters, throughput with defined clock, batch duration/size summary; all consumed rows count under every policy; selected accepted-output field profiles track missing/null and numeric count/min/max/mean/stddev without retaining inputs; storage cardinality is bounded by configuration, not stream length. |
| FR-011 | Diagnostic profiling | Both modes expose bounded cProfile/tracemalloc reports; records counts processed inputs including skip failures; consumes at most max_records; validates arguments, cleans up on exceptions and preserves caller-owned tracing; explicitly labels Python-only allocations and non-comparable native detail. |
| FR-012 | Packaging and documentation | Install wheel and build/install sdist in isolated environments; import native extension; execute native and dataclass examples; English/Russian instructions identify mode boundaries, migration and limitations; no mandatory external services or third-party Python runtime packages. |

## Non-functional requirements

| ID | Requirement and acceptance |
|---|---|
| NFR-001 | Numeric correctness: no integral input silently becomes float; checked i64 intermediates; deterministic order; no bool-as-int. Boundary tests cover i64/u64 limits, beyond-range integers, 2^53, equality and under/overflow. |
| NFR-002 | Resource behavior: bounded stream storage for fixed batch size, plan and configured fields; finite nesting limits checked before unsafe recursion; malformed/deep input cannot panic/abort the process in tests. Bounds do not promise constant bytes for an arbitrarily large record or caller-owned outputs. |
| NFR-003 | Safety: no application unsafe code, eval or unsafe deserialization; no payloads in default errors/metrics; dependencies and licenses reviewed against lockfile; advisory checks report failures/unavailable feeds without declaring security clearance. |
| NFR-004 | Measurable performance: equivalent-work baselines report throughput, batch p50/p95 latency, peak RSS, traced Python allocations separately, batch-size and metrics effects, and boundary overhead. No speed claim or numerical regression threshold until repeated measurements and user approval. |
| NFR-005 | Portability: proposed MVP matrix CPython 3.11/3.12/3.13 on Linux x86_64 and macOS arm64; run tests against installed wheels; source-build path documented. Support beyond this matrix is UNKNOWN until verified. No free-threaded Python claim. |
| NFR-006 | Maintainability: preserve useful tested code; keep serde/serde_json core independent from PyO3/Python; formatter, Rust lint and focused Python lint pass; regressions plus focused acceptance tests pass; no unexplained dependency additions. |

## Public API and semantics (proposed stable surface)

Native: Pipeline(on_error='collect', metrics=True, output_fields=()),
require(schema), check(name, expr, message=...), derive(name, expr),
map_list(path, pipeline), prepare(), run_one(record), run_batch(records),
run_iter(records, batch_size=1000), snapshot(), profile(records,max_records=1000,top=15).
Expressions: field(path), list_sum(path, field), when(condition, yes, no); literal
operands automatically lifted. Expr is exported; its mutable tree/internal
constructor and Pipeline._steps/NativePlan are not stable APIs.

Python: Processor, Runtime(processor, Settings(...), input_rules=(), output_rules=()),
process_one/process_batch/process_iter, snapshot, profile; existing Rule, Issue,
RecordResult, ProcessingError, ProfileReport, BatchSizeMismatch remain available.
Do not remove existing Settings fields or Metrics.prometheus_text.

```python
from redmud import Pipeline, field as F, list_sum
item = (Pipeline().require({'price': 'int', 'quantity': 'int'})
        .check('positive_quantity', F('quantity') > 0)
        .derive('total', F('price') * F('quantity')))
cart = Pipeline().map_list('items', item).derive('total', list_sum('items', 'total'))
r = cart.run_one(b'{"items":[{"price":1000,"quantity":3}]}')
assert r.ok and r.value['total'] == 3000
```

```python
from redmud import Processor, Runtime
class ExistingLogic(Processor):
    def transform(self, row):
        return {'total': row['price'] * row['quantity']}
r = Runtime(ExistingLogic()).process_one({'price': 1000, 'quantity': 3})
assert r.ok and r.value == {'total': 3000}
```

### Schema, paths and numbers

Schema is a map of nonempty dotted paths to type strings or constraint objects.
Reject empty path segments; no key escaping or input array-index syntax in MVP.
Error output uses dotted keys and [index]; keys containing path punctuation are
preserved as data but not addressable unambiguously. derive names are nonempty
literal keys without path punctuation; duplicate derive overwrites deliberately.
Rule names are nonempty ASCII letters/digits/underscore, unique per plan scope;
native rule codes must not collide with reserved engine codes.

Allowed constraint keys: type, nullable, min, max, allowed, fields, items; unknown
keys fail prepare. type may be omitted only with fields (object) or items (list),
unambiguously. min/max apply to int or float with bounds of that same type;
min<=max; no min/max on number in MVP. fields only on object, items only on list;
allowed is a nonempty list of values compatible with type/nullable. Validate
constraint combinations recursively, including limits. All configured fields
are required even when nullable=true. Nullable allows null through schema rules;
a later arithmetic operation still rejects null. No coercion/defaults.

Proposed D-01: native integral inputs/literals/pass-through are exact in
[-2^63, 2^64-1]; anything outside rejects with numeric_range, never float.
int schema/arithmetic/sums/order comparisons accept signed i64 only. float means
finite f64, number either supported integer or finite f64 (schema check only).
No float arithmetic, implicit numeric promotion, division, or rounding in MVP.
Mixed numeric representation equality is false (1 != 1.0); bool differs from
integer; same-kind JSON equality is structural, object key order ignored. +/-/*
evaluate left then right with checked intermediate values; sum uses list order
and starts at i64 zero. Missing field rejects even for equality; explicit null
can equal null. when condition/check must be bool; a nonbool is invalid_type.

Proposed D-02: for runtime numeric constraints, compare only the matching type;
wrong numeric representation rejects, never approximate i64 as f64. These
schema/equality restrictions change permissive current behavior: require
migration notes and explicit contract approval before implementation.

### Results, policies and lifecycle

ok means status='ok'. Schema/business failures are rejected; parse, unsupported
input, arithmetic/type/overflow and callback failures are error. Native returns
its first error per record; Python may retain multiple Rule issues/errors.
Stages: parse, validation, transform; Python retains legacy input/output quality
and transform_batch stages as documented aliases. Errors point to the offending
field where known; rule failures point to current object scope. Overflow points
to derive target or sum target when no single input is at fault. Message is safe
and not guaranteed stable; code/path/stage are contractual. Callback rule
messages are developer-supplied and must not interpolate secrets by default.

Proposed D-03: process the full finite batch, finalize all counters/profiles and
indexes, then raise ProcessingError containing the first failed result in input
order. No batch results returned on raise; previous iterator batches may already
have been yielded. skip filters batch/iterator failures only; scalar returns its
outcome. Index counts all consumed inputs, including skipped/failed, starts at 0
per instance and continues across calls. Iterator-source exceptions propagate;
there is no record to classify for a next() failure and no retry/rollback promise.

Builders copy definition data; returned pipelines own fresh counters/index and
cached plans. Nested child settings/counters are not executed; only its steps
are embedded. Instances are single-caller, not thread-safe; callbacks must be
pure where fallback can replay. Python transform input mutation remains caller
responsibility; native mode never mutates caller dictionaries.

Native metrics=False disables counters/timing but not requested field profiles;
Runtime timing_sample_every=0 disables stage timing, not counters. Output profiles
are accepted-only, sampled as configured; errors_by_code counts error entries,
not distinct bad records. Throughput uses wall time since first batch start,
including idle. Diagnostic timing is not a production benchmark. Metrics must
use fixed storage for batch sizes and type labels (exact snapshot shape approved
in T-010 before the replacement). Resource limit proposal D-04: data nesting and
plan/expression depth default 64, root depth=1; choose enforcement and combined
recursion checks in T-202, and verify boundary inputs in subprocesses.

## Completion and scope control

GOV-001: initial planning artifacts must pass reference/dependency consistency
checks, contain an auditable baseline and explicitly pending decisions; no app
code modifications. Current deliverable ends at user approval.

GOV-002: implementation follows AGENTS.md gates; each task requires requirement
links, passing acceptance evidence and current regression evidence. A milestone
requires a report and any specified approval before advancement. Amend this
specification before architecture/contract/scope changes. Legacy docs are
historical where they disagree; approval of this draft does not retroactively
verify the implementation. No requirement is fully VERIFIED by this planning pass.


Amendment A-01 (approved by user “Продолжай работу”, E-14): move T-206
from M2 to the end of M1 to remove the shared G-SAFE dependency conflict.
No functional requirement, dependency boundary or acceptance criterion changes.

Amendment A-02 (user: “Продолжай пока что не зависимые блокеры задач далее из дома я все выполню”):
permit independent local M3 fixture/measurement work using verified Linux M2
evidence while T-205 hosted/macOS acceptance stays BLOCKED for the user to run.
No platform/release gate is waived; performance-budget approval T-304 and M4
entry remain explicit checkpoints.
