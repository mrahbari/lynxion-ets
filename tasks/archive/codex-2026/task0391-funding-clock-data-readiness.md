# TASK-0391 — Funding Settlement market-quality data readiness

## خلاصه ساده فارسی

داده لازم برای یک تست کوچک Funding Settlement از قبل وجود دارد: زمان واقعی funding، جریان
خریدوفروش ۱۵دقیقه‌ای و snapshotهای عمق برای شش نماد از ۲۰۲۳ تا اوت ۲۰۲۶. spread و زمان دریافت
شبکه نداریم، بنابراین فعلاً فقط تغییرات حجم، جریان، نوسان و عمق قبل/بعد از settlement را بررسی
می‌کنیم. ساخت زیرساخت جدید لازم نیست و Rescue Ladder دست‌نخورده می‌ماند.

## Evidence

- Six Binance USD-M symbols have point-in-time funding histories with more than 5,000 settlements.
- BTC, ETH, BNB, XRP, and ADA use eight-hour intervals throughout the retained history; SOL also
  contains observed two-hour and four-hour schedules, so timestamps must be used rather than a
  hardcoded eight-hour clock.
- Six-symbol 15-minute flow/OHLCV coverage is common from `2023-01-01T00:00:00Z` through
  `2026-08-29T23:45:00Z`, 128,352 rows per symbol.
- Depth snapshots cover the same broad period and expose ±1% through ±5% depth/notional fields.
- Historical spread and receive timestamp are absent. No claim about exact executable spread or
  latency can be made from this panel.
- One focused readiness test passes.
- Verdict: `MINIMAL_DIAGNOSTIC_JUSTIFIED`.

## Boundary

This permits only a preregistered descriptive market-quality diagnostic with matched clock
controls. It does not permit a directional funding strategy, a production NO_TRADE rule, Rescue
Ladder modification, or edge claim.

## Next

Before inspecting pre/post values, freeze settlement-relative windows, matched non-settlement clock
controls, variables, folds, independence clusters, and a falsification gate. Prefer existing data;
do not add a spread collector in this phase.
