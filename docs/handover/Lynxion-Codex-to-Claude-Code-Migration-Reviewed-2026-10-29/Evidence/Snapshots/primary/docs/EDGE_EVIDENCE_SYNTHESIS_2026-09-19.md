# Lynxion edge evidence synthesis — Rescue Ladder + Funding Settlement

**Decision date:** 2026-09-19

**Portfolio verdict:** `CURRENT_INFORMATION_SET_INSUFFICIENT`

## خلاصه ساده فارسی

نتیجه Funding Settlement کنار snapshot ثابت Rescue Ladder قرار گرفت. Funding باعث افزایش فعالیت
بازار می‌شود، اما اثر آن برای ساخت قانون NO_TRADE یا strategy کافی نیست. Lead B هم اثر آماری داشت
ولی هزینه‌ها آن را زیان‌ده کردند. C-35 بیش از حد کند است، Lead A داده خروج معتبر ندارد و C-11 هنوز
فقط پنج نتیجه دارد. بنابراین فعلاً edge اثبات نشده و با داده فعلی نباید یک ایده تاریخی دیگر بسازیم.
Rescue Ladder بدون تغییر حفظ می‌شود و فقط جمع‌آوری معتبر و اصلاحات قطعی ادامه پیدا می‌کنند.

## Evidence placed beside the fixed snapshot

| Evidence unit | Result | Decision impact |
|---|---|---|
| Rescue Ladder snapshot | Operator-approved fixed snapshot; not modified in this cycle | Preserve unchanged; no post-hoc tuning |
| Lead B quarter-hour flow | Statistical replication survived, but 2026 net expectancy was `-0.2827%` at 0.30% costs; PF `0.6007` | `REJECT_ECONOMIC_EDGE` |
| Funding Settlement clock | Activity increased broadly, but adverse execution proxies were below the frozen 10% materiality gate or improved | `LOW_INFORMATION_VALUE — DO_NOT_BUILD` |
| C-35 compression release | Two signals after 202 decision hours; projected 1,010 days to 240 outcomes at its frozen gate | `TOO_SLOW — DEPRIORITIZE AS PRIMARY` |
| Lead A profit giveback | No unopened dataset joins authoritative mark path to realized exit | `INSUFFICIENT_PROVENANCE` |
| C-11 severe funding | N=5, descriptive expectancy `+0.5722%`, PF `1.7631`, predominantly ETH | `COLLECTING`; far below frozen 100/30 gates |
| C-33 liquidation cohort | 1,167 eligible buckets, but collector freshness failed after September 17 | Background evidence unavailable until freshness is restored without backfill |

## What changed our beliefs

- Quarter-hour and funding clocks can produce genuine, broad market-activity effects without
  producing executable edge.
- The current bottleneck is not a missing threshold or strategy wrapper. It is differentiated,
  point-in-time information whose economic magnitude exceeds retail execution costs.
- Continuing slow or already-opened historical variants would increase data-mining risk more than
  decision quality.

## Frozen decision

1. Do not change the Rescue Ladder from these results.
2. Do not reopen Lead B, Funding Settlement, or rejected flow/funding variants by threshold changes.
3. Continue C-11 under its original prospective gate and cadence.
4. Keep C-35 background-only with sealed economics.
5. Diagnose C-33 collector freshness without backfill.
6. Continue verified correctness/risk/execution fixes independently; they are not edge evidence.
7. Do not admit another historical strategy family until genuinely new information or a clean
   unopened evidence boundary exists.

## Next decision trigger

Revisit the portfolio only when one of these occurs:

- C-11 reaches a frozen checkpoint or material new outcome;
- the joined forward mark-path/realized-exit cohort makes Lead A testable;
- C-33 freshness is restored and its own frozen checkpoint is reached;
- the operator supplies a genuinely new causal observation with point-in-time data;
- a verified execution/correctness defect invalidates a prior economic rejection.

Until then, the correct answer is not to manufacture another candidate. It is to preserve the
evidence boundary, collect only justified forward information, and keep the platform correct.
