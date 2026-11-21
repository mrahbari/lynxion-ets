# TASK-0384 — Lead-B quarter-hour temporal-resolution gate

## خلاصه ساده فارسی

داده BTC aggTrades بررسی شد. خروجی normalized فقط ۱۵دقیقه‌ای است، اما نکته مثبت این است که هر
۹۷۲ آرشیو خام روزانه با timestamp میلی‌ثانیه‌ای در پروژه نگه‌داری شده‌اند. بنابراین پنجره ۱۰ثانیه
اول بعد از `HH:00/15/30/45` قابل بازسازی است و دانلود چندماهه جدید لازم نیست. Lead B فقط برای یک
replication diagnostic کوچک آماده است؛ هنوز اجازه بررسی سود یا ساخت candidate وجود ندارد.

## Evidence

- Manifest covers 972 days and 1,467,689,495 raw rows processed before aggregation.
- All 972 retained daily files contain 15-minute summary columns, normally 96 rows per complete day.
- All 972 raw daily ZIP archives are retained; their schema includes millisecond
  `transact_time` and aggressor-side information through `is_buyer_maker`.
- Sample aggregate timestamp delta is 900 seconds, but the raw archives preserve the externally
  required first-10-second window.
- Both the first-seconds boundary input and four-to-twelve-hour outcomes are representable.
- Verdict: `READY FOR MINIMAL REPLICATION DIAGNOSTIC — OUTCOMES STILL SEALED`.
- Reproducible script: `scripts/audit_lead_b_clock_phase_readiness.py`.
- Focused tests: 2 passed.
- C-35 passes integrity with 21,036 candles, 3,648 prospective records, 114 funding records, 666
  receipts, and 152 no-signal decisions; economics remain sealed.
- C-33 is healthy with one active public session and 1,154 eligible completed buckets.
- C-11 is not due before its eight-hour interval and remains unchanged.

## Next

Freeze a minimal sampling contract over already-retained data: BTCUSDT Binance USD-M only,
preselected chronological folds, exact first-10-second and matched control windows, and no future
return inspection until integrity and clock-phase construction pass. Do not build or download.
