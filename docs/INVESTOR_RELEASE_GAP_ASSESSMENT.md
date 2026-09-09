# Investor Release Gap Assessment

**Date:** 2026-09-09

**Task:** TASK-0224

**Verdict:** `NO_GO — TWO DEMO-SCOPE P0 BLOCKERS; PROFITABILITY UNPROVEN`

## Scope and evidence classes

This is a repository and local non-network assessment for the bounded VST/shadow
investor release. It does not inspect a broker, reload the trading runtime, place an
order, or claim current exchange state.

- `VERIFIED`: reproduced from current source/tests in this task.
- `OPEN`: missing or currently failing in the investor-release scope.
- `STALE_EVIDENCE`: previously observed but not established for the current runtime.
- `NOT_APPLICABLE`: excluded from the initial VST/shadow release.

## Current matrix

| Area | Classification | Current evidence | Release consequence |
|---|---|---|---|
| Repository regression baseline | VERIFIED | `1040 passed, 1 skipped` in 53.70s | Strong technical baseline; layering gate still skipped. |
| VST execution caps | VERIFIED | Factory and guard fallback use 1,000 USDT portfolio / 21 USDT order caps; focused tests reject both limit breaches. | Repository protection is reviewable. |
| Mandatory protection failure | VERIFIED | Mocked BingX tests prove failed SL/TP triggers unwind; failed unwind engages kill switch. | Mechanical fail-closed behavior is covered locally. |
| Trailing/profit-lock mechanics | VERIFIED | Long/short, visibility, monotonic ratchet, retry, and restart hydration tests pass in the full suite. | Code may be demonstrated locally. |
| Current exchange-side trailing | STALE_EVIDENCE | Prior BingX VST observations proved automatic amendments, but no current broker query ran. | Must be labelled historical; not needed for a broker-free demo. |
| Stop-mutation admission patch | STALE_EVIDENCE | TASK-0185 is repository-ready; the known runner still predates deployment of that reviewed change. | Do not claim current-runtime activation. Broker-free demo remains possible. |
| Phemex activation boundary | VERIFIED | Adapter initialization respects `enabled_brokers`; focused test proves credentials cannot bypass a disabled flag. | Suitable for the bounded investor config. |
| Live profile broker list | OPEN (P1) | The dated `live` profile still enables BingX, Binance, MEXC, and Phemex and enables placements. | Must not be used by the investor demo; document/profile ambiguity requires containment. |
| Deterministic paper harness | OPEN (P0) | Current Phase-10 run sent zero real orders and verified its ledger, but all 87 decisions were `BLOCKED` because it read the repository's live cooldown journal. | Demo is not isolated or deterministic enough to present. |
| Safe investor entry point | OPEN (P0) | Main CLI exposes production modes; no dedicated fail-closed investor-demo command with broker execution structurally disabled is frozen. | Accidental use of the production alias must be impossible in the demo workflow. |
| Economic strategy admission | OPEN | Existing deduplicated evidence is negative; no candidate has a qualifying positive edge verdict. | Initial release must default to no-trade shadow and disclose this limitation. |
| Reproducible investor report | OPEN (P1) | Research artifacts exist, but no single release report binds commit, test result, economics, and evidence labels. | Required before investor review. |
| Technical-review index | OPEN (P1) | Critical modules and tests exist without a concise reviewer entry map. | Required before handoff to the technical team. |
| Layering contract | OPEN (P2) | Full suite skipped one optional `import-linter` gate because the tool is not installed. | Resolve only if available without introducing a paid or risky dependency. |
| Dead-code cleanup | OPEN (P2) | No evidence-based reachability inventory exists. Duplicate imports are visible but are not proof that modules are dead. | Inventory follows P0/P1 closure; no broad cleanup yet. |
| Real-money/live release | NOT_APPLICABLE | Explicitly outside the investor VST/shadow scope. | Separate future approval and evidence gate. |

## Minimum release blockers

### P0-IR1 — Isolated deterministic demo

The existing paper burst imports persistent runtime cooldown state, making its output
depend on whatever the trading system previously wrote. Fix by injecting a temporary,
empty cooldown store or a task-local risk enforcer. Prove all intended paper decisions
take the paper path, `real_sends_to_exchange=0`, and repeated runs are identical apart
from timing/path fields.

### P0-IR2 — Dedicated fail-closed demo launcher

Provide one explicit investor-demo command that cannot select production, authenticated
brokers, or external order paths. It must emit an environment banner, use temporary
artifacts, run the deterministic scenario, and fail if any exchange send is observed.

## P1 sequence

1. Freeze the current cost-adjusted baseline and no-trade admission verdict.
2. Produce a commit-bound investor evidence report and limitations statement.
3. Add a technical-review index for execution, guard, risk, protection, reconciliation,
   strategy, data validation, and the tests proving each claim.
4. Contain live-profile ambiguity in documentation/config preflight without altering
   real account settings or deploying a runtime.

## P2 sequence

1. Enable the optional import-layering check if the dependency is safely available.
2. Produce a dead-code inventory using repository references, entry points, dynamic
   discovery rules, and tests.
3. Remove only individually proven targets in isolated commits after the release-critical
   path is green.

## Decision

The current repository is a strong engineering baseline but is not yet
`INVESTOR_REVIEW_READY`. The smallest path is to fix demo isolation, add the dedicated
fail-closed launcher, freeze honest economics, and package evidence. Strategy tuning and
broad cleanup are not prerequisites and would increase delivery risk.
