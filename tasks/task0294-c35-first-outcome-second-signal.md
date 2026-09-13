# TASK-0294 — C-35 first outcome and second signal

## Scope

Resolve the first mature C-35 signal from frozen public evidence and preserve the next portfolio
signal. Do not authenticate, access a broker, place orders, change parameters, or unseal aggregate
economics.

## Evidence

- All eleven stages pass with zero candle gaps, duplicates, or boundary-role errors.
- The first `XRPUSDT SHORT` outcome completed at its frozen exit epoch `1789290000`:
  gross return `+0.935134%`, funding return `+0.001661%`, and primary cost-adjusted net return
  `+0.636795%` under the frozen 0.30% round-trip cost assumption.
- The evidence is bound by SHA-256
  `f96d525e4985a6753acff436bce70aea58e40f16bb34fa19b16fb5b932b6e50f`.
- After resolution freed the portfolio slot, decision epoch `1789286400` emitted the second signal:
  `ADAUSDT SHORT`, frozen exit-open epoch `1789293600`.
- Aggregate economics remain sealed. One positive outcome is not evidence of durable edge.

## Verdict

`COLLECTING — FIRST OUTCOME POSITIVE; SECOND SIGNAL PENDING; NO EDGE CLAIM`.
