# TASK-0334 — BingX non-finite exposure admission guard

## Scope

Close one verified fail-open boundary in BingX broker-backed entry admission without changing
strategy, leverage, sizing, stop, trailing, symbol, or profitability policy. No broker call,
runtime reload, or cohort mutation is part of this task.

## Finding

The final admission path derives current portfolio exposure from the authoritative BingX position
snapshot. Python comparisons against `NaN` are false, so a non-finite position quantity could be
omitted and a non-finite reference price/exposure could bypass the `$1,000` portfolio comparison.
A positive open position with no positive finite mark/average price was also counted as zero.

## Minimal correction

- Reject every non-finite broker position quantity.
- For each non-zero position, require a finite mark price or a positive finite average-price
  fallback.
- Reject non-finite calculated position exposure.
- Sum only prevalidated exposures before applying the existing unchanged portfolio limit.

## Verification

- Regression cases prove `NaN` quantity, `NaN` mark price, and zero mark/average price all reject
  before any broker POST.
- Focused risk/leverage suite: `39 passed`.
- Full suite: `1165 passed, 1 skipped`; the skip is the pre-existing optional import-linter gate.

## Verdict

`KEEP — BINGX BROKER-SNAPSHOT EXPOSURE ADMISSION NOW FAILS CLOSED`.

Repository verification does not prove the running process has loaded this change. Runtime reload
and authenticated post-deployment evidence remain separate operational work.
