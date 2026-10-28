# Path Integrity Implementation Unit 1 manifest

- Date: 2026-09-23/24 UTC. Baseline source HEAD before Unit 1: `3e95da9`.
- Changes: one isolated offline test file and these four provenance/trace reports only. Production strategy, Fusion, Risk, sizing, SL/TP, routing, config, brokers, frozen research and research verdicts untouched.
- Test: `pytest -q tests/unit/test_path_integrity_unit1_routes.py --disable-warnings` — 6 passed (LONG/SHORT × normal, duplicate delivery, queued-route cooldown veto). Spy has no broker/network/guard. Both source handlers execute; auto-detection queue is drained deterministically. Route call count is evidence for possible multiple **pre-broker service attempts**, not exchange sends.
- Search: source references to `bid_ask_spread`; current Python import/call paths for major historical families; prior strategy-fidelity and backtest-engine provenance reports. No old research execution or new profitability test.
- Limits: concurrent and genuine risk-rejected deliveries, exact already-running subscriber multiplicity, and real guard/broker outcomes are not established by the focused fixture. The cooldown case is an offline queued-route veto; it does not validate every live cooldown gate. `ArchitectureOrchestrator.start()` potentially repeats subscriptions, requiring its own lifecycle regression. Historical artifact/source-version binding is incomplete for unspecified archives.
- Frozen monitoring C-11/C-35/Compression/Phase 3A was not changed by Unit 1. Existing separate monitor may update its own ledgers independently; they are excluded from the Unit 1 commit.
- Next action requires review: complete missing route-variant characterization and separately approve remediation before any production path change. No canonical replay, baseline rerun or candidate retest has started.

LIVE_ROUTE_DUPLICATE_EXECUTION_CONFIRMED
HISTORICAL_PROVENANCE_AUDIT_COMPLETE
FEATURE_CAUSALITY_AUDIT_COMPLETE
