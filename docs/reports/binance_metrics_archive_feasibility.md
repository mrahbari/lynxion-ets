# Binance Futures Metrics Archive Feasibility

**Date:** 2026-08-30
**Decision:** GO for isolated data acquisition and integrity validation; no edge candidate is
authorized yet.

## Discovery

The earlier OI audit correctly found that Binance's REST statistics endpoint exposed only a
short recent window. The official Binance Data Vision archive now contains a separate daily
USD-M Futures `metrics` collection. BTCUSDT begins on 2020-09-01.

Official sources:

- Archive root: <https://data.binance.vision/?prefix=data/futures/um/daily/metrics/>
- BTC archive: <https://data.binance.vision/?prefix=data/futures/um/daily/metrics/BTCUSDT/>
- Current Binance Futures market-data documentation:
  <https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Open-Interest-Statistics>

An official BTC sample was downloaded to temporary storage and inspected. Its schema includes
timestamp, symbol, OI quantity/value, top-trader ratios, global long/short ratio, and taker ratio.
The sample contains duplicate timestamp rows, so acquisition must record raw-versus-unique counts
and reject conflicting duplicates rather than assuming archive cleanliness.

## Implication

The prior “approximately 30 days” conclusion remains true for its REST path but is no longer a
sufficient project-wide conclusion. Multi-year official OI/positioning metrics appear obtainable
without a paid provider. This reopens a data path; it does not prove an edge.

## Required Next Step

Build an isolated, checksummed multi-symbol panel and validate archive coverage, official
checksums, schema consistency, timestamps, duplicates, gaps, finite OI fields, and causal
alignment. Only after the data gate passes may one C-16 OI hypothesis be preregistered.
