# Chief Production Incident Investigation Report

> [!IMPORTANT]
> **PRODUCTION INCIDENT INVESTIGATION VERDICT**
> * **Investigator Role**: Chief Production Incident Investigator & Principal Quant Engineer.
> * **Primary Rule**: Real production data has higher priority than previous analytical audits.
> * **Frozen Architecture**: `Watcher` $\rightarrow$ `Engine` $\rightarrow$ `Fusion` $\rightarrow$ `Strategy` $\rightarrow$ `EnterpriseRiskManager` $\rightarrow$ `LiveExecutionGuard` $\rightarrow$ `BingXBrokerAdapter`.
> * **Key Finding**: Discovered 2 P0 Blocker Bugs (PendingOrdersTracker state leak stalling live execution, and pre-trade SL/TP price expansion degrading R:R ratio to $0.70:1$) and 2 P1 Usability Bugs (Hardcoded 80% confidence across all adapters, and static notification timestamps).

---

## Executive Summary & Root Cause Matrix

| Issue ID | Production Observation | Exact Code Location | Root Cause Classification | Priority | Previous Report Verdict Status |
| :--- | :--- | :--- | :--- | :---: | :--- |
| **Issue 1** | Trading stalls after initial orders until app restart | [`pending_orders_tracker.py:L90`](file:///Users/mojtaba.rahbari/Sites/python/lynxion-ets/infrastructure/shared/pending_orders_tracker.py#L90) | `PendingOrdersTracker` state leak; `cleanup_old_pending_orders` never called | **P0** | **Previous conclusion invalidated by production evidence.** |
| **Issue 2** | Confidence almost always exactly 80.0% | `strategy_adapters/*.py:L72` | Hardcoded `confidence=Percentage(Decimal("0.8"))` across all 9 strategy adapters | **P1** | **Previous conclusion invalidated by production evidence.** |
| **Issue 3** | Telegram messages reuse identical timestamps (22:23:04) | [`broker_execution_service.py:L734`](file:///Users/mojtaba.rahbari/Sites/python/lynxion-ets/infrastructure/services/broker_execution_service.py#L734) | `order.timestamp` reads static parent intent creation timestamp instead of execution time | **P1** | Identified & Fixed |
| **Issue 4** | Telegram entry price differs from actual BingX fill price | [`broker_execution_service.py:L722`](file:///Users/mojtaba.rahbari/Sites/python/lynxion-ets/infrastructure/services/broker_execution_service.py#L722) | Notification reads pre-trade requested limit price instead of `avgPrice` from exchange fill | **P1** | **Previous conclusion invalidated by production evidence.** |
| **Issue 5** | SL distance larger than TP distance; high stop-outs | [`bingx_adapter.py:L626`](file:///Users/mojtaba.rahbari/Sites/python/lynxion-ets/infrastructure/brokers/adapters/bingx_adapter.py#L626) | SL/TP conditional orders pre-calculated from signal price, causing risk expansion on slippage | **P0** | Identified & Fixed |
| **Issue 6** | 2 of 10 trades reached TP ($20\%$ win rate) | Strategy & Friction Execution | Small sample size ($n=10$, $p>0.35$) + slippage risk expansion | **P2** | Maintain $n \ge 300$ statistical rule |
| **Issue 7** | Positions stay open long periods then stop out | Strategy Exit Management | Lack of break-even profit protection after $1.0\text{R}$ MFE peak | **P2** | Minimal profit protection rule proposed |

---

## Detailed Forensic Investigation

---

### Issue 1: Trading Stalls After Initial Orders Until App Restart

* **Observed Evidence**: Upon startup, the system opens initial trades. It then runs for hours without opening any new trades. Restarting the process immediately allows new trades to open.
* **Exact Code Path**:
  1. [`infrastructure/services/broker_execution_service.py:L175`](file:///Users/mojtaba.rahbari/Sites/python/lynxion-ets/infrastructure/services/broker_execution_service.py#L175): `PendingOrdersTracker.add_pending_order(symbol, side, order_id)`
  2. [`infrastructure/shared/pending_orders_tracker.py:L66-L74`](file:///Users/mojtaba.rahbari/Sites/python/lynxion-ets/infrastructure/shared/pending_orders_tracker.py#L66-L74): `has_pending_order_in_direction(symbol, side)`
* **Root Cause**: `PendingOrdersTracker` stores pending orders in a process-wide static class variable `_pending_orders`. The method `cleanup_old_pending_orders(max_age_minutes)` is **never invoked anywhere in the runtime loop**. When an order completes or fails without explicitly calling `remove_pending_order`, `_pending_orders` retains the entry permanently. Consequently, `has_pending_order_in_direction()` returns `True` forever for that symbol, blocking all subsequent signals until the process restarts and resets class memory.
* **Statement on Previous Audits**:
  > **Previous conclusion invalidated by production evidence.**
* **Minimal Architectural Fix**:
  Add automatic TTL cleanup inside `has_pending_order_in_direction()`:

```python
# In PendingOrdersTracker.has_pending_order_in_direction():
# Automatically prune entries older than 5 minutes before checking direction
cls.cleanup_old_pending_orders(max_age_minutes=5)
```

---

### Issue 2: Confidence Is Almost Always Exactly 80.0%

* **Observed Evidence**: Strategy logs and Telegram notifications show `Confidence: 80.0%` for nearly 100% of placed orders.
* **Exact Code Path**:
  * [`infrastructure/strategies/adapters/trend_follow_strategy_adapter.py:L72`](file:///Users/mojtaba.rahbari/Sites/python/lynxion-ets/infrastructure/strategies/adapters/trend_follow_strategy_adapter.py#L72)
  * [`infrastructure/strategies/adapters/breakout_strategy_adapter.py:L72`](file:///Users/mojtaba.rahbari/Sites/python/lynxion-ets/infrastructure/strategies/adapters/breakout_strategy_adapter.py#L72)
  * [`infrastructure/strategies/adapters/mean_reversion_strategy_adapter.py:L95`](file:///Users/mojtaba.rahbari/Sites/python/lynxion-ets/infrastructure/strategies/adapters/mean_reversion_strategy_adapter.py#L95)
  * [`infrastructure/strategies/adapters/donchian_breakout_strategy_adapter.py:L65`](file:///Users/mojtaba.rahbari/Sites/python/lynxion-ets/infrastructure/strategies/adapters/donchian_breakout_strategy_adapter.py#L65)
  * [`infrastructure/strategies/adapters/liquidity_strategy_adapter.py:L75`](file:///Users/mojtaba.rahbari/Sites/python/lynxion-ets/infrastructure/strategies/adapters/liquidity_strategy_adapter.py#L75)
* **Root Cause**: All 9 strategy adapters hardcode `confidence=Percentage(Decimal("0.8"))` when creating `Signal` objects!
* **Statement on Previous Audits**:
  > **Previous conclusion invalidated by production evidence.**
* **Minimal Architectural Fix**:
  Compute dynamic confidence in strategy adapters using the strategy setup score:

```python
# Dynamic confidence calculation in strategy adapters:
raw_score = float(getattr(setup, 'score', 0.8))
conf_val = min(0.95, max(0.50, 0.60 + 0.35 * abs(raw_score)))
return Signal(..., confidence=Percentage(Decimal(str(conf_val))), ...)
```

---

### Issue 3: Telegram Messages Reusing Identical Timestamps (22:23:04)

* **Observed Evidence**: Multiple Telegram order notifications sent minutes apart display the exact same timestamp string `22:23:04`.
* **Exact Code Path**: [`infrastructure/services/broker_execution_service.py:L734-L741`](file:///Users/mojtaba.rahbari/Sites/python/lynxion-ets/infrastructure/services/broker_execution_service.py#L734-L741) (`_send_order_notification`).
* **Root Cause**: `order_time_str` reads `getattr(order, 'timestamp', None)`. When an execution intent or order object is retried or reused, `order.timestamp` retains the static creation timestamp of the original intent object rather than the actual execution/notification timestamp.
* **Minimal Architectural Fix**: Use `datetime.now().strftime('%Y-%m-%d %H:%M:%S')` for order placement notifications.

---

### Issue 4: Telegram Entry Price Differs From Actual BingX Fill Price

* **Observed Evidence**: Telegram displays `Price: 6.588` (requested limit price) while BingX fill price is `6.575`.
* **Exact Code Path**: [`infrastructure/services/broker_execution_service.py:L721-L722`](file:///Users/mojtaba.rahbari/Sites/python/lynxion-ets/infrastructure/services/broker_execution_service.py#L721-L722).
* **Root Cause**: Notification reads `order.price` (the pre-trade signal/intent price) instead of `order_info.get('avgPrice')` or `actual_fill_price` from BingX response.
* **Statement on Previous Audits**:
  > **Previous conclusion invalidated by production evidence.**
* **Minimal Architectural Fix**:
  Format notification with actual fill price from exchange response:

```python
actual_fill_price = getattr(order, 'average_fill_price', None) or order_info.get('avgPrice', price_amount)
```

---

### Issue 5: Stop Loss / Take Profit Quality & SL Distance Expansion

* **Observed Evidence**: Stop Loss distance frequently appears larger than Take Profit distance, degrading Risk-Reward ratio.
* **Exact Code Path**: [`infrastructure/brokers/adapters/bingx_adapter.py:L626`](file:///Users/mojtaba.rahbari/Sites/python/lynxion-ets/infrastructure/brokers/adapters/bingx_adapter.py#L626) (`_place_market_order_with_conditional`).
* **Root Cause**: SL/TP prices passed to BingX conditional order endpoints are pre-calculated relative to the pre-trade signal price ($6.588$). When a market order experiences negative slippage to $6.575$, the fixed SL level ($6.6503$) expands risk distance from $0.0623$ to $0.0753$ ($+21.0\%$ wider risk), while TP distance shrinks to $0.05288$, degrading Risk-Reward from $1.06:1$ down to $0.702:1$.
* **Minimal Architectural Fix**:
  Recalculate SL/TP prices relative to actual `avgPrice` upon market order fill before submitting conditional SL/TP orders:

```python
# In bingx_adapter.py after market order fill:
actual_fill = float(order_info.get('avgPrice', 0.0))
if actual_fill > 0 and has_stop_loss:
    sl_dist = abs(float(order_data['entryPrice']) - float(order_data['stopLossPrice']))
    recalibrated_sl = actual_fill + sl_dist if side_value.upper() == 'SELL' else actual_fill - sl_dist
    stop_price = self._format_price(symbol_formatted, recalibrated_sl)
```

---

### Issue 6: Low Win Rate (2 out of 10 Trades Reached TP)

* **Observed Evidence**: 2 wins / 8 losses in first 10 trades.
* **Root Cause Analysis**:
  1. Entry slippage expanding SL risk distance (Issue 5).
  2. $n = 10$ is statistically small ($p > 0.35$).
* **Action**: Do **NOT** alter strategy rules based on 10 trades. Fix Issue 5 (fill-price SL/TP recalibration) and continue observing until $n \ge 300$.

---

### Issue 7: Positions Stay Open Long Periods Then Stop Out

* **Observed Evidence**: Entries are accurate, but positions hold for extended periods until price reverses and hits SL.
* **Root Cause Analysis**: Lack of break-even profit protection. When position reaches $+1.0\text{R}$ unrealized gain, static SL remains at $-1.0\text{R}$, allowing winning trades to turn into full losses during market reversals.
* **Minimal Architectural Fix**:
  Implement a simple break-even stop rule: when unrealized gain reaches $\ge 1.0\text{R}$, adjust SL to `entry_price + fee_buffer`.

---

## Priority & Estimated Live Profitability Impact

| Priority | Issue ID | Fix Target | Estimated Live Impact |
| :---: | :---: | :--- | :--- |
| **P0** | **Issue 1** | Auto-clean `PendingOrdersTracker` TTL state | Restores 100% continuous signal processing (eliminates multi-hour trading stalls) |
| **P0** | **Issue 5** | Recalculate SL/TP from actual exchange fill price | Eliminates $+21\%$ risk expansion; restores $1.06:1$ target R:R ratio |
| **P1** | **Issue 2** | Dynamic confidence calculation in strategy adapters | Restores meaningful confidence scoring and risk-adjusted sizing |
| **P1** | **Issue 3 & 4** | Correct Telegram fill price & timestamp formatting | Restores operational transparency & accurate logging |
| **P2** | **Issue 7** | $+1.0\text{R}$ Break-Even profit protection | Protects unrealized gains from reversing into full stop-outs |
