# TASK-0383 — Lead-A profit-giveback provenance gate

## خلاصه ساده فارسی

اولین diagnostic سرنخ پس‌دادن سود اجرا شد و قبل از تحلیل سودآوری متوقف شد. ۱٬۹۱۳ معامله بسته‌شده
داریم، اما مسیر کندل محلی آن‌ها market identity مشخص ندارد. از طرف دیگر ledger مدیریتی ۶۴۷ مشاهده
mark-price واقعی برای ۲۶ موقعیت دارد، ولی رویداد exit fill یکپارچه ندارد. بنابراین ترکیب این دو و
ادعای اینکه یک state قبل از giveback سودآور است معتبر نیست. نتیجه `INSUFFICIENT_PROVENANCE` است؛
سرنخ رد نشده، اما برای تأیید به cohort بازنشده‌ای نیاز دارد که mark path و خروج واقعی را با هم ثبت
کند. هیچ threshold یا exit production تغییر نکرد.

## Evidence

- Normalized closed-trade journal: 1,913 rows across 76 symbols; 74 symbols have a local 1m file,
  but those files do not declare Spot/perpetual venue/series identity.
- Recent BingX diagnostic: 98 reconstructed exits, but candle path and historical leverage remain
  diagnostic/inferred rather than confirmatory.
- Canonical forward-exit ledger: 1,690 events, 647 `POSITION_OBSERVED` events, all 647 using MARK,
  18 position keys, and zero integrated exit-fill events.
- No single current dataset joins authoritative point-in-time mark observations to realized exit
  fills under one unopened boundary.
- Verdict: `INSUFFICIENT_PROVENANCE — DO NOT ESTIMATE EXIT EDGE`.
- Reproducible script: `scripts/audit_lead_a_data_readiness.py`.
- Focused tests: 2 passed.
- C-35 passes integrity with 21,012 candles, 3,624 prospective records, 108 funding records, 660
  receipts, and 151 no-signal decisions; economics remain sealed.
- C-33 is healthy with one active public session and 1,141 eligible completed buckets.
- C-11 is not due before its eight-hour interval and remains unchanged.

## Next

Do not optimize historical trailing thresholds. Reuse the already-defined exit-event schema to
prepare one empty unopened observational cohort that records authoritative mark observations and
realized exit fills together. Activation remains subject to existing runtime/account safety gates.
