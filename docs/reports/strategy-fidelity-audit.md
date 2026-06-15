# Strategy Fidelity Audit (Phase A)

**Date:** 2026-06-12. Verifies whether each of the 12 production strategies
faithfully implements its intended hypothesis. Fidelity verification only — no
optimization, tuning, or redesign. Evidence is `file:line`.

## Central finding — a dual signal-path divergence

There are **two separate signal implementations per strategy**, and the one that is
**evaluated/traded is not the one carrying the intended hypothesis**:

1. **Rich adapter logic** — `infrastructure/strategies/adapters/<name>_strategy_adapter.py`,
   method `generate_signal()`. This is each strategy's *intended* hypothesis
   (structure analysis, regime checks, etc.). **5 of these are broken** — they call
   `self.calculate_ema/rsi/atr`, which are **not defined** in `BaseStrategyAdapter`
   (`infrastructure/strategies/strategy_adapters.py:20`); only `mtf_trend` defines a
   local `calculate_ema` (`mtf_trend_strategy_adapter.py:131`). Calling them →
   `AttributeError`.
2. **Simple raw-signal functions** — `infrastructure/backtest/strategy_provider.py:142+`
   (`trend_following_strategy`, `mean_reversion_strategy`, …). These read
   *precomputed indicator columns* (`row.get('rsi')`, `sma_20`, `bb_upper`, `adx`).
   The Phase-5 backtest path (`load_sample_strategy(name)`) builds a `FusedSignal`
   from **these simple functions** (`strategy_provider.py:60,79`) and passes it to
   `adapter.evaluate_fused_signal()` for discipline + risk + `ExecutionIntent`.

**Consequence:** in the evaluated path the rich `generate_signal()` is **never
called** — so the broken methods don't crash the backtest, but equally the
strategies' *real hypotheses are not what was measured in Phase 5*. The evaluated
signal is a simplified indicator function; the intended hypothesis sits dormant (and
broken for 5) in the adapters. **This divergence is the single largest fidelity gap.**

## Cross-cutting defects (affect most/all)
- **Missing indicator methods** in `BaseStrategyAdapter` (`calculate_ema/rsi/atr`) →
  breaks `generate_signal` for trend_following, mean_reversion, scalping, oi_footprint.
- **Placeholder SL/TP = 0** emitted by the base adapter (`strategy_adapters.py:113-121`),
  set downstream — no strategy emits its own structure-aware stop/target (Phase-5 B7).
- **Simulated session time** via bar-index modulo (`liquidity:173`, `vwap_reversal:47`)
  — works bar-by-bar in backtest, not production-safe.
- **Proxy/stub data:** `oi_footprint` uses volume×1.5 as an open-interest proxy (no real
  OI); `sweep_scalper.detect_sweep()` is a stub returning 0 (unused); `mtf_trend` is
  single-timeframe with 3 EMA periods, not true MTF (`compute_trend()` returns 0, unused).

## Per-strategy classification (production-adapter fidelity)

| strategy | intended hypothesis | implementation reality | classify |
|---|---|---|---|
| trend_following | structured trend + pullback | `generate_signal` calls undefined `calculate_ema` → crashes | **BROKEN** |
| mean_reversion | range reversion + rejection | calls undefined `calculate_rsi` → crashes | **BROKEN** |
| scalping | micro-condition scalping | calls undefined `calculate_ema`/`calculate_rsi`; a market-condition flag hardcoded True | **BROKEN** |
| oi_footprint | OI/volume footprint | calls undefined `calculate_rsi`/`calculate_atr`; OI = volume×1.5 proxy (no real OI) | **BROKEN** |
| volatility_breakout | ATR breakout | no `generate_signal`; only a confidence/regex-regime filter — no signal logic | **BROKEN** |
| mtf_trend | multi-timeframe alignment | functional but NOT true MTF (3 EMA periods on one timeframe); dead `compute_trend`/weights | **PARTIAL** |
| sweep_scalper | liquidity-sweep scalping in killzones | `detect_sweep` stub unused; killzone config unused; oversimplified range-ratio logic | **PARTIAL** |
| momentum | continuation w/ persistence + exhaustion | self-contained, functional, faithful on available data | **PASS** |
| breakout | structure breakout + rejection | functional; `evaluate_fused_signal` override carries real logic; minor dead fields | **PASS** |
| crypto_breakout | (alias of breakout) | aliased to `BreakoutStrategyAdapter` (`strategy_provider.py:48`) | **PASS** (alias) |
| liquidity | swing-based stop-sweep reaction | real swing + sweep detection from price action | **PASS** |
| vwap_reversal | session-VWAP mean-reversion | full VWAP + regression + regime gating, functional | **PASS** |

**Tally: PASS 5 · PARTIAL 2 · BROKEN 5.**

## Update (Phase-B verification): `generate_signal` is more deeply unwired
The indicator-method fix (#1 below) is **done and verified** — after it, the
`AttributeError` moves from `calculate_ema` to **`data_buffer`**. That is, the
adapters' `generate_signal(self, symbol: Symbol)` (a) takes a **Symbol**, not a bar,
(b) reads **`self.data_buffer`** which is **never initialized in the adapters and
never populated by any active code path**. So `generate_signal` is effectively **dead/
unrunnable** in the current system — confirming the strategies execute *only* via the
raw-signal functions + `evaluate_fused_signal`. Fully restoring `generate_signal`
fidelity therefore requires building a data_buffer feed + a symbol-based call path —
i.e. the architectural rewire below, not a one-line fix.

## Phase-B remediation targets (no optimization — restore intended behavior)
1. **Implement `calculate_ema/rsi/atr` in `BaseStrategyAdapter`** → removes the
   latent `AttributeError`. **DONE + verified** (safe, additive). Necessary but NOT
   sufficient (see data_buffer wiring above).
2. **volatility_breakout** — implement a real ATR-breakout `generate_signal`. [restore]
3. **Dead/disabled logic** — breakout `_check_new_structure_needed` always-True;
   sweep_scalper unused `killzone`/stub `detect_sweep`; mtf_trend unused `weighting`. [clean]
4. **Proxy honesty** — oi_footprint OI proxy / sweep_scalper sweep-from-price: document as
   OHLCV-proxy (cannot be true without L2/OI data — a data-dependency limit, not a code bug).

## ⚠️ Architectural decision required before Phase C (materially different directions)
Fixing `generate_signal` (target #1–2) restores **production** fidelity, but the
**Phase-5 evaluation path does not call `generate_signal`** — it uses the simple
raw-signal functions. So those fixes would **not** appear in a PRE/POST matrix unless
the evaluation is **rewired to evaluate the adapters' `generate_signal`** (the real
hypotheses) instead of the simple raw functions. That is a material change to the
*validated* evaluation framework, with two defensible directions:
- **(a)** Keep the eval on the raw-signal layer; remediate that layer + SL/TP; treat
  `generate_signal` fixes as production-only. Phase-C measures the current eval semantics.
- **(b)** Rewire the backtest to drive each strategy via its (now-fixed) `generate_signal`,
  so Phase-C measures the intended hypotheses end-to-end.

These give materially different Phase-C/D results and system semantics → **flagged for
direction before rewiring the validated eval framework.** Phase-B target #1 (implement
the missing indicator methods) is safe and proceeds regardless.
