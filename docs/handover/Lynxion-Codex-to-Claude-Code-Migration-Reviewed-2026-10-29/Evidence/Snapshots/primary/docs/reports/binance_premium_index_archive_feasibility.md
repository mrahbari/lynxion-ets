# Binance Premium-Index Archive Feasibility

## Finding

Official Binance Data Vision exposes daily USD-M `premiumIndexKlines` archives at native 15-minute
resolution. BTCUSDT listings begin in 2019 and the requested 2026-08-29 archive is available.

The sampled archive is checksum-addressable, small, and contains the standard kline schema:
`open_time, open, high, low, close, volume, close_time, quote_volume, count,
taker_buy_volume, taker_buy_quote_volume, ignore`. OHLC fields contain the premium-index/basis
series; non-price volume fields are zero by construction and must not be interpreted as trade flow.

## Decision

Historical basis acquisition is technically feasible using only the official free archive. Build
and integrity-gate the panel before defining any basis candidate. No C20 outcome, threshold, or
direction is admitted by this feasibility result.
