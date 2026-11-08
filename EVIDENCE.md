# RedMud evidence ledger

Initial audit: 2026-11-07 UTC. This file records observations, not approval.
Task status is in TASKS.md. No full product requirement is marked VERIFIED in
this planning pass; only T-001/T-002 planning deliverables are verified.
Historical docs/verification.md and docs/benchmark-results.txt remain unchanged
and are not substituted for a current run.

## E-01 — Source identity and inspection (T-001 / GOV-001)

Root: /workspace/redmud. `git -C /workspace/redmud status --short` failed with
exit 128: not a Git repository. No commit/remote/CI identity can be claimed.
`find /workspace -name AGENTS.md -print` initially returned none.

Inspected Cargo.toml/Cargo.lock, both crate manifests and sources,
pyproject.toml/LICENSE, every python/redmud module, all tests/examples, the
benchmark, both READMEs and all pre-existing docs. `rg --files --hidden` excluded
build/cache directories. Current code: one core Rust source, one binding source,
five Python modules plus __init__, four test modules, one benchmark script.

[Pre-edit SHA-256 manifest](docs/evidence/initial/source-before.json) identifies
all pre-existing non-build files. [Post-audit identity check](docs/evidence/initial/source-integrity.log)
compares those bytes after planning. No application, test, benchmark, manifest,
lockfile, example or pre-existing documentation file was changed. New files are
the five requested planning documents and docs/evidence/initial audit artifacts.
There is no Git diff; hashes are the available evidence.

## E-02 — Executed checks (T-001)

[Command/exit-code index](docs/evidence/initial/commands.json) and individual
linked logs preserve exact commands. Commands ran from /workspace/redmud;
`. "$HOME/.cargo/env"` prefixes Rust/maturin commands where shown.

| Actual command | Result / limit | Log |
|---|---|---|
| `cargo test --workspace --locked` | PASS: 3 core tests, 0 binding tests, 0 doctests. Does not prove all edge cases. | [rust-test](docs/evidence/initial/rust-test.log) |
| `cargo fmt --all -- --check` | PASS, exit 0. | [rust-format](docs/evidence/initial/rust-format.log) |
| `cargo clippy --workspace --all-targets --locked -- -D warnings` | Invocation FAILED, exit 1: component absent. Analysis NOT RUN, not a clean lint result. | [rust-clippy](docs/evidence/initial/rust-clippy.log) |
| `python -m unittest discover -s tests -v` | PASS: 41 tests, current installed package. Fresh wheel rerun below. | [python-tests](docs/evidence/initial/python-tests.log) |
| `python -m ruff check python tests examples benchmarks` | Invocation FAILED, exit 1: module absent. Analysis NOT RUN. Proposed future gate uses focused selectors, not this unconfigured command. | [python-static](docs/evidence/initial/python-static.log) |
| `maturin build --release --locked --out /tmp/redmud-audit-dist` | PASS: CPython 3.12 manylinux_2_34 x86_64 wheel. | [build-wheel](docs/evidence/initial/build-wheel.log) |
| `maturin sdist --locked --out /tmp/redmud-audit-dist` | FAIL, exit 2: --locked unsupported for sdist; retained as failed attempt. | [build-sdist](docs/evidence/initial/build-sdist.log) |
| `maturin sdist --out /tmp/redmud-audit-dist` | PASS rerun; warnings: crate documentation/homepage/repository metadata absent. sdist installation NOT RUN. | [build-sdist-rerun](docs/evidence/initial/build-sdist-rerun.log) |
| `python -m venv /tmp/redmud-audit-venv` then venv `python -m pip install --no-deps /tmp/redmud-audit-dist/redmud-0.2.0-cp312-cp312-manylinux_2_34_x86_64.whl` then venv `python -m unittest discover -s tests -v` | PASS: clean wheel install + 41 tests, exit 0; only Linux/Python 3.12. | [clean-install](docs/evidence/initial/clean-install.log) |
| `python examples/native_cart.py` | PASS, asserted total 3500. | [native-example](docs/evidence/initial/native-example.log) |
| `python examples/cart.py` | PASS, three valid totals 357000 and one parse failure. | [python-example](docs/evidence/initial/python-example.log) |
| `python examples/cpu_profiling.py` | PASS, bounded report generated. | [profile-example](docs/evidence/initial/profile-example.log) |
| `python examples/source_sink_agnostic.py` | PASS, outputs 20/40/60/80. Mock data only, no connectors. | [source-example](docs/evidence/initial/source-example.log) |

[Import identity](docs/evidence/initial/import-identity.log) records redmud and
redmud._native paths inside the new venv; installed Python module bytes match
workspace sources. Build reruns did not alter application sources.

## E-03 — Verified facts versus claims (T-001)

| Capability / claim | Evidence-based disposition |
|---|---|
| Meaningful Rust native engine | VERIFIED for tested cases: Expr/Step/Plan in crates/redmud-core/src/lib.rs perform parsing/traversal/validation/arithmetic; native Python tests and E-02 pass. Not a claim of complete spec coverage. |
| Reusable plan | CODE + smoke: Pipeline.prepare caches NativePlan; constructors deserialize typed Expr/Step. Cache identity/idempotence coverage incomplete; no semantic schema preparation. |
| Native GIL release | CODE-VERIFIED: binding wraps owned Rust byte processing in py.allow_threads; PyO3 source documents this does not launch threads. No dedicated RedMud GIL concurrency test run. |
| Nested validation/map/sum | VERIFIED for TestNative.test_nested and Rust nested_and_empty_sum/schema_edges assertions only. Deep-input safety NOT VERIFIED. |
| Python callbacks/dataclasses/batch fallback | VERIFIED by TestRuntime and examples. Dedicated Pydantic adapter/test NOT RUN; arbitrary parse hooks exist. |
| Policies compatible across modes | FALSE as a complete claim: E-04 shows different raise accounting and native status classification. |
| Input integers preserved | FALSE: E-04 demonstrates accepted oversized integer becomes float. Existing i64 overflow test does not cover parsing/pass-through. |
| All schema constraints validated | CODE-ONLY for several runtime branches; bad definitions accepted, typo silently ignored (E-04). allowed rejection, all type/limit combinations not exhaustively tested. |
| Bounded iteration | VERIFIED lookahead unit cases, not a process-memory bound. Both iterators use islice. E-07 identifies growing metadata. |
| Metrics/profiling complete | Basic smoke/profile tests pass; native has batch timing only, Runtime no populated batch duration/size distribution; E-04 finds profile skip count defect. |
| Portable/production ready | NOT VERIFIED: no CI files present and only current Linux/Python 3.12 execution. macOS/Windows/other Python versions NOT RUN. |
| Native always faster | FALSE on this fixture; E-05/E-06 show plain Python faster. No universal performance claim. |

## E-04 — Reproduced defects (T-001; future AC-101…AC-107)

Exact audit probe: `python docs/evidence/initial/probes.py`; exit 0 means probes
executed, **not** that defects passed acceptance. [Probe source](docs/evidence/initial/probes.py),
[actual output](docs/evidence/initial/probes.log).

1. **High, silent numeric corruption:** Pipeline().run_one on JSON bytes and dict
   with n=18446744073709551616 returns ok with n=1.8446744073709552e+19 (float).
   Core uses default serde_json::from_slice<Value>; outside-domain integer is not
   rejected. A second probe with n=18446744073709551617 also returns that float,
   which is numerically unequal to the input integer, proving precision loss,
   not only a type change: [precision probe](docs/evidence/initial/numeric-precision.log).
   T-103 blocks optimization and release.
2. **High, configuration validation:** prepare accepts unknown type, string min
   bound on int, and typo mni. Typo constraint then allows a record. NativePlan
   deserializes schema as Value without validating its meaning. T-101/T-102.
