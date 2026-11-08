# Reproducible performance experiments (M3)

These are local Linux observations, not approved regression budgets or a speed
promise. Historical `benchmark-results.txt` and `benchmarks/benchmark.py` are
retained; their single workload is not equivalent to this new suite.

## Reproduce

Install the release extension first, using the active Python:

```sh
. "$HOME/.cargo/env"
bash scripts/check.sh
python -m benchmarks.run --profile smoke --output target/smoke-new
python -m benchmarks.run --profile baseline --repeat 5 --rss-repeat 3 --pin-cpu --output target/baseline-new
python -m benchmarks.run --profile stream --rss-repeat 3 --pin-cpu --output target/stream-new
```

Run from the source root, without `python -O`. Output must be a new directory.
`--pin-cpu` is Linux-only; omit on macOS (not measured here).
`--tcore-source /path/to/original/src` optionally includes original TCore v0.1;
it is not installed or vendored. Original module hashes are recorded. No optional
Polars/msgspec baseline: equivalence has not been established.
`--record-scale 10` multiplies records for a longer home run; `--profile full`
is a much larger factorial sweep. Do not run builds/other benchmarks concurrently.

## Equivalent work and scope

Six deterministic fixtures (seed 20261107): arithmetic, nested parsing, nested
collection sums, multiple derives, validation-heavy, mixed accepted/rejected/
malformed records. Every engine parses bytes, checks depth/domain/schema/business
rules, computes equivalent values and produces outcomes. Dict cases start with
predecoded input. The mixed dict case intentionally includes malformed byte
records. Full digest of status/value/error code/path/stage and order is compared
against an independent checked Python oracle for every measured record.

Timed corpus is schema-valid and within numeric range except designated parse/
business failures. Schema-invalid/overflow contracts differ in callback mode;
they are covered by correctness tests, not silently normalized in timing. Plain
Python also allocates public result/error containers; Runtime/TCore have counters,
while Plain has none. Native has explicit metrics on/off cases. Legacy error
signatures are normalized outside timing. This is an equivalent-outcome workload
comparison, not an attribution of all differences to Rust.

Each case uses five fresh timing processes, three fresh RSS processes and one
separate tracemalloc process. Oracle pass, plan construction and up to 1000 warmup
records are excluded from call timing; setup duration is saved. Timing sums only
engine batch calls; caller fixture generation and digest sink are excluded.
Raw `wall_ns` includes both and is not engine throughput. Outputs are discarded
batch by batch. A previous input/result batch may coexist transiently with the
next: bounded storage is O(batch size), not one object or zero copies.

Batch latency is nearest-rank p50/p95 pooled across calls. For N=5000/B=1000 this
is only 25 samples; small case N=256/B=64 has 20. These p95 values are exploratory,
not tail latency SLAs. Five process samples show dispersion, not confidence in a
production percentile. Samples are sequential, not randomized interleaved runs;
cloud contention/frequency are uncontrolled even with CPU affinity.

RSS is whole-process Linux `/proc/self/status:VmHWM`, including interpreter,
imports, oracle, warmup and allocator high water. It is not native heap. Python
tracemalloc starts after warmup and includes caller/sink allocations; it excludes
most Rust allocations and must not be added to RSS. A finite stream experiment
can expose retention but cannot prove every arbitrary stream is bounded.
Non-Linux resource fallback is explicitly unverified.

## Recorded evidence and memory correction

[Primary timing](evidence/m3/baseline/summary.json), exact environment/source
snapshots and raw samples are retained. [Corrected memory](evidence/m3/baseline-memory-corrected/summary.json)
uses the same fixtures; [joined summary](evidence/m3/joined-summary.json) combines
timing with corrected memory after digest/count checks. Run
`python docs/evidence/m3/analyze.py` to reproduce that join.

Initial RSS used `resource.ru_maxrss`. A controlled launcher allocation showed
that Linux exec inherited the launcher high water (9344 vs 74880 KiB) while the
child's VmHWM stayed 6468 KiB: [audit](evidence/m3/rss-meter-audit.json).
Thus **all RSS in `baseline`, `stream`, and early `smoke` is superseded**; use
`baseline-memory-corrected` / `stream-corrected` only. Original timing remains
valid. Memory-only reruns use `--passes rss traced`; no timing samples were
replaced or selected by outcome. Source snapshots distinguish runner versions.

Environment: Linux x86_64, CPython 3.12.14, Rust 1.99.1, release extension,
PyO3 0.29.3; child affinity CPU 0, three visible CPUs. See environment.json for
exact compiler, extension SHA256, clocks and file hashes. No hardware model
was exposed by `platform.processor()`; portability of these rates is UNKNOWN.

## Baseline observations

Median records/s, JSON bytes, N=5000, batch=1000, five timing processes:

| Workload | Checked Python | RedMud Runtime | RedMud native | TCore v0.1 adapter |
|---|---:|---:|---:|---:|
| arithmetic | 189,216 | 110,260 | 187,997 | 143,833 |
| nested_json | 109,613 | 75,110 | 113,243 | 88,818 |
| nested_sums | 34,998 | 29,750 | 29,711 | 32,436 |
| multiple_derives | 139,436 | 87,460 | 117,093 | 111,734 |
| validation_heavy | 110,898 | 84,050 | 122,972 | 101,612 |
| mixed_rejects | 194,149 | 107,690 | 179,535 | 149,930 |

