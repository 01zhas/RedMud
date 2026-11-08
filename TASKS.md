# RedMud task ledger — version 1

Status vocabulary: TODO (not started), IN_PROGRESS (one selected task), BLOCKED
(recorded unmet external gate), VERIFIED (all applicable acceptance evidence).
M0 approved by user on 2026-11-07 (E-10); implementation follows the gates below. A dependency
on a TODO task does not imply work has started. Current implementation coverage
is recorded in EVIDENCE.md, not retroactively labelled VERIFIED here.

All implementation tasks require G-BASE/G-DOC from ROADMAP.md plus the gates in
the table. DoD = stated acceptance + required checks PASS + inspectable evidence
+ no unexplained regressions + task/docs updated. Failed experiments are not
VERIFIED optimizations. AC-* labels below are **planned acceptance cases**, not
claims that named tests/files already exist. Existing test names appear only in
the traceability table and EVIDENCE.md.

## Planning delivery

| ID | Milestone / requirements | Dependencies | Acceptance / evidence | Status |
|---|---|---|---|---|
| T-001 | M0 / GOV-001 | None | Inspect all source/docs/tests/benchmarks/manifests; rerun build/tests; separate claims from facts; probes and commands captured; source identity recorded. E-01…E-08. | VERIFIED |
| T-002 | M0 / GOV-001, GOV-002 | T-001 | Five requested documents; MVP/deferred scope, unique IDs, acyclic dependencies, requirement/test/task coverage and approval gates; hash proof no app changes. E-09. Delivery verification is not user approval. | VERIFIED |

## M1 — Contract hardening (VERIFIED; E-16)

| ID | Requirements | Depends on | Atomic deliverable / acceptance | Gates | Status |
|---|---|---|---|---|---|
| T-010 | GOV-002, NFR-005 | T-002 | Record user approval and disposition of D-01…D-05; freeze codes/status/stage aliases, depth and metric snapshot rules; identify CI host. Unresolved decision blocks its consumers. No production code in this task. | G-DOC; decision links | VERIFIED |
| T-011 | NFR-006, GOV-002 | T-010 | Define one documented local check sequence with Rust fmt/clippy and focused Ruff/compileall; record reproducible dev tool installation/versions; AC-011: tools installed, actual checks pass without blanket suppressions; existing behavior unchanged. | G-STATIC, G-PY | VERIFIED |
| T-101 | FR-002 | T-011 | Validate native plan structure/paths/rule names once in prepare; AC-101: unknown ops, bad names/paths, duplicate/reserved rule codes rejected before source iteration; valid plan cached and builder copies stable. Error is safe ValueError. | G-CORE, G-PY, G-STATIC | VERIFIED |
| T-102 | FR-005 | T-101 | Recursive schema-definition validation; AC-102: unknown type/key, bad bound/type/range, nullable/allowed/fields/items combinations, implicit object/list type rules; valid nested schemas remain accepted; errors occur at prepare. | G-CORE, G-PY, G-STATIC | VERIFIED |
| T-103 | FR-001, NFR-001 | T-011, T-206 | Preserve supported integral JSON and dict input exactly and reject larger values; AC-103: bytes/str/dict parity around ±2^63, 2^64, ±2^53; no integer-to-float escape, nonfinite/cycles/nonstring keys/unsupported input rejected without affecting next row. | G-CORE, G-PY, G-SAFE, G-STATIC | VERIFIED |
| T-104 | FR-003, FR-004, NFR-001 | T-101, T-103 | Consistent expression evaluation and precise source/target paths; AC-104: each operator, checked under/overflow, left/right evaluation, same-kind equality, nonbool condition/check, lazy branches, missing/null nested operands, empty/overflow sum and nested index. | G-CORE, G-PY, G-STATIC | VERIFIED |
| T-105 | FR-007, FR-008, FR-009 | T-011 | Whole-batch outcome accounting and index/policy parity; AC-105: both modes × collect/raise/skip × scalar/batch/iter, mixed failures and multiple calls; processed equals consumed batch length even when raise returns no results; source exceptions/empty batches covered. | G-PY, G-STATIC | VERIFIED |
| T-106 | FR-011 | T-105 | Count profile inputs independently of yielded skip results; AC-106: valid+invalid sample reports both records, max_records bounded, no retained results, invalid args, cleanup on exceptions, preserves existing tracemalloc session; both modes. Do not redesign profiling API. | G-PY, G-STATIC | VERIFIED |
| T-107 | FR-006, FR-007, NFR-003 | T-104, T-105, T-206 | Apply approved result status/code/stage table at boundary; AC-107: parse/validation/transform/callback failures classified, no partial native value, warning/reject rules and custom batch replay intact, synthetic secret absent from errors/metrics by default; explicit detail opt-in retained. | G-CORE, G-PY, G-SAFE, G-STATIC | VERIFIED |
| T-206 | NFR-003, NFR-006 | T-011 | Dependency capability/license/advisory inventory with dated data and notices decision; AC-206: inspect all locked transitives and build tools, verify scanner CLI/license before use, run checks, resolve findings or request scoped waiver; no unsafe/eval introduced. | G-SAFE, G-STATIC | VERIFIED |

