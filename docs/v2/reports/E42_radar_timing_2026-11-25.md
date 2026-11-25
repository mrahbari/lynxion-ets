# E42 — Radar timing: can it signal earlier and better? (2026-11-25)

**Brief (operator).** Radar gets the direction right but enters late. Turn it from "rank past trend strength" into "detect a change of behaviour", keep trend confirmation, and accept a change only with evidence.

**Setup.**
- Script: `research/v2/experiments/e42_radar_replay.py`, pre-registered in commit 9ff5d41.
- Data: Binance 1h lake (delisted names included), resampled to 4h and 1d.
- 8,377 Radar snapshots (every 4h), 2023-01..2026-10, 640 symbols with a 30-day median daily volume of at least $10M.
- Each coin entering a list is one event (116,818 events). Each event is traded with the live Radar levels:
  - limit entry at the 1h pullback, which must fill within 24h;
  - stop beyond the 1h swing; TP1 at 1.5R;
  - stop is checked before TP1 when both fall in the same bar; exit at 72h otherwise;
  - net of 2 × (5 bp fee + 2 bp slippage).
- Exploratory: momentum was studied on 2020–24 (E2).
- Raw data: `E42_radar_replay.csv`; events in `data/research_cache/E42_radar_events.csv`.

## Variants (fixed definitions)

| Variant | Change |
|---|---|
| BASE | Live Radar: 28-day momentum + efficiency + 4h EMA, all three must agree |
| A | 28-day momentum only as context; direction from 7-day momentum + 4h; quality includes acceleration; no all-three gate |
| B | A + a fresh trigger is required: 4h range breakout with volume, or compression → expansion |
| C | BASE with extended coins (more than 2 ATR from the 4h EMA20) removed |

## Results

| | BASE | A | B | C |
|---|---|---|---|---|
| Filled trades | 20,076 | 28,881 | 17,297 | 29,472 |
| Mean net R per trade | −0.056 | −0.048 | **−0.031** | −0.053 |
| 2023–24 / 2025–26 | −0.063 / −0.050 | −0.061 / −0.034 | −0.044 / −0.018 | −0.062 / −0.044 |
| Long / short R | −0.065 / −0.048 | −0.061 / −0.035 | −0.048 / **−0.005** | −0.058 / −0.048 |
| TP1 before SL | 40.7 % | 41.0 % | 41.3 % | 40.8 % |
| Move already made (median, ATR, 72h) | **1.73** | 2.19 | 3.07 | 1.98 |
| t vs BASE (Holm p) | — | 0.09 (0.93) | 0.62 (0.81) | −0.10 (0.93) |
| **PASS** | — | no | no | no |

**No variant passes.** None is significantly better than BASE, and none signals earlier.

## What we learned

1. **The lateness is not caused by the 28-day momentum or the all-three gate.**
   - BASE already enters after the smallest prior move: median 1.73 ATR over 72h.
   - Removing the 28-day gate (A) entered later (2.19).
   - Trigger-based entry (B) entered latest of all (3.07): a breakout or expansion bar *is* the move.
2. **"Late" entries are not worse trades on average.**
   - BASE picks that had already moved more than 3 ATR averaged −0.032 R.
   - The other BASE picks averaged −0.065 R.
   - Removing extended coins (C) did not help.
3. **The trigger version (B) is the least bad, mostly on shorts** (−0.005 R). It is not significant (t 0.62) and it has the largest drawdowns (MAE 2.57 ATR). This is not evidence.
4. **Overall, a trend-ranking list traded mechanically with these levels loses about 0.03–0.06 R per trade after costs.**
   - It wins TP1 about 41 % of the time, against 40 % needed to break even at 1.5R before costs.
   - This matches E2 and E36/E37: past trend information does not predict the next 72 hours on single coins.

## Decision

- **Radar stays unchanged.** Per the pre-registration there is no combined variant and no shadow run.
- **Radar remains an information tool.** Its direction and market view are descriptive. No mechanical rule here — earlier, later or filtered — gave a trading edge.
- **Not started (each would need its own pre-registration):** shorts-only trigger entries (B short −0.005 R); timing work that uses non-price information.

## Limits

- BingX listing history is not available. The universe is Binance-liquid coins.
- The 15m stop buffer is approximated from 1h data (0.25 × ATR1h). Funding is not included over the 72h hold (small).
- Manual trading (discretionary entries, partial exits, skipped trades) can differ from this mechanical replay.

## Prospective stage for the B-short hint (pre-registered 2026-11-25, before any data is collected)

**Why.** Variant B was near break-even on shorts in the replay (−0.005 R). That was found on data already
searched, so it can only be tested on new data.

**Logging (shadow only).**
- Every live Radar run (4-hourly) also computes the B short list. Definitions are exactly as in this report:
  - 7-day momentum (28-day volatility), signed efficiency (20d), short-term 4h, acceleration;
  - a fresh 4h breakout-with-volume or compression → expansion trigger, in the last 2 bars;
  - lowest 7 by mean rank.
- Universe: the live Radar universe (Binance ∩ BingX, $10M). Levels: the live Radar levels.
- Every qualifying coin is appended to `data/v2_live/radar_shadow_b_short.jsonl`, with a flag for a coin newly entering the list.
- It never reaches Telegram, ranking, orders or the live Radar.

**Evaluation (fixed now).**
- An event is a coin entering the B-short list.
- The outcome uses the E42 rules on Binance 1h data afterwards:
  - limit fill within 24h; SL is checked first;
  - TP1 at 1.5R; exit at 72h;
  - minus 2 × (5 bp + 2 bp).
- The comparison set is the live Radar's own short new entries over the same period, evaluated the same way (this is also R23-a).

**Decision.**
- Taken at the first of: 150 filled B-short events, or 2027-02-28.
- **PASS:** mean net R > 0 with day-clustered t ≥ 2.0, AND above the live Radar shorts' mean net R.
- **FAIL:** otherwise. Logging stops and the result is recorded.
- Interim looks report counts only. No early decision, no definition changes.
