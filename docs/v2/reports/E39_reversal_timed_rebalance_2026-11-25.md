# E39 — R6b: reversal-timed XS-COMBO rebalance, historical stage (2026-11-25)

**Result: HISTORICAL FAIL in both windows.** The prospective shadow stage is not started (the protocol requires a
historical PASS first). No live change.

## Protocol

- Script: `research/v2/experiments/e39_reversal_timed_rebalance.py`.
  - Pre-registered in commit 6f519e5.
  - Reporting-only columns (carry, price, cost, exposure, deferral share) were added in a separate commit before `--run`.
    The rule and the criteria are unchanged.
- **Rule (frozen).** On a weekly rebalance day, a trade is deferred by exactly one day when either:
  - it is a buy and the name's 1-day return is in the cross-sectional top tercile; or
  - it is a sell and the name's 1-day return is in the bottom tercile.
- **Same as the XS-COMBO-V1 baseline in every other respect:**
  - weights, live-like universe, Binance panel;
  - cost model (fee, ADV half-spread, sqrt impact);
  - funding cash flows;
  - drift between rebalances.
- **Comparison.** Paired within each of the 7 weekly rebalance phases. No phase was selected.
- **Windows.** 2020-01..2024-12 and 2025-01..2026-10 (the latter was already used).
- **Results are exploratory evidence only.** The 1-day reversal signal had already been seen on both windows in E31.

Raw table: `E39_reversal_timed_rebalance.csv` (all phases, both arms, all metrics).

## Paired results (E39 minus baseline; mean over the 7 phases)

| Metric | 2020–2024 | 2025–2026 |
|---|---|---|
| Net annual return | −0.3 pt (range −4.1 … +2.2) | −2.9 pt (range −9.3 … +3.4) |
| Phases improved | 4 / 7 | 2 / 7 |
| Net Sharpe | −0.01 | −0.11 |
| Price leg | −0.1 pt | −1.2 pt |
| Funding carry | −0.2 pt | −1.7 pt |
| Execution cost | 0.0 | 0.0 |
| Turnover (annual, x gross) | −0.02 | +0.03 |
| Max drawdown | −2.0 pt (3 phases worse by more than 2 pt) | −0.4 pt (2 phases worse by more than 2 pt) |
| Mean \|net exposure\| | +0.5 pt (1.0 % → 1.5 %) | +0.5 pt (1.4 % → 1.9 %) |
| Max \|net exposure\| | 12–21 % → 20–33 % | 9–22 % → 13–24 % |
| Trades deferred | 30 % | 33 % |

**Criteria.** Mean delta ≥ +1 %/yr and positive in ≥ 6 of 7 phases, in both windows. Neither window meets them.

## Observations

- **Turnover and cost are unchanged**, as designed. The rule moves trades in time; it does not add them.
- **Deferring entries costs carry.** The book holds the old weights for one more day, and carry fell in both windows.
- **Price timing is not positive.** The gross 1-day reversal seen in E31 does not translate into better fills for these trades.
- **Exposure gets worse.** Deferral makes the book temporarily less dollar-neutral, with larger peak net exposure.
- **The phase spread is large.** Baseline Sharpe by phase is 0.50–1.77 in 2025–26, while E39's paired deltas range −9 to +3 pt. Phase noise dominates any timing effect.
- Note: phases 0 and 1 in 2020–24 are identical. The first eligible day falls after both start offsets, so there are 6 distinct phases there.

## Decision

- R6b is rejected. The prospective shadow stage is not run.
- XS-COMBO-V1 stays unchanged: same weekly schedule, same immediate execution.
- No follow-up optimization or related experiment is started from this result.