## M2 — Reliability and gates (T-201/T-202/T-203 VERIFIED; T-205 BLOCKED)

| ID | Requirements | Depends on | Atomic deliverable / acceptance | Gates | Status |
|---|---|---|---|---|---|
| T-201 | FR-001…FR-009, NFR-001 | T-102, T-107 | Deterministic generated regression fixtures using a specified seed and reference calculations; AC-201: scalar/batch/stream parity, replay equivalence, nested failures isolated, input nonmutation, custom callback length/fallback and all numeric edges. Persist minimized failures as fixtures. | G-CORE, G-PY, G-STATIC | VERIFIED |
| T-202 | FR-002, FR-004, FR-009, NFR-002 | T-101, T-103, T-104 | Enforce approved data/plan/expression nesting limit; AC-202: at/below/above limit, combined nested map/expression path, cyclic dict and malicious JSON in bounded subprocess tests; no panic/abort; infinite source lookahead bounded and invalid batch_size consumes zero. | G-CORE, G-PY, G-SAFE, G-STATIC | VERIFIED |
| T-203 | FR-010, NFR-002 | T-010, T-105, T-107 | Bounded metric summaries and documented accepted-output profiles; AC-203: fixed batch buckets/type-label set, processed/status/error invariants in both modes, all policies, metrics disabled, idle clock semantics, null/missing/numeric summaries, no input retention or payload labels. Snapshot migration documented. | G-PY, G-STATIC | VERIFIED |
| T-205 | FR-012, NFR-005, NFR-006 | T-010, T-201, T-202, T-203, T-011 | Automated approved OS/Python matrix, release-wheel and sdist clean installation; AC-205: each job runs gates, imports installed extension, executes tests/examples and saves logs/artifacts; sdist contains build inputs; no hidden workspace imports/runtime dependencies. Config alone is not evidence of a passing CI job. | G-PKG, G-STATIC | BLOCKED: source pushed to 01zhas/RedMud; hosted run 42440898200 failed before all 7 jobs started because GitHub account is locked for billing (E-23); hosted tests/security NOT RUN |

## M3 — Measurements (no optimization)

