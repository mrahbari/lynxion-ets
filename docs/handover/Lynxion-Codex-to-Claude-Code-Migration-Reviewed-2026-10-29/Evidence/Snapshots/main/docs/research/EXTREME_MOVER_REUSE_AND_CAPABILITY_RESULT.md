# Extreme-mover opportunity view — bounded reuse and implementation result

2026-10-13. Scope: R22 research-only, outcome-blind. Baseline `025094a`. This is **not** a frozen mover formula, tradable ranking, candidate detector, trading signal or Edge experiment. No historical data were downloaded, no future outcomes opened, and no live component was registered.

## Reuse-first audit

| Existing component | Finding | Decision |
|---|---|---|
| `infrastructure/watchers/adapters/cmc_screener.py` | Current CMC listings/API-key, mutable history, local-now timestamp and fallback to another symbol when requested symbol is absent. It emits market observations but cannot prove historical perpetual membership or a same-cutoff denominator. | **UNSAFE** for historical causal ranking; do not modify/import. |
| Momentum and volatility watchers | Per-symbol mutable live windows; volatility watcher can depend on a broker service and uses runtime clocks. Existing historical C-08/C-09 relative-strength scripts rank selected panels but include already-opened outcomes and fixed selected symbols. | **REUSE CONCEPT ONLY**; no live watcher or old cohort in this capability. |
| `MacroRegimeEngine` | Classifies a supplied price series/indicators; it does not reconstruct historical exchange membership or cross-sectional rank and includes veto semantics. | **NOT EQUIVALENT**; do not couple research view to live regime state. |
| Market-context/ranking components | `signal_aggregator` ranks existing signals, not all eligible contracts with source-time membership. | **NOT EQUIVALENT**; no Fusion/Strategy confidence bridge. |
| Historical source/adapters | Local C06/C09/C15 and other study panels are selected symbol cohorts; C06 is development-only and prior outcome work exists. No complete time-T listing/status/delisting, same-cutoff full-universe bar/receipt and cost panel was qualified. | **BLOCKED_EXTERNAL** for real historical universe/ranks. No survivor list substitution. |

The pre-existing [feasibility](CROSS_SECTIONAL_EXTREME_MOVER_FEASIBILITY.md) remains `EXTREME_MOVER_DATA_PARTIAL` and its [information contract](CROSS_SECTIONAL_EXTREME_MOVER_INFORMATION_CONTRACT.md) still leaves venue, cadence, metric formula, thresholds and horizon undecided. This audit did not choose them.

## Minimal missing component

`domain/extreme_mover_opportunity.py` is a pure causal interface. The caller supplies a contemporaneous universe snapshot, one explicitly identified metric observation for **every** listed symbol, source hashes, interval ends and receipt times. It rejects absent/duplicate symbols, mixed metric identities, nonfinite values, incomplete bars, late receipts and late universe snapshots. The output sorts the supplied metric ascending with a deterministic symbol tie-break, records its source hashes and timestamp, and contains **no** selected top-N, threshold, confidence, direction, ExecutionIntent, order or outcome. It does not independently certify a caller's source hash or that the snapshot is an exhaustive exchange universe; that source qualification remains external and mandatory before real data can be claimed.

The eight synthetic unit tests run with cleared environment (`/usr/bin/env -i PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -m unittest tests.unit.test_extreme_mover_opportunity -v`). They include a mixed-cutoff rejection. A canonical JSON record from the two-symbol synthetic fixture, serialized with sorted keys and compact separators, has SHA-256 `d2817f155c90edb3ee708c6cfde9f21fed7c53ff9851057bed6eabed808cc98b`. This is a reproducible **synthetic** output hash, not a historical rank or market observation.

**Result:** research-only interface and deterministic synthetic proof are complete. Real historical opportunity output is **NOT GENERATED / BLOCKED_EXTERNAL** because a point-in-time complete tradable universe and synchronized received-at-T metric panel were not qualified locally. No source-level route from this module to FusionV3, StrategyManager, Risk, Broker or production config was added. A full independent Edge test remains scientifically unvalidated and separately approval-gated.
