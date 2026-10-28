# Forced-Liquidation and Taker-Flow Feasibility

## Forced-Liquidation Finding

The official Binance Data Vision USD-M daily catalog exposes aggTrades, book depth/ticker,
index/mark/premium klines, ordinary klines, metrics, and trades. It does not expose a historical
liquidation or force-order archive. A recent-only endpoint cannot support the frozen historical and
temporal samples. Therefore no C21 liquidation hypothesis is admitted from an unverifiable proxy.

## Taker-Flow Finding

Official native 15-minute futures kline archives contain total volume/quote volume and taker-buy
volume/quote volume with checksum-addressable daily files. A sampled 2026 archive is only a few
kilobytes and retains the complete standard schema. Symmetric taker buy/sell imbalance can therefore
be built without reconstructing trades or introducing a paid source.

## Decision

Defer forced-liquidation research until a trustworthy point-in-time historical source exists. Open
an acquisition-only task for the official taker-flow panel. Define no C21 direction, threshold, or
outcome until that panel passes its data gate.
