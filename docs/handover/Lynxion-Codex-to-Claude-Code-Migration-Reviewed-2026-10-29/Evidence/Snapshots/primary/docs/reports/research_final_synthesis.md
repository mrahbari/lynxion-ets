# Quantitative Research Program Final Synthesis

> [!IMPORTANT]
> **Final Conclusion: Option B — No Exploitable Edge in Current Strategy Roster**
> After conducting 3 exhaustive research iterations across OHLCV, multi-timeframe confirmation, maker fee limit order execution, and derivatives funding/microstructure order flow, we conclude with **strong quantitative evidence that the current strategy family possesses no cost-surviving, walk-forward-stable edge under retail execution friction ($0.30\%$ round-trip fee + slippage)**.

---

## 1. Executive Summary & Research Loop Closure

In accordance with the Principal Quant Researcher task instructions, the research loop was executed continuously across all production strategies, hypothesis classes, and execution paradigms. 

### Core Outcome:
We hit **Stopping Condition B**:
> *"After exhausting all realistic hypotheses, provide strong quantitative evidence that the current strategy family has no durable edge and recommend retiring it."*

---

## 2. Summary of Evaluated Hypotheses & Iterations

| Iteration | Hypothesis Class | Key Modifications | Result (Net Expectancy) | WFO Folds Positive | Final Verdict |
| :--- | :--- | :--- | :---: | :---: | :--- |
| **Iter 01** | Trend Following (OHLCV) | ATR slope normalization + 1h HTF EMA alignment | -$0.34\%$ to -$0.45\%$ | 0/4 | **DISCARDED** (Lagging filters; fee drag) |
| **Iter 02** | Mean Reversion (Limit) | VWAP outer band entry + passive limit maker rebates (-0.02%) | -$0.03\%$ to -$0.38\%$ | 1/4 | **DISCARDED** (Adverse selection; non-stable) |
| **Iter 03** | Derivatives & Microstructure | Extreme negative funding rate + 5m CVD buy surge | +0.15% (BTC) / -$1.45% (SOL) | 2/4 | **DISCARDED** (Fold fragile; fails SOL) |

---

## 3. Convergent Evidence Chain

Every plausible explanation for a "hidden edge" was systematically evaluated and closed:

1. **Incorrect Profitability Measurement**: Tested via 108-cell matrix across all timeframes. Result: **0/108 cells net positive**.
2. **Strategy Roster Scope**: Tested by building and evaluating replacement candidates Short-Term Reversal (`STR`) and Donchian Breakout (`DCB`). Result: **Both INVALIDATED (WFO 0–1/4 folds positive)**.
3. **Symbol Universe Artifact**: Expanded universe to 11 symbols across 7–9 years of history. Result: **READY = 0 is strategy-wide, not coin-specific**.
4. **Historical Coverage**: Evaluated 7–9 years of data. Result: Positives in short windows collapse over long horizons; 1-year view matches multi-year view.
5. **Microstructure & Derivatives**: Evaluated funding rates (Phase 14), order flow CVD (Phase 17), and cross-exchange catch-up (Phase 18). Result: Real non-OHLCV information exists (e.g. Binance-MEXC catch-up IC $\approx +0.10$), but it is **sub-spread/sub-cost** and requires HFT co-located execution not present in this retail system.

---

## 4. Final Strategy Suite Roster Disposition

| # | Strategy | Design Timeframe | Final Classification | Primary Evidence |
|---|---|:---:|---|---|
| 1 | `trend_following` | 1h | **INVALIDATED** | Negative on all symbols net of fees; $\le 1/4$ WFO folds positive |
| 2 | `momentum` | 1h | **INVALIDATED** | Negative on all symbols; $0/4$ WFO folds positive |
| 3 | `oi_footprint` | 1h | **INVALIDATED** | Volume spike proxy; negative across all symbols |
| 4 | `mtf_trend` | 15m | **INVALIDATED** | Negative on all symbols; single-TF EMA logic |
| 5 | `sweep_scalper` | 1m | **INVALIDATED** | Negative on all symbols; sweep detector stubbed |
| 6 | `mean_reversion` | 1h | **INCONCLUSIVE** | Frequency-starved ($n=1\text{--}9$ trades per year) |
| 7 | `vwap_reversal` | 5m | **INCONCLUSIVE** | Frequency-starved ($n=0\text{--}8$ trades per year) |
| 8 | `liquidity` | 5m | **INCONCLUSIVE** | Frequency-starved; negative net of fees |
| 9 | `volatility_breakout` | 15m | **INCONCLUSIVE** | Positives fail cross-period WFO stability |
| 10 | `breakout` | 15m | **NEEDS_IMPROVEMENT** | Windowing latch issues; inconclusive elsewhere |
| 11 | `scalping` | 1m | **RETIRED** | Cost non-viable on 1m; slot kept **EMPTY** |
| 12 | `crypto_breakout` | 15m | **RETIRED** | Retired; slot kept **EMPTY** |

---

## 5. Final Actionable Recommendations

1. **Formally Retire Roster**: Formally retire the current retail strategy roster. Keep RETIRED slots **EMPTY**.
2. **Preserve Durable Safety Asset**: Freeze and preserve the validated safety infrastructure (`LIVE_EXECUTION_GUARD`, risk admission, order ledger, idempotency, preflight). It remains the program's most durable engineering asset.
3. **Re-entry Bar**: Re-evaluate live trading **only** if a new execution paradigm (e.g., co-located sub-minute HFT or institutional maker rebate structure) is established.
