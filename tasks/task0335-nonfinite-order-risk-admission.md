# TASK-0335 — Non-finite order risk admission guard

## Scope

Close the matching fail-open numeric boundary on the authoritative order-path risk gate. Preserve
all strategy, leverage, sizing, stop, trailing, symbol, and profitability policy. Do not call a
broker or reload a runtime.

## Finding

`RiskEnforcement.enforce()` rejected non-positive size and price but did not reject non-finite
values. In Python, comparisons such as `NaN <= 0` and `NaN > limit` are false, so a malformed
`NaN` quantity or price could pass the local order-notional checks and reach later admission.

## Minimal correction

- Require both order size and entry price to be finite as well as positive.
- Reuse the module-level `math` import and preserve every existing threshold and decision order.
- Keep the BingX broker-snapshot validation from TASK-0334 unchanged as the independent final
  exchange-boundary check.

## Verification

- Four regressions reject `NaN` and infinity in both quantity and price.
- Focused risk/leverage suite: `43 passed`.
- Full suite: `1169 passed, 1 skipped`; the skip is the pre-existing optional import-linter gate.

## Verdict

`KEEP — NON-FINITE ORDER SIZE/PRICE NOW FAILS CLOSED BEFORE BROKER ADMISSION`.

Repository verification does not prove the currently running trading process has loaded this fix.
