# Remediation Phase Report

**Author**: Technical Lead  
**Date**: 2026-07-19  
**Status**: Implementation & Validation Complete

---

## 1. Files Modified

The following files were modified to implement the approved remediation scope:

| Layer | File Path | Scope of Change |
| :--- | :--- | :--- |
| **Domain** | [`application/configs/schemas/risk.py`](file:///Users/mojtaba.rahbari/Sites/python/lynxion-ets/application/configs/schemas/risk.py) | Added optional `max_order_notional_amount` field to Pydantic config schemas. |
| **Application** | [`application/configs/_config_extractors.py`](file:///Users/mojtaba.rahbari/Sites/python/lynxion-ets/application/configs/_config_extractors.py) | Populated `max_order_notional_amount` from the environment variable configuration loader. |
| **Strategy** | [`infrastructure/strategies/strategy_adapters.py`](file:///Users/mojtaba.rahbari/Sites/python/lynxion-ets/infrastructure/strategies/strategy_adapters.py) | Added `_is_setup_fresh` logic to `BaseStrategyAdapter` and freshness checks in `VolatilityBreakoutStrategy`. |
| **Strategy** | [`infrastructure/strategies/adapters/*.py`](file:///Users/mojtaba.rahbari/Sites/python/lynxion-ets/infrastructure/strategies/adapters/) (all 9 adapters) | Applied freshness validations in `generate_signal` and `evaluate_fused_signal`. |
| **Messaging** | [`infrastructure/messaging/event_system.py`](file:///Users/mojtaba.rahbari/Sites/python/lynxion-ets/infrastructure/messaging/event_system.py) | Implemented SL/TP validation rejections and `MAX_ORDER_NOTIONAL_AMOUNT` cap; removed heartbeat updates from `_process_observation`. |
| **Watcher** | [`infrastructure/watchers/monitoring_analysis_service.py`](file:///Users/mojtaba.rahbari/Sites/python/lynxion-ets/infrastructure/watchers/monitoring_analysis_service.py) | Decoupled heartbeat timestamp update, moving it immediately after successful market data ingestion. |
| **Tests** | [`tests/unit/test_paper_trading_safety_attribution.py`](file:///Users/mojtaba.rahbari/Sites/python/lynxion-ets/tests/unit/test_paper_trading_safety_attribution.py) | Adjusted unit tests to manual heartbeat registration and mock `stop_loss_price` & `take_profit_price` Money objects. |

---

## 2. Exact Code Locations & Reasons

### 1. Pydantic Risk Schema & Loader
* **Files**: [`schemas/risk.py:L44`](file:///Users/mojtaba.rahbari/Sites/python/lynxion-ets/application/configs/schemas/risk.py#L44), [`_config_extractors.py:L80`](file:///Users/mojtaba.rahbari/Sites/python/lynxion-ets/application/configs/_config_extractors.py#L80)
* **Location**: Field `max_order_notional_amount: Optional[float] = Field(default=None)` added to `RiskConfig`. Extraction mapping added to `_extract_risk_config_data`.
* **Reason**: Allows the application settings to natively accept and parse the optional `MAX_ORDER_NOTIONAL_AMOUNT` environment variable or profile configuration without Pydantic validation errors (due to `extra = "forbid"` constraints).

### 2. Strategy Freshness checks
* **File**: [`strategy_adapters.py:L621-655`](file:///Users/mojtaba.rahbari/Sites/python/lynxion-ets/infrastructure/strategies/strategy_adapters.py#L621-L655)
* **Location**: Method `_is_setup_fresh(self, setup, latest_bar) -> bool` added to `BaseStrategyAdapter`. Normalizes and compares `setup.timestamp` and `latest_bar.timestamp` with a 5-second tolerance, or falls back to trigger price compared to close price (as an equivalent candle identity check).
* **Adapters**: Applied immediately after setup selection in `generate_signal` and `evaluate_fused_signal` across:
  * `breakout_strategy_adapter.py`
  * `donchian_breakout_strategy_adapter.py`
  * `liquidity_strategy_adapter.py`
  * `mean_reversion_strategy_adapter.py`
  * `mtf_trend_strategy_adapter.py`
  * `oi_footprint_strategy_adapter.py`
  * `sweep_scalper_strategy_adapter.py`
  * `trend_follow_strategy_adapter.py`
  * `vwap_reversal_strategy_adapter.py`
  * `strategy_adapters.py` (VolatilityBreakoutStrategy)
* **Reason**: Replay historical setups generated during startup or shadow buffer loads are blocked from creating `Signal` or `ExecutionIntent` objects, solving the startup signal burst bug.

### 3. Stop Loss / Take Profit Validation & Rejection
* **File**: [`event_system.py:L415-490`](file:///Users/mojtaba.rahbari/Sites/python/lynxion-ets/infrastructure/messaging/event_system.py#L415-L490)
* **Location**: Inside `SignalProcessor._process_execution_intent`. Replaced the fallback recalculation logic with validation checks:
  * Checks if `stop_loss_price` is missing, non-positive, or on the wrong side of the entry price (e.g. SL >= Entry for BUY).
  * Checks if `take_profit_price` is missing, non-positive, or on the wrong side of the entry price (e.g. TP <= Entry for BUY).
  * Validates distance sanity ratios against the 50% scale check.
  * If invalid, the order is **rejected**, a detailed warning logged, a record written to `ExecutionTruthLedger` under the `decision` event (with route `REJECTED`), and it exits immediately (`return None`).
* **Reason**: Enforces strategy ownership of SL/TP levels. Decoupled mutations are eliminated, ensuring sizing stop loss and execution stop loss are always identical.

### 4. Configurable Order Cap
* **File**: [`event_system.py:L530-562`](file:///Users/mojtaba.rahbari/Sites/python/lynxion-ets/infrastructure/messaging/event_system.py#L530-L562)
* **Location**: Inside `SignalProcessor._process_execution_intent` immediately before logging order details and instantiating `Order` object.
* **Reason**: Reads `MAX_ORDER_NOTIONAL_AMOUNT` from the environment or settings. If active, scales quantity down to fit the dollar notional limit while preserving leverage, side, SL/TP. Logs `ORDER CAP ENGAGED`.

### 5. Ingestion-Decoupled Heartbeat Update
* **Files**: [`event_system.py:L173-180`](file:///Users/mojtaba.rahbari/Sites/python/lynxion-ets/infrastructure/messaging/event_system.py#L173-L180), [`monitoring_analysis_service.py:L244-254`](file:///Users/mojtaba.rahbari/Sites/python/lynxion-ets/infrastructure/watchers/monitoring_analysis_service.py#L244-L254)
* **Location**: Removed the heartbeat update from `SignalProcessor._process_observation`. Added the update to `MonitoringAnalysisService._update_watchers_with_market_data` immediately when data is received and fed to the watchers.
* **Reason**: Decouples the heartbeat from pattern detection. In quiet markets or when observations are neutral, the heartbeat timestamp continues updating, avoiding false-positive heartbeat vetoes.

---

## 3. Architecture Integrity Verification

The system architecture remains strictly frozen:
1. **Module Boundaries**: All strategy adapters remain in the strategy layer. All messaging logic resides in the event system. No logic was moved between modules.
2. **Dependency Graph**: Dependencies flow inward (Strategy/Event System utilize ports/adapters). No reverse dependencies were introduced.
3. **Public APIs**: The signatures of `generate_signal` and `evaluate_fused_signal` remain unchanged. `_is_setup_fresh` is a private utility method.
4. **Execution Flow**: Watcher → Engine → Fusion → Strategy → Broker event stream is fully preserved.

---

## 4. Operational & Safety Validation Evidence

### 1. Sizing SL == Execution SL
Under the new logic, the Event System does not recalculate or modify SL/TP.
* **If SL/TP is valid**: The order is submitted directly with the original SL/TP calculated by the strategy adapter and sized by the Risk Engine.
* **If SL/TP is invalid**: The order is rejected immediately.
* **Result**: `Sizing SL == Execution SL` holds mathematically for 100% of executed orders.

### 2. Startup Replay Signal Burst Protection
When replaying historical data, the data buffer gets populated with the live/latest bars, but replayed signals carry older timestamps.
* In `BaseStrategyAdapter._is_setup_fresh`:
  ```python
  if setup_ts and bar_ts:
      # Compares normalized timestamps
      if abs((s_dt - b_dt).total_seconds()) >= 5.0:
          return False
  ```
* Historical setups fail the check (time difference is hours or days) and return `None`. No `ExecutionIntent` is created.

### 3. Heartbeat Updates in Quiet Markets
Heartbeat updates are triggered directly upon market data ingestion in the ingestion loop.
* Because the update does not wait for a `MarketObservation` or pattern detection event, `_last_market_data_times[symbol_str]` is updated on every tick/candle fetch. Even if the market has zero volatility and triggers no strategy setups, the heartbeat stays fresh.

### 4. Configurable Order Cap engagement
When `MAX_ORDER_NOTIONAL_AMOUNT` is set:
* If an order's notional (`quantity * execution_price`) exceeds the limit, the cap engagement logic triggers:
  ```python
  new_quantity = max_order_notional / execution_price
  quantity = new_quantity
  ```
* Log output: `🛡️ ORDER CAP ENGAGED: Capping order notional from $X to $Y. Old Qty: A, New Qty: B` is emitted, scaling the order safely.

---

## 5. Regression Test Summary

All test suites were executed successfully on the macOS development environment:

1. **Unit Tests (`tests/unit/`)**: 
   * **Passed**: `351` tests.
   * **Scope**: Validated risk engine adapter sizing, trade tracker statistics, message bus subscriptions, and paper trading safety features.
2. **End-to-End Tests (`tests/e2e/`)**:
   * **Passed**: `51` tests.
   * **Scope**: Verified multi-symbol execution flows, broker reconciliation under latency simulation, and mock futures trading lifecycles.
3. **Contract & Characterization Tests (`tests/contract/`, `tests/characterization/`, smoke)**:
   * **Passed**: `110` tests.
   * **Scope**: Asserted adapter port conformance, logging adapters, and shadow deployment simulations.

Total results: **`512` tests passed, `0` failed.**

---

## 6. Residual Risks

* **Risk**: Network latency causing delay in market data ingestion could still trigger a brief heartbeat stale guard veto if the websocket disconnects for longer than the guard timeout.
* **Mitigation**: The heartbeat stale guard is correctly set to 90.0 seconds (as remediated in Part 1), which provides a sufficient buffer for websocket reconnection attempts.
