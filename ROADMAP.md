# RedMud roadmap — version 1

Status: APPROVED by user on 2026-11-07 (E-10). Order is dependency-driven, not a delivery-date promise.
Detailed task DoD and traceability live in [TASKS.md](TASKS.md); current facts in
[EVIDENCE.md](EVIDENCE.md). M1 VERIFIED (E-16); M2 partial: T-201/T-202/T-203 verified, T-205 blocked (E-17).

## Current progress

M0/M1 verified (E-16). M2 functional tasks T-201/T-202/T-203 VERIFIED:
10 Rust / 76 Python tests, seeded oracles, depth-64 enforcement and fixed-cardinality
metrics. Local Linux x86_64 CPython 3.11.17/3.12.14/3.13.17 wheel and sdist installs
pass with installed imports, all tests and examples outside the source directory.
T-205 local macOS 26.6 arm64 checks and clean wheel/sdist installations PASS for
CPython 3.11.15/3.12.13/3.13.3 (E-22): 10 Rust passed / 1 diagnostic ignored;
80 Python passed / 1 Linux-only skipped per suite. Historical Linux matrix
remains in E-17. Actual hosted matrix is NOT RUN. Current checkout has
an empty Git repository without HEAD or remote; no target hosted repository is
configured. M2 is not VERIFIED. A-02 authorizes independent Linux M3 work without waiving T-205.
M3 local progress: T-301/T-302/T-303 VERIFIED (E-19/E-20); T-304 BLOCKED
on approval of the [performance proposal](docs/performance-proposal.md).
[Home checklist](docs/home-verification.ru.md) covers the remaining user-run gates.
Hosted CI action remains: identify the repository, run the prepared workflow, inspect real
six-job matrix/security logs and fix any failures. No waiver or scope reduction.

## Milestones

| ID | Entry / dependencies | Deliverables and exit criteria | Gates / approval |
|---|---|---|---|
| M0 — Audit and specification | Existing source available | Five planning files, retained raw evidence, no product changes, all references/dependencies checked; T-001/T-002 | G-DOC; M0 APPROVED (E-10), not product certification. |
| M1 — Correct contracts | M0 approved; T-010 resolves contract decisions | Preparation rejects bad definitions; integer preservation; predictable expressions/errors; identical batch policy accounting; corrected profile counts; T-011, T-101…T-107, T-206 | G-BASE + focused G-CORE/G-PY; all AC-101…AC-107 pass; migration notes. Report and resolve any changed contract before next milestone. |
| M2 — Reliability and reproducible verification | M1 verified; platform/limit decisions accepted | Invariants and depth tests, bounded metrics, isolated package/CI matrix; T-201/T-202/T-203/T-205 | G-CORE/G-PY/G-STATIC/G-SAFE/G-PKG; no mandatory check NOT RUN; platform evidence required to claim support. |
| M3 — Trustworthy performance baseline | A-02: verified local T-201/T-202/T-203/T-206; equivalent fixtures reviewed; T-205 remains blocked separately | Correct workload oracle, reproducible timing/latency/RSS/boundary runs, raw samples and variance, proposed performance budgets; T-301…T-304 | G-PERF + regressions. **STOP for user approval of budgets and whether M4 is justified.** No arbitrary throughput goal. |
| M4 — Conditional boundary optimization | User approves T-304 proposal; evidence identifies boundary bottleneck | Direct result conversion, then dict conversion as separate reversible changes; parity and before/after evidence; T-401/T-402 | G-CORE/G-PY/G-SAFE/G-PERF and approved workload budgets. Revert an experiment that fails its acceptance rule; no Rayon. May be explicitly deferred. |
| M5 — Hardened MVP acceptance | M1/M2/M3 verified; M4 verified or explicitly deferred by user | Updated bilingual examples/contracts, fresh install and release candidate evidence against every MVP requirement; T-501/T-502 | All applicable gates, full traceability, no unsupported claims. **STOP for release/publication approval**; building local artifacts needs no extra approval. |

