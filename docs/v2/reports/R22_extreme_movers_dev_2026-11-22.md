# R22 — Cross-sectional extreme movers (operator idea), development period 2020–2024

Script: `research/v2/experiments/e6_r22_extreme_movers.py`; table: `R22_extreme_movers_dev.csv`;
12 trials logged in the trial registry (family R22).

Setup (daily, point-in-time): 7d return in top/bottom 10% of liquid names (ADV ≥ $10M), participation
(3d volume ≥ 1.5× prior 30d median), pullback 3–15% from 7d high (long) / bounce from 7d low (short),
resumption day; ATR stop (1.5 or 2.5×), 3×ATR trailing stop, time exit 10/20 days; 30 bp round trip
costs and funding included; SL priority on daily high/low.

| Variant | Trades | Win % | Avg net/trade | PF | Daily SR |
|---|---|---|---|---|---|
| Long+short, SL 2.5 ATR, 10d | 2,953 | 40.7 | +0.46% | 1.05 | 0.19 |
| Long only, SL 2.5 ATR, 10d | 2,866 | 40.1 | +0.27% | 1.03 | 0.08 |
| Short only, SL 2.5 ATR, 10d | 768 | 45.3 | −2.90% | 0.69 | −0.70 |

Year SR (best variant): 2020 −0.08, 2021 +1.01, 2022 −1.00, 2023 +0.61, 2024 +0.11.

## Verdict: REJECT (this specification)
- Long side earns only in bull years (2021, 2023); no stable edge after costs.
- Short side (fading weak names after a bounce) loses consistently, except 2022.
- Fails the dev survival rule (positive in ≥4/5 years, DSR, 2× costs).

## Caveats
- Daily bars: entry timing inside the day is not modelled; a 1h-timed entry is a different
  hypothesis and would need its own pre-registered test.
- Conditioning on regime (e.g. only in BTC uptrends) after seeing these years would be data snooping;
  not done.
