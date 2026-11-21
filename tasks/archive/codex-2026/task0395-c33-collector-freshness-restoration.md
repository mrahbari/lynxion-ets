# TASK-0395 — C-33 collector freshness restoration

## خلاصه ساده فارسی

مشخص شد collector قبلی C-33 واقعاً process فعالی نداشت و session باز آن بیش از یک روز بدون داده
مانده بود. session مرده با سیاست «فاصله گمشده غیرمجاز و بدون backfill» بسته شد و collector pinned
دوباره اجرا شد. اکنون رکوردهای تازه ثبت می‌شوند، اما تعداد bucketهای معتبر همان ۱٬۱۶۷ مانده است؛
هیچ داده تاریخی وارد cohort نشده است.

## Diagnosis

- Ledger showed one nominal active session whose only record was a heartbeat at
  `2026-09-17T17:06:36Z`.
- Read-only process inspection found no matching collector process.
- The prior session was therefore externally proven dead and older than the frozen 15-minute stale
  threshold.
- The collector source blob still matched the activation manifest's pinned commit.

## Restoration

- Closed exact stale session `357215d4-fa91-485c-a1d2-7ed1a9174e0a`.
- Missing interval policy: `INELIGIBLE_NO_BACKFILL`.
- Started the existing public collector through its fail-closed `--enable-network` entry point.
- Fresh active session: `d3c927d6-0435-4dca-8809-b54ee11aa91c`.
- Verified fresh records through `2026-09-19T16:37:01Z` and exactly one active session.
- Eligible completed buckets remain 1,167; verdict remains `COLLECTING`.

## Monitoring

- C-35 passes its hourly pipeline at 208 decisions, still two signals and background-only.
- Due C-11 update remains unchanged at N=5, expectancy `+0.5722%`, PF `1.7631`, and `COLLECTING`.
- Every C-11 settlement remains strictly after epoch `1788082349`.

## Validation

- Existing C-33 resume/recovery focused suite passes.
- No backfill, historical import, broker call, trading runtime, order/account mutation, strategy
  change, or Rescue Ladder change occurred.

## Next

Keep C-33 on the public collector and require a fresh eligible bucket before calling collection
fully productive. Continue correctness/risk/execution backlog work while waiting for valid evidence
triggers.
