# TASK-0212 — Local data independence audit

## Status

`COMPLETE — NO UNOPENED LOCAL HISTORICAL OUTCOME BOUNDARY`

## Objective

Determine whether an existing local research dataset can support the third admissible
route from TASK-0211: a genuinely new mechanism evaluated on outcomes that were not
already inspected. Do not open or recompute any return.

## Inventory result

The reusable local research stores comprise price/volume and taker flow, Spot bars,
order-book depth, open-interest metrics, premium index/basis, funding, BTC aggregate
trades, and prior BingX exit evidence. Their available historical boundaries and symbol
panels have already supplied C-16 through C-32 and C-34, earlier candidate families, or
the exit-policy diagnosis. Recombining their observed periods would not create an
independent outcome boundary.

The two still-unopened evidence stores are prospective rather than historical:

- C-33 liquidation events after its committed activation boundary; collection is
  stopped and cannot be backfilled.
- The post-fix exit-shadow cohort; activation remains behind its frozen runtime and
  provenance gates.

The existing BTC aggregate-trade store is single-symbol and belongs to an already-opened
period. The independent Spot symbol panel changes symbols, but its outcome dates were
already used as an independent confirmation; it cannot be recycled as a fresh test.

## Decision

No existing local historical file is admitted for C-35. A future historical candidate
requires both a mechanism not already family-closed and a genuinely unopened time,
venue, or asset outcome panel, frozen before its acquisition or inspection. Merely
renaming fields, combining known signals, or choosing another threshold does not qualify.

## Acceptance

This audit used manifests and committed candidate registers only. It did not read return
outcomes, download data, start a collector or runtime, call a broker, or mutate any
cohort. The valid roadmap remains prospective C-33 or prospective exit-shadow evidence.
