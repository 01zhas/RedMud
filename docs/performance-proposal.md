# T-304 performance decision — DRAFT, NOT APPROVED

Evidence: [method and measurements](benchmarks.md),
[joined raw summary](evidence/m3/joined-summary.json),
[component scopes](evidence/m3/components/summary.json). This proposal does not
make M3 VERIFIED or authorize M4. T-205 hosted/macOS remains independently blocked.

## Proposed decision

Authorize **T-401 only** as a reversible direct-output-conversion experiment.
Arithmetic and multiple-derived-field workloads have substantial envelope
serialization/decoding/container costs; these are appropriate target workloads.
Preserve all result/error/numeric/depth/index/policy contracts. Retain the current
route until parity and the approved measurements pass; revert if benefits are
not repeatable. No Arrow/Rayon/DAG/framework/dependency work.

T-402 input conversion remains conditional: public dict costs are measurable,
but measure them again after T-401 before choosing a separate experiment.
Nested sums are dominated in part by evaluation; a direct-output experiment
cannot be assumed to solve that case. A correct MVP may defer all M4 instead.

## Proposed review budgets, not an SLA or automatic CI gate

Five samples on one cloud machine are insufficient to define portable numerical
regression limits. Propose using the **observed extrema** below as provisional
review triggers on the same machine/build/workload only, with no invented
percentage allowance. These are explicit numbers for review, not statistical
confidence bounds. A new machine requires a fresh adjacent reference run.

- Full 60-case matrix: retain min/median/max call duration, sample batch p95,
  maximum batch duration and corrected RSS min/median/max as the reference
  envelope in `evidence/m3/candidate-budgets.json` (not approved).
- For each candidate on a home machine: run unchanged reference and candidate
  sequentially with identical configuration, five fresh timing processes and
  three fresh memory processes, before considering these numerical triggers.
  Never compare home results directly to cloud rates to claim a regression.
- Review any candidate whose worst observed duration or RSS exceeds the adjacent
  reference's worst observed value. Investigate sample order/allocator/clock
  effects and rerun affected cases; do not automatically excuse it by choosing a
  percentage. Latency p95 is diagnostic until there are substantially more calls.
- For the target arithmetic/multiple-derives workload, require candidate duration
  range to fall below reference duration range in two independent adjacent
  repetitions before calling it a repeatable improvement. This conservative
  non-overlap rule avoids counting changes inside the observed noise as success;
  it is a proposed experimental decision rule, not a confidence interval.
- Any unexplained correctness, memory or other-workload regression blocks adoption.
  If the effect remains within noise, defer/revert rather than expand architecture.

The six native JSON-byte reference cases at N=5000/B=1000 are below. Duration is
sum of engine calls, not wall time including fixture/sink. RSS includes interpreter
and warmup, not native heap; extrema come from separate memory processes.

| Workload | Calls min / median / max ms | Sample batch p95 ms | RSS max MiB |
|---|---:|---:|---:|
| arithmetic | 26.52 / 26.60 / 28.09 | 5.676 | 17.46 |
| nested_json | 43.67 / 44.15 / 44.42 | 9.063 | 18.93 |
| nested_sums | 167.79 / 168.29 / 169.78 | 35.158 | 20.88 |
| multiple_derives | 41.80 / 42.70 / 44.71 | 9.169 | 18.05 |
| validation_heavy | 39.59 / 40.66 / 44.80 | 8.877 | 17.95 |
| mixed_rejects | 27.21 / 27.85 / 28.57 | 5.880 | 17.50 |

## Approval still required

The user must approve or amend the review rules/target workloads and choose
T-401 or explicit M4 deferral. Until then T-304 is BLOCKED, not VERIFIED, and
T-401/T-402 stay TODO. This checkpoint is required by ROADMAP performance decision
protocol and AGENTS authority rules; A-02 only bypassed the CI scheduling blocker.
A home repeat may justify different numerical limits; record that evidence and
approval before treating any number as a binding performance gate.

Remaining unknowns: macOS behavior, hardware/clock portability, production record
shape/size and acceptable workload-specific latency/memory trade-offs. No
universal records/s promise, exact native heap metric or automatic SLA is proposed.
