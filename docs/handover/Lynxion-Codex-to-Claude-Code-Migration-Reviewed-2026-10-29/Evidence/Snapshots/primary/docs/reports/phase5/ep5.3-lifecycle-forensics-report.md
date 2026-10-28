# E-P5.3 Trade-Lifecycle Forensics — Evidence (no redesign yet)

_8355 realised trades across strategies × symbols × windows. Opportunity figures are COUNTERFACTUAL estimates from realised MFE/MAE under stated rules; in R-multiples (avg per-trade risk ≈ $3)._

**Baseline expectancy:** -1.094 R/trade  (~$-3.2/trade); win rate 15.2% (1270/8355).

## Distributions

- **Exit type:** {'TP': 3385, 'SL': 4970}
- **TP-hit:** 3385 (40.5%) | **SL-hit:** 4970 (59.5%) | **force_close:** 0 (0.0%)
- **R-multiple:** [('<-1.5', 3884), ('-1.5..-1', 1542), ('-1..-0.5', 589), ('-0.5..0', 1070), ('0..0.5', 1000), ('0.5..1', 248), ('1..1.5', 22), ('1.5..2', 0), ('>=2', 0)]
- **MFE (R):** [('<0', 0), ('0..0.25', 4812), ('0.25..0.5', 969), ('0.5..1', 1722), ('1..1.5', 656), ('1.5..2', 125), ('2..3', 57), ('>=3', 14)]
- **MAE (R):** [('<0', 0), ('0..0.25', 43), ('0.25..0.5', 978), ('0.5..1', 2356), ('1..1.5', 4304), ('1.5..2', 524), ('2..3', 125), ('>=3', 25)]

## Exit quality — B7 (SL/TP placement)

- **Mean realised R by exit type:** TP -0.255R · SL -1.666R · force_close +0.000R.
- **Reward leg (mean TP distance):** 0.51R — i.e. realised R:R ≈ 0.51:1 (target below 1R = structurally adverse).
- **TP hits that STILL lost money** (reward < round-trip cost): 2115/3385 (62% of TP exits).

## Opportunity analysis (expectancy left on the table)

- **Breakeven @ +1R:** 216 losing trades reached +1R first → +62.8 R total (~$186); per-trade ++0.008 R.
- **Breakeven @ +0.5R:** 1304 trades → +707.2 R (~$2,094).
- **Trailing (capture 50% of MFE):** 8172 trades gave back profit → +10644.7 R (~$31,527); per-trade ++1.274 R.
- **Trailing (full-MFE upper bound):** +12093.0 R (~$35,816).
- **Partial @ +1R (close 50%):** 216 losers reached +1R → +139.4 R (~$413); per-trade ++0.017 R.
- **TP set too early (MFE>realised on TP wins):** 1270 trades left +974.6 R on the table (~$2,887).

## Explicit answers (expectancy lost due to …)

1. **Stop placement:** losers that went favorable first (MFE≥0.5R) then stopped = 1304/7085 losers; recoverable via breakeven/trailing ≈ +707.2..62.8 R (~$2,094–$186).
2. **Take-profit placement:** TP-too-early left +974.6 R (~$2,887) on TP-hit winners; current TP≈0.51R.
3. **Missing breakeven:** +62.8 R (~$186) @ +1R trigger (216 trades).
4. **Missing trailing:** +10644.7 R (~$31,527) at 50% capture (upper bound +12093.0 R).
5. **Missing partial exits:** +139.4 R (~$413) @ +1R/50% (216 trades).

## Per-strategy lifecycle summary

| strategy | trades | exp R | win% | TP% | SL% | mean MFE_R | mean MAE_R | breakeven@1R (R) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| breakout | 1281 | -1.161 | 13 | 37 | 63 | 0.37 | 0.99 | +15.8 |
| crypto_breakout | 1139 | -1.077 | 15 | 41 | 59 | 0.35 | 1.02 | +8.3 |
| liquidity | 368 | -0.836 | 27 | 47 | 53 | 0.49 | 0.95 | +0.9 |
| mean_reversion | 199 | -0.865 | 28 | 41 | 59 | 0.45 | 1.00 | +0.9 |
| momentum | 95 | -0.977 | 18 | 35 | 65 | 0.39 | 1.06 | +0.6 |
| mtf_trend | 2040 | -1.137 | 12 | 40 | 60 | 0.32 | 1.00 | +14.7 |
| oi_footprint | 474 | -0.949 | 23 | 41 | 59 | 0.43 | 1.01 | +1.7 |
| scalping | 1425 | -1.175 | 12 | 42 | 58 | 0.31 | 0.99 | +12.3 |
| trend_following | 239 | -0.931 | 23 | 42 | 58 | 0.45 | 0.99 | +2.8 |
| volatility_breakout | 141 | -1.400 | 2 | 21 | 79 | 0.17 | 1.21 | +0.0 |
| vwap_reversal | 954 | -1.041 | 18 | 43 | 57 | 0.37 | 1.02 | +4.9 |

## Time-in-trade

NOT captured (entry-timestamp instrumentation pending) — add post-freeze.
