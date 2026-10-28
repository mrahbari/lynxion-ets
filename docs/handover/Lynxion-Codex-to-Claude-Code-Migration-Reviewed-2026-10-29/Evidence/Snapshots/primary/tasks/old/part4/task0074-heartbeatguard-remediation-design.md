# LYNXION ETS — TASK0074: HEARTBEATGUARD REMEDIATION DESIGN & VALIDATION IMPACT REPORT
## Task: task0074-heartbeatguard-remediation-design
## Mode: READ-ONLY REMEDIATION DESIGN & EXPERIMENTAL IMPACT ANALYSIS — ZERO CODE MODIFICATION

**Role**: Principal Quant Researcher + Senior Algorithmic Trading Engineer + Production Validation Auditor  
**Architecture Status**: **FROZEN — EXPERIMENTAL BASELINE LOCKED — ZERO STRATEGY MUTATIONS**  
**Git Commit Hash**: `75246a1f7364d12790fb1d40ad231bb0222b3d22`  
**Git Branch**: `feat/trade-quality-2026-07-29`  
**Historical Boundary**: Trade #694 (`DOTUSDT`, realized PnL = `+$0.5174 VST`)  
**Prospective Validation Cohort Boundary**: **Trade #695 Onwards** (Target Sample Size N >= 100 Completed Prospective Trades)  

---

# A. ROOT CAUSE CONFIRMATION

