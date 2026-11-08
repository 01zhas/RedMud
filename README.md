# RedMud

Transform-only library with a Rust engine and Python API. Python 3.11+.
No connectors, services, or mandatory Python runtime dependencies.
This is an initial usable release, not production certification.

## Install and verify

From this directory, with Rust stable and a C linker installed:

```sh
python -m pip install .
cargo test
python -m unittest discover -s tests -v
python examples/native_cart.py
python examples/cart.py
python benchmarks/benchmark.py
```

Build distributable wheels: `maturin build --release`. Build an sdist:
`maturin sdist`. Wheels are platform specific; source installation needs Rust.

## Native API

```python
from redmud import Pipeline, field as F
pipeline = (Pipeline().require({'price': 'int', 'quantity': 'int'})
            .check('valid_quantity', F('quantity') > 0)
            .derive('total', F('price') * F('quantity'))
result = pipeline.run_one(b'{"price":1000,"quantity":3}')
assert result.value['total'] == 3000
```

`run_one`, `run_batch`, and `run_iter(records, batch_size=1000)` produce
RecordResult objects with `ok`, `value`, `errors`, and monotonically increasing
`index`. Collect is default. `Pipeline(on_error='raise'|'collect'|'skip')`
controls rejection handling. Skip filters batch/iterator failures but metrics
still count them; scalar calls return a rejected result. Raise processes the
whole batch before raising ProcessingError; do not assume partial delivery.
Inputs are JSON bytes/strings or JSON-compatible dictionaries. Use run_batch
for lists of records, run_iter for bounded lookahead. Inputs are not mutated.

Builders return new pipelines. A typed Rust plan is cached on first use or
explicit `prepare()`. Steps execute in declaration order, so place checks before
or after derive as needed. `map_list(path, child_pipeline)` runs child steps
inside Rust; `list_sum(path, field)` sums signed integers, with empty sum zero.
Dotted field paths traverse objects. See examples/native_cart.py.

## Python business logic

```python
from redmud import Processor, Runtime
class OrderProcessor(Processor):
    def transform(self, order):
        return {'total': order['price'] * order['quantity']}
for result in Runtime(OrderProcessor()).process_iter([{'price':1000,'quantity':3}]):
    assert result.value == {'total':3000}
```

Override parse for dataclasses or Pydantic models (Pydantic remains optional).
Runtime uses Python, including callbacks and JSON decoding. It does not compile
Python code. Processor input_rules/output_rules accept Rule predicates with
reject/warn severities; custom batch transforms retain scalar fallback.
Configure Runtime via Settings(on_error=..., batch_size=..., output_fields=...).

## Quality and profiling

`require` accepts types int, float, number, str, bool, list, object. Constraint
objects support type, nullable, min, max, allowed, fields (nested schema), items
(list schema). All declared fields are required; unrelated fields pass through.
Checks reject when the expression is not true. Errors contain code/path/stage/
message; failed inputs and callback exception text are hidden by default.
The native engine stops at the first error per record; unrelated rows continue.

`snapshot()` exposes counters, errors by code, timings and optional selected
output field profiles (null/missing/count/min/max/mean/population stddev).
Configure Pipeline(output_fields=('total',)); profiles retain no records.
Pipeline(metrics=False) disables counters/timing, but explicit output profiles
remain active. Native timing currently measures whole batches, not individual
parse/validation/transform stages. Python stage timings are sampled.
`profile(records, max_records=1000)` enables cProfile/tracemalloc; its report
contains elapsed_ms, peak_traced_bytes, top_functions. It consumes records and
updates counters. Traced bytes exclude Rust allocations. Metrics throughput
includes idle time. Use separate instances per worker; instances are not
thread-safe. See docs/architecture.md and docs/benchmarks.md for trade-offs.

Russian overview: README.ru.md. Migration: docs/migration.md.

## M1 correctness updates

Developer verification: `python -m pip install -r requirements-dev.txt`, install
Rust clippy/rustfmt, then `bash scripts/check.sh` (builds/reinstalls the extension).
See docs/development.md and docs/migration.md for changes.

prepare validates definitions before reading records. Numeric bounds must match
int/float schema types; number has no min/max constraints. Native integers pass
through exactly within signed/unsigned 64-bit range; arithmetic is signed i64.
Larger integral inputs reject with numeric_range. Dict keys must be strings;
unsupported values, tuples and cycles reject. Native parse/transform errors use
status=error; schema/business failures use rejected. Both modes account the whole
batch before raise. Diagnostic profile.records counts consumed inputs under skip.
Depth-64 guards and bounded metric buckets are implemented in M2. Platform CI
execution is still pending; local Linux CPython 3.11/3.12/3.13 package checks pass.
T-206 advisory/license verification was moved to M1; see docs/development.md
for `bash scripts/security.sh`, scanner setup and report scope.
These local M1 checks do not certify production readiness or a performance gain.


## M2 reliability and package checks

Native depth is limited to 64 (root value=1, scalar leaves count). Deep input
returns depth_limit at parse; excessive output depth returns it at transform.
Definitions are checked before input consumption, including combined plan and
expression nesting. This is a depth bound, not a byte-size limit.

Metrics snapshot.batch_sizes now contains buckets 0/1/2-63/64-255/256-999/1000+;
batch_size_summary adds count/sum/min/max. Explicit empty batch calls count.
Arbitrary Python type names are grouped as other in selected output profiles.
See docs/migration.md for the snapshot compatibility change.

`python scripts/package_check.py --python /path/to/python` verifies wheel and
sdist installs in independent clean venvs and runs the full Python suite/examples
outside the checkout. `.github/workflows/ci.yml` defines the approved six-job
Linux/macOS Python matrix plus a security job, with pinned upstream actions.
A prepared workflow is not evidence of a passing hosted job; see EVIDENCE.md.
