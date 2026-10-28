# TASK-0448 — Filled-only position-closure evidence

## خلاصه ساده فارسی

reconciliation سفارش‌های محافظتی `CANCELLED/REJECTED` را هم terminal می‌دانست و ممکن بود یک TP
لغوشده را به‌عنوان خروج سودده انتخاب کند، با اینکه چنین سفارشی موقعیت را نبسته است. اکنون فقط
سفارش `FILLED` می‌تواند مدرک بسته‌شدن موقعیت باشد.

## Scope

- Require `FILLED` status when selecting the closing SL/TP/liquidation/reduce-only order.
- Preserve broader terminal-state handling outside position-closure attribution.
- Keep cooldown and profit/loss classification rules unchanged.

## Verification

`pytest -q tests/unit/test_b4_broker_reconciliation.py -q`

Result: 12 passed, including cancelled-TP versus filled-SL ordering.

## Verdict

`KEEP — VERIFIED TERMINAL-EVIDENCE CORRECTNESS FIX`.

No broker call, runtime restart, account mutation, strategy/risk setting, or research protocol was
changed. This is not edge evidence.
