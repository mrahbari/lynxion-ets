# Prefix invariance

The focused source test runs two streams: `[00:00, 00:15]` and the identical prefix plus `00:30`. Through decision time 00:30 UTC, returned completed bars are identical. A pre-close query returns no bar. Separate tests reject duplicates, gaps, out-of-order events and NaN, and withhold a 1h bar until its 01:00 close. Repeated source construction across a UTC day boundary returned identical data. Five focused tests passed.

**Release gate remains NOT TESTABLE**: no decision-level trace through Engine/Fusion/Strategy/Risk exists. Future SMA/ATR, watcher state and aggregator behavior were not tested. Source-level equality must not be misreported as `HASH(decisions <= T)` equality.
