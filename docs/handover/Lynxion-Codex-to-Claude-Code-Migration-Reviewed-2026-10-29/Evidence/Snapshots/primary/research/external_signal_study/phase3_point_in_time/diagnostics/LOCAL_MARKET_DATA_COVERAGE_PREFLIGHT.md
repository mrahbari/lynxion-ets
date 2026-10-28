# Phase 3A local market-data coverage preflight

**Scope:** file/manifest and case-time availability only. No OHLCV values, post-signal returns, Telegram outcomes, fingerprint features, or economic performance were inspected. Protocol hash: `96d0f336f9c0e335b61b8d90df81835180647f9c2d85498d210fa1e34c329193`; frozen in commit `b9ec946`. Cases were derived in `e41815c`.

Existing Binance USDT-perpetual 15m archives under `data/research/c06/binance_futures_15m/` and `data/research/c15/binance_futures_15m/` cover **11 symbols** and terminate at **2026-08-29 23:45 UTC** according to their manifests. C-09 covers 2022 and is irrelevant. These source files have the expected `timestamp,open,high,low,close,volume` schema, but this preflight did not verify every individual bar or its close-time semantics. The screenshot/source venue is not proven identical to the Binance perpetual proxy.

Of the 58 nominal primary HMT cases defined by the frozen spec:

| Gate | Cases |
| --- | ---: |
| Symbol exists in those two local archives | 30 |
| Symbol exists **and** first-message T is no later than archive endpoint | **16** |
| Missing from those archive symbol lists | 28 |
| T after archive endpoint, regardless of symbol | 29 |

The 16 are only an **optimistic upper bound** before full pre-T lookback, missing-bar validation, same-week control matching, independent-day breadth, and UTC close-time checks. They span only **six symbols and nine UTC days**. The frozen power gate requires at least 40 matched cases, 20 days, and 10 symbols. Therefore the existing C-06/C-15 files **cannot by themselves** support a decisive primary fingerprint test. A null result from them would be `INCONCLUSIVE_DATA_LIMITED`, not evidence of no fingerprint.

Next bounded action: obtain/verify only the missing 15m Binance USDT-perpetual proxy bars needed for the frozen Aug 16–Sep 13 case/control windows and pre-T lookbacks, using free public data and a separate Phase 3A source manifest. Do not mix in spot or BingX bars silently; do not reuse C-35 prospective cohort data as confirmatory Phase 3A data. Before any feature computation, audit complete timestamp grid, gaps, duplicate bars, listing availability, and `close_time <= T` for every feature input. Symbols without a verifiable perpetual listing or continuous coverage remain missing; no substitute symbol is allowed. Do not reinterpret the 28 selected symbols as the true candidate universe.

**خلاصهٔ ساده:** دادهٔ محلی فعلی برای این آزمون کافی نیست؛ از ۵۸ نمونهٔ بالقوه، حداکثر ۱۶ نمونه در بازه و نمادهای آرشیوهای موجود جا می‌گیرند. هنوز دربارهٔ وجود یا نبود اثر، نتیجه‌ای نگرفته‌ایم. باید فقط دادهٔ عمومیِ لازم را کامل و اعتبارسنجی کنیم؛ فایل‌های خام تلگرام `jan-jul` و `aug` نباید commit شوند.
