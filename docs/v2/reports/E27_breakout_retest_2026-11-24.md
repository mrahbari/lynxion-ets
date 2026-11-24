# E27 — Breakout-Retest (operator idea) (2026-11-24)

Pre-registered and committed before the run (research/v2/experiments/e27_breakout_retest.py). Wait for a
20-bar breakout aligned with the 4h EMA21/55 trend, then enter only on a held retest of the broken level with a
rejection close (operator's chart method: "touch alone is not entry"). 1h, E9 engine / universe / costs.

| window | n | win | PF | net R | net bp | symbols + | long share | R long / short |
|---|---|---|---|---|---|---|---|---|
| DEV | 913 | 0.371 | 0.77 | -0.147 | -23.5 | 1/10 | 0.29 | -0.098 / -0.167 |
| HOLDOUT | 427 | 0.436 | 1.06 | +0.026 | +5.1 | 4/10 | 0.58 | +0.076 / -0.043 |

Baseline Breakout -0.137 / -0.124. **NO EDGE, not adopted** (worse on DEV). Same pattern as E26: positive in
the trending HOLDOUT, negative in DEV.
**Measurement caveat found here:** the platform-wide SL/TP sanitiser clamped the designed retest stops — median
stop exactly 1.2 % (the clamp floor) while the target stayed at entry + 2 R of the designed stop, so the
realised reward:risk was far below the design. E28 re-tests all six setups with their designed levels.
