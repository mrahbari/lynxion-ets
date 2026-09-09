# Lynxion Investor Release Roadmap

**Status:** ACTIVE — VST/SHADOW INVESTOR RELEASE; PROFITABILITY NOT YET PROVEN

## Release objective

Deliver a technically reviewable VST/shadow release that demonstrates deterministic
execution, fail-closed risk controls, reproducible evidence, and an active edge-research
pipeline. The release should contain avoidable losses as far as current evidence allows,
but it must not claim guaranteed break-even or profitability.

Investor delivery and long-horizon edge validation are separate tracks. C-11 and C-33
remain prospective research and do not block the initial release.

## Non-negotiable boundaries

- No real-money deployment or capital scaling before the applicable approval and evidence gates.
- No weakening of risk admission, mandatory protection, reconciliation, exposure limits,
  cooldowns, duplicate prevention, or fail-closed behavior.
- No strategy, exit, symbol, or threshold change based only on intuition or post-result slicing.
- Historical improvement is not presented as prospective or out-of-sample proof.
- If no strategy clears the release evidence floor, the investor build defaults to no-trade
  shadow/VST demonstration rather than knowingly admitting negative-expectancy flow.

## Workstream A — Release ground truth

1. Reconcile the dated release checklist against current source, tests, committed evidence,
   and read-only runtime artifacts.
2. Classify every release item as `VERIFIED`, `OPEN`, `STALE_EVIDENCE`, or `NOT_APPLICABLE`.
3. Produce the smallest release scope and a blocker list ranked P0/P1/P2.

Acceptance: no release-readiness claim depends on an old checklist or an unverified runtime
assumption.

## Workstream B — Loss containment and safety

Prioritize verified defects that can create avoidable loss independently of strategy edge:

- risk-admission bypass or unbounded/duplicate entry;
- missing, stale, or incorrectly attributed SL/TP protection;
- trailing/breakeven/profit-lock mechanical defects;
- Spot/Futures broker-routing or position-source mismatch;
- stale/incomplete market-data admission;
- restart hydration, reconciliation, and single-runner invariants;
- fee, funding, slippage, and partial-fill omissions in measured economics.

Each behavioral change requires problem evidence, root cause, a minimal patch, regression
tests, an economic counterfactual where applicable, and a `KEEP/REVISE/REVERT` decision.
Changing an exit because it looks better on already-opened trades is prohibited; it must
be preregistered and validated on a fresh boundary.

Acceptance: no known P0 loss-amplification path remains open in the investor scope. This
does not imply positive expectancy.

## Workstream C — Evidence-constrained strategy admission

1. Freeze a reproducible, cost-adjusted baseline after deduplication.
2. Admit only strategies/cohorts that meet the defined evidence floor; otherwise use a
   no-trade shadow default.
3. Report net expectancy, PF, drawdown, fees, funding, slippage, concentration, temporal
   folds, and uncertainty—not win rate alone.
4. Preregister one higher-frequency independent shadow candidate for a 7–14 day delivery
   signal only if it has a genuinely unopened outcome boundary.

The short window may produce `PROMISING`, `NEGATIVE`, or `INSUFFICIENT` evidence. It cannot
produce a durable-profitability claim. C-11/C-33 continue under their original frozen gates.

## Workstream D — Technical-review hygiene

Cleanup is optional and follows correctness work. Remove code only when all are true:

- repository search and call-path analysis show it is unreachable or superseded;
- it is outside dynamic/plugin/config discovery paths, or those paths are explicitly tested;
- focused and full regression tests pass after removal;
- deletion is isolated, reviewable, and reversible in its own commit.

Do not perform broad refactors, rename sweeps, style-only churn, dependency upgrades, or
architecture redesign for presentation. Prefer a dead-code inventory before deletion.

Acceptance: reviewers see less demonstrably unused code without behavior drift or noisy diffs.

## Workstream E — Investor package

- one-command VST/shadow startup with an explicit environment banner;
- deterministic demo scenario with no broker execution;
- concise architecture and data-flow diagram;
- current risk/safety evidence and known limitations;
- reproducible performance report with honest evidence labels;
- 30/90/180-day research and production-readiness roadmap;
- technical-review index linking critical modules, tests, runbooks, and evidence.

## Ordered execution

1. TASK-0223: freeze this release track and its claims.
2. TASK-0224: current investor-release gap assessment.
3. Close verified P0/P1 loss-amplification defects with isolated tasks.
4. Freeze cost-adjusted baseline and preregister any exit/strategy counterfactual.
5. Build and verify the VST/shadow demo package.
6. Perform evidence-based dead-code inventory and only then optional cleanup.
7. Run focused regression, full suite, deterministic demo, and independent technical review.
8. Freeze the investor release and publish explicit limitations and the continuing R&D plan.

## Release verdicts

- `DEMO_READY`: safe, reproducible VST/shadow demonstration; no profitability claim.
- `INVESTOR_REVIEW_READY`: demo plus technical-review package and no open in-scope P0.
- `PILOT_REVIEW_READY`: separate future gate requiring prospective economic evidence and
  operator approval; not part of the initial release.
- `NO_GO`: any open in-scope P0, non-reproducible economics, or misleading edge claim.