3. **Medium, raise accounting:** malformed JSON then two valid rows advances
   _index to 3 in both modes; Pipeline processed=3, Runtime processed=1. Runtime
   raises inside metric-finalization loop. T-105.
4. **Medium, profile skip:** with one bad/one valid row, both modes report
   ProfileReport.records=1 while processed=2. profile counts emitted results.
   T-106; preserve sample consumption limit while fixing count.
5. **Medium, error locality:** derive('v', F('x')+1) on x=None reports path=''
   instead of x. Arithmetic eval passes current object scope to integer(). T-104.
6. **Code observation:** native Pipeline labels all failures rejected, including
   parse/arithmetic, whereas Runtime differentiates error/rejected. T-107.

These are open defects; no fixes were made during the planning pass.

## E-05 — Existing benchmark rerun (T-001 / exploratory NFR-004)

Executed `python benchmarks/benchmark.py`, exit 0; [raw output](docs/evidence/initial/benchmark.log).
10,000 records; median of five timings after warm run; simple parse/type checks,
positive quantity and one multiplication; native stream batches default 1000,
Runtime default 256. Result equivalence is checked on this valid fixture.

| Mode | Median seconds | Records/s | Python traced peak bytes |
|---|---:|---:|---:|
| Plain Python | 0.017080 | 585486 | 3465377 |
| Python Runtime | 0.069316 | 144267 | 4813204 |
| Native batches | 0.048002 | 208327 | 5281592 |
| Native scalar | 0.064393 | 155297 | 5151715 |
| Native dict incl. upstream decode | 0.077190 | 129550 | 8492576 |
| Native metrics off | 0.045252 | 220983 | NOT MEASURED |
| Native predecoded dict | 0.064646 | 154688 | NOT MEASURED |

Limitations: results retained, no invalid rows/nested cases, Runtime recreated
while native instance/counters reused; different batch defaults; no raw per-repeat
samples, latency distribution or RSS. Do not adopt as a regression gate.

## E-06 — Supplemental audit measurements (T-001 / exploratory NFR-004)

Executed `/tmp/redmud-audit-venv/bin/python docs/evidence/initial/measurement-probe.py`,
exit 0. [Exact audit-only script](docs/evidence/initial/measurement-probe.py),
[raw JSON samples](docs/evidence/initial/measurement-probe.log). No product benchmark
was modified. Five isolated processes per mode; 20,000 deterministic records,
1000 per batch, one warmup batch excluded. Same supported-range type/positive
quantity checks and preserve-plus-total output; checksum asserted. Plain Python
has no result envelope/metrics; Runtime/native include them. Validation logic
is Python transform code for baseline/Runtime and schema/check for native.

| Mode | Median records/s | Batch p50 ms | Batch p95 ms | Median process peak RSS KiB |
|---|---:|---:|---:|---:|
| Python bytes | 610319 | 1.603 | 1.909 | 20496 |
| Runtime bytes | 138162 | 6.951 | 9.392 | 21012 |
| Native bytes | 213126 | 4.633 | 5.088 | 20916 |
| Native predecoded dict | 162139 | 6.126 | 6.587 | 21044 |

Batch p95 uses pooled 100 batch samples, nearest-rank, not record/request p95.
Throughput times batch calls, excluding output checksum aggregation. Outputs are
discarded per batch; both encoded/decoded fixtures are preallocated in every
process. RSS is Linux resource.ru_maxrss in KiB, whole process including imports,
input fixtures and allocator history; it does not isolate Rust heap or prove
constant-memory streaming. No threshold or statistical significance claim.

A separate unchanged internal NativePlan call for 1000 derive-only rows measured
median 1.301 ms for conversion+Rust execution+serialization+return and 1.313 ms
for Python json.loads of those output envelopes (20 measured calls after one
warmup). Both scopes consume the same returned work; the fixture lacks validation
and must not be compared directly to the end-to-end table. This confirms a
measurable envelope-decode cost, **not** exact FFI overhead or pure Rust time.
Pure core timings and full equivalent multi-workload boundary decomposition
NOT RUN; assigned T-303. No improvement from an implementation change was measured.

Environment for both benchmark sets: Linux 6.18.57 x86_64/glibc 2.41, CPython
3.12.14, Rust 1.99.1, cargo 1.99.1, maturin 1.16.0; AMD EPYC 9V74, 3 visible CPUs.
Release extension; no CPU affinity/frequency isolation. [Environment](docs/evidence/initial/environment.log).
No thresholds proposed for approval yet: M3 must establish a representative baseline.

## E-07 — Architecture, reuse, redundancy and gaps (T-001)

Retain core Expr/Step/Plan and serde_json; Rust performs meaningful native work.
Retain Processor/Runtime, quality accumulators, sampled timing and regression
fixtures. Python/runtime flexibility is useful; no rewrite justified.

Observed costs/risks: dict -> JSON -> Rust and Rust -> JSON string -> Python;
multiple owned buffers/results per batch; arbitrary field clones in Expr;
whole-batch buffering intentional for batch APIs. Python mode reconstructs each
frozen RecordResult to attach errors. These are optimization candidates, not
proof of dominant cost across workloads. T-303 before rewriting.

Pipeline.profile = Runtime.profile is cross-class coupling, not an abstract
execution interface; fix the proven counting defect locally before adding one.
Runtime/Pipeline duplicate policy/finalization code, already diverged; shared
contract tests preferred to a speculative unified framework. Rule import in
benchmark is unused; no unused direct runtime dependency was identified. Two syn
versions in the lockfile are transitive, not by themselves a reason to upgrade.

Metrics.batch_sizes keys every observed native batch length; FieldProfile.types
uses arbitrary Python type names; cardinality can grow with the stream. Runtime
batch-size distribution is empty. No configured depth contract; serde JSON
recursion guard does not cover Python-side serialization or combined plan eval.
Selected output profiles exclude rejected inputs and are not input-wide DQ.
Missing native stage timings/parallelism are explicit scope deferrals, not verified features.

Not run: long/unbounded stream RSS test, full per-operator/generated invariants,
fuzzing, adversarial deep recursion, property tests, Pydantic/Polars examples,
sdist installation, approved platform CI, native stage/GIL concurrency tests.
No existing CI/config files found; no connector/service dependency in manifests.

## E-08 — Dependencies, capabilities and licenses (T-001 / partial NFR-003)

