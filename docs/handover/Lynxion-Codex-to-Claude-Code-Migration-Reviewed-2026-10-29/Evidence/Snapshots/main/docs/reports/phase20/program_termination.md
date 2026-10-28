# Phase 20 — Program Termination

**Date:** 2026-06-13. Formal termination of the edge-discovery program. Documentation only — recommends a
disposition; does not deploy, touch secrets, or move funds. No profitability claimed.

## Termination decision

**The program is TERMINATED.** Phase 16 closed the OHLCV era; Phases 17–19 then extended the search to a
genuinely new data paradigm (microstructure, cross-exchange, lead-lag, funding×flow combinations). That
extension has now also concluded with **no deployable edge.** With the reachable search space exhausted,
no further analysis phase can change the verdict using available data and retail-grade execution.

## Why termination is justified (not premature)

A program should terminate when additional search cannot plausibly change the decision. That condition is
met:

1. **OHLCV is exhausted** — strategies, deployment, universe, and 7–9-year history all tested; READY=0 is
   robust and coverage-independent (Phases 5–16).
2. **Integrated non-OHLCV data is exhausted** — funding, open interest, order flow, liquidity,
   cross-exchange, lead-lag, and their combinations all tested; best results are WEAK/NO_EDGE, none
   deployable (Phases 13–14, 17–19).
3. **The remaining frontier is unreachable here** — L2 depth and historical liquidations are
   backtest-blocked; sub-minute/HFT lead-lag (where the Phase-18 cross-exchange catch-up *would* be
   captured) is below resolution and requires co-located execution this system does not have.

Continuing would re-test exhausted space or chase signals this system structurally cannot execute. Hence:
terminate.

## Final state (frozen)

- **Strategy register:** READY 0 / NEEDS_IMPROVEMENT 1 / INCONCLUSIVE 4 / INVALIDATED 5 / RETIRED 2.
  RETIRED slots **EMPTY** (no candidate — OHLCV, microstructure, funding, cross-venue, or combined — ever
  cleared the replacement bar).
- **Best information found (not edges):** cross-exchange catch-up (IC ≈ 0.10, latency-arb, sub-cost);
  funding capitulation on BTC/ETH (WEAK, fails SOL). Recorded as *research leads*, not deployable signals.
- **Infrastructure:** engineering-complete and testnet-validated (guard/risk/kill/breaker/ledger/journal/
  reconciliation-halt/preflight; 69/69 tests; 0 unauthorized sends). Preserved intact.

## Production disposition (carried from Phase 16, reaffirmed)

| Mode | Disposition |
|---|---|
| Live / real funds | ⛔ **NO-GO** — no edge **and** owner/operational gates (credential rotation, full soak, alerting creds, ledger segmentation) |
| Testnet · Paper · Research | ✅ **CLEARED** |

The microstructure phases do not change this: they found no deployable edge, so the "nothing profitable to
run live" basis for NO-GO is reinforced, not relieved.

## Closure actions

1. **TERMINATE** the edge-discovery program; do not open further analysis phases against the current data/
   execution envelope.
2. **PRESERVE & FREEZE** the validated safety infrastructure as the program's durable, reusable asset.
3. **RECORD** the two frontier leads (cross-exchange catch-up; funding capitulation) as *research notes*,
   explicitly flagged as **not edges** — to prevent a future restart from re-discovering and over-trusting
   them.
4. **Keep RETIRED slots EMPTY.**
5. **Owner security action:** rotate the historically-committed credentials (hygiene, independent of
   deployment) — flagged, never silently removed, per policy.

## Re-entry criteria (fixed order — unchanged)

Live deployment may be reconsidered **only** if, **in order:**
1. a signal first demonstrates a **positive, cost-adjusted, walk-forward-stable, cross-symbol,
   out-of-sample** edge — the bar nothing has met; **or** the execution envelope changes (co-located,
   fee-advantaged, sub-minute) such that a known sub-cost effect (e.g. the cross-exchange catch-up) becomes
   capturable — in which case it must be **re-validated** under realistic latency/fee assumptions, not
   assumed;
2. then the operational gates close (credentials, soak, alerting, ledger);
3. then a staged paper → testnet → minimal-pilot rollout under the existing guard.

Absent step 1, steps 2–3 are moot.

## What this termination does and does not claim

- **Does claim:** with integrated data and retail-grade execution, no deployable edge exists across the
  exhaustively-tested space; the program has no profitable strategy to run and should not trade live.
- **Does not claim:** that no crypto edge exists in principle. The Phase-18 cross-exchange catch-up is
  direct evidence that *real* microstructure edge exists at the HFT scale — it is simply outside this
  system's reach. A different execution paradigm is a different program, not a continuation of this one.

Final verdict → `final_phase20_verdict.md`.
