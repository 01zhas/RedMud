# Approved contracts — M1 decision record (T-010)

User approved SPEC/ROADMAP version 1 in E-10 and instructed implementation.
This table resolves details within those approved contracts; no new scope.

| Failure | Code | Error stage | Record status |
|---|---|---|---|
| Malformed JSON, invalid UTF-8, nonfinite JSON number | invalid_json | parse | error |
| Unsupported Python value, cyclic containers, non-string dict key | invalid_input | parse | error |
| Integral input outside [-2^63,2^64-1] | numeric_range | parse | error |
| Required schema/map target missing, null, wrong type | missing_field / null_value / invalid_type | validation | rejected |
| Schema min/max or allowed fails | numeric_constraint / not_allowed | validation | rejected |
| Business predicate false | developer rule name | validation | rejected |
| Expression missing/null/wrong type, nonbool predicate/condition | missing_field / null_value / invalid_type | transform | error |
| Checked i64 operation overflows | overflow | transform | error |
| Python hook exception | callback_error (default JSON decode: invalid_json) | parse, transform, input_quality, output_quality, transform_batch | error |

All engine codes in this table plus depth_limit are reserved native rule names.
Config failures raise ValueError with a safe fixed message; they have no record
index/outcome and consume no input. Messages are not a machine contract. Error
paths identify offending fields, rule object scopes, or overflow derive/sum
targets; schema fields are tested in sorted order for deterministic first errors.
Missing fields and null values are distinct. Rule names: ASCII alphanumeric or
underscore, nonempty and unique in their scope. Extra AST keys are invalid.

Python Issue.stage remains input/output. Structured Rule Error.stage is
validation; RecordResult.error_stage retains the legacy hook stage for hook
exceptions. Arbitrary parser exceptions stay callback_error; JSONDecodeError or
UnicodeDecodeError become invalid_json only for the default Processor.parse.
Processor-defined warning messages are trusted developer text.

D-01/D-02 accepted as SPEC: exact signed/unsigned 64-bit pass-through, i64-only
arithmetic, type-sensitive equality and bounds; larger integral tokens reject.
D-03 accepted: process and account the full batch, then raise first failure.
D-04 accepted: future depth limit 64 (M2 enforcement); future batch buckets
0/1/2–63/64–255/256–999/1000+, count/sum/min/max; fixed type labels
bool/int/float/str/list/tuple/dict/Decimal/other. Snapshot keeps batch_sizes as a
bucket-key map, adds batch_size_summary; T-203 implements, not M1.
D-05 accepted: GitHub Actions configuration is the chosen future CI host design;
workspace has no Git repository/remote; relevant hosted-job access is unknown. Actual runner
availability remains UNKNOWN and must be resolved/evidenced in T-205. This does
not block local M1 work or authorize creating/publishing an external repository.

Native and Python results remain distinct implementations with shared contract
tests. Numeric safety, not a new query IR or direct FFI conversion, is M1 scope.


## T-202 enforced recursion semantics

Native data depth counts every JSON value (including scalar leaves), root=1;
maximum 64, for both input and output. Input over-limit returns depth_limit at
parse; derived output over-limit returns it at transform, with no partial value.
Dicts are checked before json.dumps; JSON bytes stay in Rust. serde_json RawValue
syntax scanning is iterative (verified upstream ignore_value); recursive value
conversion stops before level 65. The bound is on depth, not bytes/width.

Plans, schema nodes and expression nodes share a semantic stack budget: root
plan/root expression=1; nested child plans add one; expression children and
schema children add one. Expressions/schemas attached to a plan start at that
plan's current depth. Literal JSON values independently obey data depth 64;
final transformed records are checked too. Transport-only steps arrays/step
objects are not semantic nodes: preflight caps their JSON tree at 264 levels
(4*64+8) before serialization/typed deserialization. Combined evaluation budget
is checked at prepare and reused; no per-expression runtime timer is added.
Invalid configuration raises safe ValueError before reading source records.
Python callbacks/models remain arbitrary Python; these native data budgets do
not inspect dataclass attributes or constrain application callback recursion.


## T-203 metric snapshot migration

batch_sizes now maps fixed string buckets `0`, `1`, `2-63`, `64-255`, `256-999`,
`1000+` to call counts, instead of exact observed integer sizes. New
batch_size_summary contains count/sum/min/max; min/max are null before any call.
Explicit empty batch calls count in bucket 0 (iterator exhaustion is not a call).
Both modes time completed batches and finalize the summary before raise/skip.
Runtime sampled stage timing remains independent of always-available batch timing.

Selected field type labels are bool/int/float/str/list/tuple/dict/Decimal/other;
arbitrary class names are not retained. Missing/null counts are separate from
non-null type labels. Error/rule label sets come from the fixed plan/rule config,
not record payloads. Native metrics=False disables counters and batch clocks,
but explicitly requested field profiles remain active. Scalar counts grow, but
metadata cardinality does not grow with stream length or distinct batch sizes.
