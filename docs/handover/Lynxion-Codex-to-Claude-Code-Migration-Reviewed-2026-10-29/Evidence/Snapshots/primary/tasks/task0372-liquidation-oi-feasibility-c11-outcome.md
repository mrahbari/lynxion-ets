# TASK-0372 — Liquidation/OI feasibility, C-11 outcome, and C-35 checkpoint 132

## خلاصه ساده فارسی

داده تاریخی OI و داده forward لیکوییدیشن C-33 هم‌پوشانی زمانی ندارند؛ دو آزمون معتبر قبلی نیز
هم ادامه حرکت و هم برگشت پس از تخلیه OI را رد کرده‌اند. ساخت collector جدید پاسخ را سریع‌تر
نمی‌کند، پس آزمون تازه نمی‌سازیم و C-33 فقط در پس‌زمینه ادامه می‌یابد. C-11 یک نتیجه کامل جدید
دارد و میانگین فعلی آن مثبت است، اما فقط چهار نتیجه داریم و هنوز برای ادعای edge بسیار کم است.
C-35 نیز سالم به ۱۳۲ تصمیم بدون سیگنال رسید.

## Scope

Perform the bounded liquidation/OI feasibility review, refresh due public-only C-11 and hourly
C-35, and preserve all frozen boundaries. Do not open C-33 outcomes, create collection
infrastructure, change production, or call authenticated broker paths.

## Evidence and decision

- Historical OI ends at epoch `1788047700`; it cannot be causally joined to prospective C-33.
- C-16 continuation and C-17 exhaustion were both cost-adjusted, broad, and rejected.
- C-33 audit initially reported 1,034 eligible buckets versus 8,640 required warmup and zero active
  sessions. The existing public-only supervisor was resumed; verification now shows exactly one
  active session and a fresh heartbeat, with no backfill.
- Verdict: `TOO SLOW — DEPRIORITIZE NEW TEST; KEEP C-33 BACKGROUND ONLY`.
- C-11 now has four COMPLETE and one PENDING records. All funding settlements are strictly after
  boundary `1788082349`. Current descriptive expectancy is +0.2524% and PF 1.2693, but N=4 is not
  decision-grade evidence; verdict remains `COLLECTING`.
- C-35 passes integrity with 20,550 candles, 3,162 prospective records, 96 funding records, and 606
  receipts. One no-signal decision advances it to 132; economics remain sealed.
- Focused C-11/C-33/C-35 regression suite: `19 passed`.

## Next

Run one bounded review of whether existing order-flow toxicity evidence leaves a distinct,
low-cost incremental NO_TRADE/state-classification question beyond the rejected standalone flow
families. Do not build raw L2 infrastructure.