Native is not uniformly fastest. Its process-duration ranges span 1.2–12.8% of
the median in these six cases; this is observed noise, not a permitted regression.
Dict native rates (same order) are 123,448 / 67,151 / 19,816 / 85,962 / 82,252 /
123,663 records/s. Input validation/encoding is included in public dict calls.

Native arithmetic batches 1/64/1000: 123,833 / 185,378 / 187,997 records/s;
nested sums: 26,267 / 28,754 / 29,711. Disabling metrics: arithmetic 201,725,
nested sums 29,777. Do not assume the arithmetic difference generalizes.

| Native bytes workload | Batch p50 / p95 ms | Whole-process RSS MiB | Python traced peak KiB |
|---|---:|---:|---:|
| arithmetic | 5.320 / 5.676 | 17.45 | 784.4 |
| nested_json | 8.784 / 9.063 | 18.91 | 1608.1 |
| nested_sums | 33.455 / 35.158 | 20.88 | 3860.6 |
| multiple_derives | 8.476 / 9.169 | 18.04 | 1357.4 |
| validation_heavy | 8.185 / 8.877 | 17.94 | 1217.2 |
| mixed_rejects | 5.496 / 5.880 | 17.50 | 769.4 |

[Stream corrected evidence](evidence/m3/stream-corrected/summary.json), B=64:
Runtime RSS 15.92→16.10 MiB and traced 51.4→51.6 KiB; native RSS 16.80→17.00
MiB and traced 44.2→43.9 KiB, N=2000→100000. Exact values in JSON supersede
rounded text. This shows no input-count-sized retention on this fixture.

Component measurements and budget decisions are tracked in T-303/T-304. No
production optimization or numeric pass/fail threshold follows from this table.

## Core and boundary scopes (T-303)

```sh
python -m benchmarks.components --repeat 5 --records 1000 --pin-cpu --output target/components-new
```

[Raw component results](evidence/m3/components/summary.json) include all six
fixtures, five fresh processes each, exact plan/JSONL, source/extension/test-binary
hashes and release build log. The driver compiles the ignored diagnostic Rust
test once before timing, then executes that binary explicitly. Routine cargo
tests skip it because it needs fixture/output environment variables; the driver
actually ran it 30 times and checked exact serialized parity with the binding.
No new public API, production timer or dependency was introduced.

All component scopes use the exact same 1000 compact byte records; the Python
oracle checks values and structured errors. Rust full core executes the same
`plan.run(raw).to_string()` loop as the binding. Separately instrumented parse,
evaluate (including validation/output depth) and serialization (including envelope
construction) mirror that loop and check exact parity. Per-record clock overhead,
extra output retention and warm caches affect instrumented phases; their sum is
not an exact decomposition of the independently timed full call. Evaluation of
parse failures is a trivial branch, still timed. No native memory attribution.

Binding scope includes PyO3 Vec conversion, detach/reattach, entire core, and
Python string materialization. It is **not dispatch alone**. JSON decode measures
Python envelope parsing separately. Public calls include result/error container
construction, index and policy handling; metrics are off here. Dict scope times
the actual validation plus default JSON encoding, which uses whitespace and
therefore differs in byte count from compact fixtures (both counts retained).
Public dict output parity is also checked. Scope order is fixed, caches warm,
outputs retained for this finite-batch diagnostic only. Do not subtract medians
from different processes to assert exact FFI overhead. In particular a binding
median below core median is measurement context/noise, not negative FFI cost.

Median microseconds/record, N=B=1000, five processes; core and public columns
are independent observable scopes:

| Workload | Core full | Parse* | Evaluate* | Serialize* | Binding+core | Python decode | Dict validate+encode | Public bytes | Public dict |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| arithmetic | 2.04 | 0.48 | 0.57 | 0.84 | 2.04 | 1.45 | 2.87 | 5.36 | 8.16 |
| nested_json | 5.27 | 1.87 | 1.60 | 1.61 | 5.08 | 1.84 | 5.58 | 9.19 | 15.26 |
| nested_sums | 27.76 | 6.63 | 14.92 | 5.33 | 26.59 | 5.29 | 16.63 | 34.21 | 51.13 |
| multiple_derives | 4.32 | 0.73 | 1.67 | 1.75 | 4.36 | 2.18 | 3.29 | 8.60 | 11.79 |
| validation_heavy | 4.23 | 1.10 | 1.55 | 1.35 | 4.18 | 1.95 | 3.82 | 8.05 | 11.71 |
| mixed_rejects | 1.94 | 0.43 | 0.51 | 0.84 | 1.92 | 1.54 | 2.59 | 5.28 | 7.79 |

*Instrumented separately; includes timing perturbation. Raw JSON has ns units.

These data justify investigating output conversion for arithmetic/multiple
derives, and input conversion only after output results. They do not justify
assuming that FFI dominates nested sums: evaluation itself takes about 14.92
microseconds/record in the instrumented native path. Keep correctness architecture
and dependency graph; no Rayon/Arrow/custom optimizer is indicated by this study.
The performance-budget proposal is separate and requires user approval.
