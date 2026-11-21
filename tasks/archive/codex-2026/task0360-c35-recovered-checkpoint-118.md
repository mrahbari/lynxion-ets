# TASK-0360 — C-35 recovered hourly checkpoint at 118 decisions

## خلاصه ساده فارسی

اولین تلاش C-35 به‌دلیل قطع موقت اتصال عمومی صرافی شکست خورد، اما تلاش مجدد سالم اجرا شد و سه
ساعت عقب‌مانده را بدون gap ثبت کرد. cohort اکنون ۱۱۸ تصمیم دارد، ولی هر سه تصمیم جدید بدون سیگنال
بودند؛ پس edge تازه‌ای مشاهده نشده است.

## Scope

Recover the frozen public-only C-35 hourly collection after a transient connection reset without
authentication, broker access, protocol changes, or synthetic backfill.

## Evidence

- The first public candle request failed with `ConnectionResetError: [Errno 54]`.
- A bounded retry completed the frozen pipeline successfully.
- Candle integrity passes with 20,202 records, 2,814 prospective records, and zero gaps or
  duplicate keys.
- Funding integrity passes with 84 records and 552 coverage receipts.
- Three no-signal decisions advance C-35 from 115 to 118 decisions.
- The two prior completed SHORT outcomes remain unchanged and aggregate economics stay sealed.

## Verdict

`COLLECTING — TRANSIENT NETWORK ERROR RECOVERED; NO NEW EDGE EVIDENCE`.
