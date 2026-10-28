# Phase 5 — System Readiness Assessment (Closure)

**Date:** 2026-06-11  **Basis:** frozen POST baseline
`data/results_storage/eval_matrix_POST_FROZEN_20260611.json` (108 cells = 12
strategies × {BTC,ETH,SOL} × {90,180,365}d, 1m data), PRE baseline
`eval_matrix_PRE_FROZEN_20260611.json`. This is the formal Phase-5 decision
report. No optimization, no new architecture, no scope extension.

---

## VERDICT

# → NOT READY — BLOCKERS REMAIN

The evaluation framework is now **trustworthy** (two catastrophic exit-layer bugs
fixed; losses cut ~76%), but **no strategy is profitable in any tested
configuration**. Zero of 108 cells are net-positive; zero strategies earn a GO
verdict. The system is suitable for **continued research/diagnosis only** — it is
not ready for production live trading, and does not yet meet the bar for
meaningful paper trading (there is no measured positive expectancy to validate
forward).

---

## 1. Strategy validity — are any strategies actually profitable after corrections?

**No. 0 / 108 cells profitable. 0 / 9 positive cells for every one of the 12
strategies. 0 GO verdicts.**

Verdict distribution (POST): **GO 0 · NO_GO 73 · DIRECTIONAL_NO_GO 17 ·
INSUFFICIENT_DATA 18.**

Per-strategy aggregate (9 cells each), best→worst total P&L:

| strategy | total P&L | trades | avg win% | positive cells |
|---|---:|---:|---:|---:|
| volatility_breakout | −197 | 510 | 1.1% | 0/9 |
| sweep_scalper | −1,241 | 17 | 50.0%* | 0/9 |
| mean_reversion | −2,692 | 873 | 9.3% | 0/9 |
| momentum | −2,855 | 809 | 7.5% | 0/9 |
| trend_following | −3,887 | 1,411 | 9.0% | 0/9 |
| vwap_reversal | −5,400 | 1,694 | 10.3% | 0/9 |
| oi_footprint | −6,231 | 2,133 | 10.0% | 0/9 |
| liquidity | −6,810 | 2,040 | 10.0% | 0/9 |
| scalping | −15,269 | 5,779 | 9.0% | 0/9 |
| breakout | −17,612 | 7,220 | 8.4% | 0/9 |
| crypto_breakout | −19,001 | 7,534 | 9.6% | 0/9 |
| mtf_trend | −23,970 | 9,450 | 8.1% | 0/9 |

\* sweep_scalper's 50% win rate is on **17 trades total across 9 cells** →
INSUFFICIENT_DATA in all 9; the win rate is not statistically meaningful.

Win rates cluster at **7–10%** with R:R-style targets — i.e. trades are being
stopped out far more often than they reach target. This is an entry-precision /
trade-management signal, not a strategy-hypothesis disproof, so no strategy is
classified "Needs Redesign" on this evidence. Classification: **all 12 = Research
Ready / Insufficient Evidence** — measurable now, none validated.

## 2. Stability of edge — consistent across BTC/ETH/SOL and 90/180/365?

**Not applicable in the positive sense: there is no positive edge to be stable.**
The only consistency is consistent unprofitability — every strategy is negative
across all three symbols and all three windows (0/9 positive for each). No
strategy shows a regime/symbol/window pocket of profitability that survives the
edge gate. There is therefore **no stable edge** to carry into paper trading.

## 3. Execution correctness — are fills, SL/TP, and lifecycle reliable?

**Substantially improved, not yet fully reliable.**

- **Fixed & verified:** B1 market-impact unit bug (entries inflated ~5%) and B2
  inverted SL/TP geometry for longs (domain/infra enum mismatch). Combined effect
  was catastrophic; their removal cut aggregate loss **−441,594 → −105,164
  (~76%)** and lifted win rate **7.0% → 11.9%**. Long-side SL/TP geometry is now
  correct.
- **Still open (reliability gaps):**
  - **B4 — short positions are not SL/TP-tracked** (SELL-when-flat opens a short
    without lifecycle registration → shorts only ever force-close). Short-side
    execution is therefore **not** reliable; the system is effectively long-only
    for evaluation purposes.
  - **B7 — SL/TP emitted as placeholder, single-TP only** (no entry zone /
    invalidation / TP-ladder / R:R pre-gate).
  - **B8 — breakeven / trailing / partial / time-stop lifecycle logic exists but
    is never called** → winners not protected or extended.

Conclusion: long-entry fills and SL/TP are now correct; **short-side and the
trade-lifecycle layer are not yet reliable.** This alone bars production.

## 4. Risk of false confidence (overfitting / artifact recovery / residual bias)

**High — and explicitly flagged.**

- **The 76% improvement is artifact recovery, not edge discovery.** It is the
  removal of two bugs that were destroying P&L; the system moved from
  *catastrophic* loss to *moderate* loss. **It remains loss-making everywhere.**
  Reading the recovery as progress-toward-profit would be a false-confidence
  error; it is progress-toward-*measurability*.
- **No overfitting risk yet** (no tuning/Hyperopt/curve-fitting was performed —
  by design), but equally **no out-of-sample validation, no WFO** has been run.
- **Residual data bias:** all three symbols have **only 1-minute history**; every
  window (incl. 365d ≈ 525k bars) runs on 1m. There is no multi-resolution
  corroboration, and the MTF strategies (B9 mock trend) and microstructure
  strategies (B12 OHLCV-only proxies) cannot realize their named edges on this
  data. Any apparent result is single-resolution.
- **Small-sample traps:** 18 INSUFFICIENT_DATA cells (notably all of
  sweep_scalper); their metrics must not be read as signal.

Multiple major uncertainties remain → per the closure rule, the system is marked
**NOT READY**.

---

## What this verdict does and does not say

- It does **not** disprove any trading hypothesis. No strategy should be removed.
  Every strategy is now *measurable* on a trustworthy framework — that is the real
  Phase-5 achievement.
- It **does** say that on current evidence there is no demonstrated positive
  expectancy anywhere, short-side and lifecycle execution are unreliable, and the
  data is single-resolution. These are blockers, not verdicts on the strategies.

## Open blockers gating readiness (from `blocker-ledger.md`)

B4 (shorts untracked), B7 (placeholder SL/TP), B8 (uncalled lifecycle logic),
B9 (mock MTF), B10 (portfolio offline), B11 (SL/TP not structure-aware),
B12 (OHLCV-only microstructure), B13 (open learning loop). The 7–10% win-rate
pattern points first at B7/B8 (entry precision + unprotected/​unextended trades)
as the highest-likelihood expectancy leak — to be confirmed by E-P5.3 lifecycle
forensics **if/when** Phase-5 execution mode is reopened.

## Phase-5 closure state

Per instruction, **Phase 5 is formally concluded for decision-making purposes**
with the verdict **NOT READY — BLOCKERS REMAIN**. The corrected evaluation
baseline is frozen and immutable. No further analysis, epics, optimization, or
architecture changes were initiated.
