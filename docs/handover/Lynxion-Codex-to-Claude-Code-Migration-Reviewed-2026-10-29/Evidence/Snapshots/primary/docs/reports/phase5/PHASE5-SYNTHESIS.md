# Phase 5 — Consolidated Profitability Synthesis (Final Diagnostic Closure)

**Date:** 2026-06-11   **Status:** FINAL — closes Phase-5 diagnostics
(E-P5.2 Edge Measurement · E-P5.3 Lifecycle/Economic Viability · E-P5.4 MTF &
Portfolio · E-P5.5 Microstructure & Adaptation). No new analysis or experiments.

**Evidence base (all frozen/immutable):** 108-cell POST matrix
(`eval_matrix_POST_FROZEN_20260611.json`, 12 strat × {BTC,ETH,SOL} × {90,180,365}d);
8,380-trade lifecycle dump (`lifecycle_trades.json`, 90d, all longs); reports
`ep5.3-economic-viability.md`, `ep5.3-lifecycle-forensics-report.md`,
`ep5.4-mtf-portfolio.md`, `ep5.5-microstructure.md`; ledger `blocker-ledger.md`.

---

## 1. Profitability Blocker Ranking (impact · confidence · effort · reversibility)

Impact = effect on **net expectancy (R/trade)**. Confidence = strength of
evidence. Effort = implementation cost. Reversibility = ease of safe rollback.

| # | Blocker | Impact on net exp | Confidence | Effort | Reversibility | Net priority |
|---|---|---|---|---|---|---|
| **B14** | **Negative GROSS entry edge** — all 11 strategies lose −0.25R…−0.72R *before* costs | **HIGHEST** (the binding constraint; ~0.25–0.7R of the gap) | **High** (gross<0 every strategy, all cells) | **Very high** (signal R&D; may have no solution) | High (research, not a deploy) | **P1** |
| **B7 / B16** | **Adverse R:R + stops too tight vs cost** — reward leg 0.51R vs 1R risk; ~0.68R/trade cost cliff on 17 bps stops | **High** (~0.6R mechanical drag) | **High** (8,355 trades) | **Low** (TP/SL distances, R:R gate, turnover) | High (config) | **P2** |
| **B8** | Lifecycle logic (breakeven/trailing/partial) never called | Low–Med (cannot rescue gross<0; upside is an inflated upper bound) | Med | Med | High | P4 |
| **B10** | Portfolio correlation/heat offline-only — 0.83 corr, 1.25 effective bets, 1.6× hidden risk | **Risk only** (drawdown, not expectancy) | **High** | Med | High | **P3 (risk)** |
| **B4 / B15** | Shorts not SL/TP-tracked → effectively long-only; half the directional space unevaluated | Med (unknown; unmeasured) | High (8,380/8,380 longs) | Med | Med | P3 |
| **B12** | OHLCV-only → 4 micro-named strategies on proxy/stub features | Indeterminate (insufficient evidence) | High (structural) | **Very high** (L2/trades/OI/funding data) | High | P5 |
| **B9** | MTF `compute_trend()` mock → no HTF gate | **~Zero** (refuted: HTF gate *worsens* exp 0.027R/trade) | High | Med | High | **De-prioritised** |
| **B13** | Learning loop is a print stub; no adaptation | ~Zero (moot until edge exists) | High | Med | High | De-prioritised |
| B1 / B2 | Market-impact unit bug; inverted long SL/TP | (was catastrophic) | — | — | — | **FIXED** (76% loss cut) |

**Three orderings requested:**
- **By impact on net expectancy:** B14 ≫ B7/B16 > B4 > B8 > B10(risk) > B12 > B9 ≈ B13.
- **By implementation effort (low→high):** B7/B16 (config) < B8 ≈ B10 ≈ B4 ≈ B13 < B14 (signal R&D) ≈ B12 (data).
- **By ROI (impact ÷ effort, highest first):** **B7/B16** (high impact, low effort) > B10 (risk control, med) > B8 > B4 > B14 (high impact but very high/uncertain effort) > B12 > B9/B13 (~no benefit).

> ROI ranks B7/B16 first, but note: B7/B16 is **loss-reduction**, not edge creation.
> Even fully fixed, strategies remain gross-negative (B14). B14 is the true gate.

---

## 2. Strategy Status Matrix (final)

Definitions used: **Validated Edge** = net>0, stable. **Near Profitability** =
gross>0 or net within ~−0.10R. **Research Ready** = measurable on the trustworthy
framework, hypothesis intact, least-adverse gross — geometry/entry work *might*
surface edge. **Needs Redesign** = as-implemented structure (R:R/turnover) is
fundamentally adverse; substantial rework required. **Non-Viable** = no plausible
path on current evidence. (net/gross R = E-P5.3, 90d.)

