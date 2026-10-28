# Historical Market-Type Semantics Audit — 2026-09-16

## Verdict

`BLOCKED — HISTORICAL MARKET TYPE IS NOT DECLARED OR ENFORCED`.

## Verified call path

- Live strategy buffer hydration asks the shared enhanced provider for historical candles.
- `DataConfig.preferred_historical_data_source` defaults to `binance`; fallback order includes
  Binance, MEXC, Phemex, and BingX.
- The configurable provider accepts only a venue name. Its contract, registry key, cache identity,
  and returned candle rows carry no `SPOT` versus `PERPETUAL` market type.
- Binance uses `/api/v3/klines`, and MEXC uses `/api/v3/klines`; those paths are Spot market-data
  namespaces. BingX uses `/openApi/quote/v1/klines`, without a derivatives-market contract in the
  provider. Phemex likewise has no enforced market-type identity at this boundary.
- Lynxion execution in the reviewed production/VST path is derivatives/perpetual. Therefore the
  repository cannot prove that dynamically hydrated strategy history represents the market being
  traded.

## Risk

TASK-0377 now rejects incomplete and stale history, but completeness does not prove semantic
equivalence. A complete Spot panel can still be the wrong point-in-time input for a perpetual signal,
especially around funding, basis, listing differences, and venue-specific liquidity. The current
cache key also cannot distinguish Spot from perpetual candles for the same venue/symbol/timeframe.

This is a signal/data-correctness issue, not evidence that Spot data is always unusable. Spot may be
an intentional explanatory input, but that must be explicit in the strategy contract; it cannot be
an implicit fallback for a perpetual series.

## Required correction boundary

1. Add an explicit market type to the historical-data request and cache identity.
2. Map each source to a verified endpoint for that market type; unsupported combinations fail
   closed rather than silently changing markets.
3. Make the perpetual strategy buffer request perpetual candles explicitly.
4. Test source/endpoint mapping, cache isolation, fallback rejection, and missing market type.
5. Do not change the signal, symbol universe, or broker/order path.

No endpoint was called, runtime was started, or policy was changed in this audit. Endpoint selection
must be verified against current official venue documentation before implementation.
