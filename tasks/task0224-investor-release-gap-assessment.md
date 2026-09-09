# TASK-0224 — Investor release gap assessment

## Scope

Reconcile the current repository and non-network evidence against the bounded investor
VST/shadow release. Make no runtime, broker, strategy, risk, or cohort change.

## Verified evidence

- Full suite: 1,040 passed and one optional import-layering test skipped.
- Repository VST risk caps remain 1,000 USDT portfolio and 21 USDT per order.
- Guaranteed-protection tests unwind after SL/TP failure and engage the kill switch if
  the unwind also fails.
- Trailing/profit-lock regression coverage remains green.
- Phemex initialization respects the explicit `enabled_brokers` boundary.
- The existing paper burst sent zero real orders and produced a valid ledger.

## Findings

- P0-IR1: the paper burst is contaminated by the persistent runtime cooldown journal;
  all 87 intended decisions were blocked, so it is not a deterministic demonstration.
- P0-IR2: there is no dedicated investor-demo launcher that structurally excludes
  production/authenticated execution paths.
- Current broker-side trailing and TASK-0185 runtime activation are stale evidence and
  cannot be presented as current facts.
- No strategy currently clears a defensible positive-edge floor; the initial release
  must use a no-trade shadow default and explicit limitation.
- Evidence packaging, reviewer index, optional layering gate, and dead-code inventory
  remain P1/P2 work.

## Verdict

`NO_GO — TWO DEMO-SCOPE P0 BLOCKERS; PROFITABILITY UNPROVEN`.

## Next

TASK-0225: isolate the existing deterministic paper burst from all persistent runtime
state and add exact repeatability/no-exchange-send tests. Do not add a launcher until
the underlying scenario is independently safe and deterministic.
