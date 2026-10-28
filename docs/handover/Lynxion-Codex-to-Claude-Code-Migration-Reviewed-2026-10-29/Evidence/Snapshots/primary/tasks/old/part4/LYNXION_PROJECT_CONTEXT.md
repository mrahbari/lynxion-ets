# LYNXION ETS — MASTER PROJECT CONTEXT & ENGINEERING HANDOVER DOCUMENTATION
## File: ./docs/LYNXION_PROJECT_CONTEXT.md
## Mode: CANONICAL ARCHITECTURAL & OPERATIONAL REFERENCE — FROZEN VALIDATION BASELINE

---

# 1. EXECUTIVE SUMMARY & SYSTEM IDENTITY

**Lynxion ETS (Execution & Trading System)** is a high-reliability quantitative algorithmic trading platform designed for perpetual crypto futures execution. 

### Key System Attributes
- **Primary Venue / Exchange**: BingX Perpetual Futures (VST Testnet / Paper Trading Mode)
- **Target Asset Universe**: 34 active perpetual contracts (`BTCUSDT`, `ETHUSDT`, `SOLUSDT`, `BCHUSDT`, `BNBUSDT`, `DOGEUSDT`, `NEARUSDT`, etc.)
- **Execution Architecture**: Multi-layered event-driven pipeline (Watcher → Engine → Fusion → Strategy → SignalAggregator → RiskEnforcement → LiveExecutionGuard → MultiBrokerService → Exchange).
- **Current Development Phase**: **FROZEN PROSPECTIVE VALIDATION PHASE** (Executing passive prospective observation starting from Trade #695 through Trade #794+).

---

# 2. IMMUTABLE VALIDATION BASELINE & PROSPECTIVE EXPERIMENT

The production codebase is currently under a **FROZEN PROSPECTIVE VALIDATION GATE**. The state of the strategy and risk parameters must remain untouched during this phase.

- **Git Commit Baseline**: `75246a1f7364d12790fb1d40ad231bb0222b3d22`
- **Git Branch**: `feat/trade-quality-2026-07-29`
- **Historical Boundary**: Locked at **Trade #694** (`DOTUSDT`, realized PnL = `+$0.5174 VST`).
- **Prospective Cohort Boundary**: **Trade #695 Onwards**
- **Target Sample Size**: **$N \ge 100$ completed prospective trades** (Target Endpoint: Trade #794+).
- **Prospective Checkpoints**:
  - Checkpoint #1: Trade #710 ($N = 16$ completed prospective trades)
  - Checkpoint #2: Trade #725 ($N = 31$ completed prospective trades)
  - Checkpoint #3: Trade #750 ($N = 56$ completed prospective trades)
  - Checkpoint #4: Trade #775 ($N = 81$ completed prospective trades)
  - Final Acceptance Gate: Trade #794+ ($N \ge 100$, Net PnL > $0, Expectancy > +$0.25/trade, 0 risk violations).

---

# 3. END-TO-END DATA FLOW & PIPELINE ARCHITECTURE

```text
               +-------------------------------------------------------+
               | Live Market Data Stream (WebSocket Ticks & REST OHLCV)|
               +-------------------------------------------------------+
                                           |
                                           v
               +-------------------------------------------------------+
               |  Watcher Layer (MarketPulse, Volatility, TrendMTF)   |
               +-------------------------------------------------------+
                                           |  (Emits MARKET_OBSERVATION)
                                           v
               +-------------------------------------------------------+
               |  SignalProcessor & Engine Layer (Indicator Processing)|
               +-------------------------------------------------------+
                                           |  (Emits INTERPRETED_SIGNAL)
                                           v
               +-------------------------------------------------------+
               |  Fusion Layer (Multi-Timeframe & Indicator Fusion)    |
               +-------------------------------------------------------+
                                           |  (Emits FUSED_SIGNAL)
                                           v
               +-------------------------------------------------------+
               |  Strategy Manager & Adapters (10 Active Strategies)   |
               +-------------------------------------------------------+
                                           |  (Strategy Signal)
                                           v
               +-------------------------------------------------------+
               |  SignalAggregator (1s Ranking & Filtering Window)     |
               +-------------------------------------------------------+
                                           |  (Emits EXECUTION_INTENT)
                                           v
               +-------------------------------------------------------+
               |  HeartbeatGuard Gate (Staleness Check < 90.0s)        |
               +-------------------------------------------------------+
                                           |  (If Fresh < 90s)
                                           v
               +-------------------------------------------------------+
               |  RiskEnforcement Gate (P1 $1k Cap, P2 60m Cooldown)   |
               +-------------------------------------------------------+
                                           |  (If Approved)
                                           v
               +-------------------------------------------------------+
               |  LiveExecutionGuard Gate (Paper Mode & Order Cap $21)  |
               +-------------------------------------------------------+
                                           |  (If Validated)
                                           v
               +-------------------------------------------------------+
               |  MultiBrokerService / BingXBrokerAdapter             |
               +-------------------------------------------------------+
                                           |  (Market Order + OCO SL/TP)
                                           v
               +-------------------------------------------------------+
               |  Exchange (BingX Perpetual VST Orderbook)             |
               +-------------------------------------------------------+
                                           |
                    +----------------------+----------------------+
                    |                                             |
                    v                                             v
+----------------------------------------+   +----------------------------------------+
| LiveOrderJournal & TruthLedger Logging |   | BrokerReconciliationService Sync       |
+----------------------------------------+   +----------------------------------------+
```

---

# 4. SUBSYSTEM CODE MAP

| Subsystem | Primary Modules / Files | Key Classes & Functions | Core Responsibilities |
| :--- | :--- | :--- | :--- |
| **Pipeline Event System** | [`infrastructure/messaging/event_system.py`](file:///Users/mojtaba.rahbari/Sites/python/lynxion-ets/infrastructure/messaging/event_system.py) | `EventRouter`, `SignalProcessor`, `update_market_data_heartbeat()` | Routes signals between layers; enforces `HeartbeatGuard` freshness check. |
| **Watcher Layer** | [`infrastructure/watchers/market_opportunity_watcher.py`](file:///Users/mojtaba.rahbari/Sites/python/lynxion-ets/infrastructure/watchers/market_opportunity_watcher.py) | `MarketOpportunityWatcher`, `MonitoringAnalysisService` | Ingests market ticks; discovers dynamic symbols; emits `MARKET_OBSERVATION` events. |
| **Engine Layer** | [`infrastructure/engines/engine_service.py`](file:///Users/mojtaba.rahbari/Sites/python/lynxion-ets/infrastructure/engines/engine_service.py) | `EngineService`, `TechnicalAnalysisEngine` | Computes Technical Analysis indicators (RSI, ATR, MACD, EMA) from OHLCV bars. |
| **Fusion Layer** | [`infrastructure/fusion/fusion_service.py`](file:///Users/mojtaba.rahbari/Sites/python/lynxion-ets/infrastructure/fusion/fusion_service.py) | `FusionService`, `SignalFusionEngine` | Fuses multi-timeframe indicator signals into `FusedSignal` domain entities. |
| **Strategy Management** | [`infrastructure/strategies/strategy_adapters.py`](file:///Users/mojtaba.rahbari/Sites/python/lynxion-ets/infrastructure/strategies/strategy_adapters.py) | `StrategyManager`, 10 Strategy Adapters | Evaluates strategy rules (Breakout, Trend, Mean Reversion, Liquidity, etc.). |
| **Signal Aggregation** | [`infrastructure/aggregators/signal_aggregator.py`](file:///Users/mojtaba.rahbari/Sites/python/lynxion-ets/infrastructure/aggregators/signal_aggregator.py) | `SignalAggregator` | Collects, ranks, and filters strategy signals in 1-second windows to produce `ExecutionIntent`. |
| **Risk Enforcement** | [`infrastructure/risk/risk_enforcement.py`](file:///Users/mojtaba.rahbari/Sites/python/lynxion-ets/infrastructure/risk/risk_enforcement.py) | `RiskEnforcement`, `EnterpriseRiskManager` | Enforces P1 ($1,000 Exposure Cap), P2 (60m Cooldown), SL distance boundaries, and P1.1 Gate. |
| **Symbol Cooldown Gate** | [`infrastructure/risk/symbol_cooldown_gate.py`](file:///Users/mojtaba.rahbari/Sites/python/lynxion-ets/infrastructure/risk/symbol_cooldown_gate.py) | `SymbolCooldownGate`, `symbol_cooldown_gate` | Enforces 60-minute same-symbol entry cooldown with durable JSON state persistence. |
| **Live Execution Guard** | [`shared/live_execution_guard.py`](file:///Users/mojtaba.rahbari/Sites/python/lynxion-ets/shared/live_execution_guard.py) | `LiveExecutionGuard` | Prevents unauthorized real-money order routing; enforces paper trading safety mode. |
| **Broker Adapter Layer** | [`infrastructure/brokers/multi_broker_service.py`](file:///Users/mojtaba.rahbari/Sites/python/lynxion-ets/infrastructure/brokers/multi_broker_service.py) | `MultiBrokerService`, `BingXBrokerAdapter` | Formats order payloads; submits market entries and protective OCO SL/TP orders to exchange. |
| **Durable Order Journal** | [`infrastructure/execution/live_order_journal.py`](file:///Users/mojtaba.rahbari/Sites/python/lynxion-ets/infrastructure/execution/live_order_journal.py) | `LiveOrderJournal`, `live_order_journal` | Durable append-only operational log (`data/live_order_journal.json`) for startup order recovery. |
| **Truth Ledger** | [`infrastructure/execution/execution_truth_ledger.py`](file:///Users/mojtaba.rahbari/Sites/python/lynxion-ets/infrastructure/execution/execution_truth_ledger.py) | `ExecutionTruthLedger` | Immutable hash-chained audit log recording every execution decision and result. |
| **Broker Reconciliation** | [`infrastructure/execution/broker_reconciliation.py`](file:///Users/mojtaba.rahbari/Sites/python/lynxion-ets/infrastructure/execution/broker_reconciliation.py) | `BrokerReconciliationService` | Reconciles local journal orders against exchange open positions and order statuses. |
| **System Entrypoint** | [`run_trading_system.py`](file:///Users/mojtaba.rahbari/Sites/python/lynxion-ets/run_trading_system.py) | Main CLI Script | Daemon launcher for production auto-detection trading mode. |

---

# 5. PROVEN RISK CONTROLS & INVARIANTS

All trading operations must comply with these **non-negotiable P0 invariants**:

1. **P1 Position Sizing Exposure Cap**: Total open position notional across all active trades is strictly capped at **`$1,000.00 VST`** (`MAX_POSITION_EXPOSURE`).
2. **Order Slice Notional Cap**: Single-entry order notional is strictly capped at **`$21.00 VST`** (`MAX_ORDER_NOTIONAL_AMOUNT`).
3. **P2 Symbol Cooldown Gate**: Position entry on a symbol is blocked for **60 minutes** following a stop-loss exit or closed trade on that symbol (`SymbolCooldownGate`). State is persisted to `data/symbol_cooldowns.json`.
4. **Strategy Confidence Floor**: ExecutionIntents must meet or exceed **`0.50` (50%) minimum confidence threshold**.
5. **Mandatory Protective SL/TP Orders**: Every entry order MUST be submitted with explicit, finite Stop-Loss and Take-Profit price parameters creating an exchange OCO order pair.
6. **HeartbeatGuard Data Freshness Gate**: Enforces that market data was received for the target symbol within **`90.0` seconds** of intent execution. Uses local receipt wall-clock timestamps (`datetime.now()`). Fail-closed.
7. **Dynamic P1.1 Short-Side Safety Gate**: Short position entries on restricted symbols configured in `RESTRICTED_SHORT_SYMBOLS` environment variable are blocked to prevent short-squeeze orderbook slippage.

---

# 6. HISTORICAL FORENSIC INCIDENTS & REMEDIATION SUMMARY

### **Incident 1: HeartbeatGuard Data Staleness Veto Defect (Task 0073–0075)**
- **Root Cause**: `_last_market_data_times[symbol]` was mutated ONLY inside `MonitoringAnalysisService._fetch_and_update_symbol_data()` during initial setup. Live WebSocket tick and REST candle ingestion loops updated market data buffers but bypassed `MonitoringAnalysisService`, leaving stored timestamps frozen at startup time.
- **Remediation**: Implemented `SignalProcessor.update_market_data_heartbeat(symbol)` with uppercase string key normalization (`symbol_key = str(symbol_value).upper().replace("-", "")`), calling it on every incoming `MARKET_OBSERVATION` event.
- **Verification**: Verified via 7/7 passing targeted unit tests ([`tests/unit/test_heartbeat_guard_remediation.py`](file:///Users/mojtaba.rahbari/Sites/python/lynxion-ets/tests/unit/test_heartbeat_guard_remediation.py)) and 15/15 control risk unit tests ([`tests/unit/test_risk_enforcement.py`](file:///Users/mojtaba.rahbari/Sites/python/lynxion-ets/tests/unit/test_risk_enforcement.py)). Confirmed $\Delta = +1.5009\text{s}$ dynamic movement and 0 false vetoes in live runtime audit (PID 56791).

### **Incident 2: Un-reconciled In-Flight Order Journal Recovery (Task 0076)**
- **Root Cause**: 24 legacy test orders created during manual testing (August 11–13) were written to `data/live_order_journal.json` as `SUBMITTED` but were terminated without writing a terminal status record. Every daemon startup scanned the journal and flagged them as in-flight.
- **Remediation**: Reconciled all 24 stale pre-baseline test orders to `CANCELLED` status in `data/live_order_journal.json`. Enhanced `BrokerReconciliationService` to auto-resolve un-found orders on inactive symbols to `CANCELLED`.
- **Verification**: Daemon startup log verified: `♻️ STARTUP RECOVERY: loaded 576 journaled order(s); none in-flight`.

---

# 7. REGRESSION TEST SUITE MAP

| Test Suite File | Tested Components / Invariants | Command | Expected Result |
| :--- | :--- | :--- | :---: |
| [`tests/unit/test_heartbeat_guard_remediation.py`](file:///Users/mojtaba.rahbari/Sites/python/lynxion-ets/tests/unit/test_heartbeat_guard_remediation.py) | Heartbeat timestamp updates, key normalization, staleness veto, fail-closed missing heartbeat, continuous streaming regression. | `pytest tests/unit/test_heartbeat_guard_remediation.py` | **7 / 7 PASSED (100% GREEN)** |
| [`tests/unit/test_risk_enforcement.py`](file:///Users/mojtaba.rahbari/Sites/python/lynxion-ets/tests/unit/test_risk_enforcement.py) | P1 $1,000 Position Cap, P2 60m Cooldown Gate, Mandatory SL/TP, Short-side safety gate, SL distance boundaries. | `pytest tests/unit/test_risk_enforcement.py` | **15 / 15 PASSED (100% GREEN)** |

---

# 8. DIRECTIVES FOR FUTURE AI CODING AGENTS

When working on this repository, future AI agents MUST adhere to these strict execution rules:

1. **Do NOT Modify Production Code during Prospective Validation**: The current baseline commit `75246a1f7364d12790fb1d40ad231bb0222b3d22` is frozen. Strategy parameters, confidence thresholds, risk limits, and position sizing must NOT be altered without explicit operator authorization.
2. **Observe, Record, and Audit**: The prospective validation cohort (Trades #695 through #794+) must run passively. Observe market behavior, record trade outcomes, and audit control health invariants without manual intervention.
3. **No Lookahead or Data Snooping Bias**: All indicator calculations and market observations must use strictly historical/current candle data (`shift(1)` / bar close alignment).
4. **Never Weaken Risk Gates**: Never make `HeartbeatGuard`, `RiskEnforcement`, `LiveExecutionGuard`, or `SymbolCooldownGate` fail-open.
5. **Always Run Verification Commands**: Never declare a task complete without executing `pytest` test suites and verifying empirical log evidence.

---

### **DOCUMENTATION INTEGRITY COMPLETE**
*This canonical context file reflects the real, verified production codebase state of Lynxion ETS as of August 13, 2026.*
