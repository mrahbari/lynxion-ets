# LYNXION ETS — STRATEGY STRICTNESS AUDIT & ADVISORY REPORT

**Role**: Principal Quant Researcher + Senior Algorithmic Trading Engineer  
**Mode**: **ADVISORY & FORENSIC AUDIT ONLY — ZERO CODE MODIFICATION**  
**Canonical Dataset**: Trades 601–681 (Modern Controlled Regime, N=81 Trades)  

---

## 1. EXECUTIVE VERDICT & STRATEGY ADVISORY

### **Would Making Strategies Stricter Improve Profitability?**
**Yes, BUT ONLY if strictness is applied selectively to low-confidence entries and exit decisions, NOT via blanket entry restrictions.**

1. **Empirical Fact — Current Controlled System Is Already Profitable**:
   - Under $1,000 position exposure caps and active symbol cooldown, Trades 601–681 generated **`+$67.88 VST`** net profit with a **`3.40 Profit Factor`** (Expectancy **`+$0.84 / trade`**).
   - SHORT trades generated **`+$77.36 VST`** with a **`13.68 Profit Factor`**.
2. **The Danger of Blanket Entry Tightening**:
   - Arbitrarily raising entry indicator thresholds across the board will drastically reduce trade frequency and risks filtering out highly profitable SHORT trends.
3. **The True Leverage Point — Selective Strictness**:
   - **Confidence Gating**: Raising `min_confidence` from `0.50` to `0.60–0.65` eliminates low-conviction noise trades.
   - **Exit Management Strictness**: Applying a minimum profit threshold on discretionary `MARKET` exits prevents premature truncation of winning trades.

---

## 2. COMPREHENSIVE AUDIT: CURRENT VS RECOMMENDED STRICTNESS SETTINGS

Below is the complete audit of all 10 registered strategies, detailing their **Current Source Parameters**, **Observed Behavior**, and **Recommended Strictness Parameters**:

| Strategy Name | Current Conditions & Parameters | Current Behavior | Recommended Strictness Parameters | Expected Impact |
| :--- | :--- | :--- | :--- | :--- |
| **`trend_following`** | • EMA 20 / Lookback 50<br>• Trend Thresh: `0.01`<br>• Min Conf: `0.50`<br>• SL/TP: `1.5x` / `2.0x` ATR | Generates most active signals; high volume. | • Min Conf: **`0.60`**<br>• Trend Thresh: **`0.015`**<br>• SL/TP: **`1.5x` / `2.5x`** | Filters noise entries; expands profit capture on strong trends. |
| **`mean_reversion`** | • RSI 14 (Oversold 30 / Overbought 70)<br>• Bollinger Std Dev: `2.0`<br>• Min Conf: `0.50`<br>• SL/TP: `1.2x` / `1.8x` ATR | Active in ranging markets; occasional false breakouts. | • RSI: **`25 / 75`**<br>• Bollinger Std Dev: **`2.2`**<br>• Min Conf: **`0.60`** | Ensures signals fire only at deep statistical over-extensions. |
| **`breakout`** | • Lookback: 20 bars<br>• Breakout Thresh: `0.015`<br>• Min Conf: `0.50`<br>• SL/TP: `1.4x` / `2.8x` ATR | Moderate frequency; sensitive to fake-outs. | • Breakout Thresh: **`0.020`**<br>• Vol Spike Factor: **`> 1.8x`**<br>• Min Conf: **`0.65`** | Requires volume confirmation to avoid bull/bear traps. |
| **`liquidity`** | • Lookback: 10 bars<br>• Liquidity Thresh: `1,000,000`<br>• Vol Spike: `1.5x`<br>• Min Conf: `0.50` | Low frequency; targets liquidity pools. | • Vol Spike: **`2.0x`**<br>• Min Conf: **`0.60`** | Triggers only on major liquidity sweeps. |
| **`vwap_reversal`** | • VWAP Period: 89<br>• Std Dev: `1.5`<br>• Reversal Thresh: `0.01`<br>• Min Conf: `0.50` | Medium frequency; mean reversion to VWAP. | • Std Dev: **`2.0`**<br>• Reversal Thresh: **`0.015`**<br>• Min Conf: **`0.60`** | Avoids counter-trend entries until price touches outer VWAP bands. |
| **`mtf_trend`** | • Timeframes: 5m / 15m / 1h<br>• Alignment Thresh: `0.70`<br>• Min Conf: `0.50` | Low frequency; multi-timeframe trend. | • Alignment Thresh: **`0.85`**<br>• Min Conf: **`0.65`** | Ensures 100% strict alignment across short, medium, and long timeframes. |
| **`oi_footprint`** | • Lookback: 25 bars<br>• OI Change Thresh: `0.05`<br>• Price Corr: `0.60`<br>• Min Conf: `0.50` | Low frequency; tracks open interest delta. | • OI Change Thresh: **`0.08`**<br>• Price Corr: **`0.75`** | Requires massive OI expansion to validate institutional positioning. |
| **`sweep_scalper`** | • Timeframe: 1m<br>• Vol Thresh: `50,000`<br>• Spread Thresh: `0.001`<br>• Min Conf: `0.60` | High frequency; scalps micro-spreads. | • Vol Thresh: **`100,000`**<br>• Min Conf: **`0.70`** | Prevents micro-scalp churn in low-volume consolidation. |
| **`volatility_breakout`** | • ATR Period: 14<br>• ATR Mult: `1.5`<br>• Volatility Thresh: `0.02`<br>• Min Conf: `0.50` | Rare frequency; targets volatility expansion. | • ATR Mult: **`2.0`**<br>• Volatility Thresh: **`0.03`** | Triggers exclusively during explosive volatility shifts. |
| **`crypto_breakout`** | • Lookback: 20 bars<br>• Breakout Thresh: `0.015`<br>• Min Conf: `0.50` | Crypto-specific channel breakout. | • Breakout Thresh: **`0.022`**<br>• Min Conf: **`0.65`** | Reduces false breakout losses on high-wick altcoins. |

---

## 3. KEY TAKEAWAYS FOR OPERATOR DECISION

1. **Keep Current Baseline Intact**:
   - The current baseline is generating **`+$67.88 VST`** net profit (**PF 3.40**). No emergency changes are required.
2. **If You Decide to Increase Strictness**:
   - The safest first step is raising global `STRATEGY_MIN_CONFIDENCE_THRESHOLD` from **`0.50` to `0.60`** in `.env`.
   - This simple configuration change immediately filters out low-conviction signals across all 10 strategies without modifying underlying code.
3. **P3 Priority Recommendation**:
   - Focus P3 on **Exit Management Strictness** (preventing discretionary `MARKET` exits from cutting LONG profits early) before tweaking individual entry parameters.
