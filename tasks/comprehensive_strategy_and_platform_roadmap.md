# Comprehensive Strategy & Platform Performance Roadmap

> **LEGACY / SUPERSEDED ANALYSIS (2026-09-14):** Retained for historical traceability only. The
> performance labels and recommendations below are hypotheses derived from older, non-admissible
> evidence; they do not prove Alpha or edge and do not authorize production changes. Current
> roadmap authority is defined in `docs/ROADMAP_INDEX.md` and `tasks/00-right-path.md`.

---

## 1. Quantitative Strategy Performance Hierarchy

Based on exhaustive quantitative auditing of the live trade journal ($N = 1,458$ trades):

```
==========================================================================================================
QUANTITATIVE STRATEGY PERFORMANCE SCORECARD
==========================================================================================================
Tier   Strategy          Trades    Win Rate    Profit Factor    Total PnL      Status / Strategic Role
──────────────────────────────────────────────────────────────────────────────────────────────────────────
Tier 1 OIFootprint (BUY)    34     100.00%         999.00     +$19.55 VST    ★ Alpha Engine (Scale Up)
Tier 1 TrendFollow (BUY)    12      83.33%           2.84      +$1.71 VST    ★ Strong Edge (Scale Up)
──────────────────────────────────────────────────────────────────────────────────────────────────────────
Tier 2 VWAPReversal        537      35.75%           0.18    -$484.58 VST    ⚠️ Needs 2.5σ Deviation Filter
Tier 3 SweepScalper         53      18.87%           0.26     -$14.66 VST    ⚠️ Needs MSS/CHoCH & Trend Gate
Tier 3 MTFTrend             36      13.89%           0.06     -$31.56 VST    ⚠️ Needs HTF Momentum Filter
Tier 4 MeanReversion        32       3.12%           0.04      -$9.56 VST    🛑 Toxic Fading (Restructure)
Legacy trend_following     742      31.40%           0.16  -$14,765.57 VST   🛑 Retired in Favor of V2
==========================================================================================================
```

---

## 2. Strategy-by-Strategy Diagnostic & Recommendations

### 1. `OIFootprint` (Open Interest + Volume Footprint) — ★ Tier 1 Alpha Engine
- **Current Performance**: **$100.0\%$ Win Rate** on BUY signals ($N=34$), $+19.55\text{ USDT}$ PnL.
- **Root Edge**: Captures true institutional positioning by identifying Open Interest expansion combined with aggressive buyer market order delta (CVD).
- **Actionable Recommendations**:
  1. **Primary Strategy Scaling**: Increase max risk allocation from $1.0\% \to 2.0\%$ portfolio equity for `OIFootprint` BUY setups.
  2. **Directional Trend Lock**: Disable counter-trend `SELL` signals when Bitcoin & Macro Market EMA50 > EMA200.
  3. **Multi-Asset Expansion**: Broaden footprint scanning across top 20 perpetual symbols.

---

### 2. `TrendFollow` — ★ Tier 1 Momentum Engine
- **Current Performance**: **$85.7\%$ Win Rate** ($N=14$), Profit Factor $3.26$.
- **Root Edge**: Enters pullbacks in established trend regimes rather than chasing breakouts.
- **Actionable Recommendations**:
  1. **Scanning Frequency Increase**: Increase scanning interval from 15m to 5m/15m multi-timeframe polling.
  2. **Pullback Depth Filter**: Require price to retrace to the 20-period EMA or Value Area POC before triggering entry.

---