MVP completion requires FR-001…FR-012 and NFR-001…NFR-006 acceptance, not merely
passing the old suite. GOV-001 covers this planning delivery; GOV-002 applies
throughout. A performance baseline with honest limits can satisfy NFR-004;
M4 is not a prerequisite for claiming a correctness MVP. A high-performance
positioning claim still needs demonstrated workload-specific evidence.

## Shared quality gates

Every implementation task inherits G-BASE and G-DOC. Other gates are explicitly
selected in TASKS.md. Record exact commands, source/build identity, exit codes,
tests/counts and raw results in EVIDENCE.md. Statuses are PASS, FAIL, NOT RUN,
or justified N/A; an unavailable mandatory check blocks verification.

- **G-BASE:** read scope and acceptance; test the defect before/fix after when
  relevant; run `cargo test --workspace --locked` and installed-package
  `python -m unittest discover -s tests -v`; compare against current evidence,
  not just a historical count. Test changed code via a freshly built wheel or
  controlled development install; record import/extension paths. No lost tests.
- **G-CORE:** focused Rust cases for affected expression/schema/path/parser,
  integer boundaries, nested empty/malformed structures, deterministic replay;
  Python integration for behavior crossing FFI. Plan-only and binding-only
  changes need an explicit coverage rationale rather than irrelevant tests.
- **G-PY:** public API, result/status/error/index, policies, callback failure,
  skip/raise accounting, iterator consumption and unchanged regression cases.
- **G-STATIC:** `cargo fmt --all -- --check`;
  `cargo clippy --workspace --all-targets --locked -- -D warnings`;
  proposed focused `python -m ruff check --select E9,F63,F7,F82 python tests examples benchmarks`;
  `python -m compileall -q python`. Configuration/tool versions must be installed
  and recorded by T-011; Python reformatting is not a separate architecture task.
- **G-SAFE:** default secret-redaction fixtures, no unexpected application unsafe/
  eval/deserialization hooks; nesting/cycle/large-number subprocess tests with
  process timeout; lockfile/license review; advisory scan with dated database.
  RustSec/pip tooling choice verified in T-206. Feed unavailable => NOT RUN,
  not zero vulnerabilities. A finding requires a fix or explicit scoped waiver;
  a waiver never turns an unexecuted check into PASS.
- **G-PKG:** `maturin build --release --locked` and `maturin sdist`; install
  wheel in a new venv; separately build/install sdist, check dependency metadata,
  import both redmud and redmud._native, run full Python suite and native/cart
  examples outside the source package path. Execute the approved OS/Python matrix.
  `maturin sdist --locked` is unsupported by the currently installed maturin.
- **G-PERF:** release build; equivalent outputs, validation, errors and retention
  policy verified before timing; plan initialization/warmup separate; repeated
  isolated processes, raw timing samples, workload seed, machine/build identity;
  throughput, batch p50/p95, peak RSS and Python-traced memory clearly separated;
  metrics toggle, bytes vs dict, scalar vs batch and native-core/end-to-end views.
  Use approved thresholds only; control environmental variance. Never infer GIL
  speedup, zero-copy or native memory use from a Python-only timer/profile.
- **G-DOC:** update affected requirement/task, contract/migration/example and
  evidence links; check IDs, dependency cycles, local links; no undocumented API
  change. A docs-only task can mark implementation gates N/A with a reason.

## Performance decision protocol

Existing benchmark is exploratory: only one valid-record arithmetic fixture;
not an acceptable regression gate. T-301 adds simple arithmetic, nested JSON,
nested collection sums, several derives, validation-heavy and rejected-record
cases. Compare bytes and predecoded dicts at small/large record counts and batch
sizes 1/64/1000; these are experiment settings, not performance targets.

