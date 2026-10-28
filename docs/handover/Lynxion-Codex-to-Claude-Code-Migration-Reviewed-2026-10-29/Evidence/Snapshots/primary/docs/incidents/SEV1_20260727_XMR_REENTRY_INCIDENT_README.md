# SEV-1 Incident Report: XMRUSDT Rapid Sequential Re-Entry & Notification Silence

**Incident Date:** 2026-07-27  
**Severity Level:** SEV-1 (Production Critical)  
**Status:** **RESOLVED & VERIFIED**  
**Target Files Modified:** [`infrastructure/strategies/strategy_manager.py`](file:///Users/mojtaba.rahbari/Sites/python/lynxion-ets/infrastructure/strategies/strategy_manager.py), [`infrastructure/execution/broker_reconciliation.py`](file:///Users/mojtaba.rahbari/Sites/python/lynxion-ets/infrastructure/execution/broker_reconciliation.py)

---

## 1. Executive Summary & Incident Timeline

During live trading on **2026-07-27 (17:20 to 17:43 UTC)**, symbol **XMRUSDT** entered 7 consecutive losing trades within 23 minutes during a sharp downward move:

* `17:20:34` → `17:20:57`: XMRUSDT Long (Loss: -9.73 USDT)
* `17:22:21` → `17:24:09`: XMRUSDT Long (Loss: -10.24 USDT)
* `17:26:33` → `17:27:09`: XMRUSDT Long (Loss: -10.04 USDT)
* `17:30:09` → `17:30:57`: XMRUSDT Long (Loss: -9.65 USDT)
* `17:33:57` → `17:35:21`: XMRUSDT Long (Loss: -9.95 USDT)
* `17:36:57` → `17:39:09`: XMRUSDT Long (Loss: -9.40 USDT)
* `17:42:09` → `17:43:09`: XMRUSDT Long (Loss: -9.67 USDT)

### Key Observed Symptoms:
1. **Bypassed Cooldown**: The configured 60-minute Stop Loss Cooldown did not activate, allowing rapid re-entry immediately after a Stop Loss exit.
2. **Missing Notifications**: No Telegram alert was dispatched when the position was closed by BingX.

---

## 2. Root Cause Analysis

Forensic audit revealed **two structural root causes**:

### Root Cause 1: Dual Instance Disconnection in `StrategyManager`
* **Vulnerability**:
  * `bootstrap/container.py` built an instance of `StrategyManager` and registered all 10 strategy adapters (`trend_following`, `breakout`, `mean_reversion`, etc.) into that container instance.
  * When `BrokerReconciliationService` ran `from infrastructure.strategies.strategy_manager import strategy_manager`, module import returned a **separate, unregistered `_strategy_manager_singleton` instance** with `self.strategies = {}`.
* **Impact**:
  * When `BrokerReconciliationService` detected position closures on BingX and invoked `strategy_manager.record_trade_result(sym, is_profitable=False)`, the event was delivered to the unregistered instance with **0 strategies**.
  * The actual strategy adapters on the container instance **never received the trade result event**. `last_sl_exit_time['XMRUSDT']` remained `None`, completely bypassing the 1-hour Stop Loss Cooldown!

### Root Cause 2: Missing Telegram Dispatch on Exchange Position Exit
* **Vulnerability**: Telegram notifications were previously implemented only during order placement (`execute_order()`).
* **Impact**: When BingX closed positions via Stop Loss, no Telegram notification was dispatched for the position exit event, resulting in silent background trade closures.

---

## 3. Permanent Solution Implemented

### Solution 1: Canonical `StrategyManager` Singleton Pattern
* **Location**: [`infrastructure/strategies/strategy_manager.py:L359-L375`](file:///Users/mojtaba.rahbari/Sites/python/lynxion-ets/infrastructure/strategies/strategy_manager.py#L359-L375)
* **Implementation**:
  ```python
  class StrategyManager:
      _instance = None

      def __new__(cls, *args, **kwargs):
          if cls._instance is None:
              cls._instance = super(StrategyManager, cls).__new__(cls)
              cls._instance._initialized = False
          return cls._instance

      def __init__(self):
          if getattr(self, '_initialized', False):
              return
          self._initialized = True
          self.strategies: Dict[str, BaseStrategyAdapter] = {}
  ```
* **Effect**: Guarantees that `container.resolve("strategy_manager")`, `from infrastructure.strategies.strategy_manager import strategy_manager`, and direct instantiation all resolve to the **exact same singleton instance** holding all registered strategy adapters.

### Solution 2: Real-Time Telegram Position Exit Alerts
* **Location**: [`infrastructure/execution/broker_reconciliation.py:L119-L135`](file:///Users/mojtaba.rahbari/Sites/python/lynxion-ets/infrastructure/execution/broker_reconciliation.py#L119-L135)
* **Implementation**:
  ```python
  # Dispatch immediate Telegram Alert for Position Close
  try:
      from infrastructure.services.risk_alerts import send_telegram
      outcome_str = "STOP LOSS" if not is_profitable else "TAKE PROFIT"
      emoji = "🛑" if not is_profitable else "✅"
      msg = (
          f"{emoji} <b>EXCHANGE POSITION CLOSED</b>\n\n"
          f"• <b>Symbol:</b> <code>{sym}</code>\n"
          f"• <b>Outcome:</b> {outcome_str}\n"
          f"• <b>Realized PnL:</b> <code>{realized_pnl if realized_pnl is not None else 'N/A'} USDT</code>\n"
          f"• <b>Cooldown:</b> {'60-Minute Stop Loss Cooldown Activated' if not is_profitable else 'None'}"
      )
      send_telegram(msg)
  except Exception as tel_err:
      self.logger.warning(f"Telegram notification for {sym} close could not be sent: {tel_err}")
  ```
* **Effect**: Dispatches an immediate HTML Telegram notification whenever a position closure is confirmed on BingX.

---

## 4. Empirical Verification & Test Evidence

### Singleton Identity Proof:
```text
Container StrategyManager id: 4416948064
Module strategy_manager id:   4416948064
New StrategyManager() id:     4416948064
✅ SUCCESS: StrategyManager is a true singleton across container, module import, and direct instantiation.
Registered strategies count: 10
```

### Full Unit Test Suite:
```text
============================= 400 passed in 11.23s =============================
```

---

## 5. Operations Guide & Restart Instructions

Restart the live trading system to apply the unified `StrategyManager` singleton and Telegram position exit alerts:

```bash
python run_trading_system.py --mode production --auto-detect
```