- **Confirmed Mechanism**: `SignalProcessor._execute_intent()` reads `_last_market_data_times[symbol]` to enforce the 90-second data staleness safety check. However, `_last_market_data_times` is updated **ONLY** inside `MonitoringAnalysisService._fetch_and_update_symbol_data()` ([`infrastructure/watchers/monitoring_analysis_service.py:253`](file:///Users/mojtaba.rahbari/Sites/python/lynxion-ets/infrastructure/watchers/monitoring_analysis_service.py#L253)).
- **Production Pipeline Bypasses**: In live production execution mode (`run_trading_system.py --mode production --auto-detect`), live WebSocket streaming and REST candle ingestion update OHLCV candle buffers directly in `BingXBrokerAdapter` / `ArchitectureOrchestrator`, bypassing `MonitoringAnalysisService`.
- **System Consequence**: `_last_market_data_times` remains frozen at daemon startup time. 90 seconds after service start, `datetime.now() - last_time > 90.0s` evaluates `True` permanently, causing `HeartbeatGuard` to falsely veto 100% of live prospective trades across all symbols.

---

# B. CANONICAL REMEDIATION POINT

To avoid duplicate heartbeat tracking logic and maintain strict architectural layering, the remediation must establish a single canonical update method on `SignalProcessor` and invoke it at the market-data ingestion boundary:

1. **Canonical Helper Method**: Add `update_market_data_heartbeat(self, symbol: Union[Symbol, str], timestamp: datetime = None)` to `SignalProcessor` in [`infrastructure/messaging/event_system.py`](file:///Users/mojtaba.rahbari/Sites/python/lynxion-ets/infrastructure/messaging/event_system.py).
   - Normalize `symbol` to uppercase string key (`symbol.value if hasattr(symbol, 'value') else str(symbol)`).
   - Set `_last_market_data_times[symbol_str] = timestamp or datetime.now()`.
2. **Canonical Ingestion Boundary**: Call `signal_processor.update_market_data_heartbeat(symbol)` inside:
   - `MarketDataWatcher` / `MarketOpportunityWatcher.update_data()` when live WebSocket or REST bar updates are received.
   - `ArchitectureOrchestrator` / `AutoDetectionOrchestrator` when feeding live market candle updates into the strategy pipeline.

---

# C. HEARTBEAT SEMANTICS DESIGN

- **Timestamp Type**: **Local Receipt Wall-Clock Timestamp (`datetime.now()`)**.
- **Rationale**: `HeartbeatGuard` answers: *"Has our trading process received a valid market-data update for this symbol within the last 90 seconds?"* Using local receipt time ensures that clock skew or candle close timestamps (which naturally lag real-time during 5m or 15m bar assembly) do not trigger false stale data vetoes.
- **WebSocket Behavior**: Every incoming WebSocket tick/candle update for a symbol calls `update_market_data_heartbeat(symbol)`.
- **REST Fallback Behavior**: Every successful REST OHLCV fallback update calls `update_market_data_heartbeat(symbol)`.
- **Missing Heartbeat Behavior**: If no heartbeat is recorded for a symbol, `HeartbeatGuard` vetoes submission with: `❌ HEARTBEAT GUARD VETO: No market data heartbeat recorded for <symbol>`.

---

# D. SYMBOL COVERAGE & KEY NORMALIZATION

- **Key Canonicalization**: Symbol keys in `_last_market_data_times` must be strictly string-normalized:
  ```python
  symbol_key = symbol.value if hasattr(symbol, 'value') else str(symbol).upper().replace("-", "")
  ```
- **Coverage Guarantee**: All 34 active target symbols (`BTCUSDT`, `ETHUSDT`, `SOLUSDT`, `BCHUSDT`, etc.) will update the exact same dictionary key structure upon data ingestion, eliminating symbol string mismatches (`BCH-USDT` vs `BCHUSDT`).

---

# E. CONCURRENCY & THREAD SAFETY

- **Storage Structure**: `SignalProcessor._last_market_data_times` is a Python dictionary.
- **Thread Safety**: In Python (CPython GIL), dictionary key insertion (`d[k] = v`) and retrieval (`d.get(k)`) are atomic bytecode operations (`STORE_SUBSCR`).
- **Synchronization**: Thread-safe atomic writes without requiring heavy locks, preventing performance bottlenecks in high-frequency WebSocket tick callbacks.

---

# F. FAILURE SAFETY ANALYSIS

| Failure Scenario | Live System Event | Expected Guard Behavior |
| :--- | :--- | :--- |
| **Case 1: Market data genuinely stops (> 90s)** | Exchange/WS drops connection | `HeartbeatGuard` **MUST VETO** (`elapsed > 90.0s`) |
| **Case 2: Market data arrives normally** | WS/REST ticks arriving continuously | `HeartbeatGuard` **MUST ALLOW** (`elapsed < 2.0s`) |
| **Case 3: WS disconnects, REST fallback healthy** | REST fallback fetches fresh candle | `HeartbeatGuard` **MUST ALLOW** (REST updates heartbeat) |
| **Case 4: Heartbeat missing for symbol** | Uninitialized new symbol entry | `HeartbeatGuard` **MUST VETO** (`No heartbeat recorded`) |
| **Case 5: Invalid/malformed timestamp** | System error during ingestion | `HeartbeatGuard` **MUST VETO** (Safe fallback) |
| **Case 6: Wall-clock skew anomaly** | System clock jump backward | `HeartbeatGuard` **MUST VETO** (`elapsed < 0` safe check) |

---

# G. MINIMAL CHANGE SURFACE TABLE

| File | Class / Module | Proposed Change Summary |
| :--- | :--- | :--- |
| `infrastructure/messaging/event_system.py` | `SignalProcessor` | Add `update_market_data_heartbeat(symbol)` method and enforce string key normalization |
| `infrastructure/watchers/monitoring_analysis_service.py` | `MonitoringAnalysisService` | Use `signal_processor.update_market_data_heartbeat(symbol)` |
| `infrastructure/orchestrators/_auto_detection_execution.py` | Auto-Detection Loop | Call `signal_processor.update_market_data_heartbeat(symbol)` on live bar update |

---

# H. TEST PLAN

1. **Unit Tests**:
   - `test_heartbeat_fresh_allowed()`: Verify `elapsed <= 90s` returns `True`.
   - `test_heartbeat_stale_vetoed()`: Verify `elapsed > 90s` returns `None` and logs warning.
   - `test_heartbeat_missing_vetoed()`: Verify uninitialized symbol returns `None`.
   - `test_heartbeat_string_normalization()`: Verify `Symbol.BTCUSDT` and `"BTCUSDT"` update the exact same key.
2. **Integration Test**:
   - Simulate live WebSocket candle stream $\to$ `update_market_data_heartbeat()` $\to$ `SignalProcessor._execute_intent()`. Verify zero HeartbeatGuard vetoes when stream is active.
3. **Mandatory Regression Test**:
   - **Step 1**: Start daemon, wait > 90 seconds while streaming live market ticks. Generate `ExecutionIntent`. Verify `HeartbeatGuard` **DOES NOT VETO**.
   - **Step 2**: Pause market ticks, wait > 90 seconds. Generate `ExecutionIntent`. Verify `HeartbeatGuard` **MUST VETO**.

---

# I. ACCEPTANCE CRITERIA

1. **Before Fix**: Uptime > 90s + Active WS Stream + Valid ExecutionIntent $\implies$ `HeartbeatGuard FALSE VETO`
2. **After Fix**: Uptime > 90s + Active WS Stream + Valid ExecutionIntent $\implies$ **`ALLOW` (Order Submitted to Broker)**
3. **After Fix**: No Market Stream for > 90s + Valid ExecutionIntent $\implies$ **`VETO` (Order Rejected)**

---

# J. PROSPECTIVE VALIDATION IMPACT ANALYSIS

### **DECISION: `CONTINUE #695` (Reschedule Start Boundary at Trade #695 Post-Remediation)**

- **Methodological Rationale**:
  1. **Zero Trade Execution**: Because 100% of execution intents post-Trade #694 were vetoed at `HeartbeatGuard` prior to broker submission, **completed prospective trade count is `N = 0`**.
  2. **Zero Outcome Bias**: Zero realized PnL, zero win/loss results, and zero position changes occurred. No data filtering or outcome-based selection occurred.
  3. **Baseline Integrity Un-mutated**: Historical boundary remains locked at Trade #694 (`DOTUSDT`, PnL `+$0.5174 VST`). Git commit `75246a1f7364d12790fb1d40ad231bb0222b3d22` remains frozen.
  4. **Methodological Equivalency**: Option `CONTINUE #695` post-remediation is mathematically and statistically identical to a reset because `N` was exactly 0. The prospective validation cohort (Trades 695–794+, N >= 100) will execute cleanly under the remediated execution infrastructure.

---

# K. IMPLEMENTATION STATUS

### **`NO CODE MODIFIED`**

---

# ABSOLUTE SAFETY STOP CONDITION

CURRENT CONTROL STATUS:

P1 POSITION SIZING:
    PROVEN CLOSED ($1,000 CAP ACTIVE)

P2 SYMBOL COOLDOWN:
    PROVEN CLOSED (60M GATE ACTIVE)

EXIT MANAGEMENT:
    REJECTED (0 FAILURE)

PROSPECTIVE VALIDATION EXECUTION:
    ARMED — ZERO PROSPECTIVE EXECUTION

CODE MODIFICATION:
    NONE

REMEDIATION DESIGN COMPLETE.  
NO PRODUCTION CODE MODIFIED.  

WAITING FOR EXPLICIT OPERATOR APPROVAL BEFORE IMPLEMENTING INFRASTRUCTURE REMEDIATION.
