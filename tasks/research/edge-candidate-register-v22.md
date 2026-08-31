# Edge Candidate Register v22 — C-23 Delta-Neutral Positive-Funding Carry

**Status:** OPENED — C-23 REJECTED

C-23 tests a new, non-directional mechanism: persistence of unusually positive completed
funding may compensate a cash-and-carry position that is LONG spot and SHORT the matching
USDT perpetual. This is not a continuation/reversal bet and does not reopen a rejected family.

## Frozen Data and Boundaries

- Symbols: BTCUSDT, ETHUSDT, BNBUSDT, XRPUSDT, ADAUSDT, SOLUSDT.
- Spot: the TASK-0118 official native 15-minute panel.
- Perpetual prices: the TASK-0094 official native 15-minute futures panel.
- Funding: the already acquired official Binance funding histories used by C-16.
- Primary outcome: 2024-01-01 through 2026-08-29. Four equal chronological folds are formed
  from eligible entry timestamps, without symbol-specific reshuffling.
- Temporal reverse: 2023-01-01 through 2023-12-31.
- Exact timestamp intersection only. Missing spot, perpetual, or funding timing rejects the
  event; no fill, interpolation, or nearest-bar match is permitted.

## Frozen Signal and Execution

- At a completed funding settlement `t`, compute the p75 threshold from the previous 180
  completed funding rates for that symbol, excluding the rate at `t`.
- The event is eligible only when the observed rate at `t` is strictly positive and strictly
  greater than that causal threshold. Warm-up failures are censused and excluded.
- Enter LONG spot and equal-notional SHORT perpetual at the first exact common 15-minute open
  strictly after `t` (`t + 900s`).
- Hold through the next official funding settlement and exit both legs at the first exact common
  15-minute open strictly after that settlement. The next funding rate is not used by the signal.
- Reject overlapping positions per symbol. Entries and exits use opens; no outcome-bar close,
  high, or low is used.
- Funding cashflow includes only settlements strictly after entry and at or before exit. A SHORT
  perpetual receives positive funding and pays negative funding.

## Frozen Economics

- Allocate one unit of notional to spot and one to the perpetual with no leverage assumption;
  gross capital is therefore two units.
- Capital-normalized gross return is `(spot long PnL + perpetual short PnL + short funding PnL)/2`.
- Primary round-trip cost is 0.20% of gross capital. It represents both legs' entry/exit fees and
  slippage after the same two-unit capital normalization. Sensitivities are 0.15%, 0.30%, and
  0.50%; costs are subtracted once from each completed pair.
- Report the spot leg, perpetual leg, basis component, funding component, gross pair return, and
  net capital return separately. No borrow yield, collateral yield, leverage benefit, or maker
  rebate is credited.

## Frozen Uncertainty and Gate

- Bootstrap 10,000 samples with fixed seed 230023, clustering all symbols by UTC entry date so
  simultaneous cross-symbol funding events are not treated as independent.
- Report aggregate metrics, four folds, all six symbols, annual cells, funding contribution,
  cost sensitivity, and maximum positive-PnL symbol concentration. Diagnostic cells cannot
  change the verdict.
- KEEP requires every condition: primary N >= 1,000; net expectancy > 0; PF > 1; clustered 95%
  bootstrap lower bound > 0; at least 3/4 folds positive with N >= 150 each; at least 5/6 symbols
  positive with N >= 100 each; positive-PnL concentration <= 30%; temporal reverse N >= 250 with
  expectancy > 0 and PF > 1; and primary expectancy remains positive at 0.30% cost.
- Any failed condition is REJECT. A pass is only KEEP_FOR_PROSPECTIVE_VALIDATION and cannot alter
  production, risk, symbol admission, trailing, or broker execution.

## Frozen Prohibitions

No threshold, lookback, holding interval, cost, capital denominator, symbol slice, fold boundary,
funding inclusion rule, or gate may change after the first outcome is opened. No orders are placed.

## Frozen Result

C-23 produced 3,407 primary pairs with -0.1914% net expectancy at 0.20% cost, PF 0, and a
clustered 95% interval of [-0.1924%, -0.1904%]. Every fold and every symbol was negative. Mean
capital-normalized basis return was +0.0019% and funding return +0.0067%, leaving only +0.0086%
gross carry before costs. The 2023 reverse was also negative (-0.1902%, N=1,033). Every economic
and stability gate except sample size fails; verdict **REJECT**. Machine report:
`docs/reports/edge_candidate_c23.json`.
