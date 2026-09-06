# Edge Candidate Register v30 — C-31 Spot-Led Perpetual Underreaction

**Status:** PREREGISTERED — OUTCOMES UNOPENED

C-31 tests a distinct cross-venue price-discovery mechanism: a large completed Spot move that is
only partially reflected in the same asset's perpetual may predict short-horizon perpetual catch-up.
This is not C-26's cross-symbol BTC lead, a basis-convergence trade, or a taker-flow continuation;
the aligned Spot-versus-perpetual return response has not been opened by prior candidates.

## Sequential-Policy Admission

- Mechanism family: cross-venue same-asset information transmission.
- Point-in-time inputs are exact native Binance Spot and USDT-perpetual 15-minute bars already
  normalized and integrity-gated; execution and funding use the perpetual only.
- One primary signal is frozen before any conditional forward return is calculated.
- A four-hour target can economically clear the frozen 0.30% round-trip friction; 0.50% remains a
  mandatory stress gate.

## Frozen Data and Boundaries

- Symbols: BTCUSDT, ETHUSDT, BNBUSDT, XRPUSDT, ADAUSDT, and SOLUSDT.
- Spot SHA-256: BTC `2b58717c3f464e84ab531db07f4263b4c83b52c2f6b460a5445ec150f9c5dec3`,
  ETH `79e83e1947022c51126093ef72ab97f0e38fe3d40851fed8c3ad5a15afce75fa`, BNB
  `29294ff4fe8c7ee52b3e35f36e944735c7fed09fb5e3878f0720d7ae3352c4c8`, XRP
  `a87b83e107e7536fa4e68b280c27700da9bd3f6dbd8b96ca8e39aa104c817455`, ADA
  `f081b9da47ce30e2746a235d6a78ad7269ef7add8d6738eac49ac8b1af7c5452`, and SOL
  `7ac0701eeb2b50ac30cd3575219ada620d567783a3cd10be98813f39869c9011`.
- Perpetual price and funding files and full hashes are exactly those frozen for C-28; the evaluator
  must enforce all 18 hashes before calculating outcomes.
- Primary: 2024-01-01 through 2026-08-29. Temporal reverse: 2023-01-01 through 2023-12-31.
- Only exact timestamp intersection is allowed; no fill, interpolation, nearest match, or resampling.

## Frozen Signal

- Decisions occur on exact hourly UTC boundaries using only completed bars.
- Spot and perpetual four-bar returns use the close at decision minus 15 minutes divided by the
  close at decision minus 75 minutes, minus one. Both exact endpoints must exist.
- For each symbol, calculate the causal p95 of absolute Spot four-bar return from the prior 4,320
  valid hourly decisions (approximately 180 days), excluding current.
- Require absolute Spot return strictly above both its causal p95 and 0.50%.
- Require Spot and perpetual returns to have the same nonzero sign and the absolute perpetual/Spot
  response ratio to be at most 0.50.
- Trade in the Spot direction on the perpetual: positive Spot return => LONG; negative => SHORT.
- No volume, taker, funding, OI, basis-level, regime, symbol-ranking, time, or diagnostic filter.

## Frozen Execution and Economics

- Enter at the exact perpetual open at the decision timestamp; exit at the exact open 16 bars/four
  hours later. Require all 17 perpetual timestamps to be contiguous.
- One position per symbol; retain earliest signal and reject overlaps.
- Include funding strictly after entry and at or before exit; LONG pays and SHORT receives it.
- Charge 0.30% round trip; report frozen 0.20% and 0.50% sensitivities.

## Frozen Reporting and Gate

- Four global chronological primary folds; fold-crossing trades are excluded. Cluster-bootstrap
  10,000 samples by UTC decision hour with seed 310031.
- Report alignment, warmup, shock, sign, response, path, and overlap census; N, expectancy, PF,
  win rate, drawdown, funding, costs, folds, sides, symbols, years, response ratios, and concentration.
- KEEP requires all: primary N>=300; expectancy>0; PF>1; clustered lower bound>0; >=3/4 positive
  folds with N>=50; both sides positive with N>=75; >=4/6 symbols positive with N>=40; every
  primary year positive with N>=50; maximum positive-PnL symbol concentration<=35%; reverse N>=150
  with expectancy>0 and PF>1; and positive primary expectancy at 0.50% cost.
- Any failed condition is REJECT. A pass is only `KEEP_FOR_PROSPECTIVE_VALIDATION`.

## Frozen Prohibitions

No shock, lookback, response ratio, direction, horizon, cost, funding rule, overlap rule, period,
symbol, fold, cluster, or gate may change after outcomes open. Diagnostics cannot alter the verdict.
No order or production strategy/risk/trailing/symbol/leverage change is authorized.