### 3. `SweepScalper` (Liquidity Sweeps) — Tier 3 Strategy
- **Current Performance**: **$18.87\%$ Win Rate** ($N=53$), $-14.66\text{ USDT}$ PnL.
- **Root Problem**: Fades new 20-bar highs during macro trend expansions. Wicking above a high in a bull market is **absorption before breakout**, not a reversal.
- **Actionable Recommendations**:
  1. **Price Action Rejection Filter** *(Implemented)*: Require candle to close red/bearish or form an upper rejection wick $\ge 30\%$ of total candle range.
  2. **Trend & Value Area Gating** *(Implemented)*: Strictly prohibit `SELL` sweeps when $\text{EMA}_{10} > \text{EMA}_{20}$ or $\text{Price} > \text{VAH} \times 1.005$.
  3. **Lower-Timeframe CHoCH Confirmation**: Require a 5m market structure shift (candle close below previous swing low) before confirming 15m sweep entry.
  4. **Volume Exhaustion Gate**: Ensure sweep candle volume is lower than the previous expansion candle (no buying climax).

---

### 4. `VWAPReversal` — Tier 2 Strategy
- **Current Performance**: **$35.75\%$ Win Rate** ($N=537$), $-484.58\text{ USDT}$ PnL.
- **Root Problem**: Enters at $\pm 1.0\sigma$ to $\pm 1.5\sigma$ VWAP standard deviation bands, which are easily penetrated during normal trending volatility.
- **Actionable Recommendations**:
  1. **Extreme Deviation Threshold**: Expand entry trigger from $\pm 1.5\sigma \to \pm \mathbf{2.5\sigma}$.
  2. **Mean-Reversion Re-entry Filter**: Require price to cross back inside $\pm 2.0\sigma$ on a confirmed close before executing entry.
  3. **ADX Trend Suppression**: Disable `VWAPReversal` entirely when $\text{ADX}(14) > 25$ (Strong Trend).

---

### 5. `MeanReversion` (Value Area Reversion) — Tier 4 Strategy
- **Current Performance**: **$3.12\%$ Win Rate** ($N=32$), $-9.56\text{ USDT}$ PnL.
- **Root Problem**: Enters at Value Area High (VAH) or Value Area Low (VAL) assuming price will return to POC, but market often breaks out of the value area.
- **Actionable Recommendations**:
  1. **Range Regime Prerequisite**: Only enable when 1H Market Structure is confirmed as `RANGE / CHOP` ($\text{ADX} < 20$ and Bollinger Band Width $< 3\%$).
  2. **POC Distance Requirement**: Ensure minimum Reward-to-Risk ratio to POC is $\ge 2.0$.

---

## 3. Platform & Architectural Enhancements

```mermaid
graph TD
    A[Market Opportunity] --> B{Regime Classifier}
    B -- "Trending Regime (ADX > 25)" --> C[Enable: OIFootprint + TrendFollow]
    B -- "Ranging Regime (ADX <= 22)" --> D[Enable: VWAPReversal (2.5σ) + SweepScalper (MSS)]
    C --> E[Active Position Manager]
    D --> E
    E --> F{ROE >= +5%?}
    F -- Yes --> G[Move SL to Breakeven + Fee Buffer]
    F -- No --> H[Monitor Initial 2.2x ATR SL]
    G --> I{ROE >= +10%?}
    I -- Yes --> J[Dynamic Trailing SL Ratchet (0.5% behind peak)]
```

### 1. Active Position Management & Trailing Engine
- **Breakeven Protection**: When $ROE \ge +5.0\%$, automatically move Stop Loss to $\text{Entry Price} \pm 0.1\%$ fee buffer.
- **Dynamic Trailing Ratchet**: When $ROE \ge +10.0\%$, trail Stop Loss $0.5\%$ behind peak price mark, locking in gains.
- **Time-Decay Invalidation**: If a position stays stagnant ($|ROE| < 3\%$) for more than 4 hours (16 candles), execute a market exit to free up margin.

### 2. Universal Dynamic Symbol Normalizer
- Standardize all ticker formats via `SymbolFormatHelper` to prevent broker syntax rejections (`BTC-USDT` for BingX, `BTC/USDT` for Binance/Phemex, `BTC_USDT` for MEXC).

### 3. Volatility-Scaled Dynamic Stop Loss ($2.2\times\text{ATR}$)
- Dynamic ATR stops prevent premature wicking on volatile crypto assets (SOL, TAO, ZEC, XLM) while maintaining strict dollar risk caps.
