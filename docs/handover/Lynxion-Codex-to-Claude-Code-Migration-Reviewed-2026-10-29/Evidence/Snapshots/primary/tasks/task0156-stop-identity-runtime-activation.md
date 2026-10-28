# TASK-0156 — Stop-Identity Runtime Activation

**Status:** COMPLETE — COLLECTING FORWARD EVIDENCE

## Objective

Activate the TASK-0154 stop-identity correction on the approved BingX VST runner without mixing
code revisions or importing historical observations into the replacement forward cohort.

## Frozen Procedure

1. Audit and preserve the legacy TASK-0151 cohort before shutdown.
2. Stop only the uniquely identified existing auto-detect runner.
3. Start current HEAD through `lynxion` with an explicit absent/empty cohort root.
4. Require the runtime preflight to identify TESTNET and `live_trading=False`.
5. Verify one runner, a fresh activation boundary, exact HEAD provenance, and no historical events.

## Activation Evidence

- Operator approval was received on 2026-09-05.
- Legacy runner PID `32276` was uniquely identified and exited after `SIGTERM`.
- The replacement runner started at PID `53950`; the launch preflight reported `mode=TESTNET`,
  `testnet=True`, `order_placement_enabled=True`, and `live_trading=False`.
- New cohort root:
  `data/observability/forward_exit/cohorts/task0154-runtime-20260905T183755Z`
- Activation run ID: `task0155-20260905T183808Z`
- Activation boundary: `2026-09-05T18:38:08.780489+00:00`
- Frozen commit: `bf93cc061501474cad00a61767cb449f5730faba`
- `historical_import_allowed` is false. The first audit contained zero events; the next audit found
  one `POSITION_OBSERVED` event at `2026-09-05T18:40:09.603670+00:00`, strictly after the frozen
  boundary, with zero integrity violations. No legacy observation entered the post-fix cohort.
- The legacy TASK-0151 cohort remains at its original root and remains independently auditable.

## Verdict

Runtime activation is complete. The post-fix cohort remains `COLLECTING`; no claim about stop
visibility, trailing correctness, exit-policy superiority, or profitability is available until its
frozen evidence gates are satisfied.