Executed `cargo metadata --locked --offline --format-version 1` and inspected
installed crate/tool metadata and direct license texts. [Metadata](docs/evidence/initial/cargo-metadata.json),
[license inventory](docs/evidence/initial/licenses.json). Direct licenses copied
as evidence under docs/evidence/initial/*LICENSE*.txt. Project MIT attribution
contains historical TCore contributor notice; preserve it.

Direct third-party crates: serde 1.0.229 derive, serde_json 1.0.154, PyO3 0.23.5;
all declare MIT OR Apache-2.0 and provide corresponding license files. Maturin
1.16.0 metadata declares MIT OR Apache-2.0 with included license files. No
mandatory Python runtime dependencies in wheel metadata (`pip show redmud`).
Core/binding JSON dependencies both have actual call sites.

Verified installed APIs: serde_json from_slice for JSON, serde derive for typed
enums, PyO3 Python::allow_threads for GIL release, actual maturin wheel/sdist build.
`rg` of installed pyo3/src/marker.rs confirms allow_threads does not spawn workers.
Transitive license expressions are in metadata (including LLVM-exception and
Unicode terms); full notice compliance/security review NOT RUN, assigned T-206.
Advisory scan NOT RUN; absence of findings has not been established. Search of
application source found no unsafe/eval/pickle implementation (Expr::eval is a
Rust method, not dynamic code execution). [Search output](docs/evidence/initial/code-search.log).

## E-09 — Planning acceptance (T-002 / GOV-001)

Created SPEC.md, ROADMAP.md, TASKS.md, AGENTS.md and this ledger. Validation checks
requirements/tasks/milestones/AC references, task dependency cycles, local links,
MVP traceability and pre-existing file hashes. Exact validator and results:
[consistency check](docs/evidence/initial/plan-check.py),
[result](docs/evidence/initial/plan-check.log). It verifies document structure,
not product behavior; semantic review is recorded in ROADMAP critical review.

Consistency attempts: first failed on a dangling depth-task reference (corrected to T-202),
second failed on an obsolete acceptance label after the tool-bootstrap task was
moved to T-011 (corrected to AC-011). Failures retained in
[attempt 1](docs/evidence/initial/plan-check-attempt1.log) and
[attempt 2](docs/evidence/initial/plan-check-attempt2.log). A subsequent check
flagged the historical invalid identifier in this narrative; wording corrected,
[attempt 3](docs/evidence/initial/plan-check-attempt3.log) retained. Final rerun PASS:
20 requirements, 24 tasks, 6 milestones, 8 gates, all local links resolve,
dependencies acyclic. A manual semantic review also moved tooling bootstrap
before implementation tasks so mandatory static gates do not depend on a later
milestone. This is planning repair, not product implementation.

Approval UNKNOWN/PENDING. T-010 BLOCKED. No implementation task was started;
M0 delivery stops here. Future entries append approval, task acceptance evidence,
failures/reruns and milestone reports rather than rewriting this initial baseline.


## E-10 — User approval and next milestone (2026-11-07 / GOV-002)

User message: “Потверждаю какой сдедующий Milestone”. This approves the delivered
specification/roadmap and their proposed defaults D-01…D-05 without exceptions;
it does not approve future numeric performance budgets, remote publication,
or establish that a CI host/runner is available. M0 approval checkpoint is closed.

Next milestone: M1 — Correct contracts. T-010 is TODO, with the approval recorded;
remaining acceptance is the detailed code/status/stage table and CI-host
disposition. GitHub Actions is the accepted design proposal, while remote/runner
availability remains UNKNOWN. Then T-011 establishes local checks before product
fixes. No implementation task or application change is claimed in this response.

Changed planning headers/status in SPEC.md, ROADMAP.md, TASKS.md and AGENTS.md;
initial E-01…E-09 evidence retained unchanged. Structural check command:
`python docs/evidence/approval/check.py` (uses initial structural checks with
approval-aware status assertions). Result: [approval check](docs/evidence/approval/check.log).
Application tests and benchmarks NOT RUN again: this update changes only
planning/evidence documents and no functional/performance claim is made.


## E-11 — T-010 decision record

Completed after user instruction “Начинай работу”. [Contract table](docs/contracts.md)
freezes codes/status/stages and D-01…D-05 details within approved SPEC. CI design
is GitHub Actions; actual remote/runner access UNKNOWN, deferred to T-205 rather
than blocking unrelated M1 work. Depth/bucket implementation remains M2.
T-010 VERIFIED by inspectable contract table and E-10 approval. No code change
in this task; implementation gates N/A (documentation/decision task).

## E-12 — T-011 verification tooling

Installed clippy and Ruff; versions/license/usage recorded in docs/development.md
and requirements-dev.txt. `bash scripts/check.sh` runs the exact changed-wheel
local gate sequence. [Run 001](docs/evidence/m1/run-001-T-011.log): PASS, format,
clippy -D warnings, focused Ruff, compileall, 3 Rust tests, release build/install,
41 Python tests; import paths are installed package/extension. No runtime
dependency or product semantics changed. T-011 VERIFIED. Commands and source
identities for subsequent tasks append to [run index](docs/evidence/m1/runs.jsonl).

## T-101 — verified M1 task

AC-101: tests/test_prepare.py (3 cases) and prepare::tests::definitions_are_validated; 4 Rust and 44 Python tests pass. NativePlan validates names/paths and both branches; invalid AST fields are rejected safely. run_iter prepares before reading source. No new dependency.

Command `bash scripts/check.sh` exit 0: [full log](docs/evidence/m1/run-003-T-101.log); source identity and earlier failures in m1/runs.jsonl. G-BASE/G-STATIC plus focused acceptance passed; no performance comparison made. Task VERIFIED; this does not verify the full MVP requirement.

## T-102 — verified M1 task

AC-102 tests/test_schema.py and schema::tests::schemas_are_checked_once pass; 5 Rust and 47 Python tests. Schema definitions validated recursively at prepare, inferred list/object schemas supported, integer/float bounds no longer mixed.

Command `bash scripts/check.sh` exit 0: [full log](docs/evidence/m1/run-005-T-102.log); source identity and earlier failures in m1/runs.jsonl. G-BASE/G-STATIC plus focused acceptance passed; no performance comparison made. Task VERIFIED; this does not verify the full MVP requirement.

## T-103 — verified M1 task

AC-103 tests/test_inputs.py and json::tests::integral_tokens_are_never_floats pass; 6 Rust and 50 Python tests. serde_json raw_value feature preserves token text before i64/u64 range check; verified installed RawValue API, no new crate/lockfile package. Unsupported keys/tuples/cycles rejected, bytes stay direct Rust. JSON private-looking keys preserved. Performance cost is NOT MEASURED; correctness change only.

Command `bash scripts/check.sh` exit 0: [full log](docs/evidence/m1/run-007-T-103.log); source identity and earlier failures in m1/runs.jsonl. G-BASE/G-STATIC plus focused acceptance passed; no performance comparison made. Task VERIFIED; this does not verify the full MVP requirement.

## T-104 — verified M1 task

AC-104 tests/test_expressions.py and expression_contract_tests::failure_order_paths_and_lazy_branches pass; 7 Rust and 54 Python tests. Checked operations report source fields and derive/sum overflow targets; left operand validation precedes right evaluation, nonbool predicates error, only selected conditional evaluated, structural type-sensitive equality preserved.

Command `bash scripts/check.sh` exit 0: [full log](docs/evidence/m1/run-009-T-104.log); source identity and earlier failures in m1/runs.jsonl. G-BASE/G-STATIC plus focused acceptance passed; no performance comparison made. Task VERIFIED; this does not verify the full MVP requirement.

## T-105 — verified M1 task

AC-105 tests/test_policies.py exercise both modes across scalar/batch/iter and collect/raise/skip, full-batch counters/profiles, stable indexes, empty batches/source exceptions/invalid sizes; 7 Rust and 57 Python tests pass. Runtime now finalizes all outcomes before raise.

Command `bash scripts/check.sh` exit 0: [full log](docs/evidence/m1/run-011-T-105.log); source identity and earlier failures in m1/runs.jsonl. G-BASE/G-STATIC plus focused acceptance passed; no performance comparison made. Task VERIFIED; this does not verify the full MVP requirement.

## T-106 — verified M1 task

AC-106 tests/test_profiling.py validates skip input counts even with native metrics disabled, bounded consumption, argument validation, exception cleanup, caller-owned tracing and weakref result release. 7 Rust and 60 Python tests pass; existing profile implementation reused.

Command `bash scripts/check.sh` exit 0: [full log](docs/evidence/m1/run-013-T-106.log); source identity and earlier failures in m1/runs.jsonl. G-BASE/G-STATIC plus focused acceptance passed; no performance comparison made. Task VERIFIED; this does not verify the full MVP requirement.

## T-107 — verified M1 task

AC-107 tests/test_errors.py validates native/Python parse-validation-transform classifications, Rule warnings/rejections, safe messages/metrics and custom parser behavior; original fallback/dataclass tests retained. 7 Rust and 63 Python tests pass. Native failures now distinguish error/rejected, Python Rule errors use validation stage. M1 final review reopens T-104 for intermediate map-path locality.

Command `bash scripts/check.sh` exit 0: [full log](docs/evidence/m1/run-015-T-107.log); source identity and earlier failures in m1/runs.jsonl. G-BASE/G-STATIC plus focused acceptance passed; no performance comparison made. Task VERIFIED; this does not verify the full MVP requirement.

## T-104 — verified M1 task

Final AC-104 review added nested-map intermediate path case, first reproduced failure (run 016), then corrected map traversal prefixes. Run 017 passes all static checks, 7 Rust and 63 Python tests including T-107 regressions; dependent T-107 acceptance remains passing.

Command `bash scripts/check.sh` exit 0: [full log](docs/evidence/m1/run-017-T-104.log); source identity and earlier failures in m1/runs.jsonl. G-BASE/G-STATIC plus focused acceptance passed; no performance comparison made. Task VERIFIED; this does not verify the full MVP requirement.

## E-13 — M1 implementation report and final gate review

Implemented and locally tested: T-010/T-011/T-101…T-107 code/functional acceptance.
Verified ledger tasks: T-010, T-011, T-101, T-102, T-105, T-106.
**M1 is not formally VERIFIED**: final review supersedes the earlier provisional
T-103/T-104/T-107 VERIFIED entries with BLOCKED. Functional assertions pass;
G-SAFE advisory scan has not run, and T-104 depends on T-103 final verification.
History/failures are retained; no false PASS for an unavailable mandatory gate.

Requirement clauses addressed: FR-001 input/range handling; FR-002 preparation;
FR-003/FR-004 expression traversal; FR-005 configuration validation; FR-006/FR-007
safe structured outcomes and callback compatibility; FR-008 whole-batch policies;
FR-009 input consumption/index behavior; FR-011 profile counts/cleanup;
NFR-001 checked numbers and NFR-006 local verification tooling. Full MVP
requirements are not certified: depth/cardinality/CI/security/performance work
remains as specified in M2/M3.

Evidence: runs 001–019 in docs/evidence/m1/runs.jsonl preserve exact commands,
exit status, source identities and failures before fixes. Final functional
`bash scripts/check.sh` (run 017): PASS, 7 Rust tests, 63 Python tests, Rust fmt,
clippy -D warnings, focused Ruff, compileall, release build/install and actual
package/extension import paths. Every added defect fixture has a failing-before
and passing-after record. No pre-existing tests were removed or weakened.

G-SAFE checks actually run: default redaction/classification fixtures; malformed,
nonfinite, range/key/cycle fixtures; timeout-bounded subprocess depth probes
64/256/1000 (run 018), no process abort; source search for application unsafe.
These probes do not establish the specified depth-64 rejection boundary (T-202).
`cargo audit --version` fails exit 101 (run 019): tool absent, advisory analysis
NOT RUN. Initial direct licenses retained; complete lockfile advisory/notice
review belongs to T-206 and is not declared passed here.

Plan conflict: G-SAFE is mandatory for T-103/T-107, while AGENTS.md says
“T-206 selects/verifies an advisory scanner before installation.” T-206 is
assigned to M2, whose entry requires M1 verified. Proposed concrete amendment:
move existing T-206 to the end of M1 and execute its existing acceptance unchanged.
No new dependency/scanner is chosen or installed yet. User approval required
by AGENTS.md scope/amendment rule; do not bypass by silently narrowing G-SAFE.

Changes: Rust core preparation/schema modules and exact numeric JSON parsing,
binding preparation; Python pipeline/runtime/rule validation; seven new test
modules (22 tests); scripts/check.sh and requirements-dev.txt; development,
contract/migration/architecture/English/Russian docs and planning ledger updates.
Current code remains an unreleased development build with 0.2.0 metadata.
No performance measurement after these changes; speed/memory delta NOT MEASURED.
RawValue token preservation adds traversal; do not assume a speedup. CI host/
runner availability UNKNOWN, other platforms NOT RUN. M2 limits/metrics and M3
representative performance baseline remain TODO. No application unsafe or new
runtime crate/Python dependency; serde_json raw_value feature is the sole crate
feature change and uses its existing documented API/license.

Required next action: approve the T-206 milestone reassignment, complete the
security gate, then close M1. Do not automatically proceed into M2.

Final documentation consistency check (run 020) PASS with blocked gate statuses;
native/cart/CPU profiling examples run successfully (run 021). See
[changed files](docs/evidence/m1/changed-files.json),
[final source hashes](docs/evidence/m1/final-source.json) and
[execution recorder](docs/evidence/m1/execution-runner.py). The source hashes cover
product/planning inputs before this final evidence append; they exclude audit
logs/build/cache files. Local source snapshot: /workspace/redmud-m1-source.zip.

## E-14 — A-01 approval and T-206 start

User instruction “Продолжай работу” follows the explicit request to move T-206
to the end of M1. Recorded as authorization for that concrete amendment: T-206
IN_PROGRESS in M1, with unchanged acceptance. T-103/T-104/T-107 remain BLOCKED
until its safety evidence and final regression checks pass. No M2 work started.

## E-15 — T-206 findings and scoped remediation

Scanner capability/license review precedes installation: runs 022–026, 031,
scanner-selection.json and license snapshots. Rust scanner cargo-audit 0.22.2
(MIT OR Apache-2.0), pip-audit 2.10.1 (Apache-2.0) installed separately from product.
Python pinned build/dev scan passes (run 028). Initial combined scan FAILS
(run 032): RustSec reports two PyO3 0.23.5 vulnerabilities, RUSTSEC-2025-0020
and RUSTSEC-2026-0177. [Original report](docs/evidence/m1/rust-advisories-before-fix.json)
preserved; no ignores/waivers applied. Advisory database commit/time is in JSON.

T-206 explicitly requires resolving findings. Select existing approved dependency
PyO3 0.29.0, the minimum release fixing both according to RustSec. Capability,
MIT OR Apache-2.0 license, MSRV 1.83 and detach API verified from downloaded
upstream source (runs 034/035). This is a scoped security update, not a blanket
upgrade or architecture amendment. Binding changes allow_threads -> detach and
explicitly declares gil_used=true, retaining the GIL-required module contract.
No promise of free-threaded support. Public Python API and core engine unchanged.
Regressions and advisory rerun must pass before task verification.

## E-16 — T-206 verified; M1 closure (2026-11-07 UTC)

Supersedes E-13 blockers. A-01 authorized moving T-206 into M1; task acceptance
unchanged. T-206 and previously blocked T-103/T-104/T-107 are now VERIFIED after
actual scanner/remediation/regression evidence. All M1 tasks are verified;
M2 tasks remain TODO and no M2 implementation was combined into this milestone.

### Findings and remediation

Initial scan (run 032) found RUSTSEC-2025-0020 and RUSTSEC-2026-0177 in PyO3
0.23.5; original JSON retained. Upstream reports first fully patched family
0.29.0. Cargo resolves the approved 0.29 constraint to **0.29.3**, recorded in
Cargo.lock and verified separately by cargo info/source metadata (run 038).
E-15 describes the fixed-family selection; 0.29.3, not 0.29.0, is the actual
installed/tested version. Binding replaces allow_threads with detach and marks
module gil_used=true. No architecture/public Python contract change, ignore,
waiver or unrelated dependency update. Graph shrank from 28 to 22 external
packages; 24 packages total including the two internal crates.

### Gate results and exact command evidence

- `bash scripts/check.sh`: [run 042](docs/evidence/m1/run-042-T-206-final-functional.log),
  PASS: Rust fmt/clippy -D warnings, focused Ruff/compileall, 7 Rust tests,
  release wheel rebuild/reinstall, import paths and 63 Python tests.
- `REDMUD_CARGO_AUDIT=/tmp/redmud-security-tools/bin/cargo-audit REDMUD_PIP_AUDIT_PYTHON=/tmp/redmud-pip-audit/bin/python REDMUD_SECURITY_OUTPUT=docs/evidence/m1/security bash scripts/security.sh`:
  [run 043](docs/evidence/m1/run-043-T-206-final-security.log), PASS: exact notices
  checked, Rust advisories refreshed, no Rust vulnerabilities/warnings/ignores,
  two pinned Python build/dev packages audited, none skipped, no known findings.
  pip-audit recommends dependency hashes; this is a tool warning, not a finding.
- `python scripts/update_notices.py --check --inventory docs/evidence/m1/license-inventory-final.json`:
  [run 041](docs/evidence/m1/run-041-T-206-final-static.log), PASS; source legal
  file hashes/expressions checked for all locked transitives, including target-
  specific/build-only packages. Wheel runtime Requires-Dist is empty. CPython
  3.11+ default requirements of pinned maturin/ruff are empty; extras not enabled.
- `maturin build --release --locked --out target/security-wheels` and
  `maturin sdist --out target/security-wheels`: [run 044](docs/evidence/m1/run-044-T-206-final-packages.log),
  PASS. Existing missing homepage/repository/documentation metadata warnings
  remain; no remote URL was invented.
- Clean venv wheel installation, `python -m unittest discover -s tests -v`
  and native cart example: [run 046](docs/evidence/m1/run-046-T-206-isolated-wheel.log),
  PASS, 63 tests and expected cart total 3500.
- `python docs/evidence/m1/verify-final-artifacts.py`: [run 047](docs/evidence/m1/run-047-T-206-artifact-acceptance.log),
  PASS; exact current notices present in wheel/sdist, empty Requires-Dist,
  PyO3/lockfile/scan package count matched. [Artifact hashes](docs/evidence/m1/final-artifacts.json).
- `python docs/evidence/m1/final-safety.py`: [run 048](docs/evidence/m1/run-048-T-206-final-safety.log),
  PASS; timeout-bounded depth/range/malformed/cycle/isolation subprocesses and
  no application unsafe blocks or Python eval/exec. Explicit depth-64 rejection
  remains T-202, not claimed by these process-survival probes.

### Licensing, data freshness and scope

[Final inventory](docs/evidence/m1/license-inventory-final.json) covers all 22
external locked Rust packages. Original MIT/Apache/Unlicense, target-lexicon
LLVM exception and unicode-ident Unicode-3.0 texts are retained in
THIRD_PARTY_NOTICES.md and built distributions. Full initial 28-package inventory
is retained separately for history. Build/dev tools maturin/ruff license files,
metadata and hashes are recorded; cargo-audit/pip-audit capabilities and license
files were inspected before installation. Tool-only security environment is
separate; scanners and their own dependency graphs are not product runtime deps.
No new mandatory Python runtime package or Rust runtime crate was introduced.

[Rust report](docs/evidence/m1/security/rust-advisories.json): 1422 advisories,
database commit 309392b18f6b17022f82c701f300433126901068, updated
2026-11-06T16:34:32+01:00. Final scan executed 2026-11-07T09:47:06Z.
[Python report](docs/evidence/m1/security/python-advisories.json): maturin 1.16.0
and ruff 0.17.4, zero findings, queried live through pip-audit/PyPI; no independent
immutable Python feed version is available. Both reports are dated evidence,
not a guarantee against unknown vulnerabilities. Full command/source identities
and initial failures remain in docs/evidence/m1/runs.jsonl.

### Milestone outcome, files and remaining work

Verified M1 acceptance clauses: FR-001/FR-002/FR-003/FR-004/FR-005 native contract
hardening; FR-006/FR-007 callback compatibility and safe outcomes; FR-008/FR-009
batch/stream policies/indexing; FR-011 profiling fixes; NFR-001 numeric boundaries,
NFR-003 scoped dependency/safety checks and NFR-006 local gates; GOV-002 traceable
execution. This is not a claim that every MVP clause in those requirements is
complete: M2/M3/M5 acceptance and the approved platform matrix remain outstanding.

This continuation changed crates/redmud-python/Cargo.toml and src/lib.rs,
Cargo.lock (security update), pyproject.toml (notice inclusion), notices,
scripts/security.sh and update_notices.py, requirements-security.txt,
development/architecture/English/Russian documentation and planning/evidence
ledgers. No existing test removed/weakened; no waiver. Performance delta NOT
MEASURED; M3 baseline remains planned. Other OS/Python combinations, CI runner
availability, fuzzing, enforced depth-64 limits, bounded metric cardinality and
sdist installation remain unverified/outstanding. No release/tag/publication.

Next milestone M2; next task T-201 (generated invariant fixtures), followed by
T-202 resource limits, T-203 metrics, T-205 isolated installation/platform CI.
No additional approval is requested for already approved M2 scope. This turn
ends with the M1 report and does not start M2.

Final closure structure/status check: `python docs/evidence/m1/closure-check.py`,
PASS ([log](docs/evidence/m1/closure-check.log)). All 10 M1 tasks and their
dependencies verified, all reference/AC/gate links resolve; M2 remains TODO.
Source snapshot and product/planning hashes: redmud-m1-verified-source.zip and
docs/evidence/m1/verified-source-sha256.json (excludes audit/build/cache files).

## T-201 — verified M2 task

AC-201: deterministic seed 20261107, 126 nested rows and independent oracle across input forms and execution modes, 500 numeric-edge cases, i128 Rust oracle and custom batch-length/fallback isolation; 8 Rust and 67 Python tests pass. No invariant defect was found; no fabricated failing-before result or new dependency.

Command `bash scripts/check.sh` exit 0: [full log](docs/evidence/m2/run-002-T-201-final.log); source identity and earlier failures in m2/runs.jsonl. G-BASE/G-STATIC plus focused acceptance passed; no performance comparison made. Task VERIFIED; this does not verify the full MVP requirement.

## T-202 — verified M2 task

AC-202: tests/test_limits.py (5 tests) and Rust depth_contract_tests cover depth 63/64/65, schema/literal/combined plan+expression budgets, 20000-deep JSON, 5000-node configuration, cycles, bounded subprocesses and infinite-source lookahead. 10 Rust / 72 Python tests and all static gates pass; security scan also passed (run 005). Semantics recorded in docs/contracts.md; no new dependencies.

Command `bash scripts/check.sh` exit 0: [full log](docs/evidence/m2/run-004-T-202.log); source identity and earlier failures in m2/runs.jsonl. G-BASE/G-STATIC plus focused acceptance passed; no performance comparison made. Task VERIFIED; this does not verify the full MVP requirement.

## T-203 — verified M2 task

AC-203 tests/test_metrics_bounds.py: fixed six-bucket histogram across 4000 sizes, exact summary counters and batch timing in both modes/all policies including empty calls; 500 dynamic types mapped to other with weakref release; disabled native metrics still profiles, deterministic idle-clock test. 10 Rust / 76 Python tests and static gates pass; no new dependencies.

Command `bash scripts/check.sh` exit 0: [full log](docs/evidence/m2/run-007-T-203.log); source identity and earlier failures in m2/runs.jsonl. G-BASE/G-STATIC plus focused acceptance passed; no performance comparison made. Task VERIFIED; this does not verify the full MVP requirement.

T-202 final review: reopened briefly during T-205 to cover schema allowed-value
depth (run 013 reproduces acceptance of a 65-deep allowed value). Guard added
and full regression/static suite rerun (T-202-final); task verified again, T-205
resumed. Earlier Linux package checks are pre-fix snapshots and are rerun for
final source identity; no historical log is rewritten.

## E-17 — M2 implementation and verification report (2026-11-07 UTC)

Status: T-201/T-202/T-203 VERIFIED; T-205 BLOCKED on actual hosted CI/macOS
execution. M2 is **not** fully VERIFIED. No M3 implementation or performance
budget/optimization started. No dependency, architecture or approved gate waiver.

### Implemented clauses and changed files

- AC-201 / FR-001…FR-009, NFR-001: tests/test_invariants.py uses seed 20261107,
  independent nested Python oracle (126 mixed records), 500 operator/edge cases,
  scalar/batch/stream and byte/string/dict equivalence, repeated-run index/value
  parity, input nonmutation, and custom Python batch-length/fallback isolation.
  Rust invariant_tests compare checked i64 math with an i128 oracle. Tests pass
  on addition; no fabricated failing-before result. Original tests retained.
- AC-202 / FR-002/FR-004/FR-009, NFR-002: crates/redmud-core/src/limits.rs,
  bounded json.rs conversion, semantic prepare/schema budgets, output-depth
  guard, binding plan parse limit, python/redmud/_limits.py and dictionary/config
  preflight. Tests in test_limits.py and Rust depth_contract_tests cover 63/64/65,
  combined nested maps/expressions, schemas/literals/allowed values, cycles,
  20000-deep valid/malformed JSON and 5000-node config in timed subprocesses,
  and infinite-source lookahead. Input/output JSON depth counts scalar leaves,
  root=1, max=64. No caller byte/width/expansion limit is claimed.
- AC-203 / FR-010, NFR-002: metrics.py fixed six buckets and exact scalar summary;
  both pipeline/runtime account completed calls (including empty) and batch
  durations before raise/skip. quality.py uses fixed builtin/Decimal/other
  labels. test_metrics_bounds.py exercises 4000 distinct sizes, 500 dynamic
  classes, weak-reference release, both modes/all policies, metrics=False
  profile behavior and deterministic idle-clock semantics. Migration documented.
- AC-205 partial / FR-012, NFR-005/NFR-006: scripts/package_check.py builds for
  the selected interpreter, installs wheel and sdist independently in fresh
  venvs, verifies isolated imports and runs all Python tests/examples outside
  the repository. scripts/check.sh now explicitly selects its active Python
  for maturin and separates wheels by CPython cache tag. No stale cross-version
  wheel installation. .github/workflows/ci.yml defines six approved platform/
  Python jobs and a separate security job, read-only permissions, retained
  evidence/artifacts and pinned official action SHAs.

No existing test removed/weakened. New tests add 13 Python and 3 Rust tests
relative to M1. Definition/metric snapshot details are in docs/contracts.md;
README English/Russian, architecture, migration and development docs updated.
No unsafe application code, new runtime dependency or connector/service added.
Developer-only CI actions are not library dependencies.

### Commands actually executed and results

Exact command/exit/source-identity history: [M2 run index](docs/evidence/m2/runs.jsonl).

| Check | Result / evidence |
|---|---|
| `bash scripts/check.sh` | Final PASS: 10 Rust tests, 76 Python tests; Rust fmt, clippy -D warnings, focused Ruff, compileall, rebuilt/installed release extension. [Run 022](docs/evidence/m2/run-022-M2-final-regression.log). |
| `python -m unittest tests.test_limits.TestLimits.test_data_boundary -v` before fix | FAIL: depth 65 accepted in dict/str/bytes (run 003). Fixed; subsequent suite PASS. |
| Schema allowed-depth regression before fix | FAIL in run 013; guard added; run 014 and final suite PASS. |
| `python -m unittest tests.test_metrics_bounds -v` before fix | FAIL: unbounded/exact-size labels, no summary, arbitrary type names (run 006). Final suite PASS. |
| `python scripts/package_check.py --python "$(uv python find 3.11)"` | Final PASS, CPython 3.11.17 wheel + sdist, each with 76 Python tests and native/cart examples. [Run 016](docs/evidence/m2/run-016-T-205-final-python311.log). |
| `python scripts/package_check.py` | Final PASS, CPython 3.12.14 wheel + sdist, each with 76 tests/examples. [Run 017](docs/evidence/m2/run-017-T-205-final-python312.log). |
| `python scripts/package_check.py --python "$(uv python find 3.13)"` | Final PASS, CPython 3.13.17 wheel + sdist, each with 76 tests/examples. [Run 018](docs/evidence/m2/run-018-T-205-final-python313.log). |
| `REDMUD_CARGO_AUDIT=/tmp/redmud-security-tools/bin/cargo-audit REDMUD_PIP_AUDIT_PYTHON=/tmp/redmud-pip-audit/bin/python REDMUD_SECURITY_OUTPUT=docs/evidence/m2/security bash scripts/security.sh` | PASS: current notices, Rust/Python dated scans, no known findings/skips/ignores. [Run 023](docs/evidence/m2/run-023-M2-final-security.log). |
| Shell syntax, focused Ruff/compileall for package runner; local YAML/config checks | PASS, [run 021](docs/evidence/m2/run-021-M2-final-static.log). YAML parse/shape is not hosted execution. |
| Git/CLI repository inspection | FAIL: not a Git repository (runs 019/020). Source remains ZIP/workspace; no origin/remote invented. |

[Linux package matrix](docs/evidence/m2/linux-package-matrix.json) records exact
artifacts/hashes. Current Python module bytes match each wheel, Rust source
bytes match each sdist. Documentation was updated after these package runs;
tested product code is unchanged. Source builds use pinned maturin 1.16.0 in
fresh install venvs without build isolation; no hidden workspace API imports.
Full sdist installs are now verified locally (M1 only built archives).

CPython 3.11.17/3.13.17 installed using existing uv 0.13.5 (run 008); 3.12.14
was already available. Linux x86_64, Rust 1.99.1, PyO3 0.29.3. No timing/RSS
comparison or performance threshold measured here; M3 remains gated. The
resource tests verify depth/lookahead/metadata cardinality and result release,
not a universal constant-RSS bound or unbounded per-record byte-size guarantee.

### CI evidence, missing information and blocked acceptance

[Upstream action pins](docs/evidence/m2/ci-action-pins.json): checkout v7.0.1,
setup-python v7.1.0, upload-artifact v7.0.2. Release tags resolved to immutable
commits; MIT license text and action.yml inputs/runtime captured before use.
Official [hosted runner reference](docs/evidence/m2/hosted-runner-reference.txt)
confirms Ubuntu 24.04 x86_64/macOS 15 arm64 labels; workflow asserts architecture.
Local parser is preinstalled PyYAML 6.0.3/MIT, not a new project dependency;
parser/license evidence captured. No third-party action code was executed locally.

Actual GitHub-hosted workflow jobs, artifact uploads and macOS installs/tests:
**NOT RUN**. No target repository was provided. Connected GitHub read-only searches
for RedMud and the legacy TCore name returned no matching accessible installed
repository ([search results](docs/evidence/m2/github-repository-search.json));
this does not assert that no repository exists globally or that GitHub is
unavailable. No remote repository, branch, commit, PR or publication was created.
A concise asynchronous request for the target repository URL was sent while
independent local verification continued; a URL is still needed to execute CI.

T-205 remains BLOCKED because its approved acceptance explicitly says config
alone is not evidence of a passing CI job; G-PKG requires the actual OS/Python
matrix. Cannot mark NFR-005/M2 verified from Linux checks alone. Remaining work:
identify/authorize the repository target, run the prepared workflow, inspect all
six matrix jobs plus the security job and repair any failures. No request to
waive/defer the approved platform requirement; no M3 advancement past the gate.

Final progress consistency check: `python docs/evidence/m2/progress-check.py`,
PASS ([log](docs/evidence/m2/progress-check.log)); references/dependencies/statuses
consistent and unavailable CI left BLOCKED. Reproducible source snapshot:
/workspace/redmud-m2-source.zip (partial M2, not a verified cross-platform release).
Product/planning file hashes in docs/evidence/m2/source-sha256.json; command
recorder preserved in docs/evidence/m2/execution-runner.py.

## E-18 — A-02 authorization and independent M3 work

User requests continuing tasks independent of blockers and will run blocked
steps from home. A-02 records this scheduling amendment: T-301 depends on verified
local correctness/resource/metric/security tasks, not on hosted CI. T-205 remains
BLOCKED, no platform claim or release gate waived. T-301 starts first; T-302/303
follow only after its evidence. T-304 numerical budgets still require explicit
approval; no optimization/FFI changes are authorized by scheduling alone.

## T-301 — verified M3 task

AC-301: six workloads, bytes/dict forms, complete value/index/status/error signatures checked across plain checked Python, Runtime and native/off; 10 Rust and 79 Python tests pass. Original TCore adapter also passes 960 legacy-inclusive outcome checks (separate log). Corpus excludes schema-invalid/overflow cases from timing because callback/native reporting differs; arithmetic/domain validation still executes for supported inputs. No runtime API/dependency change.

Command `bash scripts/check.sh` exit 0: [full log](docs/evidence/m3/run-001-T-301.log); source identity and earlier failures in m3/runs.jsonl. G-BASE/G-STATIC plus focused acceptance passed; no performance comparison made. Task VERIFIED; this does not verify the full MVP requirement.

## E-19 — T-302 reproducible baseline and corrected memory (VERIFIED)

NFR-002/NFR-004 measurement clauses: `benchmarks/run.py`, fixture tests and
[methodology/results](docs/benchmarks.md). Exact commands, exits and source
identities: [runs.jsonl](docs/evidence/m3/runs.jsonl), runs 003–013.
`bash scripts/check.sh` PASS (run 012): fmt/clippy/Ruff/compileall, 10 Rust / 81
Python tests; rebuilt/reinstalled release extension. No production API change.

`python -m benchmarks.run --profile baseline --repeat 5 --rss-repeat 3 --pin-cpu
--tcore-source /workspace/original/tcore-project/src --output docs/evidence/m3/baseline`
PASS, 60 cases, five timing + three RSS + one traced fresh process each; all
full-corpus outcome digests match the oracle. Equivalent TCore adapter included.
Linux CPython 3.12.14/Rust 1.99.1/PyO3 0.29.3; CPU 0. Environment/extension/source
hashes and measured source snapshots accompany each run. Outputs discarded by
batch, no retained full input/output corpus. Small/large batches, bytes/dicts,
metrics toggle covered; no arbitrary target or improvement claimed.

**Measurement correction:** original `ru_maxrss` RSS was invalid for clean child
comparison: controlled exec audit reproduced launcher high-water inheritance
[raw probe](docs/evidence/m3/rss-meter-audit.json). Timing remains usable; original
RSS is superseded, not silently removed. Changed Linux meter to `/proc` VmHWM,
added regression check and reran all 60 cases `--passes rss traced` into
`baseline-memory-corrected` (run 010). Repeated stream N=2000/100000 B=64 into
`stream-corrected` (run 011). Whole-process high water includes oracle/warmup;
tracemalloc excludes Rust heap. Non-Linux meter remains NOT VERIFIED.

`python docs/evidence/m3/analyze.py` PASS (run 013), checks identities, outcomes
and corrected RSS provenance, writes [joined summary](docs/evidence/m3/joined-summary.json).
Five timing samples/case and 25 batch latency samples at B1000 give exploratory
noise ranges/p95, not production confidence or approved thresholds. Sequential
cloud measurements have uncontrolled contention/frequency. No retention growth
proportional to stream count observed on this finite arithmetic fixture; no
universal constant-RSS claim. T-303 selected next; T-205 still BLOCKED.

## E-20 — T-303 native core and boundary experiment (VERIFIED)

NFR-004 component evidence: `benchmarks/components.py` and test-only
`crates/redmud-core/src/benchmark_probe.rs`, included under cfg(test); no public
API or production instrumentation/dependency changes. Same exact six JSONL
fixtures through release core/binding/public pipeline; exact serialized
core/binding equality plus independent oracle value/error parity for both byte
and dict public paths. Core's independent staged implementation matches full
production envelopes on all rows, including mixed failures.

`bash scripts/check.sh` PASS [run 014](docs/evidence/m3/run-014-T-303-static.log):
fmt/clippy/Ruff/compileall, 10 Rust passed / 1 diagnostic intentionally ignored,
81 Python passed, rebuilt release wheel and installed import paths recorded.
Ignored is not counted as a passing test. `python -m benchmarks.components
--repeat 5 --records 1000 --pin-cpu --output docs/evidence/m3/components` PASS
[run 015](docs/evidence/m3/run-015-T-303-components.log): built the release test
binary, **explicitly executed** that ignored diagnostic in 30 subprocesses and
verified its outputs. [Environment/build/source identity](docs/evidence/m3/components/environment.json)
and per-process raw ns samples retained. Binary SHA256 supplied for reproducibility;
not redistributed as a portable executable.

[Component method/table](docs/benchmarks.md) distinguishes core full, separately
instrumented parse/evaluate/envelope serialization, binding including all core,
Python decode, dict validation/encoding and public pipeline. Binding contains
FFI dispatch/conversion; dispatch alone is NOT observable and no new synthetic
API was invented to pretend otherwise. No exact additive time attribution or
native heap claim. N1000, five process medians with fixed phase order/warm caches
are diagnostic, not tail SLAs. Nested evaluation is substantive; measurements
do not support an indiscriminate FFI or parallel-engine rewrite. T-304 next.

## E-21 — T-304 proposal prepared; approval BLOCKED

[Performance proposal](docs/performance-proposal.md) and 60
[unapproved reference envelopes](docs/evidence/m3/candidate-budgets.json) derive
from all original timing/corrected-memory cases, not selected best samples.
Observed extrema proposed as same-environment review triggers, not portable hard
CI limits or invented percentages. Proposes adjacent home reference/candidate
runs, conservative repeated non-overlap benefit checks on arithmetic/multiple
derives and investigation of all other-workload duration/memory regressions.
Detailed raw scopes support T-401 investigation; they do not guarantee a gain.
T-402 remains conditional and no output/input conversion implementation occurred.

T-304 is **BLOCKED**, not VERIFIED: its acceptance explicitly requires user
approval of budgets and M4/defer decision, which has not been given. This is the
ROADMAP/AGENTS checkpoint, not the external CI issue A-02 permitted bypassing.
M3 measurement tasks complete locally, milestone approval incomplete. T-205
still BLOCKED; hosted/macOS NOT RUN; M4/M5 remain TODO. No release/publish claim.
[Russian home checklist](docs/home-verification.ru.md) provides concrete CI,
local install and repeated benchmark commands; no remote write was performed.

### Final independent M3 handoff checks

`python scripts/package_check.py --output target/m3-package-check` PASS
[run 016](docs/evidence/m3/run-016-M3-final-package.log), Linux x86_64 CPython
3.12.14: new wheel and independently built/installed sdist, each with installed
extension import check, **81 Python tests** and native/dataclass examples from
outside the source package. [Artifact metadata/hashes](docs/evidence/m3/final-linux-package.json).
Current M3 test changes are covered; historical M2 3.11/3.13 evidence remains
historical, no new macOS claim. This extra local check does not close T-205.

`python docs/evidence/m3/progress-check.py` PASS
[run 017](docs/evidence/m3/run-017-M3-progress.log): 20 requirement/24 task IDs,
acyclic dependencies/links, verified tasks have verified dependencies, exact
measured source snapshots match hashes, all 60 unapproved envelopes match the
reference and six component fixtures have real parity samples. T-205/T-304
explicitly BLOCKED; M4/M5 TODO; no active task or invented approval.

Delivery source archive: `/workspace/redmud-m3-source.zip`, includes code,
benchmark runners, evidence and home instructions; excludes build/cache/venv
products. It is a source snapshot with M2/M3 gates outstanding, not a verified
cross-platform release. No application dependency or public API was changed in
M3; Rust addition is a cfg(test) diagnostic. No M4 optimization was implemented.

## E-22 — T-205 local macOS verification (2026-11-08)

Scope authorized by current user request: read current planning/evidence, confirm
macOS, execute available Rust/Python/build/clean wheel and sdist installation
checks, record actual results, **do not start M4**. Archive instructions were
read as project context within this scope; they do not authorize later milestones.
T-205 was selected IN_PROGRESS for this local verification, then remains BLOCKED
on hosted acceptance. T-304 remains BLOCKED; M4/M5 remain TODO.

### Source and environment identity

The supplied `/Users/im01zhas/Downloads/redmud-m3-source.zip` was extracted into
`/Users/im01zhas/Documents/ChatGPT/RedMud`, which initially contained only `.git`.
Archive SHA256: `af4ae73ff4c36c14676061d31a16a02460dd0f13d30ca89797a2df14e473a050`.
[Pre-verification source hashes](docs/evidence/t205-macos/source-before.json)
identify restored product/planning bytes. Current Git repository has no HEAD or
remote: `git rev-parse --verify HEAD` exit 128, not a build/test failure
([log](docs/evidence/t205-macos/host-git-identity.log)). No commit identity,
remote write or hosted job is claimed.

[Environment log](docs/evidence/t205-macos/environment.log): actual Darwin,
macOS **26.6**, build **25G5028f**, **arm64**; Apple clang 21.0.0 and Command Line
Tools available. This is local macOS 26.6, not execution on the workflow's macOS
15 hosted runner. Native CPython **3.11.15 / 3.12.13 / 3.13.3** already available;
system default Python 3.14.5 was not used for approved matrix verification.

Rust was initially absent. Installed approved Rust **1.99.1**, rustfmt and clippy
with rustup under `target/t205-tools/{cargo,rustup}`, without modifying shell
startup configuration. Pinned maturin **1.16.0** / Ruff **0.17.4** installed in
separate task venvs from unchanged `requirements-dev.txt`. No runtime/dev graph
change or substitute tool version. Exact tool commands and results:
[run index](docs/evidence/t205-macos/runs.jsonl),
[Rust identity](docs/evidence/t205-macos/tool-versions.log),
[installed Python tools](docs/evidence/t205-macos/python-tool-versions.log).
The initial tool-version snapshot preceded completion of pip installation;
the separate Python tools snapshot records its completed state.

### Commands and local acceptance results

Commands ran sequentially, using the matching interpreter venv first in PATH,
plus isolated CARGO_HOME/RUSTUP_HOME. Reproduction setup:
[env.sh](docs/evidence/t205-macos/env.sh),
[matrix helper](docs/evidence/t205-macos/matrix.sh),
[command recorder](docs/evidence/t205-macos/run.py).
Every recorded subprocess log includes exact argv, cwd, UTC start and exit code;
run index also includes elapsed seconds. No benchmark was run concurrently.

| Native interpreter | `bash scripts/check.sh` | `python scripts/package_check.py --output target/t205-macos-package` |
|---|---|---|
| CPython 3.11.15 | PASS, exit 0: [check-311](docs/evidence/t205-macos/check-311.log) | PASS, exit 0: [package-311](docs/evidence/t205-macos/package-311.log) |
| CPython 3.12.13 | PASS, exit 0: [check-312](docs/evidence/t205-macos/check-312.log) | PASS, exit 0: [package-312](docs/evidence/t205-macos/package-312.log) |
| CPython 3.13.3 | PASS, exit 0: [check-313](docs/evidence/t205-macos/check-313.log) | PASS, exit 0: [package-313](docs/evidence/t205-macos/package-313.log) |

Each check script passed Rust fmt, clippy `-D warnings`, focused Ruff and
compileall, then Rust tests: **10 passed, 0 failed, 1 diagnostic ignored**.
It rebuilt/installed the matching release wheel and recorded installed Python
package/native-extension paths. Python discovery: **81 tests run, 80 passed,
1 skipped**, no failures. The skipped test explicitly requires Linux `/proc`;
it does not verify the macOS RSS meter. The ignored Rust diagnostic is an M3
measurement requiring fixture/output variables, not a passing correctness test.
Neither benchmark nor that diagnostic was executed in this T-205 work.

Each package command built a fresh release wheel with `--locked` and an sdist;
then installed wheel and independently built/installed sdist in **two fresh
venvs**, six installations overall. Each installation passed isolated `-I`
imports from its own prefix, full Python discovery (**80 passed / 1 skipped**),
and native/cart dataclass examples, using cwd outside source package. Build
backend maturin 1.16.0 was explicitly installed for the sdist path; installation
used `--no-deps --no-build-isolation`, as in the existing approved runner.
Temporary installation environments were removed after successful checks;
full import/test/example outputs remain in logs. Build products remain under
`target/t205-macos-package/Darwin-arm64-<version>/`.

[Artifact verification](docs/evidence/t205-macos/verify_artifacts.py),
[log](docs/evidence/t205-macos/artifact-verification.log) and
[artifact paths/hashes](docs/evidence/t205-macos/artifacts.json) check all three
wheels/sdists: wheel Python bytes match current modules, native Mach-O is arm64,
Requires-Dist absent, legal notices retained, sdist Cargo manifests/lockfile,
Rust and Python build inputs match current source. Wheel deployment tag is
macosx_11_0_arm64; execution was verified only on this macOS 26.6 host.

One orchestration error was observed and retained:
[helper incident](docs/evidence/t205-macos/orchestration-note.log). Editing the
running helper's env source path caused a stray shell command `ackage` to exit
127. Actual checks were separately recorded and exited 0; no failed product
check was hidden or treated as PASS. Final helper was syntax-checked. No product
fix, dependency change, assertion weakening or repeated test gate was needed.

### Remaining gates and outcome

Local macOS clauses of AC-205 / FR-012 / NFR-005 / NFR-006 now have direct
build/install/static/test evidence for all three approved Python minor versions.
**T-205 remains BLOCKED; M2 is not VERIFIED.** GitHub-hosted six-job matrix,
security job, artifact upload and macOS 15 runner execution: **NOT RUN**.
No configured target remote; local macOS results do not replace hosted jobs or
historical Linux evidence. Current advisory scanners were not rerun in this
Rust/Python/package-only task; E-16/E-17 scans remain dated historical evidence.

Changed files: TASKS.md, ROADMAP.md, EVIDENCE.md, home verification checklist,
and new `docs/evidence/t205-macos/` audit sources/logs/manifests. Product, tests,
benchmarks, manifests, lockfile and SPEC unchanged, checked against initial
hashes. Performance delta **NOT MEASURED**. No release/tag/publication. M4 not
started; T-304 budget approval remains outstanding. Next T-205 gate is actual
hosted workflow execution and review of all matrix/security jobs, once a target
repository is available. No gate waiver or new approval inferred.

Final evidence checks: `python docs/evidence/m3/progress-check.py` PASS, exit 0
([log](docs/evidence/t205-macos/progress-check.log)); task/requirement IDs,
acyclic dependencies, links and historical measurement identities checked.
Artifact verifier and helper syntax check also PASS, exit 0. Counts cross-checked
against all nine suite logs; [test summary](docs/evidence/t205-macos/test-summary.json)
retains passed/skipped/ignored distinctions. No local product test failed.


## E-23 — T-205 hosted CI execution (2026-11-08; IN_PROGRESS)

User supplied `https://github.com/01zhas/RedMud.git` after being asked for the
repository target to upload current project and execute Verify RedMud. This
authorizes that repository upload and T-205 workflow execution; no release,
performance budget or M4 work is authorized. Repository inspected through the
GitHub connector: public, empty, write access available. `git ls-remote` returned
no refs. Local authenticated Git CLI is used for initial source upload because
the connector create_commit API requires a parent SHA.

Local macOS results remain E-22. Hosted results will be appended only after
actual execution; T-205 is IN_PROGRESS, not VERIFIED. Root source snapshot,
retained historical evidence and current workflow are uploaded together. No
runtime implementation, lockfile or approved requirement changed.
