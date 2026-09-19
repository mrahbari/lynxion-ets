# TASK-0390 — C-35 frozen throughput gate

## خلاصه ساده فارسی

C-35 از checkpoint از پیش تعیین‌شده ۱۶۸ تصمیم عبور کرده و حالا ۲۰۲ تصمیم دارد، اما فقط دو سیگنال
ساخته است. با این سرعت رسیدن به ۲۴۰ نتیجه حدود ۱٬۰۱۰ روز طول می‌کشد؛ خیلی بیشتر از سقف عملی
۹۰روزه. بنابراین C-35 از مسیر اصلی تحقیق کنار گذاشته می‌شود، ولی جمع‌آوری کم‌هزینه آن بدون تغییر
در پس‌زمینه ادامه پیدا می‌کند و نتیجه‌های اقتصادی همچنان بسته می‌مانند.

## Frozen evidence

- Decision hours: 202.
- Signals: 2; signals/day: `0.2376`.
- Mechanical projection to 240 raw outcomes: 1,010 days.
- The preregistered acceleration rule deprioritizes C-35 when projected completion remains beyond
  90 days at the 168-decision checkpoint.
- Candle integrity: PASS at 22,230 total and 4,842 prospective records.
- Funding integrity: PASS at 150 records and 696 coverage receipts.
- Completed outcomes remain 2, both SHORT, two symbols, one UTC week; economics remain sealed.

## Verdict

`TOO_SLOW — DEPRIORITIZE AS PRIMARY`

This is a throughput verdict, not an economic rejection. Continue the existing low-cost background
collector unchanged; do not loosen thresholds, backfill, inspect sealed aggregate economics, or
delay faster research for C-35.

## Next

Proceed with the Funding Settlement market-quality readiness diagnostic. C-35 remains background
only. Diagnose C-33 freshness separately without backfill.
