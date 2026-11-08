# Assessment and migration
The supplied TCore 0.1 is entirely Python: four modules, 22 archive entries,
no native engine. Its Processor/Runtime API, dataclass examples, bounded batching,
quality profiling, and regression tests are useful and retained under redmud.
The original archive remains untouched outside this project.

Native Pipeline is a new independent execution path. It uses a serialized typed
expression tree prepared once, not callbacks. Operations execute in declaration
order; this supplies explicit dependency ordering without a query optimizer.
No Arrow, Polars, scheduler, connector, or mandatory Python runtime dependency.

Change imports from tcore to redmud; Prometheus prefix changes to redmud.
Processor hooks remain compatible. Native inputs are JSON objects; arbitrary
Python models belong in Runtime. Rust signed 64-bit arithmetic differs from
Python arbitrary precision deliberately: overflow is an explicit error.

## M1 contract hardening (unreleased development build)

prepare now rejects invalid schemas, unknown keys/types/AST members, invalid
paths, reserved/duplicate native check names and incompatible constraints.
min/max require int or float bounds matching the declared type; number supports
type validation only. fields/items infer object/list when type is omitted.

Native input/pass-through integers are exact in [-2^63,2^64-1]; outside this
range is numeric_range, not a float. Arithmetic remains checked signed i64.
Python dicts require string keys and JSON-native values (tuples/sets/cycles
reject). Existing arbitrary Python objects remain supported by Runtime hooks.

Native parse/expression failures now have status=error; schema/business failures
have status=rejected. Errors identify the offending source/derived/sum path.
Python structured Rule errors use stage=validation while Issue.stage stays
input/output. Default JSON parser failures use invalid_json; custom parsers
retain callback_error. Rule names must be ASCII alphanumeric/underscore.

Both modes finalize metrics/profiles for the entire batch before raise;
ProcessingError identifies the first failure in input order. No batch outputs
are returned on raise. profile.records now counts consumed inputs even under
skip or disabled native metrics. Limits must be positive integers, not bools.

Full code/status mapping: docs/contracts.md. No public version/tag/publication
has been created; current package metadata remains the development 0.2.0.


## M2 resource and metrics contracts

Native inputs, outputs, literal/allowed values now have maximum depth 64; root
and scalar leaves count as described in docs/contracts.md. Combined semantic
plan/expression/schema recursion is checked in prepare, independently of JSON
transport wrappers. Deep records receive depth_limit with parse/transform stage;
invalid deep definitions raise ValueError before source consumption.

Metrics snapshot.batch_sizes changes from exact integer sizes to six fixed string
buckets. Use batch_size_summary for exact count/sum/min/max (null extrema before
any call). Explicit empty batch calls are observed; iterator exhaustion is not.
Runtime now reports aggregate batch timings/sizes as native mode does. Output
profile types use builtin/Decimal labels plus other; custom class names no longer
appear. No public transform method is removed and no external runtime service
or dependency is added. Existing instances remain single-caller.