| strategy | net expR | gross expR | win% | payoff | status |
|---|--:|--:|--:|--:|---|
| liquidity | −0.836 | −0.246 | 27% | 0.28 | **Research Ready** (least-adverse; micro-dep B12) |
| mean_reversion | −0.865 | −0.320 | 28% | 0.27 | **Research Ready** |
| trend_following | −0.931 | −0.339 | 23% | 0.21 | **Research Ready** |
| oi_footprint | −0.949 | −0.348 | 23% | 0.25 | **Research Ready** (micro-dep B12; insufficient evidence) |
| vwap_reversal | −1.041 | −0.364 | 18% | 0.23 | **Needs Redesign** (micro-dep B12) |
| momentum | −0.977 | −0.430 | 18% | 0.32 | **Needs Redesign** |
| crypto_breakout | −1.077 | −0.405 | 15% | 0.24 | **Needs Redesign** |
| mtf_trend | −1.137 | −0.448 | 12% | 0.23 | **Needs Redesign** (highest turnover) |
| breakout | −1.161 | −0.468 | 13% | 0.24 | **Needs Redesign** |
| scalping | −1.175 | −0.438 | 12% | 0.26 | **Needs Redesign** (most cost-sensitive) |
| volatility_breakout | −1.400 | −0.718 | 2% | 0.11 | **Non-Viable** (2% win; worst gross) |
| sweep_scalper | n/a | n/a | (≈4 trades) | — | **Insufficient Evidence** (micro-dep B12) |

**Counts:** Validated Edge **0** · Near Profitability **0** · Research Ready **4**
· Needs Redesign **6** · Non-Viable **1** · Insufficient Evidence **1**.

No strategy is removed: "Research Ready / Needs Redesign" mean the *implementation*
is unprofitable, **not** that the trading hypothesis is disproven (only
volatility_breakout, at 2% win, approaches hypothesis-level rejection).

---

## 3. Profitability Gap Analysis

All figures in R/trade (1R = entry-to-stop risk). Aggregate net expectancy
**−1.094R**; best strategy (liquidity) **−0.836R**.

**Distance to BREAKEVEN (net exp = 0):**
- Aggregate: **+1.094R/trade** required.
- Best strategy: **+0.836R/trade** required.
- Composition of the gap (aggregate): ~**0.68R** is mechanical (B7/B16 cost +
  adverse R:R — *addressable* by widening stops / R:R gate / less turnover); the
  residual ~**0.42R** is **negative gross edge (B14)** — requires real entry-signal
  improvement, for which **no path is demonstrated**.
- Even the *mechanically* best case (costs→0, stops widened) leaves the best
  strategy at its gross **−0.246R** — still short of breakeven by ~0.25R of pure
  signal edge.

**Distance to SUSTAINABLE profitability** (assume ~+0.25R net buffer to survive
drawdowns/regime drift):
- Aggregate: **~+1.34R/trade**; best strategy **~+1.09R/trade**.
- Of which only ~0.68R is mechanically recoverable; **≥0.5–0.7R must come from
  genuine entry edge that does not currently exist.**

**Portfolio overlay (B10):** even if per-trade expectancy were fixed, the 0.83
correlation / 1.25 effective-bets / 1.6× hidden-risk profile means realised
portfolio drawdown would exceed per-symbol backtests — a *risk* gap on top of the
*return* gap.

---

## 4. Final Conclusion — Does a real edge exist?

- **Does ANY strategy contain a real edge?** **No demonstrated edge.** Zero of 108
  cells and 0 of 11 evaluable strategies are net-positive; **none is even
  gross-positive.** No positive expectancy appears in any symbol, window, or regime.
- **Is edge masked (by costs/execution)?** **No — not by costs.** Execution bugs
  were fixed (B1/B2, −76% loss); the remaining cost cliff is large (~0.68R) but
  removing it still leaves every strategy **gross-negative**. The deficit is
  upstream of fees/spread/slippage, so it is **not cost-masked**.
- **Is edge masked by geometry?** **Unproven and unsupported.** Gross R is measured
  through the system's adverse 0.5R-TP / tight-SL exits, so in principle a latent
  entry edge could be suppressed by geometry. But nothing in the evidence positively
  indicates this: MFE is small (mean ~0.3–0.5R), win rates (12–28%) are far below
  even the ~67% needed at the current R:R, and trend context (E-P5.4) does not help.
  Confirming or excluding latent edge would require an entry-signal predictive study
  (forward-return independent of SL/TP) — **explicitly out of scope** and not run.
- **Or does no edge exist at all?** On **all available evidence, no edge is
  demonstrable.** The single unresolved possibility (geometry-masked latent edge)
  is speculative and unsupported by the data in hand.

**Net:** the binding constraint is **B14 — absent realised entry edge.** Every
other blocker is a loss-reduction or risk-control lever that cannot manufacture
edge. Fixing them improves *survivability of measurement*, not profitability.

---

## 5. Phase 5 Final Verdict

# → NOT READY (no edge)

No strategy contains a demonstrated edge; none is net- or gross-positive in any
tested configuration; the deficit is not explained by costs or execution. The
system is a **trustworthy measurement framework around strategies that, as
implemented and on the data available, have no realised profitable edge.**

- **Not** READY FOR PAPER TRADING — there is no positive expectancy to validate
  forward; paper trading would observe the same negative expectancy at risk-free
  cost of time only.
- **Not** CONDITIONALLY READY — no subset (symbol, window, regime, or strategy)
  clears breakeven, so there is no limited scope that qualifies.

**What Phase 5 achieved:** it made the system *measurable* (fixed two catastrophic
exit-layer bugs, built a trustworthy frozen baseline and per-trade forensics) and
**proved, with evidence, where the profitability deficit actually is** — in the
realised entry edge and risk geometry, not in execution plumbing or
microstructure mispricing. That is the correct, evidence-based foundation for any
future Phase-6 decision.

**This report formally closes Phase-5 diagnostics.** No remediation, optimization,
or new experiments were performed under this closure.
