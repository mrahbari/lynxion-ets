# TASK-0239 — Small-notional and MeanReversion causal decomposition preregistration

## Status

`PREREGISTERED — OUTCOMES UNOPENED UNDER THIS CONTRACT`

## Question

Are the positive post-hoc `<=25 USDT` and `MeanReversion` baseline slices independent entry
signals, or are they aliases for one another, a calendar/risk-era change, symbol concentration,
or arithmetic scale effects?

## Frozen input

- Immutable TASK-0228 journal: `data/research/investor_release/trade_journal_baseline_v1.csv`.
- Resolve duplicate rows by the final row for each non-empty `trade_id`, exactly as
  `scripts/performance_attribution.py`.
- Cost-adjusted PnL is recorded PnL plus signed fees. Technical-demo strategies remain excluded.
- Known descriptive leads before this preregistration: `<=25 USDT` has N=719, expectancy
  +0.26954775 and PF 2.44223004; MeanReversion has N=106, expectancy +0.04093170 and PF
  1.29712322. These are discovery facts, not confirmatory outcomes.

## Frozen variables

- `small_notional`: entry price multiplied by quantity is `<=25` USDT.
- `mean_reversion`: canonical strategy label equals `MeanReversion`.
- Calendar block: UTC ISO week of `entry_timestamp`.
- Scale-normalized return: cost-adjusted PnL divided by entry notional; invalid/non-positive
  notionals are excluded and counted.
- Concentration dimensions: symbol, side, timeframe, calendar block, and strategy.
- Regime and confidence are excluded from causal interpretation because TASK-0228 found them
  missing for all 1,257 and 747 records respectively.

## Frozen analysis order

1. Report the 2x2 overlap of `small_notional` and `mean_reversion`: N, cost-adjusted PnL,
   expectancy, PF, win rate, normalized-return median, and fee/notional ratio.
2. Within every strategy with at least 30 observations in both notional bands, compare small
   versus larger trades using the same metrics.
3. Within every UTC week with at least 20 observations in both bands, repeat the comparison to
   expose risk-era/calendar confounding.
4. For the small-notional and MeanReversion leads separately, report top-one and top-three symbol
   shares of N and positive PnL. No symbol is removed after outcomes are viewed.
5. Run a trade-level bootstrap with seed `2309`, 10,000 resamples, and percentile 95% intervals
   for mean normalized return in each 2x2 cell. This is descriptive uncertainty, not OOS proof.

## Frozen interpretation

- `SIZE_ALIAS`: the small-notional lead disappears or reverses inside MeanReversion and the
  qualifying strategy/time strata, or its bootstrap interval includes zero.
- `STRATEGY_ALIAS`: MeanReversion disappears or reverses outside the small-notional band, or its
  bootstrap interval includes zero.
- `CONCENTRATED`: one symbol supplies more than 35% of positive PnL or the top three supply more
  than 65%.
- `TEMPORALLY_UNSTABLE`: qualifying weekly comparisons do not share the aggregate direction in
  at least half of eligible weeks.
- `DESCRIPTIVE_LEAD_SURVIVES`: both leads retain positive normalized direction outside their
  overlap, neither is temporally unstable, neither is concentrated, and relevant intervals
  exclude zero. This still requires a prospective/OOS hypothesis before edge admission.

## Boundary

No strategy, risk, sizing, symbol, leverage, trailing, runtime, broker, or cohort changes. Do not
reinterpret position size as a causal entry signal: it may encode different eras or risk policies.

## Next

Implement this contract once, freeze the artifact, and issue one of the named descriptive
verdicts. Only surviving entry-time predictors may enter the subsequent maximum-five candidate
preregistration.
