# TASK-0376 — Exit-shadow recorded-blocker reporting and C-35 coverage refresh

## خلاصه ساده فارسی

readiness checker فقط می‌گفت «بررسی تازه runner لازم است» و دو مانع شناخته‌شده را نشان نمی‌داد:
در آخرین بررسی هیچ runner فعالی نبود و یک سفارش TRX-USDT هنوز pending ثبت شده بود. checker اکنون
این دو مورد را صریح گزارش می‌کند، ولی چون snapshot قدیمی است همچنان بررسی تازه را الزامی نگه
می‌دارد. هیچ سفارشی لغو نشد، runtime اجرا نشد و policy تغییر نکرد. C-35 سالم ماند ولی هنوز ساعت
کامل تازه‌ای برای تصمیم ۱۳۶ آماده نبود، بنابراین شمارش تصمیم‌ها روی ۱۳۵ باقی ماند.

## Scope

Make the repository-only exit-shadow readiness report surface recorded external blockers while
preserving the mandatory fresh read-only preflight. Do not infer current account state, access a
broker, start a runner, cancel an order, or activate the cohort.

## Evidence and decision

- The committed TASK-0359 preflight records runner count zero and one unexpected pending TRX-USDT
  entry order.
- The static checker previously ignored both facts and emitted only the generic fresh-evidence
  blocker.
- It now reports `RECORDED_RUNNER_COUNT_NOT_ONE` and
  `RECORDED_UNEXPECTED_PENDING_ENTRY_REQUIRES_OPERATOR_DECISION`, then still reports the mandatory
  fresh-evidence blocker because the snapshot cannot establish current external state.
- Malformed/non-object recorded evidence adds no inferred blocker and cannot authorize activation.
- Focused readiness regressions: `9 passed`.
- C-35 passes integrity with 20,628 candles, 3,240 prospective records, 96 funding records, and 624
  receipts. No newly completed decision hour was eligible, so decisions remain 135 and economics
  remain sealed.
- C-33 remains healthy with one active session and 1,081 eligible buckets.

## Next

Continue frozen cohorts and inventory the next local correctness claim. Exit-shadow activation
remains blocked on a fresh read-only external preflight and operator resolution of any still-pending
entry.
