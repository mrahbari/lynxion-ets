# TASK-0238 — Entry opportunity versus exit giveback classification

## Scope

Classify the already-opened 98-position diagnostic using only TASK-0180's frozen +10% MFE and
+5% retained-exit thresholds. Do not select a new threshold, simulate a new exit, or generalize
the result beyond the exact-linked subset established by TASK-0237.

## Frozen classification

| Class | Definition at confirmed 10x | N | Net PnL | Net-positive |
|---|---|---:|---:|---:|
| Opportunity retained | MFE >= +10%, exit >= +5% | 29 | +13.769234 | 29 |
| Opportunity giveback | MFE >= +10%, exit < +5% | 27 | -0.212963 | 22 |
| No +10% opportunity observed | MFE < +10% | 42 | -7.555204 | 23 |

The three classes partition all 98 exact-linked positions. Aggregate net PnL is +6.001067.

## Attribution

- **FACT:** 56/98 positions reached the preregistered +10% candle-extreme opportunity marker.
- **FACT:** 27/56 of those positions exited below +5%, so material profit giveback exists in
  this sample.
- **FACT:** the 42 positions that never reached +10% produced the largest realized economic drag,
  -7.555204, while the 29 retained-opportunity positions generated all gross group-level surplus.
- **INFERENCE:** this is a mixed failure, not an exit-only diagnosis. Entry/universe/regime
  admission must explain the no-opportunity group, while exit handling must explain the giveback
  group.
- **UNKNOWN:** whether excluding the no-opportunity group was predictable at entry time and
  whether a different executable exit would improve OOS net expectancy after costs.

## Limits

The sample is recent and post-hoc, MFE uses one-minute candle extremes, leverage is supported by
operator/account confirmation rather than the downloaded order rows, and there is no independent
policy holdout. This classification cannot authorize a strategy or trailing change.

## Next

Causally decompose the `<=25 USDT` and `MeanReversion` descriptive leads without treating position
size or strategy labels as causes. Freeze candidate predictors available at entry, then preregister
at most five independent hypotheses before opening their outcomes.

## Verdict

`KEEP — MIXED ENTRY-OPPORTUNITY AND EXIT-GIVEBACK FAILURE; NO POLICY ADMITTED`.