| ID | Requirements | Depends on | Atomic deliverable / acceptance | Gates | Status |
|---|---|---|---|---|---|
| T-301 | NFR-004 | T-201, T-202, T-203, T-206 | Equivalent workload fixtures/oracle for simple, nested parse, nested sums, multiple derives, validation-heavy and mixed rejects; AC-301: identical expected values/errors and work/retention scopes for plain Python, Runtime and native; bytes/dict split; optional baselines excluded unless equivalence demonstrated. | G-PY, G-PERF (fixture equivalence only) | VERIFIED |
| T-302 | NFR-002, NFR-004 | T-301 | Reproducible benchmark runner for throughput, batch p50/p95 latency, isolated-process peak RSS and separate tracemalloc; AC-302: warmup/initialization separated, raw samples/environment/hash/units stored, batch/metrics sweeps and bounded-stream run included; explain sample sufficiency and variance. | G-PERF, G-STATIC | VERIFIED |
| T-303 | NFR-004 | T-302 | Native-core versus end-to-end/boundary experiment using same fixtures; AC-303: independently timed scopes for parse/evaluate/serialization and Python conversion/dispatch where observable; no synthetic API exposed publicly; no Python allocations misreported as native heap. Store component method and limits. | G-PERF, G-CORE | VERIFIED |
| T-304 | NFR-004, GOV-002 | T-303 | Baseline report plus proposed per-workload thresholds justified by noise/use; identify bottlenecks and whether M4 is worthwhile; AC-304: explicit USER APPROVAL of budgets and M4/defer decision is recorded. Merely writing a proposal leaves task BLOCKED. | G-DOC, G-PERF (baseline report) | BLOCKED: proposal and reference envelopes ready; explicit budget/M4 decision pending (E-21) |

## M4 — Conditional experiments

| ID | Requirements | Depends on | Atomic deliverable / acceptance | Gates | Status |
|---|---|---|---|---|---|
| T-401 | FR-007, NFR-003, NFR-004 | T-304 | Replace JSON result envelopes with direct PyO3 output conversion only; AC-401: byte-for-byte contractual parity, object lifetime/refcount and GIL safety, repeatable target-workload benefit and approved latency/memory budgets. Revert if acceptance fails; record rejected experiment. | G-CORE, G-PY, G-SAFE, G-PERF, G-STATIC | TODO |
| T-402 | FR-001, NFR-001, NFR-004 | T-401 | Direct dict input conversion only if remaining costs justify it; AC-402: numeric/key/cycle/depth/input-nonmutation parity with bytes route; approved benchmarks pass; native-only work releases GIL; revert if unjustified. | G-CORE, G-PY, G-SAFE, G-PERF, G-STATIC | TODO |

T-304 can explicitly defer all of M4. T-401 success alone is not permission for
T-402 if input conversion has no measured value; record the scoped deferral.
A deferred task remains TODO/BLOCKED with a reason, never VERIFIED by waiver.

## M5 — Acceptance

| ID | Requirements | Depends on | Atomic deliverable / acceptance | Gates | Status |
|---|---|---|---|---|---|
| T-501 | FR-012, GOV-002 | T-304; T-402 or explicit M4 deferral | Update English/Russian README, API/migration/architecture docs and executable examples against approved behavior; AC-501: instructions work from a clean installed package and statements link to evidence; preserve legal attribution. | G-DOC, G-PKG | TODO |
| T-502 | FR-001…FR-012, NFR-001…NFR-006, GOV-002 | T-501 | Release-candidate traceability audit and fresh gate run; AC-502: every MVP clause has passing evidence, fresh CI/package/security/baseline evidence, no mandatory NOT RUN and no unresolved correctness failure. Produce report; request release approval, do not publish. | All gates | TODO |

## Requirement-to-test traceability

M1 closure: E-16 records T-206 findings/remediation, final security gate and clean
wheel installation. T-103/T-107 explicitly depend on T-206 verification to avoid
reintroducing an implicit milestone-level safety dependency. M2 progress is in E-17.

M2 acceptance evidence: tests/test_invariants.py (AC-201), test_limits.py plus
Rust depth_contract_tests (AC-202), test_metrics_bounds.py (AC-203). T-205 Linux
package checks pass for three Python versions (historical E-17). Local macOS
26.6 arm64 checks and independent wheel/sdist installs now pass for CPython
3.11.15/3.12.13/3.13.3 (E-22): each suite runs 81 tests, 80 pass and one Linux-only
test skips. Actual hosted matrix/security jobs remain NOT RUN; task/milestone
are not marked VERIFIED.

