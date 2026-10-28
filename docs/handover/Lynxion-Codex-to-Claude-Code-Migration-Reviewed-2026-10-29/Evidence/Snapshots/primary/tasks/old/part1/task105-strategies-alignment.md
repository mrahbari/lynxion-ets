You must comply with all rules and requirements defined in:
./tasks/task0-force-to-cover.md

CRITICAL CONSTRAINTS:
• Prefer modifying and extending EXISTING code files.
• Creating new files is allowed ONLY if existing files cannot be safely extended.
• Any new file must be explicitly justified.
• No architectural rewrites without necessity.


## 🔴 IMPORTANT ALIGNMENT (READ ONCE)

These prompts are **NOT asking to “make strategies profitable”**.
They are asking to:

* make each strategy **well-defined**
* enforce **clear market hypothesis**
* remove **implicit noise behavior**
* make strategies **testable, falsifiable, and Hyperopt-ready**

Each prompt:

* focuses on **conceptual correctness**
* allows **small, surgical changes**
* avoids new files unless absolutely necessary
* respects your existing architecture & ExecutionIntent flow

You should run them **in order**, and **finish one strategy before moving to the next**.

---

# ✅ STRATEGY REPAIR PROMPTS (ORDERED)

---

## **PROMPT 1 — Breakout Strategy (FOUNDATIONAL)**

> **Context**
>
> The current Breakout strategy relies on indicator-based resistance detection and price crossing logic.
> Backtests show excessive false breakouts, late entries, and poor R:R.
>
> ---
>
> **Objective**
>
> Refactor the Breakout strategy into a **structure-based breakout hypothesis**, without introducing new indicators or files.
>
> ---
>
> **Required Changes**
>
> 1. Explicitly define:
>
>    * What constitutes a *range* (time + price compression)
>    * When the market is *eligible* for breakout trading
> 2. Separate logic into:
>
>    * **Setup**: market compression / consolidation
>    * **Trigger**: breakout validation candle (close, not wick)
>    * **Entry**: first pullback or acceptance, not the breakout bar
> 3. Add **invalid breakout detection**:
>
>    * wick-only breaks
>    * immediate rejection
> 4. Ensure:
>
>    * at least one trade per range
>    * no re-entry unless a new structure forms
>
> ---
>
> **Constraints**
>
> * Do NOT add new indicators
> * Do NOT add new files
> * Extend existing logic only
> * ExecutionIntent interface must remain unchanged
>
> ---
>
> **Expected Outcome**
>
> * Higher-quality trades
> * Clear separation between noise and valid breakouts
> * Trade count reduction without hard limits

---

## **PROMPT 2 — Liquidity Strategy**

> **Context**
>
> The Liquidity strategy currently reacts to price movements labeled as liquidity events without confirming actual liquidity sweeps.
>
> ---
>
> **Objective**
>
> Convert the Liquidity strategy into a **true stop-sweep reaction model**.
>
> ---
>
> **Required Changes**
>
> 1. Redefine liquidity as:
>
>    * prior swing highs/lows
>    * equal highs/lows
> 2. Require:
>
>    * sweep beyond the level
>    * **close back inside the range**
> 3. Entry must:
>
>    * occur *after* sweep confirmation
>    * never on the sweep candle itself
> 4. Add:
>
>    * session awareness (Asia/London/NY)
>    * time-based invalidation of unused sweeps
>
> ---
>
> **Constraints**
>
> * No new indicators
> * No volume proxies
> * No new files
>
> ---
>
> **Expected Outcome**
>
> * Drastic reduction in false liquidity signals
> * Trades aligned with real stop-hunt behavior

---

## **PROMPT 3 — VWAP Reversal Strategy**

> **Context**
>
> The VWAP Reversal strategy currently assumes mean reversion without session anchoring or trend context.
>
> ---
>
> **Objective**
>
> Restrict VWAP Reversal trades to **valid mean-reversion regimes only**.
>
> ---
>
> **Required Changes**
>
> 1. Enforce session anchoring:
>
>    * VWAP must reset per session
> 2. Only allow reversal trades when:
>
>    * price deviates significantly from VWAP
>    * higher-timeframe trend is flat or exhausted
> 3. Block trades:
>
>    * during strong trend continuation
>    * immediately after VWAP breaks
> 4. Require:
>
>    * rejection candle or failure pattern near VWAP
>
> ---
>
> **Constraints**
>
> * Use existing VWAP logic only
> * No trend indicators added
> * Minimal logic extension
>
> ---
>
> **Expected Outcome**
>
> * Higher quality trades
> * Better alignment with real VWAP behavior

---

## **PROMPT 4 — Mean Reversion Strategy**

> **Context**
>
> The Mean Reversion strategy currently trades reversals without volatility contraction or regime filtering.
>
> ---
>
> **Objective**
>
> Ensure Mean Reversion trades only occur in **range-bound, low-momentum markets**.
>
> ---
>
> **Required Changes**
>
> 1. Explicitly block trades when:
>
>    * volatility is expanding
>    * directional momentum is increasing
> 2. Require:
>
>    * range definition
>    * multiple failed expansion attempts
> 3. Entry must:
>
>    * occur near range extremes
>    * include rejection confirmation
>
> ---
>
> **Constraints**
>
> * Reuse existing volatility logic
> * No new filters added globally
>
> ---
>
> **Expected Outcome**
>
> * Mean reversion behaves as intended
> * No trend-fighting behavior

---

## **PROMPT 5 — Trend Following Strategy**

> **Context**
>
> The Trend Following strategy currently reacts to short-term slope changes, resulting in noise trades.
>
> ---
>
> **Objective**
>
> Restrict Trend Following to **established directional regimes only**.
>
> ---
>
> **Required Changes**
>
> 1. Require:
>
>    * sustained directional movement
>    * higher-high / higher-low (or inverse) structure
> 2. Entry must:
>
>    * occur on pullbacks
>    * never at trend extremes
> 3. Block:
>
>    * choppy or overlapping price action
>
> ---
>
> **Constraints**
>
> * No new timeframes
> * No new indicators
>
> ---
>
> **Expected Outcome**
>
> * Reduced whipsaw losses

---

## **PROMPT 6 — Momentum Strategy**

> **Context**
>
> The Momentum strategy currently confuses volatility spikes with sustainable momentum.
>
> ---
>
> **Objective**
>
> Ensure momentum trades only occur when **continuation probability is high**.
>
> ---
>
> **Required Changes**
>
> 1. Momentum must:
>
>    * persist across multiple candles
>    * show follow-through, not single spikes
> 2. Entry must:
>
>    * occur after momentum confirmation
>    * avoid exhaustion candles
>
> ---
>
> **Expected Outcome**
>
> * Momentum trades reflect continuation, not noise

---

## **PROMPT 7 — Scalping Strategy (OPTIONAL / LAST)**

> **Context**
>
> The Scalping strategy shows extreme trade counts and poor expectancy.
>
> ---
>
> **Objective**
>
> Decide whether this strategy is **structurally viable**.
>
> ---
>
> **Required Changes**
>
> 1. Explicitly define:
>
>    * market micro-conditions required
>    * maximum acceptable spread / volatility
> 2. If these cannot be enforced reliably:
>
>    * the strategy must self-disable
>
> ---
>
> **Expected Outcome**
>
> * Either a disciplined scalping model
> * Or a justified deprecation

---

## 🔚 FINAL GUIDANCE

* Do **NOT** run Hyperopt until:

  * at least **4 strategies** show sane behavior
  * trade counts are explainable
  * drawdowns are bounded


