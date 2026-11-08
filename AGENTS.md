# RedMud engineering instructions

Applies recursively to this repository. User instructions take precedence.
This file is binding for subsequent work; it does not authorize new features.

## Authority and approval

Read SPEC.md, ROADMAP.md, TASKS.md and current EVIDENCE.md before work. Version 1 was approved on 2026-11-07 (E-10); T-010 recorded the contract decisions; M1 is verified in E-16. During the initial planning pass,
only planning/evidence documents may change; stop after delivering the plan.
No application, test, benchmark, manifest or existing example changes in that pass.
Audit commands/probes and build products are verification, not feature work.

After approval, SPEC is the contract, TASKS the progress ledger, ROADMAP the gate
order, EVIDENCE the factual record. Existing README/architecture claims do not
override inspected behavior. Resolve conflicts explicitly, never silently.
Record approval text/date/scope. Stop at M0, T-304 performance-budget approval,
and release publication; don't ask again for approvals already recorded.
An unforeseen contract/architecture/scope change requires a proposed spec
amendment and user approval before implementation of the affected work.

## Architecture and scope

- Rust core owns parsing, typed native plans, traversal, numeric evaluation,
  schema checks, native batches and structured errors. No Python/PyO3 in core.
- PyO3 binding owns conversion/lifetimes and GIL handling. Release the GIL only
  while no Python objects are accessed. Arbitrary Python callbacks remain Python.
- Python owns ergonomic APIs, callbacks, configuration and user-facing reports.
- Reuse the existing Processor/Runtime, plans, profiles, tests and examples.
  No rewrite without a scoped demonstrated defect or measured benefit.
- No connectors, I/O services, storage, schedulers, distributed runtimes,
  speculative plugin APIs, custom optimizers or automatic Python compilation.
- Serial execution remains MVP. Arrow/Polars/DataFusion/Rayon need a requirement,
  benchmark and approved amendment. Do not add any because they are fashionable.
- Native inputs are untrusted data; definitions are trusted developer config,
  nevertheless validate config and enforce depth bounds. Safe Rust by default;
  new application unsafe requires a documented safety argument and approval.
- Preserve legal attribution including historical TCore copyright in LICENSE.

## Dependency policy

Approved current direct crates: serde (derive), serde_json, PyO3; workspace
redmud-core is internal. Maturin is the build backend (currently >=1.7,<2).
Python runtime is standard-library-only. Retain Cargo.lock for reproducibility.
Current versions/capability/license evidence: E-08; do not assume newer releases
have the same APIs, licenses or safety properties.

Verified development tooling: rustfmt/clippy and focused Ruff checks in T-011. Pin/record actual versions when selected; do not invent
version numbers. T-206 (moved into M1 by E-14 approval) selects/verifies an advisory scanner
before installation.
T-206 selected cargo-audit 0.22.2 (MIT OR Apache-2.0) and pip-audit 2.10.1
(Apache-2.0) as isolated security tools; approved by A-01 and verified in E-16.
Existing PyO3 dependency is now 0.29.3 after advisory remediation, with unchanged
public Python contracts. Use current E-16 evidence alongside historical E-08.
No new runtime or dev dependency without a concrete task, justification,
capability/license verification and recorded graph change. Dependency changes
outside this approved list require approval. Optional examples must not become
mandatory dependencies. No blanket dependency upgrades as part of unrelated fixes.

## Task execution

1. Choose only the next unblocked task in the current milestone; mark IN_PROGRESS.
2. Inspect relevant code and tests. Distinguish OBSERVED, CODE-ONLY, NOT RUN,
   UNKNOWN and ASSUMPTION; never invent an API, fixture or existing test.
3. Make the smallest complete change, staying inside task/requirement scope.
4. Execute required gates in ROADMAP.md, including regressions against the actual
   changed native extension (rebuild/reinstall as necessary). Record import paths.
5. Compare with every acceptance clause. Capture failures before fixing them;
   a passing test count alone does not demonstrate contract correctness.
6. Update SPEC only for approved amendments; update TASKS/ROADMAP/EVIDENCE and
   affected docs/examples with real command/test/artifact references.
7. Mark VERIFIED only after objective acceptance and all mandatory gates pass.
   An unavailable check is NOT RUN and blocks required verification. Do not
   delete a failing test or weaken its assertion to pass a gate.
8. Report the milestone and stop at explicit approval boundaries. Do not combine
   unrelated milestones or start a deferred experiment without authorization.

## Verification and reporting

Use ROADMAP gates rather than duplicating them here. Tests must cover the
contract or defect, not merely mirror implementation. Generated tests use fixed
seeds. Test malformed inputs, overflow, null/missing, isolation, policies,
ordering, bounded iterators and secret redaction where relevant. Do not
parallelize benchmarks with builds or other benchmarks.

No performance claim without equivalent-work repeated release-build results.
No arbitrary threshold: collect baseline, justify budgets, obtain T-304 approval.
Report throughput, batch latency, RSS, traced Python memory and boundary scopes
separately; tracemalloc is not native heap/RSS. Record environment and raw samples.
A no-regression assertion requires an approved baseline and threshold.

EVIDENCE entries include task/requirement, source/build identity, exact command,
exit code, result/counts, artifact path and limits. Keep initial failures and
later rerun entries; never overwrite history to imply a check always passed.
NOT RUN is not PASS; missing information is UNKNOWN/ASSUMPTION. A security
scan is dated evidence, never proof that the library is universally secure.

Milestone report: completed requirement clauses and IDs, changed files, tests
and results, measured performance delta or NOT MEASURED, outstanding risks,
unverified assumptions, remaining tasks, next milestone and needed approval.
Do not claim a release, CI job or installation was executed without its log.

A-02 permits independent local M3 work while T-205 hosted/macOS execution is
blocked; do not treat that authorization as a passing CI result or as approval
of T-304 budgets/M4 optimization. Preserve the deferred user's CI checklist.
