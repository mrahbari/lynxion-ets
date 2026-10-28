# Opportunity Radar V1 — implementation handover

## 2026-10-28 — current source location and output-format correction

Actual integrated offline source is local main `/Users/mojtaba.rahbari/.codex/worktrees/epic01-main-integration/lynxion-ets` (review baseline6e99742),
not the original feature worktree named below and not deployed primary. The CLI writes
**one JSON document containing a rows array**, followed by a newline. References below
to canonical output JSONL are corrected to JSON; optional detector INPUT remains JSONL.
The previously recorded SHA-256 values and frozen contract are unchanged.

Latest dated verification is27October: selected Radar/ClosedBarSource/ExtremeMover suite
23PASS/1warning; six-row descriptive replay hash00e2826377d2fcd7cc89a906c37030b11026c6d0bf3f053a8a8fac49823c937d.
No rerun today. T02-S02 watcher/screener shadow integration remains BLOCKED. This is not
live trading Radar, market-wide historical qualification, modeled fill proof or demonstrated Edge.
[Current project status](/Users/mojtaba.rahbari/Sites/python/lynxion-ets/docs/LYNXION_CURRENT_STATUS_AND_BLOCKERS.md); old tests/worktree statements below remain dated evidence.

Baseline main commit `096885b`; isolated managed worktree `opportunity-radar-v1`. Final worktree commit is the containing commit of this file. P0 recovery worktree is separate and higher priority. No production runtime/deployment or frozen research artifact was modified.

## Capability delivered

`scripts/opportunity_radar_v1.py` is a read-only CLI. It validates the six-symbol local C06 M15 panel against its manifest, calculates a fixed four-bar signed move, ranks **only the observed cohort** by absolute movement, and shows a separate completed-H1 research context and optional same-cutoff Structural Pullback Failure metadata. It does not import live StrategyManager/FusionV3, create ExecutionIntent, access a broker or emit an order. The existing 5m/15m/1h MTF_TREND structure and automatic strategy routing remain unchanged. See [contract](OPPORTUNITY_RADAR_V1_CONTRACT.md) for exact timing, quality and formula.

### Reuse boundary

`HistoricalClosedBarSource` is used for strict UTC closed-bar and OHLC/gap validation. The H1 context uses the same 30-close normalized linear-regression calculation as `TrendMTFWatcher.calculate_trend` via a stdlib adapter; the live watcher itself is unsafe to import into this minimal environment because it imports shared runtime/NumPy and carries mutable/live-clock state. CMC screener is current/API-key/mutable and cannot prove historical perpetual eligibility. MacroRegimeEngine is a separate 4H regime/veto component, not the configured 1H context. Historical C08/C09 rankers use selected, outcome-opened panels. The pure `domain/extreme_mover_opportunity.py` interface remains available; it demands a complete supplied universe and metric but cannot fabricate historical membership. None is an equivalent qualified whole-market radar.

### Exact replay

```sh
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 scripts/opportunity_radar_v1.py \
  --data-dir /Users/mojtaba.rahbari/Sites/python/lynxion-ets/data/research/c06/binance_futures_15m \
  --cutoff 2023-01-15T00:00:00+00:00 \
  --output /private/tmp/opportunity-radar-v1-2023-01-15.json
```

Result: six rows, all `OBSERVED_IN_PANEL_TRADABILITY_UNKNOWN`; contiguous/hash-checked local bars are `data_quality=VALID`, while `source_qualification=MANIFEST_HASH_MATCHED_DEVELOPMENT_ONLY_NO_RECEIPT`. The six descriptive movement ranks, separate completed-H1 context and `SETUP_UNAVAILABLE` without the optional research file remain distinct. SHA-256 of canonical JSON output: `00e2826377d2fcd7cc89a906c37030b11026c6d0bf3f053a8a8fac49823c937d`. This is development-only real **observed-cohort** output, not historical top movers across Binance.

Optional existing detector JSONL at its separate research worktree can be passed with `--setup-records`. At 2023-01-04T01:45:00+00:00, the radar reported four same-cutoff research candidates over BNB/BTC/ETH as separate setup evidence, with output JSON SHA-256 `5ee1160bc726e9cde48001177e8d97243b82bc13bbc055a87b7b398c8bf9889d`. No outcome was read. The underlying structural file remains development-only and its SHA-256 must be independently checked before use.

### Tests and limits

`/usr/bin/env -i PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -m unittest tests.unit.test_opportunity_radar_v1 -v`: nine offline tests pass. They cover deterministic rank/context, future candle exclusion, strict source hash, stale cutoff, gap/duplicate/invalid OHLC rejection, late out-of-order records after the cutoff, incomplete final bar, same-cutoff setup isolation and socket denial. The added late-record test failed before the bounded loader correction and passed afterward. The loader still emits no candle beyond the cutoff; it reads later CSV timestamps solely to reject out-of-order source records. The real six-row replay retained its prior output hash `00e2826377d2fcd7cc89a906c37030b11026c6d0bf3f053a8a8fac49823c937d`. A full-file source hash can change when future rows are appended; the cutoff-dependent *features* remain prefix invariant. No real acquisition-receipt timestamps or historical full-universe eligibility were established; the output is not independent confirmation. No fee/spread/slippage/fill analysis or Edge/profit claim exists.

Final status: `RADAR_RESEARCH_OPERATIONAL` for descriptive observed-cohort/development-only use; **market-wide historical eligibility and scientific Edge are unvalidated**. Real-time radar, production activation and any new collection are out of scope and not authorized.

## 2026-10-15 setup-record replay identity check

A red deterministic fixture showed the optional `--setup-records` path displayed the same `candidate_id` twice if a replay JSONL repeated a record, and changed event order when the input lines were reordered. The bounded research-only correction deduplicates byte-equivalent displayed events by candidate ID, sorts distinct events by ID, and rejects conflicting records with the same ID. All **10** offline radar tests pass. Replaying the existing six-symbol panel with the development-only detector file at `2023-01-04T01:45:00+00:00` retained its recorded canonical output SHA-256 `5ee1160bc726e9cde48001177e8d97243b82bc13bbc055a87b7b398c8bf9889d`. No outcome, broker, production strategy or frozen contract was changed.
