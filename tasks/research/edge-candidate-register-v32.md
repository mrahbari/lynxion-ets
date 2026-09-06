# Edge Candidate Register v32 — C-33 Forced-Liquidation Exhaustion

**Status:** PRE-REGISTERED — PROSPECTIVE SHADOW ONLY

**Prospective boundary:** `2026-09-06T07:13:23Z` (`1788678803` epoch seconds).

C-33 tests whether an exceptional completed cluster of exchange-labelled USD-M forced liquidations
temporarily exhausts one side and reverses over the next four hours. It uses Binance's public
liquidation snapshot stream and never sends an order.

## Frozen Source and Universe

- Source: public Binance USD-M `!forceOrder@arr` websocket stream plus public one-minute kline and
  mark-price/funding streams for BTCUSDT, ETHUSDT, BNBUSDT, SOLUSDT, XRPUSDT, and ADAUSDT.
- Retain only `st=1` USD-M events whose `s` and `ps` identify the same frozen USDT pair. Reject CM,
  delivery, unknown, malformed, non-filled, non-positive, or inconsistent events.
- The liquidation feed is a censored snapshot: it reports only the latest event per symbol in each
  1,000-ms interval. `count` and `notional` always mean observed snapshots, never complete exchange
  liquidation activity.
- Persist raw message bytes and SHA-256, event/receipt monotonic time, parsed fields, connection
  session ID, and lifecycle state in append-only files. No event at or before the boundary counts.
- No backfill is allowed. Restarts deduplicate liquidation snapshots by
  `st:s:S:T:z:ap` and candles by `symbol:open_time`.

## Frozen Liveness and Buckets

- Aggregate exact non-overlapping UTC five-minute buckets by liquidation trade time `T`; an event
  may enter only after its bucket is complete.
- A bucket is eligible only if the websocket session was uninterrupted for its full five minutes,
  every expected symbol kline closed, and a successful public `/fapi/v1/time` heartbeat was recorded
  in each constituent UTC minute. Silence on `!forceOrder@arr` then represents zero observed events;
  any liveness or candle gap makes the entire bucket missing rather than zero.
- Event notional is filled quantity `z` times average price `ap`. Sum observed SELL and BUY notional
  separately per symbol and bucket; dominance is the larger side divided by their sum.

## Frozen Signal

- Warm up using the previous 8,640 eligible five-minute buckets for the same symbol (30 exact days),
  excluding current. Warmup is forward-only; pre-boundary buckets cannot be imported.
- Require current total observed liquidation notional strictly above its causal prior-window p99,
  at least 1,000,000 USDT, at least three observed snapshots on the dominant side, and dominant-side
  notional share at least 0.80.
- Trade exhaustion reversal: dominant forced SELL => virtual LONG; dominant forced BUY => virtual
  SHORT. If dominance is tied or undefined, emit no signal.
- At most one unresolved virtual position per symbol; retain the earliest signal.

## Frozen Virtual Execution and Economics

- Enter at the exact first one-minute open after the completed five-minute bucket. Exit at the exact
  open 240 one-minute bars after entry. Require all 241 entry-through-exit timestamps contiguous.
- Include public Binance funding settlements strictly after entry and at or before exit. LONG pays
  and SHORT receives the funding rate; missing or ambiguous funding makes the outcome incomplete.
- Charge 0.30% round-trip cost and report fixed 0.20% and 0.50% sensitivities. Primary promotion
  requires positive expectancy at 0.50% cost.
- No midpoint, current-bucket price, stop, take-profit, trailing, leverage, sizing, or liquidation
  model is used. This is a one-leg virtual directional outcome only.

## Frozen Prospective Gate

- Remain `COLLECTING` for at least 180 UTC days and until at least 300 completed trades exist, with
  at least 30 per symbol, 75 per side, and signals in at least 20 distinct UTC weeks.
- Form four chronological folds without allowing positions to cross fold boundaries. Require at
  least three positive folds with at least 50 trades each, both sides positive, and at least four of
  six symbols positive.
- KEEP additionally requires net expectancy > 0, PF > 1, daily-clustered bootstrap 95% lower bound
  > 0 using 10,000 samples and seed 330033, maximum positive-PnL symbol concentration <= 35%, equity
  max drawdown <= 20%, and positive expectancy at 0.50% cost.
- Any failed completed gate is `REJECT`. A pass is only `KEEP_FOR_OPERATOR_REVIEW`; it does not
  authorize paper or real deployment.

## Frozen Prohibitions

No venue, stream, universe, bucket, warmup, percentile, absolute floor, count, dominance, direction,
horizon, cost, funding boundary, overlap, liveness rule, sample gate, fold, bootstrap, concentration,
or drawdown rule may change after the first accepted event. No historical import, diagnostic
reslicing, authentication, broker call, paper/real order, production integration, or secret use is
authorized.
