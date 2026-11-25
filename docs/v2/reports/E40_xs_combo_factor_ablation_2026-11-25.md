# E40 — XS-COMBO-V1 factor ablation (2026-11-25)

**Question.** Does each frozen ranking factor add value beyond the others, net of costs?
The factors are 21-day funding carry, 30-day Amihud illiquidity and 7-day taker imbalance.

**Scope.** This is evidence only:
- no live change;
- no new combination selected;
- no parameter, weight, lookback or rebalance-day search.

**Setup.**
- Script: `research/v2/experiments/e40_xs_combo_factor_ablation.py`, pre-registered in commit 23ba63a.
- Variants:
  - **A** = carry
  - **B** = carry + illiq
  - **C** = carry + taker
  - **D** = all three. D is asserted equal to the live V1 signal.
- Everything else matches the frozen baseline:
  - live-like universe;
  - 20 % long / 20 % short, gross 1, weekly rebalance;
  - lib.backtest cost model, funding cash flows, drift.
- All 7 rebalance phases, paired. No phase is selected.

**Status of the evidence: both windows are exploratory.**
- DEV (2020–24) is where the combination was designed, so increments there are biased upward.
- HOLDOUT_USED (2025-01..2026-10) has been seen before (V1 freeze, E30–E32, E38, E39).

**Raw data.** `E40_factor_ablation_by_phase.csv` and `E40_factor_ablation_comparisons.csv`.

## Per variant (mean of 7 phases; annual, fraction of gross-1 book)

| Window | Variant | Net | Price leg | Funding carry | Cost | Max DD | Net range over phases |
|---|---|---|---|---|---|---|---|
| DEV | A carry | +20.8 % | +11.3 % | +13.0 % | 3.5 % | −22 % | +17 … +24 % |
| DEV | B +illiq | +29.7 % | +23.8 % | +9.0 % | 3.1 % | −19 % | +25 … +33 % |
| DEV | C +taker | +22.5 % | +16.6 % | +10.6 % | 4.7 % | −25 % | +18 … +29 % |
| DEV | **D (V1)** | **+35.0 %** | +29.5 % | +10.0 % | 4.5 % | −18 % | +32 … +39 % |
| HOLDOUT_USED | A carry | **−32.3 %** | **−78.0 %** | +51.0 % | 5.3 % | **−64 %** | −47 … −16 % |
| HOLDOUT_USED | B +illiq | −0.6 % | −31.2 % | +34.6 % | 4.0 % | −33 % | −19 … +11 % |
| HOLDOUT_USED | C +taker | +20.3 % | −14.0 % | +41.4 % | 7.2 % | −27 % | +10 … +34 % |
| HOLDOUT_USED | **D (V1)** | **+30.4 %** | −3.7 % | +40.7 % | 6.6 % | −19 % | +13 … +43 % |

## Predefined comparisons

All values are paired. Holm correction is over all 10 comparisons.

| Comparison | DEV Δ/yr | phases + | Holm p | HOLDOUT Δ/yr | phases + | Holm p |
|---|---|---|---|---|---|---|
| illiq given carry (B−A) | +8.9 % | 7/7 | 1.00 | +31.7 % | 7/7 | 0.85 |
| taker given carry (C−A) | +1.7 % | 5/7 | 1.00 | +52.6 % | 7/7 | **0.015** |
| full vs carry-only (D−A) | +14.2 % | 7/7 | 0.18 | +62.7 % | 7/7 | 0.09 |
| illiq given carry+taker (D−C) | +12.5 % | 7/7 | 0.42 | +10.1 % | 5/7 | 1.00 |
| taker given carry+illiq (D−B) | +5.3 % | 7/7 | 1.00 | +31.0 % | 7/7 | 0.10 |

## Result against the pre-registered rule

- **illiq: NOT SUPPORTED.**
  - Every increment is positive.
  - But given carry+taker, only 5 of 7 phases are positive on HOLDOUT, and no comparison is Holm-significant.
- **taker: NOT SUPPORTED.**
  - Given carry, only 5 of 7 phases are positive on DEV.
  - Given carry+illiq, Holm p is 0.10.
- **The rule is strict.** The data cannot *prove* either factor's incremental value at the 5 % level. That is "not proven", not "harmful".
- **No comparison points the other way.** In 52 of 56 phase pairs (4 conditional comparisons × 2 windows × 7 phases), adding the factor helped.

## What this changes in our understanding (material)

1. **Funding carry alone is not an edge in 2025–26.**
   - Carry-only collected +51 %/yr funding but lost −78 %/yr on price: net −32 %/yr, max DD −64 %.
   - Names with crowded positive funding kept rallying, and shorting them cost more than the funding paid.
2. **The live edge is the combination.**
   - The price-based factors (illiquidity, taker flow) neutralise the price loss of the carry book.
   - Price leg: −78 % → −3.7 %. Funding is mostly kept (+51 % → +41 %).
   - The earlier summary "the edge is funding, price ≈ 0" (E2–E4) is true for the combination only. The ≈0 price leg is produced *by* the other two factors.
3. **Risk implication for R5.** The main tail risk of XS-COMBO is the carry leg's price exposure (squeezes of crowded names).
   - Funding indicators alone cannot show it.
   - The R5 realized P&L and drawdown lines (INFO) are the place to watch it.
   - The cluster-correlation indicator (R5 addition, below) measures whether the book's names move together.

## Decision

- XS-COMBO-V1 stays as frozen (D). Removing either factor is not supported. Every reduced variant was worse in every window on average.
- No factor is replaced and no new combination is proposed.
- Possible future direction, **not** started: a price-risk-neutral carry construction, e.g. carry ranked within volatility or beta buckets. It would need its own pre-registration and prospective validation. It is recorded only.
