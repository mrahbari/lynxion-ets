# R31 — Prospective calendar shadow: short large insider unlocks with a hard stop (pre-registered 2026-11-26)

**Why.** E47 found that about 65 % of unlock shorts win (median +5–6 % per event), but rare squeezes make the mean about
zero. A hard stop may cut that tail. Both historical windows have now been read, so the stop rule can only be judged on
future events. Unlock dates are public weeks in advance, which makes a clean forward test possible.

**Fixed rules (decided before any shadow data).**

- **Events.** Same definition as E47:
  - DefiLlama emissions cliff unlocks mapped to Binance USDT-M perps;
  - insider allocation ≥ 1 % of circulating supply;
  - 30-day median volume ≥ $5M at entry;
  - one event per token per 44 days.
  - Schedules are refreshed weekly. The schedule used is the one known at entry.
- **Entry.** Short at the Binance daily close of T−30. Hedge: long 50 % BTC + 50 % ETH (perp), same notional.
- **Stop (chosen a priori, not fitted).**
  - Exit when the token's daily high reaches entry × 1.20, at the stop price.
  - The 20 % level is a round number below the 5 % tail seen in E47 (−49 %), so the tail is cut but ordinary noise is not.
  - It was not optimised.
- **Exit otherwise.** Daily close of T+14.
- **Net per event.**
  - −token return + hedge return;
  - minus 4 × (5 bp fee + 2 bp slippage);
  - plus funding received on the token short, minus funding paid on the hedge longs (real Binance funding).
- **Logging.**
  - `data/v2_live/unlock_shadow.jsonl`: one line per opened shadow event, with the schedule snapshot fields.
  - Outcomes are computed only by `research/v2/experiments/r31_unlock_shadow_eval.py`.
- **No trading, no Telegram, no effect on any live sleeve.**

**Decision.**
- Taken at 40 closed events or 2027-06-30, whichever comes first.
- **PASS:** mean net ≥ +2 % per event, t ≥ 2 (events clustered by calendar week), ≥ 55 % positive.
  A PASS goes to the operator as a candidate live strategy.
- **FAIL:** record and close.
- No interim decisions; interim reports show counts only.
