# E11-4 — Signal-to-order latency from the live journal (2026-11-25)

**Source.** `data/live_order_journal.json`, INTENT records carrying `signal_ts` (added 2026-11-24).
- 164 records with a timezone-aware `signal_ts`.
- 14 earlier records were written in local time without an offset (before the fix) and are excluded.

| Step | median | p95 | max |
|---|---|---|---|
| Setup signal → INTENT persisted | 15.4 s | 35.8 s | 52.0 s |
| INTENT → order submitted to BingX | 3.6 s | 4.6 s | 7.2 s |
| **Total signal → order** | **18.6 s** | **38.7 s** | 56.0 s |

Median total by strategy: TrendFollow 11.3 s, OIFootprint 20.7 s, VWAPReversal 21.6 s.

**Price drift from signal price to fill.**
- 53 fills carry an average price. Median 8 bp adverse; mean 34 bp; p95 263 bp.
- The signal price is the Binance price and the fill is on BingX VST, where the spread and level differ (W0-1). This number mixes venue basis with latency and is not a real-execution cost estimate.

**Verdict.**
- Latency is small next to the strategies' bars: 15 min (VWAP) to 1 h (TrendFollow, OIFootprint).
- No action needed. The earlier user-reported "candidate → order delay" is not visible in these records.
