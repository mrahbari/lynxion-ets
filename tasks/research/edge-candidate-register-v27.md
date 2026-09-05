# Edge Candidate Register v27 — C-28 Volatility-Sweep Rejection

**Status:** OPENED — C-28 REJECTED

C-28 tests a distinct market-structure mechanism: an unusually large completed 15-minute candle
that trades beyond a causal multi-day extreme but closes back inside that extreme may represent a
failed liquidity sweep, with short-horizon continuation in the rejection direction. This is not a
retune of a rejected momentum, funding, basis, OI, depth, or taker-flow candidate.

## Frozen Data and Boundaries

- TASK-0094 native Binance USDT-perpetual 15-minute OHLCV for BTCUSDT, ETHUSDT, BNBUSDT,
  XRPUSDT, ADAUSDT, and SOLUSDT, plus the existing official funding histories.
- Exact price-file SHA-256 values: BTC `30e02acebd29a4e47032be70baa7dd3ec0c38a246915fa8329e899edbc07aabb`,
  ETH `d44a16a5a7363d6833d0e4e60035acd63826e3e9f65fb3aef260e4c4fde08843`, BNB
  `7c9f289c34040f6228f8cdfe415fa045f641b2e7292108bf97bdde34db74c0c0`, XRP
  `89629283deadf39234f7d9cd07ad27f0e378c4c81e6d3a227798494667dcfd57`, ADA
  `643dc2f29d3e50fb008391fd4787472836dd88eeab7dd92f71ff0820b5dea79a`, and SOL
  `e6efc15ec3544227426076b059bcaec71a2557520d64433f08cea398c554a382`.
- Exact funding-file SHA-256 values: BTC `2fe89ca06907e7953cb49c2db052e74158ea9319f50f0bd9dac08fb2a579c097`,
  ETH `b978d9a54809ad232583b9419ed2695647d0557bc58074112082fa1472057148`, BNB
  `7edf30b5a20f5572361ba7bc41ff89b02df8105a82ff24c1b32a5dc807bca08d`, XRP
  `2886be913f6678b660e827d481a2b60d426de6c8b406bcff3c282d3f275e74f9`, ADA
  `f27f351e603c0563d9c1e0ea6be10640a8bf38c4a1640383d914cd5aaaa79301`, and SOL
  `be28b9621e6baf0d3b50365c73e59352996274f4097cae60fe4ffce2528c55a3`.
- Primary: 2024-01-01 through 2026-08-29. Temporal reverse: 2023-01-01 through 2023-12-31.
- Four global chronological primary folds formed from eligible entry timestamps.
- No interpolation, forward fill, nearest match, or synthetic candle. Reject every incomplete path.

## Frozen Signal

- All features use the completed signal candle and strictly earlier candles only.
- Compute the prior 96-bar high and low excluding the signal candle.
- Compute true range as `max(high-low, abs(high-prev_close), abs(low-prev_close))` and its causal
  2,880-bar p95 from true ranges strictly before the signal candle.
- Require signal true range strictly above that p95 and nonzero candle range.
- Bearish rejection: signal high is strictly above the prior 96-bar high, close is at or below that
  prior high, and upper wick `(high-max(open,close))/(high-low)` is at least 0.60; enter SHORT.
- Bullish rejection: signal low is strictly below the prior 96-bar low, close is at or above that
  prior low, and lower wick `(min(open,close)-low)/(high-low)` is at least 0.60; enter LONG.
- If both directions qualify on one candle, reject it as ambiguous. No trend, volume, funding,
  symbol rank, hour, weekday, regime, or diagnostic filter is allowed.

## Frozen Execution and Economics

- Enter at the next exact 15-minute open; exit at the exact open 16 native bars later (four hours).
- Reject a path unless all 17 entry-through-exit timestamps are contiguous.
- Permit at most one open position per symbol; retain the earliest signal and reject overlaps.
- Include official settlements strictly after entry and at or before exit. LONG pays funding and
  SHORT receives it.
- Charge 0.30% round trip. Report frozen 0.20% and 0.50% sensitivities.

## Frozen Reporting and Gate

- Report causal-lookback, range, sweep, ambiguity, path, and overlap census; N, expectancy, PF,
  win rate, drawdown, costs, funding, folds, sides, symbols, years, and positive-PnL concentration.
- Cluster-bootstrap 10,000 samples by UTC entry day with seed 280028.
- KEEP requires every condition: primary N>=500; expectancy>0; PF>1; clustered 95% lower bound>0;
  >=3/4 positive folds with N>=75; both sides positive with N>=150; >=4/6 symbols positive with
  N>=50; every primary calendar year positive with N>=100; maximum positive-PnL symbol
  concentration<=30%; temporal reverse N>=150 with expectancy>0 and PF>1; and positive primary
  expectancy at 0.50% cost.
- Any failed condition is REJECT. A pass is only `KEEP_FOR_PROSPECTIVE_VALIDATION`.

## Frozen Prohibitions

No lookback, percentile, wick share, direction, holding period, cost, funding rule, overlap rule,
period, symbol, fold, cluster, or gate may change after outcomes are opened. Diagnostics cannot
alter the verdict. No order or production strategy/risk/trailing/symbol/leverage change is allowed.

## Frozen Result

C-28 produced 986 primary trades with -0.2581% net expectancy, PF 0.6782, and a daily-clustered
95% interval of [-0.4258%, -0.0866%]. Every fold, side, symbol, and primary calendar year was
negative; expectancy was also negative at 0.20% and 0.50% costs. The 2023 temporal reverse was
negative (-0.3081%, PF 0.5804, N=518). Only the concentration gate passed. Verdict **REJECT**.
Machine report: `docs/reports/edge_candidate_c28.json`.
The report reproduced byte-for-byte on a second run; five focused tests and the full suite pass
with 876 passed and one optional import-linter skip.
