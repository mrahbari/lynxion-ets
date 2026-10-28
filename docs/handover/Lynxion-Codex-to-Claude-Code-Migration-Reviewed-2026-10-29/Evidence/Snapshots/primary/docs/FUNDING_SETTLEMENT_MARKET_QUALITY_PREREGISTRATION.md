# Funding Settlement market-quality diagnostic preregistration

**Frozen:** 2026-09-19 before inspecting settlement-relative market-quality outcomes

**Status:** `FROZEN_BEFORE_OUTCOMES`

## Question

Do actual Binance USD-M funding settlements cause a repeatable change in observable market quality
relative to a nearby non-settlement clock control?

This is a descriptive clock diagnostic. It does not test whether funding direction predicts return,
does not authorize a strategy or `NO_TRADE` production rule, and does not modify the frozen Rescue
Ladder snapshot.

## Frozen universe and sample

- Symbols: BTCUSDT, ETHUSDT, BNBUSDT, SOLUSDT, XRPUSDT, ADAUSDT.
- Funding source: retained point-in-time `data/research/c16/funding/*.csv` timestamps.
- Market source: retained 15-minute taker-flow/OHLCV panel and depth snapshots.
- Evaluation period: `2023-01-01T00:00:00Z` through `2026-08-29T16:00:00Z`.
- Use actual settlement timestamps. Never hardcode eight hours; SOL contains observed 2h/4h/8h
  intervals.
- A settlement is eligible only when the previous and next funding timestamp exist and every
  required market window is complete.

## Frozen event and control windows

For settlement time `t`:

- pre window: three complete 15-minute bars `[t-45m, t)`;
- post window: three complete 15-minute bars `[t, t+45m)`;
- matched control time: the exact midpoint between `t` and the next actual settlement;
- control-pre/control-post: identical 45-minute windows around that midpoint;
- reject the event if any control window comes within 45 minutes of another actual settlement.

The paired effect is fixed as:

`(settlement_post - settlement_pre) - (control_post - control_pre)`.

This nearby midpoint control reduces ordinary clock/regime drift without pretending observations
from the same UTC day or common market shock are independent.

## Frozen variables

Primary 15-minute-panel variables:

1. log quote volume;
2. log trade count;
3. absolute log return summed across the three-bar window.

Secondary variables:

- absolute signed taker imbalance, where signed imbalance is
  `(2 * taker_buy_quote_volume / quote_volume) - 1`;
- total ±1% depth notional;
- ±1% depth imbalance.

Depth uses the last snapshot strictly before each window boundary within five minutes. Missing or
late snapshots are reported, never forward-filled across the tolerance.

## Frozen independence and folds

- Nominal observations are symbol-settlement pairs.
- Independent clusters are unique settlement timestamps across all symbols.
- Use cluster bootstrap by settlement timestamp, seed `392`, 5,000 draws.
- Four chronological folds: calendar 2023, 2024, 2025, and 2026 through August 29.
- Report symbol breadth and each fold separately; do not count simultaneous symbols as independent.

## Frozen validity and verdicts

Integrity requires:

- at least 2,000 eligible unique settlement-time clusters;
- all six symbols represented in every fold;
- at least 90% complete primary windows;
- zero use of candles or snapshots after their declared point-in-time boundary.

If integrity fails: `INVALID_DATA`.

`INFORMATION_VALUE_CONFIRMED` requires all of:

1. at least two of three primary paired effects have cluster-bootstrap intervals excluding zero;
2. those effects have the same sign in at least three of four folds;
3. at least five of six symbols share the full-sample sign;
4. at least one execution-risk proxy is adverse and non-trivial: absolute-return increase at least
   10%, absolute-imbalance increase at least 10%, or ±1% depth decrease at least 10%;
5. the adverse proxy's cluster-bootstrap interval excludes zero.

Otherwise verdict is `LOW_INFORMATION_VALUE — DO_NOT_BUILD`.

Even `INFORMATION_VALUE_CONFIRMED` permits only a new unopened `NO_TRADE` economic hypothesis. It
does not prove that avoiding settlements improves net expectancy, because historical spread and
receive-latency data are absent.

## Engineering budget

- One disposable evaluator.
- One focused test file.
- One machine-readable report and task record.
- No collector, service, production rule, broker call, new download, or Rescue Ladder change.

## خلاصه ساده فارسی

قبل از دیدن نتیجه دقیقاً مشخص کردیم ۴۵ دقیقه قبل و بعد از زمان واقعی funding را با وسط همان چرخه
مقایسه کنیم. حجم، تعداد معامله، نوسان، عدم‌تعادل جریان و عمق سنجیده می‌شوند. اگر تغییر در چند سال
و چند نماد تکرار نشود، ایده رد می‌شود. حتی نتیجه مثبت فقط اجازه یک تست مستقل NO_TRADE می‌دهد و
هیچ تغییری در Rescue Ladder یا معاملات ایجاد نمی‌کند.
