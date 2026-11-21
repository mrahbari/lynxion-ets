# TASK-0359 — Exit-shadow read-only runtime preflight

## خلاصه ساده فارسی

بررسی فقط‌خواندنی نشان داد هیچ runner فعالی وجود ندارد و هیچ پوزیشن بازی هم نداریم، بنابراین شرط
«دقیقاً یک runner» پاس نشد. همچنین یک سفارش LIMIT فروش برای SHORT روی TRX-USDT هنوز در حساب VST
pending است. این سفارش بدون مجوز صریح لغو نشد و تا تعیین تکلیف آن، فعال‌سازی آزمایش خروج ایمن نیست.

## Scope

Use the operator-authorized read-only process and BingX VST account checks to evaluate the final
exit-shadow activation prerequisite. Do not start/reload a runner, place/cancel/amend an order, or
change policy.

## Evidence

- Process enumeration found zero `run_trading_system.py`/Lynxion runners.
- BingX VST reports zero open positions and therefore zero positions missing SL or TP.
- BingX VST reports one pending non-protective order: TRX-USDT SELL/LIMIT, SHORT, quantity 139,
  price 0.35925.
- All checks were read-only and no broker state was mutated.

## Verdict

`BLOCKED — EXACTLY ONE RUNNER REQUIRED; UNEXPECTED PENDING ENTRY REQUIRES OPERATOR DECISION`.
