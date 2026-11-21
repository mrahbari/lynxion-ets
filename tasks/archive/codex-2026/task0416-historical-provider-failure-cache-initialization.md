# TASK-0416 — Historical-provider failure-cache initialization

## خلاصه ساده فارسی

runner در حالت TESTNET بالا آمد، اما برای همه نمادها پیام نبودن داده معتبر perpetual می‌داد. علت واقعی
این بود که provider یک cache را قبل از ساخته‌شدن می‌خواند؛ خطا در لایه بالاتر به لیست خالی تبدیل می‌شد
و سیستم به‌صورت امن ولی بدون امکان تحلیل ادامه می‌داد. cache اکنون قبل از اولین درخواست ساخته می‌شود.

## Scope

- Initialize only the already-required failed-symbol cache and TTL.
- Store failures under the same `(market_type, symbol)` identity used for lookup.
- Do not change strategy rules, risk limits, symbol policy, endpoints, or execution behavior.

## Evidence

- Reproduced pre-fix `AttributeError: ... has no attribute 'failed_symbols_cache'` through the actual
  configurable provider.
- Thirteen focused coverage/routing tests pass, including initialization and market-scoped failure
  identity regressions.
- Post-fix public-provider diagnostic returns complete BTCUSDT perpetual windows:
  - 30 candles for `30m/1m`;
  - 240 candles for `10d/1h`;
  - 288 candles for `3d/15m`.
- No authenticated broker call, order, cancellation, position mutation, or strategy-policy change
  occurred during diagnosis or verification.

## Verdict

`KEEP — PRODUCTION DATA-LIVENESS DEFECT FIXED LOCALLY — RESTART REQUIRED`.

The operator-started process still contains the old in-memory code. It must be stopped and restarted
from this task's commit using a new empty forward-exit cohort. Runtime evidence after restart remains
required; this task is correctness evidence, not edge evidence.
