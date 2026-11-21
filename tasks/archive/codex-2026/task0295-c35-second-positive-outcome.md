# TASK-0295 — C-35 second prospective outcome

## Scope

Resolve the second mature C-35 signal using frozen public evidence and preserve subsequent no-signal
decisions. Do not authenticate, access a broker, trade, change parameters, or unseal economics.

## Evidence

- All eleven stages pass with zero candle gaps, duplicates, or boundary-role errors.
- `ADAUSDT SHORT` completed at its frozen exit epoch `1789293600`: gross return `+0.585938%`,
  primary cost-adjusted net return `+0.285938%`, and 0.50% stress-cost net return `+0.0859375%`.
- Its evidence SHA-256 is
  `1bd479277bf9cdf0fb1a2fcb1866e258161a49f7ee172e8ec096faa8efe83187`.
- Both completed prospective outcomes are individually positive under primary costs, but N=2, one
  side, two symbols, and one UTC week fail every aggregate minimum gate.
- Two later decisions were recorded as no-signal; no unresolved portfolio signal remains.

## Verdict

`COLLECTING — TWO POSITIVE OUTCOMES; FAR BELOW EVERY EDGE GATE`.
