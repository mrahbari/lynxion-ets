# Lynxion-ETS: Task 0003 Resolution & Analysis Report
**Date: July 13, 2026**

This document summarizes the root cause analysis, implemented solutions, and future improvements regarding the multi-strategy signal generation and conflict issues on `WLDUSDT` and `HYPEUSDT` under high-frequency (`1m` / `5m`) timeframes.

---

## 🔍 Root Cause Analysis

### 1. Confidence Scores Sticking at `76.0%`
* **Cause**: In `BaseStrategyAdapter` and `BreakoutStrategyAdapter`, the final intent confidence calculation was hardcoded with a `* Decimal('0.8')` reduction multiplier. When the raw watcher confidence reached its upper limit of `95.0%`, the mathematical result was always capped at exactly `76.0%` ($0.95 \times 0.8 = 0.76$).

### 2. Simultaneous Opposite Trades (`WLDUSDT`)
* **Cause**: At `20:14:39`, `WLDUSDT` opened a `BUY` order (via `balanced_strategy` under a `stable` regime) and a `SELL` order (via `trend_following` under a `trending` regime) at the exact same timestamp. 
  * The strategy adapters did not enforce their corresponding regime context checks (`trend_following` bypassed the regime veto check).
  * The duplicate trade prevention checks only blocked subsequent trades if they were in the **same** direction, allowing simultaneous opposite trades to execute.

### 3. Sequential Opposite Trades (`HYPEUSDT`)
* **Cause**: At `20:14:39`, `HYPEUSDT` opened a `SELL` order, and 17 minutes later (`20:31:36`) opened a `BUY` order under the same `trend_following` strategy.
  * Because the duplicate trade checker allowed opposite-direction orders on the same symbol, the system ended up with concurrent open `LONG` and `SHORT` positions on the same symbol.

---

## 🛠️ Implemented Solutions

### 1. Dynamic Confidence Calibration
* **Calibrator Persistence**: Refactored `ConfidenceCalibrator` (`confidence_calibrator.py`) to auto-load its model on startup from `data/confidence_calibration.pkl` and save automatically after samples are updated.
* **Adapter Wiring**: Replaced the hardcoded `* 0.8` multiplier with dynamic scaling: `confidence_calibrator.calibrate_confidence(...)`.
* **Outcomes Feedback Loop**: 
  - `log_strategy_decision` now saves `raw_confidence` in the tracker history.
  - `log_broker_close` retrieves the raw confidence by `trade_id` and adds the trade outcome (profitable/loss) to the calibrator, triggering dynamic `IsotonicRegression` fitting.

### 2. Regime Veto Enforcement
* Implemented strict `should_execute(self, fused_signal)` methods in all adapters:
  - `TrendFollowStrategyAdapter` & `MTFTrendStrategyAdapter` $\rightarrow$ Rejects if regime doesn't contain `trend`.
  - `MeanReversionStrategyAdapter` & `VWAPReversalStrategyAdapter` $\rightarrow$ Rejects if regime doesn't contain `mean`, `revert`, `ranging`, or `stable`.
  - `BreakoutStrategyAdapter` & `DonchianBreakoutStrategyAdapter` $\rightarrow$ Rejects if regime doesn't contain `volatile` or `breakout`.

### 3. Universal Conflict Prevention
* Updated the duplicate filters in `_auto_detection_dedup.py`, `multi_broker_service.py`, and `broker_execution_service.py`.
* **New Rule**: If `prevent_same_direction_trade_per_symbol` is enabled (default is `True`), the system blocks any new entry orders on a symbol if **any** active position or pending order already exists for that symbol, regardless of the direction.

---

## 🚀 Recommended Future Improvements

### 1. Adaptive Parameter Scaling (Volatility-Aware)
* **Problem**: Hardcoding thresholds (like `breakout_threshold=0.001` or `trend_extreme_threshold=0.999`) works for a specific timeframe but breaks if the system switches from `1m` to `1h`.
* **Solution**: Strategies should dynamically scale thresholds using average ATR (Average True Range). For example:
  $$\text{Breakout Threshold} = \beta \times \frac{\text{ATR}(14)}{\text{Close}}$$
  This naturally adjusts the breakout sensitivity to the current timeframe's volatility.

### 2. Warm-Up Pipeline Validation
* **Problem**: Fresh starts or restarts have empty data buffers, resulting in missing indicators and blocked trades ("not enough bars").
* **Solution**: Implement a boot-stage loader that queries the historical database to warm up the strategy adapters with `100` historical candles before enabling order execution.

### 3. Regime Transition Cooldowns
* **Problem**: In choppy markets, the detected regime context can flip-flop rapidly between `stable` and `trending`, causing strategies to rapidly open and close opposite trades.
* **Solution**: Add a regime switch grace period (e.g. 5–10 candles) during which the system is locked into the last selected regime to avoid whip-sawing.
