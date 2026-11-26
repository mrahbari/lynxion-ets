# E49 — H1 funding-settlement flow (2026-11-26)

**Method.** Pre-registered: `research/v2/experiments/e49_funding_settlement_flow.py`.
- Binance 1h lake with real settlement stamps. Liquid perps ≥ $20M/day, 2022–2026.
- At each stamp, form deciles by the previous funding rate.
- **POST:** long the top decile and short the bottom from T to T+1h.
- **PRE:** short the top decile and long the bottom from T−1h to T.
- **Control:** the same construction at T+4h, an hour without a stamp for 8h symbols.
- 8,529 stamp events and 8,529 control events.

| Leg | Window | Stamp gross bp | Control gross bp | Stamp − control | Net bp (stamp) | t | Symbols with sign |
|---|---|---|---|---|---|---|---|
| POST | DEV | +0.76 | +1.02 | −0.3 | −13.2 | 2.0 | 48 % |
| POST | TEST | +9.51 | +9.15 | **+0.4** | −4.5 | 10.0 | 61 % |
| PRE | DEV | +0.57 | −0.07 | +0.6 | −13.4 | 1.7 | 47 % |
| PRE | TEST | −0.58 | −0.09 | −0.5 | −14.6 | −0.6 | 51 % |

**Verdict: REJECT the mechanism.**
- There is no funding-stamp flow. The stamp hour behaves like any other hour; the stamp minus control difference is under 1 bp.
- The script's mechanical label "execution aid" (TEST gross ≥ 5 bp) is overridden by the pre-registered control, which shows the 9 bp is not a stamp effect.

**Side observation (not a new finding).**
- In 2025–26, high-funding names outperform low-funding names by about 9 bp per hour in *any* hour (t ≈ 9–10). In 2022–24 it was about 1 bp.
- This is the same phenomenon as E40: the short-carry book lost −78 %/yr on price in 2025–26, because crowded positive-funding names kept rising.
- At 14 bp per round trip it is not tradable hourly.
- It confirms that the price side of carry is the main risk for F1 in the current regime. R5 and the leg-correlation line already watch it.
