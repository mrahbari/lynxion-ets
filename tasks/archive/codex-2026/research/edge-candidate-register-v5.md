# Edge Candidate Register v5 — C-06 Market-Neutral Extreme Reversal

**Status:** PRE-REGISTERED — SHADOW RESEARCH ONLY

This protocol is frozen after TASK-0094 dataset integrity passed and before C-06 output is
generated. It is motivated by the archived Phase-6 extreme-reversion lead, not by inspecting
C-06 forward returns.

## Hypothesis

When cross-sectional short-horizon dispersion is unusually high, the weakest liquid major over
the prior 75 minutes should mean-revert upward and the strongest should mean-revert downward
over the next hour. Pairing both legs should reduce broad-market direction exposure. If
dispersion is ordinary, NO TRADE is preferred.

## Frozen Data and Features

- Dataset: TASK-0094 isolated Binance USDT-margined futures 15m panel.
- Universe: BTCUSDT, ETHUSDT, SOLUSDT, BNBUSDT, XRPUSDT, ADAUSDT; exact six-way aligned bars.
- Decision frequency: hourly, epoch-anchored (`timestamp % 3600 == 0`).
- Signal: each symbol's close-to-close return over the prior five completed 15m bars.
- Cross-sectional dispersion: median absolute deviation of the six signal returns.
- Regime threshold: current dispersion must be strictly above the rolling median of the prior
  2,880 completed dispersion observations (approximately 30 days); current dispersion is
  excluded from its threshold. Otherwise emit NO TRADE.
- LONG the single lowest-return symbol and SHORT the single highest-return symbol. Ties are
  resolved lexicographically by symbol for deterministic reproduction.

## Frozen Execution

- Enter both legs at the next 15m open and exit at the open four bars later (one hour).
- Charge 0.30% round trip per leg (0.10% fee plus 0.05% slippage per side).
- At most one position per symbol and exactly two positions per admitted pair. The next hourly
  entry may occur at the same open as the prior pair exit, after that exit.
- Missing bars reject the pair; fills and features are never forward-filled.

## Validation Gate

- Four chronological disjoint folds; pairs may not cross boundaries.
- Report per-leg and equal-weight pair N, net expectancy, PF, win rate, payoff, drawdown,
  deterministic decision-cluster bootstrap 95% CI, folds, sides, symbols, dispersion buckets,
  and cost sensitivity at 0.20%, 0.30%, and 0.50% per leg.
- `KEEP_FOR_FURTHER_VALIDATION` requires pair expectancy > 0 and PF > 1 at primary cost,
  cluster-bootstrap lower bound > 0, at least 3/4 positive folds with >=100 pairs each, LONG
  and SHORT leg expectancy both non-negative with >=100 observations each, at least four of
  six symbols non-negative, and no symbol above 30% of total positive leg PnL.
- Otherwise `REJECT`. KEEP does not authorize production or shadow deployment.

## Limitations

- Funding is unavailable and unmodeled; cost sensitivity must remain explicit.
- Fixed-horizon exits isolate selection quality and are not a production exit policy.
- The six-major fixed universe avoids current-listing selection but does not represent all
  contracts or delisted instruments.
