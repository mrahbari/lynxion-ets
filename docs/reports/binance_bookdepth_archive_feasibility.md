# Binance Futures Book-Depth Archive Feasibility

**Date:** 2026-08-30
**Decision:** GO for isolated acquisition; no L2 edge candidate is authorized yet.

The official Binance Data Vision USD-M Futures archive exposes daily `bookDepth` files from
2023. A BTC sample contains timestamped depth and notional at percentage levels -5 through -1
and +1 through +5. The first sample has 28,560 data rows and is approximately 0.46MB compressed.

Official archive:
<https://data.binance.vision/?prefix=data/futures/um/daily/bookDepth/BTCUSDT/>

This materially changes the older project conclusion that historical L2 depth was unavailable.
The archive is not full tick-by-tick order-book reconstruction, but it is genuine aggregated
bid/ask depth at fixed distance bands and can support causal retail-horizon research.

`bookTicker` is also archived, but individual daily files are tens of megabytes and the full
multi-symbol history is materially larger. TASK-0109 therefore limits scope to `bookDepth`.

The next step is data acquisition and validation only: official checksums, schema, fixed levels,
duplicate/conflict handling, non-negative finite depth/notional, cadence/gaps, and coverage.
No price outcome may be evaluated before the data gate and separate C18 preregistration.
