# Historical Market-Type Official Mapping — 2026-09-17

## Verdict

`PARTIAL KEEP — BINANCE, MEXC, AND PHEMEX CONTRACTS VERIFIED; BINGX EXACT SERIES CONTRACT UNRESOLVED`.

This is a mapping decision, not an endpoint change. No runtime, broker account, order, strategy,
symbol, or production-risk setting was touched.

## Official public contracts verified

| Venue | Market type | Official public candle contract | Repository state | Decision |
|---|---|---|---|---|
| Binance | Spot | `https://api.binance.com/api/v3/klines` | Exact current path | Keep only when the caller explicitly requests `SPOT` |
| Binance | USD-M perpetual | `https://fapi.binance.com/fapi/v1/klines` | Not implemented | Eligible for an explicit `PERPETUAL` mapping |
| MEXC | Spot | `https://api.mexc.com/api/v3/klines` | Exact current path | Keep only when the caller explicitly requests `SPOT` |
| MEXC | Contract/perpetual | `https://contract.mexc.com/api/v1/contract/kline/{symbol}` or the documented fair-price series | Not implemented; schema and symbol form differ | Do not substitute without choosing last-price versus fair-price semantics |
| Phemex | USD-M perpetual | `/exchange/public/md/v2/kline/list` (historical range) and `/last` (latest) | Current code uses legacy `/md/kline` and parses a different shape | Replace only behind explicit `PERPETUAL` mapping and response tests |
| BingX | Unknown in reviewed provider | Current code uses `/openApi/quote/v1/klines` | Market identity is implicit | Fail closed until the exact official Spot/perpetual series and response schema are frozen |

Official references reviewed on 2026-09-17:

- Binance USD-M Futures Kline/Candlestick Data:
  `https://developers.binance.com/en/docs/products/derivatives-trading-usds-futures/market-data/rest-api/Kline-Candlestick-Data`
- MEXC Contract API: `https://mexcdevelop.github.io/apidocs/contract_v1_en/`
- Phemex API Reference, USD-M Perpetual REST API, Query kline:
  `https://phemex-docs.github.io/`
- BingX documentation is dynamically rendered at `https://bingx-api.github.io/docs/`; the reviewed
  static evidence did not establish that the repository's legacy `/openApi/quote/v1/klines` path is
  the intended perpetual last-price series. It remains `UNKNOWN`, not guessed.

## Frozen minimal correction boundary

1. Require `market_type` at the historical-data request boundary; accepted values initially are
   `SPOT` and `PERPETUAL`.
2. Include `market_type` in unsupported-symbol and local-cache identities.
3. Allow only source/market mappings whose endpoint, symbol form, pagination, and response schema
   have focused tests. Unsupported combinations return no data and permit the next explicit
   same-market fallback; they must never cross from perpetual to Spot.
4. Make the perpetual strategy buffer request `PERPETUAL` explicitly.
5. Keep Spot available as an intentional explanatory input, but never as an implicit replacement.
6. Do not activate BingX until its exact official candle contract is independently verified.

## Why implementation is intentionally deferred one bounded unit

BingX is the preferred operational venue, and changing the endpoint based on an unverified path can
silently change last-price, mark-price, index-price, symbol format, or pagination semantics. The
safe next unit is therefore the explicit fail-closed request/cache contract plus tested Binance
USD-M mapping; BingX remains unsupported at this boundary until its contract is proven.
