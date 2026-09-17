# TASK-0382 — New edge lead tournament

## خلاصه ساده فارسی

سرنخ‌های جدید وارد یک رقابت محدود شدند تا دوباره دچار ساخت candidate و زیرساخت بی‌پایان نشویم.
Lead A، یعنی تشخیص وضعیت پس‌دادن سود بعد از MFE، به‌عنوان تنها diagnostic فعال انتخاب شد. اثر
ربع‌ساعت رتبه دوم است ولی ابتدا باید ثابت شود داده خام ۱۰ثانیه‌ای کافی داریم. مسیرهای flow قدیمی،
liquidation و calendar بدون اطلاعات جدید باز نمی‌شوند. C-11، C-33 و C-35 بدون تغییر ادامه دارند.

## Deliverables

- `docs/NEW_EDGE_LEAD_TOURNAMENT.md`
- `docs/HUMAN_OBSERVATION_INBOX.md`
- One active diagnostic only: Lead A descriptive/provenance analysis.
- No production, strategy, exit, risk, broker, or frozen-cohort change.

## Verdict

`ACTIVATE LEAD A MINIMAL DIAGNOSTIC; B DATA-READINESS NEXT; PARK OR REJECT THE REST`.

## Next

Build the smallest disposable Lead-A provenance/path diagnostic and reject immediately if the
reconstructable sample or independent-event breadth is inadequate.