T-302 uses isolated processes and streamed sinks to avoid conflating retained
outputs with bounded engine memory. T-303 runs unchanged core/binding paths to
estimate serialization, FFI dispatch and result materialization costs without
calling subtraction of noisy end-to-end times an exact decomposition.
T-304 proposes per-workload budgets from observed dispersion and product use,
including permitted latency/memory regressions. User approves before a gate or
optimization commitment is created. If data are noisy, collect better evidence
instead of inventing a percentage. No deadline or universal Rust speed target.

## Decisions requiring approval or investigation

Approval of the specification accepts its proposed defaults unless the user
records an exception. Unresolved exceptions block only dependent tasks.

| ID | Proposed decision / unresolved part | Owner task / effect |
|---|---|---|
| D-01 | Preserve integral JSON exactly through i64/u64 pass-through; reject larger values; arithmetic stays i64. Parsing technique UNKNOWN until inspected/prototyped without weakening range checks. | T-010, T-103; closes observed corruption; no bigint API. |
| D-02 | Strict schema configuration and matching numeric bound types; representation-sensitive equality; nonbool check is a type error. These are intentional contract changes. | T-010, T-101/T-102/T-104. |
| D-03 | Whole-batch accounting before raise in both modes; retain legacy Python stage aliases. Choose and freeze reserved codes/status mapping in T-010 per SPEC. | T-010, T-105/T-107. |
| D-04 | Default nesting/plan/expression depth 64; verify safe combined recursion. Fixed batch buckets and fixed built-in type labels plus 'other'; proposed batch buckets 0/1/2–63/64–255/256–999/1000+ with count/sum/min/max. Confirm snapshot compatibility before coding. | T-010, T-202/T-203; changes current exact histogram. |
| D-05 | Linux x86_64/macOS arm64, CPython 3.11–3.13; GitHub Actions proposed, repository/remote and runner access UNKNOWN (workspace is not Git). | T-010, T-205; do not invent CI execution or initialize/publish a remote without authorization. |
| D-06 | No direct FFI rewrite until measurements justify it; no numeric performance budget yet. | T-304; separate user checkpoint even if this plan is approved. |

## Risks and mitigation

| Risk | Evidence / mitigation |
|---|---|
| Passing tests mask corruption | Oversized integer currently turns into float; T-103 before optimization, T-201 boundary/property tests. |
| Contracts diverge between modes | raise counters/profile counts differ from claimed behavior; shared policy table and fixtures T-105/T-106. |
| Direct FFI introduces new semantic differences | Conditional M4, byte/dict parity and refcount/lifetime tests; keep existing JSON route as comparison during experiment. |
| Resource claims exceed implementation | Current exact batch-size/type counters can grow; T-202/T-203 plus long stream measurement; no constant-byte promise. |
| Platform/tooling work blocks release | No current CI, clippy/ruff absent; T-011/T-205 explicit NOT RUN and support evidence rather than assumed portability. |
| Benchmark misleading or environment noisy | Single fixture, missing latency/RSS and component timings; M3 evidence gate before thresholds. |
| Dependency/license assumptions | Small direct graph retained; recorded license metadata is not a full license/security audit; T-206 includes transitives/notices/advisories. |

## Critical review and scope discipline

Reuse Rust Expr/Step/Plan, PyO3 module, Runtime/Processor, quality classes and all
useful tests/examples. There is no evidence justifying a rewrite, a DAG runtime,
a custom query optimizer, Arrow or a task-tracking service. Keep serde_json as
the representation until measured alternatives justify an amendment. Duplicate
JSON conversion is a suspected bottleneck, not permission for a large rewrite.

Five Markdown files plus evidence logs are sufficient for planning; no custom
spec framework or new app service. Invariant tests can start with seeded standard
library generators; property-testing dependencies are optional, not prerequisites.
Do not force performance work into a patch release: integer/status/schema fixes
can affect users and need explicit migration/release notes. Dates, RSS targets,
CPU speedups and CI availability remain uncommitted until evidence exists.
