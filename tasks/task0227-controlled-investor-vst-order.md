# TASK-0227 — Controlled investor-visible VST order

## Scope

Add and execute one fail-closed BingX VST demonstration order after explicit operator
authorization. This task does not authorize live funds or recurring automated orders.

## Acceptance criteria

- explicit CLI opt-in is required;
- BingX testnet, broker placement, non-paper execution, and BingX-only routing are verified;
- existing VST positions must already have exchange-side SL and TP;
- duplicate-symbol entry is rejected;
- notional is at most 20 USDT and current configured leverage is used;
- the normal broker risk-admission and protected execution path is used;
- the resulting isolated position and exchange-side SL/TP are independently visible.

## Evidence — 2026-09-09

- Focused tests: `7 passed`.
- An initial invocation failed closed because the paper-mode field was read from the wrong
  settings domain; no order was sent. The settings lookup was corrected and regression-tested.
- ADAUSDT was rejected by the existing cooldown gate; the cooldown was not cleared or bypassed.
- One DOGEUSDT LONG was accepted by the normal BingX risk gate at 19.92 USDT notional.
- BingX VST order ID: `2097618310297292800`; quantity 219; configured leverage 5x.
- Independent postflight: DOGEUSDT is isolated, with one STOP_MARKET and one
  TAKE_PROFIT_MARKET; the account-wide audit reports three positions and no missing SL/TP.

## Verdict

`KEEP — CONTROLLED VST DEMO VERIFIED`. This proves test-exchange execution and protection,
not strategy profitability or live readiness.
