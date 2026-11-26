# E46 — Cash-and-carry: long spot + short perp (2026-11-26)

**Question.** Can we collect funding without the price risk of the XS carry book?
**Method.** Pre-registered: `research/v2/experiments/e46_cash_and_carry.py`.
- P&L = funding received on the short perp + change of the perp-spot basis − costs.
- Costs: spot 10 bp + perp 5 bp + slippage, per side.
- 474 perps that have a Binance USDT spot pair.
- Returns are on capital: spot fully paid plus perp margin at 3×.
**Raw data.** `E46_cash_and_carry.csv`.

| Variant | Window | Net/yr on capital | Sharpe | Max DD | Funding | Basis | Cost | Names held |
|---|---|---|---|---|---|---|---|---|
| CC_TOP (enter ≥ 20 %/yr funding, exit < 5 %) | 2020–24 | **+12.0 %** | 8.6 | −0.4 % | +12.1 % | +0.2 % | −0.4 % | 4.4 |
| CC_TOP | 2025–26 | **+1.6 %** | 5.5 | −0.1 % | +1.6 % | +0.1 % | −0.2 % | 1.3 |
| CC_MAJORS (BTC + ETH, always on) | 2020–24 | +11.9 % | 10.2 | −0.6 % | +11.9 % | 0.0 % | 0.0 % | 2 |
| CC_MAJORS | 2025–26 | +3.0 % | 11.2 | −0.4 % | +2.9 % | 0.0 % | 0.0 % | 2 |

**Net/yr by calendar year**

| | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|
| CC_TOP | 12 % | 30 % | 0.2 % | 4.6 % | 12.7 % | 2.1 % | 1.0 % |
| CC_MAJORS | 16.6 % | 25.5 % | 1.9 % | 6.0 % | 9.4 % | 3.8 % | 2.0 % |

**FAIL** (rule: ≥ 8 %/yr in both windows).

## Reading

- **The construction works.** Price risk is gone: drawdowns are under 1 % and Sharpe is very high. The basis term is about zero.
- **The return source is gone.**
  - Positive funding on Binance perps has compressed: about 12 %/yr in 2020–24, about 2–3 %/yr in 2025–26.
  - That is below stablecoin yields, so the strategy is not worth running now.
  - This matches the carry-decay literature behind R5.
- **Contrast with XS-COMBO.** Its 2025–26 funding came mostly from being **long** names with **negative** funding (E41).
  Cash-and-carry cannot earn that side without borrowing spot to short it, which is expensive and often unavailable.
- **Squeeze risk while held:** a held name rose up to +102 % (2025–26) and +203 % (2020–24) in one day. 3–4 % of position-days rose more than 20 %.
  The perp margin must stay low-leverage and be topped up automatically if this is ever run.
- **No live implementation.** It is worth re-checking if funding regimes widen again. R5 already watches the funding level.
