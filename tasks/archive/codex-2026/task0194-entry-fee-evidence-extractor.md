# TASK-0194 — Entry-fee evidence extractor

## Scope

Implement a pure disconnected extractor against already supplied order-history rows.
Do not fetch history, wire runtime, or calculate shadow outcomes.

## Result

- Admission requires a filled, explicitly non-reduce-only order matching symbol, side,
  entry price, quantity, and pre-observation time.
- Supplied exchange position identity is mandatory when available; otherwise exactly
  one composite attribute match is labeled `UNIQUE_ATTRIBUTES`.
- Ambiguity, missing commission/order identity, post-observation rows, exits, and
  cross-position evidence fail closed.
- Signed commission is retained and the absolute entry-fee price percentage is derived
  from authoritative fill notional.

## Remaining gap

Expected exit fee rate known before activation is still unavailable. TASK-0195 must
admit an explicit broker fee-schedule snapshot; it may not reuse entry rate as a hidden
proxy. Runtime collection remains deployment-gated.