M1 acceptance evidence: tests/test_prepare.py (AC-101), test_schema.py (AC-102),
test_inputs.py (AC-103), test_expressions.py (AC-104), test_policies.py (AC-105),
test_profiling.py (AC-106), test_errors.py (AC-107). EVIDENCE.md records per-task
failures, passing reruns and scope limitations. The initial audit column below
is retained as historical context, not current defect status.

Existing tests below are verified only for their actual assertions, not entire
requirements. AC cases become real tests in their owning implementation tasks;
record exact test selectors and evidence IDs when they exist.

| Requirement | Initial audit coverage / gap (historical) | Completion tasks and planned acceptance |
|---|---|---|
| FR-001 | TestNative.test_arithmetic_inputs; gaps beyond-range/dict keys/cycles | T-103/T-201: AC-103/AC-201 |
| FR-002 | TestNative.test_condition_and_snapshot covers schema copy only; bad prepare unchecked | T-101/T-202: AC-101/AC-202 |
| FR-003 | TestNative.test_overflow/test_condition_and_snapshot; most operator edges absent | T-104/T-201: AC-104/AC-201 |
| FR-004 | TestNative.test_nested; Rust validation_tests::nested_and_empty_sum | T-104/T-202: AC-104/AC-202 |
| FR-005 | Rust validation_tests::schema_edges, TestNative.test_nested; definitions not validated | T-102/T-201: AC-102/AC-201 |
| FR-006 | TestRuntime custom batch/rules/nested_custom_parser cases; Pydantic NOT RUN | T-107/T-201: AC-107/AC-201; no mandatory Pydantic adapter |
| FR-007 | TestRuntime.test_parse_failure_is_isolated/test_transform_failure_is_isolated; native status discrepancy | T-105/T-107: AC-105/AC-107 |
| FR-008 | TestNative.test_policies, TestRuntime.test_fail_fast; no full mixed raise parity | T-105: AC-105 |
| FR-009 | TestRuntime.test_iterator_lazy_and_bounded, TestNative.test_stream_and_metrics | T-105/T-202: AC-105/AC-202 |
| FR-010 | TestQuality profile tests, TestRuntime.test_output_quality_profiles, TestNative.test_stream_and_metrics; cardinality/raise gaps | T-203: AC-203 |
| FR-011 | TestRuntime.test_profile_reports_and_bounded_input, native smoke; skip count wrong | T-106: AC-106 |
| FR-012 | Fresh Linux CPython 3.12 wheel/test/example checks only; sdist install and wider matrix missing | T-205/T-501/T-502: AC-205/AC-501/AC-502 |
| NFR-001 | Rust tests::overflow_and_isolation/schema_edges; corrupt oversized pass-through probe | T-103/T-104/T-201: AC-103/AC-104/AC-201 |
| NFR-002 | Lookahead unit tests only; no RSS/depth contract or cardinality bound | T-202/T-203/T-302: AC-202/AC-203/AC-302 |
| NFR-003 | Hidden callback exception tested; no full security/license/advisory gate | T-107/T-202/T-206: AC-107/AC-202/AC-206 |
| NFR-004 | Single-fixture exploratory benchmark only | T-301…T-304, conditional T-401/T-402 |
| NFR-005 | Linux CPython 3.12 only | T-205: AC-205 |
| NFR-006 | Rust fmt passes, clippy/Ruff unavailable, no CI | T-011/T-205/T-206: AC-011/AC-205/AC-206 |
| GOV-001 | This planning delivery; E-01…E-09 | T-001/T-002 |
| GOV-002 | Documents define future protocol; not yet approved/executed | T-010/T-011/T-304/T-501/T-502 |

## Progress protocol

Select one next unblocked task; set IN_PROGRESS before editing. Record test
selectors, command exit status, source/build identity, failures and fixes in
EVIDENCE.md. Only then set VERIFIED and update milestone progress. If an
architectural amendment is needed, stop affected work and propose the change;
never broaden a task silently. Report requirement clauses completed, files,
checks, measured deltas or NOT MEASURED, risks, assumptions and next task.
