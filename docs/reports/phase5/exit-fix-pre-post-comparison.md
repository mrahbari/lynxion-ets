# Exit-Layer Fix — PRE vs POST Comparison

_Compared on 108 matching (symbol,window,strategy) cells — symbols ['BTCUSDT', 'ETHUSDT', 'SOLUSDT'], windows [90, 180, 365]d. PRE = before exit-layer fixes; POST = after market-impact + SL/TP-geometry fixes. (FULL 108-cell matrix)._

| strategy | win% PRE→POST | total P&L PRE→POST | sharpe PRE→POST | verdicts POST |
|---|---|---|---|---|
| breakout | 3.2%→8.4% | -40340→-17612 | -0.51→-1.00 | {'NO_GO': 9} |
| crypto_breakout | 3.4%→9.6% | -45252→-19001 | -0.39→-1.03 | {'NO_GO': 9} |
| liquidity | 4.0%→10.0% | -40017→-6810 | -0.68→-0.51 | {'NO_GO': 8, 'DIRECTIONAL_NO_GO': 1} |
| mean_reversion | 3.2%→9.3% | -44234→-2692 | -0.45→-0.31 | {'INSUFFICIENT_DATA': 2, 'DIRECTIONAL_NO_GO': 2, 'NO_GO': 5} |
| momentum | 3.3%→7.5% | -48610→-2855 | -0.63→-0.31 | {'DIRECTIONAL_NO_GO': 4, 'NO_GO': 3, 'INSUFFICIENT_DATA': 2} |
| mtf_trend | 2.7%→8.1% | -47031→-23970 | -0.42→-1.30 | {'NO_GO': 9} |
| oi_footprint | 3.7%→10.0% | -35667→-6231 | -0.65→-0.54 | {'NO_GO': 9} |
| scalping | 4.0%→9.0% | -46942→-15269 | -0.36→-0.85 | {'NO_GO': 8, 'INSUFFICIENT_DATA': 1} |
| sweep_scalper | 50.0%→50.0% | -1268→-1241 | -0.04→-0.04 | {'INSUFFICIENT_DATA': 9} |
| trend_following | 2.7%→9.0% | -45669→-3887 | -0.43→-0.35 | {'INSUFFICIENT_DATA': 3, 'NO_GO': 3, 'DIRECTIONAL_NO_GO': 3} |
| volatility_breakout | 0.4%→1.1% | -3556→-197 | -0.58→-0.89 | {'DIRECTIONAL_NO_GO': 5, 'NO_GO': 4} |
| vwap_reversal | 3.2%→10.3% | -43008→-5400 | -0.55→-0.54 | {'NO_GO': 6, 'INSUFFICIENT_DATA': 1, 'DIRECTIONAL_NO_GO': 2} |

**Aggregate win rate:** 7.0% → 11.9%
**Aggregate total P&L:** -441594 → -105164

**GO/positive-edge strategies POST:** none

Interpretation: the win-rate lift quantifies how much edge the exit-layer bugs were destroying. Strategies still net-negative POST are genuine signal/edge questions (now measurable); proceed to per-strategy refinement.
