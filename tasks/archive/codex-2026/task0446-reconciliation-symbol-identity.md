# TASK-0446 — Reconciliation terminal-order symbol identity

## خلاصه ساده فارسی

reconciliation جدیدترین terminal order را انتخاب می‌کرد، اما اگر پاسخ broker شامل چند نماد بود،
symbol هر ردیف را دوباره کنترل نمی‌کرد. بنابراین خروج نماد دیگری می‌توانست اشتباهاً سود/زیان این
موقعیت محسوب شود. اکنون ردیف‌های دارای symbol ناسازگار نادیده گرفته می‌شوند.

## Scope

- Normalize and compare a terminal-order symbol when the broker row provides one.
- Preserve compatibility with symbol-filtered broker responses that omit the symbol field.
- Keep exit classification and cooldown policy unchanged.

## Verification

`pytest -q tests/unit/test_b4_broker_reconciliation.py -q`

Result: 11 passed, including a mixed-symbol history regression.

## Verdict

`KEEP — VERIFIED RECONCILIATION IDENTITY FIX`.

No broker call, runtime restart, account mutation, strategy/risk setting, or research protocol was
changed. This is not edge evidence.
