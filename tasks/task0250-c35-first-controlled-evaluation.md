# TASK-0250 — C-35 first controlled evaluation

## Scope

Refresh the public candle ledger, verify it, and perform the first read-only C-35 signal evaluation.
Append a signal only if the frozen evaluator finds one; never open an outcome here.

## Correctness defect and repair

The committed bridge passed module-import tests but direct CLI execution failed because `scripts`
was not importable from the script directory. Added the same explicit package/direct-execution
fallback used by adjacent research tools and a subprocess regression for the documented CLI.

## Evidence

- Public refresh appended 27 completed candles per symbol.
- Verified ledger: 17,676 rows, exactly 2,946 per symbol, 17,388 warmup and 288 prospective rows,
  with zero gap, duplicate, boundary-role, hash, timing, numeric, or OHLC defect.
- Twelve exact-hour decisions were causally evaluable. None met the frozen compression-release
  signal, so no signal or outcome ledger was created.
- Eight focused bridge/state tests pass, including direct CLI execution.
- Candle ledger SHA-256 after refresh:
  `090299324fb2622d9db2db69a9501d8e896f07d444cc2559ddaeeb088e67a65b`.

## Verdict

`COLLECTING — FIRST 12 DECISIONS VALID; ZERO QUALIFYING SIGNALS; NO OUTCOME OPENED`.

Zero signals is an expected research result, not an error or evidence of edge. Continue hourly
public refresh and deterministic evaluation; implement outcome resolution before any signal can
mature.
