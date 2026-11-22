# E7 — Exit-policy replay on real platform entries (2026-11-22)

Script: `research/v2/experiments/e7_exit_policy_replay.py` · data: `E7_exit_policy_replay_{summary,trades}.csv`

## Method
- 697 real platform entries from `data/trade_journal.csv` (Aug–Nov 2026, de-duplicated per symbol within 10 min).
- Path: Binance USDT-M 1m klines, entry at next-bar open, 24h time exit.
- R = 2% of entry (platform sanitize default). SL checked before TP inside a bar; a stop moved
  because of a bar's high/low is active only from the next bar (no lookahead).
- Costs: 0.05% taker per side + 0.02% slippage on stop exits.

## Results (net, R units per trade)
| Policy | mean R | PF | win rate | paired vs current (SE) |
|---|---|---|---|---|
| static SL 1R / TP 3R | +0.093 | 1.16 | 38% | +0.111 (0.052) |
| BE 1.5R, trail 1.5R after 2R, TP 4R | +0.071 | 1.14 | 45% | +0.089 (0.048) |
| BE 1.5R, trail 1.5R after 2R, TP 2.75R | +0.044 | 1.09 | 45% | +0.062 (0.044) |
| BE 1.5R, trail 1.5R after 2R, TP 1.75R | +0.021 | 1.04 | 45% | +0.039 (0.038) |
| BE 1R, trail 1R after 1.5R, TP 3R | +0.021 | 1.05 | 53% | +0.039 (0.038) |
| BE 0.5R, trail 0.75R after 1R, TP 3R | −0.007 | 0.98 | 66% | +0.011 (0.025) |
| **current APM** (BE +0.7%, 0.5% trail after +1%) | **−0.018** | **0.93** | **74%** | — |

## Conclusions
1. The legacy manager is the worst policy: a 74% win rate made of tiny wins, while losers run to
   the full stop. Every standard R-based policy beats it; the looser the management, the better.
2. No exit policy makes these entries profitable in the second half of the sample (all ≈ −0.1R).
   Exits cannot create an edge; the entries had none — consistent with the stale shared
   strategy-buffer P0 fixed in `1f3028a` (entries were priced from another symbol's candles).
3. Adopted default (`APM_STOP_MODE=r`): breakeven +0.15% at 1.5R, trail 1.5R behind the best
   price after 2R, ratchet-only, min step 0.25R, at most one amendment per 60s. All knobs are
   env-tunable (`APM_*`); `APM_STOP_MODE=legacy` restores the old behaviour.
4. The TP is still set at entry by the sanitize defaults (≤5.5%, usually 1.75R). The replay favours
   wider TP (3–4R); that change belongs to the entry route and is deferred until post-fix live
   trades show whether entries now carry an edge.
