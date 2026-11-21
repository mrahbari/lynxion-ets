# TASK-0236 — MFE/MAE provenance and coverage audit

## Scope

Establish whether the frozen investor baseline can support a defensible separation of weak
entries from profit giveback. This is an evidence audit only; it does not change an exit rule,
strategy, runtime, broker path, cohort, or economic verdict.

## Evidence

- The immutable TASK-0228 baseline contains 1,913 source rows and 1,257 deduplicated final
  trades. Its 31-column schema contains neither MFE nor MAE, so direct excursion coverage is
  `0 / 1,257` for both measures.
- The production journal schema and the current attribution report likewise do not persist
  MFE/MAE. `scripts/performance_attribution.py` correctly reports both as unavailable rather
  than inferring them.
- The separate BingX exit diagnostics contain one-minute candle-extreme MFE/MAE estimates for
  50 and 98 reconstructed VST positions. The 98-position artifact has complete estimated
  excursion fields, but the broker response omitted historical leverage for all 98 positions.
  Operator-confirmed 10x therefore remains external provenance, not self-contained source data.
- Those diagnostics are a recent, post-hoc subset and do not carry the baseline `trade_id`.
  They cannot be silently joined to, or generalized across, the 1,257-trade frozen baseline.
- One-minute candle extremes measure opportunity within a candle. They do not prove that the
  trailing manager observed the extreme, that a stop mutation was exchange-visible at that
  instant, or that the extreme was executable after spread, slippage, fees, and funding.

## Classification consequence

The existing 98-position diagnostic supports a bounded hypothesis that profit giveback may be
an exit-management problem. It does **not** establish that entries have positive edge, that
exit changes would make net expectancy positive, or that the baseline losses are primarily an
exit failure. A causal entry-versus-exit classification is therefore currently `UNKNOWN`.

## Required next evidence unit

Build a deterministic, ambiguity-rejecting linkage assessment between broker-reconstructed
positions, the trade journal, and complete one-minute candle intervals. Report coverage and
collision rates before calculating or selecting any exit-policy outcome. If authoritative
linkage is insufficient, preregister prospective MFE/MAE capture instead of imputing history.

## Verdict

`KEEP — PROVENANCE GAP IDENTIFIED; NO EDGE OR EXIT-POLICY CLAIM ADMITTED`.
