# TASK-0442 — Fail closed without a verified execution price

## خلاصه ساده فارسی

اگر قیمت از execution service و fallback عمومی دریافت نمی‌شد، مسیر سفارش قیمت ساختگی ۵۰هزار دلار
استفاده می‌کرد. این قیمت می‌توانست quantity و notional واقعی را اشتباه کند. اکنون بدون قیمت مثبت و
محدود، سفارش قبل از sizing و broker routing رد می‌شود.

## Scope

- Retain the existing execution-service price and one public fallback attempt.
- Reject when both sources fail or produce a non-positive/non-finite price.
- Remove the synthetic `$50,000` execution and sizing fallback.

## Verification

`pytest -q tests/unit/test_heartbeat_guard_remediation.py -q`

Result: 8 passed, including fresh-heartbeat/no-price fail-closed coverage.

## Verdict

`KEEP — VERIFIED EXECUTION-PRICE SAFETY FIX`.

No broker call, runtime restart, account mutation, strategy/risk threshold, or research protocol was
changed. This is not edge evidence.
