# Phase 3A proxy-source coverage gate

**Status:** DATA_COVERAGE_READY_FOR_MATCHING; fingerprint/economic verdict **NOT RUN**. Frozen protocol: `b9ec946`, SHA-256 `96d0f336f9c0e335b61b8d90df81835180647f9c2d85498d210fa1e34c329193`.

The bounded public-only collector `src/fetch_phase3_proxy_panel.py` queried Binance USDT-perpetual `exchangeInfo` and 15-minute `klines` for the 24 distinct symbols in the frozen primary HMT case list. No credentials, broker account, order path, Telegram outcome, or future-return calculation was used. The proxy is **not** asserted to be the sibling system's exact chart instrument or execution venue.

The [source manifest](../manifests/phase3_proxy_source_manifest.json) records retrieval time, endpoint, exchange-info response hash, current contract type/status, onboard timestamp, requested window, per-symbol CSV hash, bar count, duplicate/missing/invalid counts, and timestamp semantics. The downloaded public CSVs reside under ignored `data/research/phase3_point_in_time/binance_futures_15m/`, **not** in the Git commit. The private Telegram `jan-jul` and `aug` exports/photos were neither copied nor staged.

| Gate | Result |
| --- | ---: |
| Symbols in primary HMT list | 24 |
| Complete, validated Binance USDT-perpetual proxy files | **22** |
| Primary HMT cases with validated proxy symbol/window | **56 / 58** |
| Distinct UTC case days among those 56 | **23** |
| Distinct symbols among those 56 | **22** |
| Sides among those 56 | 25 LONG / 31 SHORT |

Each of the 21 non-BTC validated symbols has **3,552/3,552** 15-minute bars from 2026-08-08 00:00 through 2026-09-13 23:45 UTC. BTC has **6,528/6,528** bars from 2026-07-08 00:00 through the same endpoint to support the preregistered coarse-regime sensitivity. For these files the API close timestamp equals bar-open + 899,999 ms; there were zero internal gaps, duplicate opens, nonpositive prices, OHLC violations, or out-of-range rows. These checks establish a complete proxy time grid, **not** absence of venue-basis or selection-universe bias.

`SIG-000283`/`ALUSDT` and `SIG-000293`/`XAUUSD` have no verified current Binance USDT-perpetual contract in the public `exchangeInfo` response. Current absence does not prove historical nonexistence. They remain missing for this proxy; no guessed alias, spot series, or replacement symbol is permitted. Their source chart/contract identity remains an unresolved limitation.

Next step under the frozen protocol: construct Family-A same-symbol same-week 4-hour-block controls, enforce the signal ±6h exclusion and at least two controls per case, then audit `input_close_time <= each case/control T` for all six fixed features. Only **after** that do matched-case count, independent-day count, missingness, and power become known. The current 56 is a coverage ceiling, not the effective sample. Do not infer a fingerprint, edge, or profitability from these coverage numbers.

**خلاصهٔ ساده:** دادهٔ عمومیِ لازم برای بیشتر نمونه‌ها آماده و از نظر زمان‌بندی اولیه سالم است. دو نماد هنوز منبع قرارداد دائمیِ قابل‌تأیید ندارند. هنوز نمی‌دانیم بعد از ساخت نمونه‌های مقایسه‌ای چند مورد واقعاً برای آزمون معتبر می‌ماند؛ هیچ ادعای سوددهی یا edge مطرح نیست.
