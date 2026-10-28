# Future Bug Fixes & Performance Optimization Roadmap

This document outlines completed runtime remediation steps and provides the technical specification for upcoming performance and CPU optimization tasks.

---

## 1. Completed Runtime & Behavior Fixes

| Task / Issue | Status | Affected Components | Technical Summary |
| :--- | :--- | :--- | :--- |
| **Order Placement Lockout (~30min Halt)** | `COMPLETED` | `PendingOrdersTracker`, `StrategyAdapter` | Fixed in-flight lock leak and hardcoded 30-minute exit cooldown. Set in-flight TTL to 30s with auto-release on placement completion. |
| **Telegram Alert Watcher Name (`Watcher: N/A`)** | `COMPLETED` | `BrokerExecutionService`, `MultiBrokerService` | Propagated watcher metadata across signal chain and added strategy-based fallback mapping (`MTFTrend` $\rightarrow$ `TrendMTFWatcher`). |
| **Telegram Alert Timestamp Drift** | `COMPLETED` | `BrokerExecutionService`, `MultiBrokerService` | Replaced intent creation timestamps with live `datetime.now()` placement timestamps. |
| **Solution B: Logging Verbosity Reduction** | `COMPLETED` | `shared/logger.py`, `_config_extractors.py`, `dev.py` | Default `LOG_LEVEL` changed from `DEBUG` to `INFO`. High-frequency debug string formatting and disk writing overhead removed. |

---

## 2. Queued Performance & CPU Optimizations (Next Phases)

The following solutions are queued for implementation to optimize CPU utilization without altering frozen architecture or core decision logic:

### Task 0044: Symbol Universe Screening (Solution A)
* **Status**: `QUEUED`
* **Root Cause**: `approved_symbols.json` currently contains **787 active pairs**. Evaluating 10 Watchers across 787 symbols produces **~7,870 watcher calculations per cycle**, consuming significant CPU cores.
* **Planned Implementation**:
  1. Define a core active trading list (e.g. top 20–30 liquid USDT perpetual pairs like `BTCUSDT`, `ETHUSDT`, `SOLUSDT`, `AVAXUSDT`, `ZAMAUSDT`).
  2. Implement pre-screening to skip low-volatility/low-volume symbols before invoking compute-heavy watchers.

### Task 0045: Bar-Close Indicator & ML Caching (Solution C)
* **Status**: `QUEUED`
* **Root Cause**: `AnomalyMLWatcher` (Isolation Forest / Z-scores) and `TrendMTFWatcher` (multi-timeframe linear regressions) recalculate mathematical models on raw tick updates.
* **Planned Implementation**:
  1. Implement `last_evaluated_bar_timestamp` caching per symbol and timeframe.
  2. Skip full matrix/regression calculations until a new bar closes or a minimum elapsed interval (e.g. 15 seconds) has passed.

### Task 0046: Asynchronous Log Queueing (Solution D)
* **Status**: `QUEUED`
* **Root Cause**: `ForensicLogger` performs blocking synchronous JSON disk writes to `logs/forensic.log`.
* **Planned Implementation**:
  1. Wrap file logging handlers in Python's standard `QueueHandler` / `QueueListener`.
  2. Offload disk I/O to a background thread to eliminate I/O blocking on main trading loops.

---

## 3. Related Documentation

* [`docs/system_components_catalog.md`](file:///Users/mojtaba.rahbari/Sites/python/lynxion-ets/docs/system_components_catalog.md): Complete catalog of 10 Watchers, EngineService, 3 Fusion modules, and 11 Strategies.
* [`docs/README.md`](file:///Users/mojtaba.rahbari/Sites/python/lynxion-ets/docs/README.md): Master technical documentation index.
