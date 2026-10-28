# TASK-0180 — Extended recent BingX exit audit preregistration

## Status

`COMPLETE — PERSISTENT_GIVEBACK_DIAGNOSTIC`

## Data-availability amendment (outcomes still unopened)

The official maximum single-response limit of 1,000 orders produced 98 fully
reconstructable completed positions. Before requesting any candle or calculating any
excursion/outcome metric, freeze all 98 as a labeled `INSUFFICIENT_FOR_N100` diagnostic
sample. Compare positions 1–49 with 50–98. This availability-only amendment changes no
metric, trade definition, threshold, or interpretation gate.

## Objective

Extend the read-only TASK-0129 diagnostic from 50 to the latest 100 completed BingX
VST positions, or up to 150 only if the same single history response supports that
many fully reconstructable positions. Determine whether profit giveback persists in
an older temporal block without selecting or deploying new exit thresholds.

## Frozen analysis

- Source: one authoritative BingX VST `allOrders` response plus public BingX one-minute
  candles from each reconstructed entry through exit.
- Position reconstruction: filled non-reduce-only entry and filled reduce-only exit
  sharing a non-zero `positionID`, identical to TASK-0129.
- Primary sample: latest 100 completed positions. If fewer than 100 are reconstructable,
  report insufficiency and do not substitute another endpoint or widen the definition.
- Optional extension: latest 150 only when already reconstructable from that response;
  do not paginate adaptively after seeing outcomes.
- Primary temporal comparison: newest positions 1–50 versus positions 51–100.
- Metrics: sample size, net realized PnL/estimated ROE, profit factor, win rate, median
  MFE/MAE/giveback, exit types, side/symbol concentration, and counts crossing estimated
  +10%/+12% MFE before exiting below +5% net ROE.
- Historical leverage missing from `allOrders` remains explicit. Any normalized 10x
  view initially remains sensitivity analysis. Post-outcome provenance note: the
  operator confirmed on 2026-09-06 that all scoped trades were 10x isolated and that
  this is verified in BingX; the history artifact itself still omits the field.
- One-minute candle extremes estimate opportunity; they do not prove manager observation,
  exchange-visible stop state, or executable fill at the extreme.

## Interpretation gate

This is diagnostic attribution, not a trading-edge admission test. Persistence of
giveback across both 50-position blocks may prioritize execution-path remediation and
a prospective exit-policy comparison. It cannot select a 5% floor from the same data.
No result authorizes a threshold, runtime, account, or order mutation.

## Next

The 98-position result is recorded in `docs/LYNXION_EXTENDED_BINGX_EXIT_AUDIT.md`.
Resume the TASK-0179 correction implementation after this bounded operator-requested
audit; do not select a 5% floor from these outcomes.
