# EPIC-01 — observed MTF / maker execution / economic qualification contract

Frozen before acquired market outcomes, 2026-10-28. Source baseline main `d9307db`,
primary `5191c02`. This is continuation of T01/T04/T05, not a new backlog or Pilot-3.
The operator explicitly directed work on missing actual MTF data, maker execution and
a qualified economic experiment. Earlier no-new-collection limits are relaxed only
for this named public-data qualification unit; old cohorts/protocols remain immutable.

## Acquisition unit and provenance

Start with BTCUSDT, Binance USD-M, 2024-01-01, selected mechanically as the first day
in the existing raw aggregate-trade archive. This is a schema/coverage/composition
unit, not a chosen profitable day, market-wide universe or independent holdout.
No prospective collectors, exchange account, API keys, subscription or payment.

- Official Binance `bookTicker` checksum GETs for BTC/ETH, 2024-01-01 and 2026-06-01
  verified two historical 200 responses and two 404s. This is existence evidence;
  checksum files alone do not supply quotes or qualify any historical coverage.
- Acquire Tardis's public first-of-month samples `book_snapshot_5` and `trades` for
  Binance-futures BTCUSDT on 2024-01-01. Exactly two fixed unauthenticated HTTPS GETs;
  cap 256 MiB compressed/file, 512 MiB total; no retry, paid fallback or credentials.
- Store in a separate `data/research/epic01_mtf_maker/qualification_2026-10-28/` root.
  Exclusive raw files, SHA-256, byte counts, canonical source URL, UTC acquisition
  request/completion, gzip/CSV validity, schema and row/time coverage go into a manifest.
  Preserve original gzip bytes. Acquisition receipt now is not historical message receipt.

Sources: [provider schema and free-sample policy](https://docs.tardis.dev/downloadable-csv-files),
[Binance archive schemas/checksums](https://github.com/binance/binance-public-data).
Vendor snapshots are reconstructed from observed WebSocket depth, with documented
crossed-level removal, not exchange-native raw diffs or proof of complete queue state.
CSV lacks disconnect messages; never promote its absence to uninterrupted feed proof.

## Causal MTF binding, version OBSERVED_TOP5_MTF_V1

Source exchange timestamp and vendor `local_timestamp` use microseconds. Preserve row
order for equal clocks. Availability is `max(exchange_timestamp, local_timestamp)`;
do not use acquisition-time receipt or candle-open time as historical availability.
Nondecreasing local receive order, explicit symbol/venue, finite positive ordered
prices, nonnegative sizes and uncrossed bid/ask are required. Unknown/malformed rows
invalidate their interval rather than supplying constants.

- 1m quote: last actually received valid book within the completed UTC minute,
  available by its boundary; require age <= 1 second at the boundary. No synthetic
  +/-spread or unbounded forward fill. Include source row and both clocks.
- 5m OBI: at each completed UTC five-minute boundary use that last valid observed
  top-five book, with age <= 1 second. `(sum(bid amounts)-sum(ask amounts)) /
  (sum(bid amounts)+sum(ask amounts))`; empty/zero total is unavailable.
- 5m signed volume delta: sum observed buy amount minus sell amount over the half-open
  exchange-time bucket; require receipt no later than its close. Report late arrivals
  and exclude incomplete/late buckets. This is a bounded five-minute delta, not a
  reconstructed full-book CVD guarantee. Do not treat a missing trade stream as zero.
- 15m/H1 context: complete candles only, using already frozen C06 OHLCV with its
  source hash and warm-up. No new C06 labels or claim of historical whole-market membership.
- Interval gap and staleness masks remain separate from statistical acceptance.
  Top-five OBI is an explicit research binding of an otherwise under-specified scalar;
  equivalence to every historical/live OBI producer is NOT established.

## Maker model, CONSERVATIVE_TRADE_THROUGH_V1

Pure offline opt-in, no production adapter or policy change. Preserve existing market
behavior and fail-closed rejection for unsupported maker calls without this contract.

- Explicit aware decision/arrival/expiry clocks; model arrival latency 100 ms and TTL
  60 seconds as assumptions, not measured latency. A quote must be available at arrival,
  no older than 1 second. Reject a BUY at/above ask or SELL at/below bid at arrival.
- Only an at-best same-side resting limit is supported initially. Visible same-side
  quantity at arrival is the modeled queue ahead; do not invent unseen queue position.
  Deeper/inside-spread limits require another declared model and fail closed here.
- Events at/before arrival cannot fill. At expiry the remainder expires before a
  same-clock trade. Cancel is effective at the explicitly supplied clock, never retroactive.
- Only opposite-aggressor trades consume modeled queue. Equal-price trades may deplete
  queue but never alone prove a fill. Require strict trade-through after queue depletion.
- Fill quantity <= remaining order and 1% of the eligible trade volume remaining after
  modeled queue consumption. Partial fills accumulate; reuse of an event cannot refill.
  No candle-low touch, total-bar volume or future quote may fabricate an execution.
- Fill at the resting limit, no favorable price improvement. Maker fee 2 bps per
  fill is a frozen modeling assumption, not an assertion about an account's fee tier.
  Stress: maker 5 bps. Any market exit requires taker 5 bps + adverse slippage 1 bp;
  stress taker 10 bps + slippage 2 bps. Funding must use observed eligible settlements.
- This is a declared queue/participation model, not a guaranteed lower bound, matching
  engine reconstruction or proof that a real order would fill. Report nonfills/expiry.

## Economic admission and acceptance

Do not print/optimize PnL before input and model gates. Use existing actual setup
families NGTREND_FOLLOW, NGBREAKOUT and NGLS_SWEEP with source-frozen parameters;
do not relabel these pullback/retest/momentum scalping. Before outcomes, record exact
strategy/feature/model hashes, frozen parameter values, funding/cost contract, data
cuts, evaluation budget and dataset receipts. No fmin or parameter search in the unit.

The one-day source/composition unit cannot be an untouched OOS/Edge result: C06 price
outcomes are already development-opened, universe is selected and statistical power
is insufficient. Any economic output on it must be a separately qualified development
component baseline with actual strategy decisions and declared modeled execution,
not the full accepted three-family baseline or an independent profitability claim.

Full experiment still requires per-file eligibility, complete causal strategy/admission
composition, source-qualified observation overlap, no invented missing metrics, fees,
funding, partial-fill accounting, SL/TP post-fill causality (SL priority on ambiguity),
peak-to-trough equity drawdown, exposure/duplicate controls and reproducibility.
Only training windows may optimize; holdout boundaries and three-family multiplicity
controls must be frozen before any later evaluation. If a gate fails, report exact
evidence and continue independent ready units; do not change the gate or silently
replace inputs. EPIC 7 packages/30 scenarios and R01–R26 verdicts remain unchanged.
