# Prefix invariance

The focused source test runs two streams: `[00:00, 00:15]` and the identical prefix plus `00:30`. Through decision time 00:30 UTC, returned completed bars are identical. A pre-close query returns no bar. Separate tests reject duplicates, gaps, out-of-order events and NaN, and withhold a 1h bar until its 01:00 close. Repeated source construction across a UTC day boundary returned identical data. Five focused tests passed.

**Unit-1 result:** at that point the release gate was NOT TESTABLE because no decision-level trace through Engine/Fusion/Strategy/Risk existed. Future SMA/ATR, watcher state and aggregator behavior were not tested. Source-level equality must not be misreported as `HASH(decisions <= T)` equality.

## Completed-bar decision subset (subsequent bounded unit)

The existing `HistoricalCandleWatcherAdapter` now receives validated completed bars in a separate, explicitly bounded driver and publishes its `MarketObservation` into fresh canonical Engine/Fusion/aggregator handlers. A two-bar prefix and the same source with one later bar produced identical normalized observation/event-type outputs and identical recorded Risk price history through T; two symbols used separate watcher buffers. This is **partial-prefix evidence only**: a complete intent/Risk/order decision trace, unavailable live watchers and MTF parity are not covered. The full release status remains `PREFIX_INVARIANCE_NOT_TESTABLE`.

## Normalized routed-event subset

A later two-bar fixture compares the complete normalized payloads of reached `MARKET_OBSERVATION`, `INTERPRETED_SIGNAL` and `FUSED_SIGNAL` events for a prefix run versus the same input with one future candle appended. The traces are identical through T and repeat identically. No `EXECUTION_INTENT` is produced; adapter lazy historical data sourcing is not point-in-time bound. This is **not** full decision-level or after-cost prefix invariance. Status remains `PREFIX_INVARIANCE_NOT_TESTABLE`.
