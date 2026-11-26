# E50 — H2 cross-venue funding dispersion, Binance vs Bybit (2026-11-26)

**Method.** Pre-registered in commit ed87f09: `research/v2/experiments/e50_cross_venue_funding.py`.
- New data: Bybit public funding and 1h history, 60 symbols, 2021–2026, in `data/lake/bybit_linear`. 57 symbols were usable.
- Trigger: the 3-day funding spread between venues is at least 20 %/yr.
- Trade: short the dearer venue, long the cheaper, hold 7 days.
- Costs: 4 × 7 bp.

| Window | Trades/yr | Funding collected/trade | Price basis/trade | Net/trade | t | Win % | Yield on capital (2× notional) | Worst basis |
|---|---|---|---|---|---|---|---|---|
| DEV 2022–24 | 189 | +0.24 % | −0.01 % | **−0.05 %** | −3.3 | 38 % | −1.4 %/yr | −12.9 % |
| TEST 2025–26 | 177 | +0.23 % | +0.01 % | **−0.05 %** | −0.4 | 26 % | −1.2 %/yr | −3.3 % |

Spread persistence: median autocorrelation 0.80 at lag 1 day, 0.21 at lag 7 days.

**FAIL.**

## Reading

- **The mechanism is real; the economics are not.**
  - The venue spread exists and persists for days (lag-1 autocorrelation 0.80).
  - Price basis is about zero on average.
  - Each 7-day trade collects about 0.23 %, but taker costs (0.28 %) are slightly larger.
- **Even with maker fills on both venues** (about 0.12 % per trade, not modelled), the edge would be about 3 %/yr on
  capital. That is below a stablecoin yield, and it would add venue risk and a second account.
- **Rare basis shocks are a risk:** −12.9 % on one trade in 2022–24.
- **No account at a second venue is justified on this evidence.**
