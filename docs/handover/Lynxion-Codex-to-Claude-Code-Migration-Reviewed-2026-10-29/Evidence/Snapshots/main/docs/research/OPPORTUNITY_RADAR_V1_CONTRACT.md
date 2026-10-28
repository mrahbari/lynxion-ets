# Opportunity Radar V1 — frozen research-output contract

Status: research-only read-only observation, not Strategy/Fusion/ExecutionIntent. Version `OPPORTUNITY_RADAR_V1_RESEARCH`. No outcome labels, PnL, success probability, top-N trading rule, order, sizing or risk action.

## Input and cutoff

Input is an existing local Binance USD-M *reported* six-symbol M15 CSV panel plus its hash manifest. The historical universe is **not** known; all output is `OBSERVED_COHORT_RANKING_DEVELOPMENT_ONLY`, never an exchange-wide rank. `--cutoff` is an aware UTC decision instant. A bar opens at the CSV epoch and becomes available no earlier than open + 15 minutes. The loader validates UTC, strict contiguous 15-minute times, positive/consistent OHLCV, no duplicates and the whole-file manifest SHA-256. It stops before any bar whose close exceeds cutoff. Locally valid contiguous bars are `data_quality=VALID`, while source qualification remains separately `MANIFEST_HASH_MATCHED_DEVELOPMENT_ONLY_NO_RECEIPT` because source acquisition receipt times are absent; eligibility is `OBSERVED_IN_PANEL_TRADABILITY_UNKNOWN`, not point-in-time exchange tradability. No new download, capture or backfill.

## Fixed descriptive metrics

At cutoff T, use the last five **completed, contiguous** M15 closes for each symbol. `movement_pct_4_closed_m15 = 100 * (close_T / close_(T-4 bars) - 1)`. Direction is `UPWARD_MOVEMENT`, `DOWNWARD_MOVEMENT` or `NO_CLEAR_DIRECTION` by sign; this is a price observation, not LONG/SHORT. Magnitude is absolute percent; rank descending by magnitude with symbol-ascending tie break. No confidence or composite score. A missing five-bar sequence is `INCOMPLETE`; last close older than 15 minutes is `STALE`; such rows have no rank. Metric window and stale limit are mechanically simple research defaults, not optimized thresholds or production policy.

## Separate context and setup

Repository `StrategyConfig.DESIGN_TIMEFRAMES` preserves `mtf_trend:15m`, and MTF_TREND declares 5m/15m/1h short/medium/long. V1's independent context field uses **completed H1 candles only**, formed from exactly four contiguous M15 bars each. It mirrors the pure 30-H1-close normalized regression slope/strength formula in `TrendMTFWatcher.calculate_trend`, via a stdlib research adapter because importing the live watcher pulls shared runtime/NumPy state into a credential-free CLI. It records last confirmed H1 close and availability time. This is not a production MTF decision and does not change automatic timeframe routing. If fewer than 30 complete H1 closes exist, context is `INCOMPLETE`.

Optional `--setup-records` reads the pre-existing Structural Pullback Failure V1 research JSONL. Only a candidate with the same symbol, exact decision/confirmation instant equal to T, a matching dataset hash and nonempty candidate/contract identity is shown. The detector is **not** reimplemented or activated. Setup is a separate field; missing/unmatched data are `SETUP_UNAVAILABLE`. The existing detector's frozen contract is not changed.

## Reproducibility and limits

JSON output uses sorted keys and compact separators. Each row includes source hash, cutoff/observation time, venue/instrument *reported* identity, eligibility unknown, movement, H1 context, setup and data-quality status. No broker/Fusion/Strategy/Risk import or order path. Local C06 source has a matching per-file manifest but lacks independently captured exchange response/receipt and complete historical membership; prior C06 outcome work makes this development-only. The rank cannot support a market-wide or independent Edge claim. No future outcomes are opened by this radar.
