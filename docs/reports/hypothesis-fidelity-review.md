# Hypothesis Fidelity Review (HFR)

**Date:** 2026-06-12. **Scope:** the signal-starvation cluster of the 12 production
strategies (strategies that fired ~0 trades through their real `generate_signal()`
after the Direction-B rewire). **Mandate:** before classifying any strategy
NON_VIABLE / INSUFFICIENT_DATA, decompose it into **HYPOTHESIS CORE** /
**IMPLEMENTATION LAYER** / **ENGINEERING CONSTANTS** and classify each defect:

- **A** — hypothesis-preserving defect (fix authorized)
- **B** — engineering miscalibration / arbitrary constant suppressing the hypothesis (fix authorized)
- **C** — implementation bug (fix authorized)
- **D** — genuine hypothesis failure (NOT authorized to modify; classify + justify)

This is **fidelity restoration**, not parameter optimization. Thresholds are *not
automatically sacred* — they may be implementation artifacts that accidentally
suppress the hypothesis. The test applied to every constant: *is it theory-driven,
or arbitrary?* No value was chosen to maximize profit; values were chosen to make a
suppressed gate **reachable / scale-correct** and were grounded in the measured data
distribution or the strategy's own (dead) parameters.

Measurement tool: `research/profitability_diagnostics/signal_frequency_diagnostic.py`
(feeds 20 000 real BTC 1m bars to the real `generate_signal`, counts BUY/SELL/HOLD/None,
no execution). Sub-condition instrumentation done per strategy.

---

## Signal-frequency (BTC, 20 000 1m bars) — PRE vs POST HFR

| strategy | PRE (rewire) | POST HFR | classification of the binding defect(s) |
|---|---|---|---|
| trend_following | 0 | 534 | B (trend_extreme_threshold 0.99→0.999) |
| mean_reversion | 0 | 10 | C (range window included tested bars) + B (failed_expansion 3→1) |
| breakout / crypto_breakout | 0 | 13 | C (range recomputed each bar → latched-range state machine) + B (threshold 2%→0.1%) |
| vwap_reversal | 0 | 67 | C (slope unit bug) + C (24-bar "session") + B (2% deviation → σ-band) |
| liquidity | ~0 | 87 | resolved by base-feed / Signal-API fixes (no HFR change needed) |
| sweep_scalper | ~0 | 11 624 | resolved by base-feed / Signal-API fixes (no HFR change needed) |
| **scalping** | 0 | **0** | **B (volume-units) FIXED** + **D (tick-cost gate = hypothesis; correctly refuses)** |

After HFR, **11/12 strategies fire and are measurable.** Only **scalping** remains at
0 signals on 1m — and that is the hypothesis working as designed (see justification).

---

## vwap_reversal — full decomposition

**HYPOTHESIS CORE:** price reverts toward the session-anchored VWAP when significantly
deviated, while the market is in a mean-reversion (non-trending) regime.

**IMPLEMENTATION LAYER:** session VWAP computation + reset; trend-exhaustion regime
filter; deviation gate; rejection/failure-swing confirmation.

**ENGINEERING CONSTANTS:** `deviation_threshold`, `trend_exhaustion_threshold`,
`std_mult`, `lookback`, `session_reset_hour`.

Sub-condition instrumentation (19 941 bars) located three binding defects, none of
which is the hypothesis:

1. **`_assess_trend_exhaustion` slope unit bug — type C.** The regime filter compared
   `np.polyfit` slope (absolute **$/bar**, ~$5 for BTC) to a small *fractional*
   threshold (0.005). `abs(slope) ≤ 0.005` (the "flat trend" clause) was therefore
   unreachable → the mean-reversion regime fired **14 / 19 941 bars (0.07 %)**.
   *Fix:* normalize slope to a fractional per-bar change (scale-invariant). Result:
   regime now fires on essentially all flat-trend 1m bars (≈19 941), which is correct —
   1m rarely sustains a >0.5 %/bar trend over 50 bars.

2. **`_should_reset_session` simulated time — type C.** Sessions were anchored with
   `current_bar_index % 24`, i.e. a "session" was **24 bars (24 minutes on 1m)**. A
   24-bar VWAP hugs price, so the maximum deviation observed was ~0 and the deviation
   gate was unreachable. The code comment itself said *"In a real system, this would
   use actual timestamps."* *Fix:* anchor sessions to the bar's **real UTC timestamp**
   (day boundary at `session_reset_hour`); legacy `%24` retained only as a fallback
   when no timestamp is present.

3. **`deviation_threshold = 0.02` (2 %) — type B (arbitrary, structurally unreachable).**
   With a proper daily session VWAP, the **maximum** deviation ever observed on 1m BTC
   is **~1.15 %** (mean |dev| 0.02 %, 2σ ≈ 0.21 %). A 2 % gate can never trigger. The
   strategy *already declares* `std_mult = 2.0` and `lookback = 200` — the parameters
   of the canonical **VWAP ± std_mult·σ** reversion band — but they were **dead code**;
   the fixed 2 % placeholder shadowed them. *Fix:* wire the σ-band the `std_mult`
   parameter was meant for (self-calibrating across assets/timeframes), with a small
   absolute floor (`min_deviation_floor = 0.001`) so a collapsed-volatility session
   can't trigger on noise.

