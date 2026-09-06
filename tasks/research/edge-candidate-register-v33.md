# Edge Candidate Register v33 — C-34 Cross-Venue Aggressive-Flow Divergence

**Status:** PRE-REGISTERED — OUTCOMES SEALED

C-34 tests whether aggressive Spot flow contains information when same-asset USD-M perpetual flow
leans the other way. The new causal moderator is venue-of-origin disagreement; this is not a
threshold, symbol, direction, or horizon variant of rejected single-venue taker-flow continuation.

## Sequential-Policy Admission

- One primary specification is frozen before any conditional forward return is calculated.
- C-21/C-22 used futures flow alone. C-34 requires exact contemporaneous Spot/futures flow with
  strictly opposite signs and follows Spot; neither prior candidate opened this interaction.
- Inputs are completed native bars, exactly timestamp-aligned and point-in-time reconstructable.
- The 24-hour horizon is retained from the parent economic mechanism and can clear 0.30% primary
  friction; 0.50% is a mandatory stress gate.

## Frozen Data and Boundaries

- Symbols: BTCUSDT, ETHUSDT, BNBUSDT, XRPUSDT, ADAUSDT, and SOLUSDT.
- Spot flow files from TASK-0118 (`quote_volume`, `taker_buy_quote_volume`) full compressed-file
  SHA-256: BTC `2b58717c3f464e84ab531db07f4263b4c83b52c2f6b460a5445ec150f9c5dec3`, ETH
  `79e83e1947022c51126093ef72ab97f0e38fe3d40851fed8c3ad5a15afce75fa`, BNB
  `29294ff4fe8c7ee52b3e35f36e944735c7fed09fb5e3878f0720d7ae3352c4c8`, XRP
  `a87b83e107e7536fa4e68b280c27700da9bd3f6dbd8b96ca8e39aa104c817455`, ADA
  `f081b9da47ce30e2746a235d6a78ad7269ef7add8d6738eac49ac8b1af7c5452`, SOL
  `7ac0701eeb2b50ac30cd3575219ada620d567783a3cd10be98813f39869c9011`.
- Futures flow files from TASK-0114 (`quote_volume`, `taker_buy_quote_volume`) full compressed-file
  SHA-256: BTC `f0af424c2b0d001b479f91f3ed0429d0d089b990c007f8968e09761138dd5a93`, ETH
  `166467c924a404d5c9927c450c9da927532aabcbd828918c38bd53638d3fd970`, BNB
  `79d701f617d3d1920cea26f0217c9a5c8ef6cc24a869a59cc846fcbb93e49276`, XRP
  `e11d0e30bdd00574dbc6b2bef2c60b66bd6a8a102806544ad3305d0a24898805`, ADA
  `b088031506c7fa0c42f609b1afa6eb9a49ab9898cb848ed6dd00c6b5b71b9520`, SOL
  `d45916f83648f1f534e1cc6ab2adba28679403491963279134118a8e8b2c1b29`.
- Native perpetual price SHA-256: BTC `30e02acebd29a4e47032be70baa7dd3ec0c38a246915fa8329e899edbc07aabb`,
  ETH `d44a16a5a7363d6833d0e4e60035acd63826e3e9f65fb3aef260e4c4fde08843`, BNB
  `7c9f289c34040f6228f8cdfe415fa045f641b2e7292108bf97bdde34db74c0c0`, XRP
  `89629283deadf39234f7d9cd07ad27f0e378c4c81e6d3a227798494667dcfd57`, ADA
  `643dc2f29d3e50fb008391fd4787472836dd88eeab7dd92f71ff0820b5dea79a`, SOL
  `e6efc15ec3544227426076b059bcaec71a2557520d64433f08cea398c554a382`.
- Funding SHA-256: BTC `2fe89ca06907e7953cb49c2db052e74158ea9319f50f0bd9dac08fb2a579c097`,
  ETH `b978d9a54809ad232583b9419ed2695647d0557bc58074112082fa1472057148`, BNB
  `7edf30b5a20f5572361ba7bc41ff89b02df8105a82ff24c1b32a5dc807bca08d`, XRP
  `2886be913f6678b660e827d481a2b60d426de6c8b406bcff3c282d3f275e74f9`, ADA
  `f27f351e603c0563d9c1e0ea6be10640a8bf38c4a1640383d914cd5aaaa79301`, SOL
  `be28b9621e6baf0d3b50365c73e59352996274f4097cae60fe4ffce2528c55a3`.
- Every full file hash is enforced before outcomes. Primary is 2024-01-01 through 2026-08-29;
  temporal reverse is 2023-01-01 through 2023-12-31.
- Exact timestamp intersection only. No fill, interpolation, resampling, nearest match, or synthetic
  observation. Any missing constituent bar rejects the decision.

## Frozen Signal

- Decisions occur at exact four-hour UTC boundaries.
- Use exactly the 16 completed native bars from `t-4h` through `t-15m` for both venues.
- For each venue, sum total quote volume and taker-buy quote volume, require finite positive totals
  and `0 <= taker_buy <= total`, then define `score = 2*taker_buy/total - 1`.
- Define `divergence = spot_score - futures_score`.
- From the prior 180 valid four-hour decisions for that symbol, excluding current, calculate causal
  p90 thresholds for `abs(spot_score)` and `abs(divergence)`; require all 180 observations.
- Signal only when Spot and futures scores have strictly opposite signs, absolute Spot score is
  strictly above its causal p90, and absolute divergence is strictly above its causal p90.
- Trade in the Spot-flow direction: positive Spot score => LONG; negative Spot score => SHORT.
- Zero/tied scores are no-signal. No price-return, OI, funding-level, basis, depth, volatility,
  trend, regime, persistence, ranking, hour, weekday, or diagnostic filter is allowed.

## Frozen Execution and Economics

- Enter at the exact perpetual open at decision timestamp `t`; exit at the exact open 96 native
  15-minute bars later (24 hours). Require all 97 timestamps contiguous.
- At most one unresolved position per symbol; retain the earliest signal and reject overlaps.
- Include actual funding settlements strictly after entry and at or before exit. LONG pays and SHORT
  receives funding.
- Charge 0.30% round trip and report fixed 0.20% and 0.50% sensitivities.

## Frozen Reporting and Gate

- Report alignment, validity, warmup, opposition, threshold, signal, path, fold-crossing, overlap,
  and funding census; N, expectancy, PF, win rate, drawdown, costs, funding, folds, sides, symbols,
  years, positive-PnL concentration, and temporal reverse.
- Form four global chronological primary folds; positions crossing fold boundaries are excluded.
- Cluster-bootstrap 10,000 samples by UTC entry day with seed 340034.
- KEEP requires every condition: primary N>=300; expectancy>0; PF>1; clustered 95% lower bound>0;
  >=3/4 positive folds with N>=50; both sides positive with N>=75; >=4/6 symbols positive with
  N>=40; every primary year positive with N>=50; maximum positive-PnL symbol concentration<=35%;
  temporal reverse N>=150 with expectancy>0 and PF>1; and positive primary expectancy at 0.50% cost.
- Any failed completed condition is REJECT. A pass is only `KEEP_FOR_PROSPECTIVE_VALIDATION`.

## Frozen Prohibitions

No source, universe, window, score, threshold, lookback, opposition rule, direction, horizon, cost,
funding boundary, overlap rule, sample gate, fold, bootstrap, concentration, drawdown, or period may
change after outcomes open. Diagnostics cannot change the verdict. No new variant, historical
reslice, order, broker call, production strategy/risk/trailing/symbol/leverage change is authorized.