**Result:** 0 → **67 signals / 20 k** (12 BUY / 55 SELL). Hypothesis unchanged; three
implementation/calibration defects removed.

**Documented residual (type C, not yet fixed):** `_check_rejection_pattern`'s
`bullish_rejection` requires the latest close to be *above* VWAP, while the BUY gate
requires the close to be *below* VWAP (and symmetrically for SELL). The two halves of
the same entry condition contradict, so the named "rejection" confirmation path is
**dead** — only `failure_swings` can confirm. Fixing it (detect a reversal candle at
the *deviation extreme* rather than a VWAP recross) would increase frequency but
requires reinterpreting the rejection geometry and bar opens; deferred to avoid a
larger rewrite. It does not block firing (67 signals come via `failure_swings`).

---

## scalping — full decomposition (terminal: NON_VIABLE on 1m, justified)

**HYPOTHESIS CORE:** capture many small intrabar moves, **but only when the expected
move exceeds round-trip transaction costs** (fees + spread + slippage). The cost gate
is not an add-on — it *is* the scalping thesis.

**IMPLEMENTATION LAYER:** structural-viability check; market micro-conditions
(volatility / volume / spread); the tick-cost gate; MA-crossover + momentum + RSI
signal logic.

**ENGINEERING CONSTANTS:** `min_volume_threshold`, `min_spread_threshold`,
`required_tick_size_multiple`, `max_volatility_threshold`, `profit_target`, `stop_loss`.

Sub-condition instrumentation (19 986 bars) found the gates fire in this order, and the
**first** one short-circuited everything:

1. **`adequate_volume` — `min_volume_threshold = 100` — type B (units miscalibration).**
   The gate required average volume ≥ **100**, an *absolute* figure, but BTC 1m volume
   is ~**6/bar** (median 6.06, min 0.08, max 434). It failed **19 986 / 19 986 bars** and
   short-circuited *before the hypothesis (cost) gate ever ran*. This is not part of the
   scalping thesis — it is an arbitrary liquidity floor in the wrong units.
   *Fix:* make the liquidity gate **relative/scale-invariant** (recent volume hasn't
   collapsed vs its own baseline: `recent_vol ≥ min_volume_ratio · avg_volume`, ratio
   0.5). Result: micro-conditions now pass on **13 640 / 19 986 bars** (was 0) — the
   strategy reaches its real decision gate.

2. **Tick-cost gate (`_calculate_tick_size_impact`) — type D (HYPOTHESIS FAILURE; NOT
   modified).** It requires average move ≥ `min_spread_threshold · required_tick_size_
   multiple` = 0.0005 · 4 = **0.2 %**. This threshold is **theory-driven**: round-trip
   crypto taker fees (~0.04–0.1 %/side) + spread + slippage ≈ 0.15–0.2 %, so a scalp
   must move ≥ ~0.2 % merely to break even. The measured 1m move distribution is
   median **0.027 %**, p90 **0.066 %** — an order of magnitude below cost. The gate
   therefore refuses **every** 1m bar. This is the strategy **working exactly as
   designed**: it correctly declines trades whose expected move cannot beat costs.

**Why this is type D and not B:** the volume floor (B) was an arbitrary constant in the
wrong units, unrelated to the thesis — fixed. The cost gate (D) *is* the thesis, its
threshold is economically grounded (not arbitrary), and the refusal is driven by the
**real 1m return distribution**, not by a miscalibrated constant. Weakening it to force
trades would (a) redesign the hypothesis and (b) manufacture trades that lose to costs
by construction — the precise failure Phase-5 already identified (scalping is the most
cost-sensitive class). After the type-B fix, the strategy *reaches* its honest gate and
the gate says no.

### Written justification — scalping = NON_VIABLE on 1m
- Fidelity **verified**: implementation runs end-to-end; the prior 0-signal result was
  caused by a type-B units bug (now fixed) — micro-conditions pass on 68 % of bars.
- Defects **resolved**: the arbitrary volume floor is fixed; no remaining
  implementation defect suppresses the hypothesis.
- Failure is **realistic and hypothesis-intrinsic**: 1m moves (median 0.027 %) are an
  order of magnitude below the ~0.2 % round-trip cost the scalping thesis itself
  requires. The strategy cannot trade on 1m without violating its own (correct)
  economics.
- **Not modifiable:** the cost gate is the hypothesis; lowering it is forbidden
  (redesign + curve-fitting toward cost-losing trades).
- **Conditional path (not pursued here):** scalping could only become viable on a
  *different data regime* — higher timeframe / higher-volatility instrument where
  typical moves exceed ~0.2 % — which is a data/instrument decision, not an
  implementation fix. On the mandated 1m evaluation, the verdict is **NON_VIABLE,
  with the hypothesis intact.**

---

## Principle upheld
Every fix made a *suppressed gate reachable or scale-correct* (unit bugs, simulated
time, absolute-unit thresholds, dead σ-band parameters). No fix altered a hypothesis,
and no constant was tuned toward profitability. Where a gate refused for a
**hypothesis-valid, economically-grounded** reason (scalping's cost gate), it was left
intact and the strategy classified NON_VIABLE with justification — never papered over
by weakening the entry.
