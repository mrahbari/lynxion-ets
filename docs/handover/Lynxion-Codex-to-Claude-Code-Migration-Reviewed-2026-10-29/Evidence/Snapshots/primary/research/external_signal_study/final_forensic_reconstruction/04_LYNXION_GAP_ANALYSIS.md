# Read-only Lynxion comparison

This is source-level comparison, not proof of active VST behavior. No production module was changed.

| Sibling observation | Lynxion source-level behavior | Classification | Limit |
|---|---|---|---|
| WatcherX watchlist and selective waiting | `infrastructure/watchers/market_opportunity_watcher.py` discovers/filters symbols; `application/services/fusion_services.py` combines signals | PRESENT_BUT_DIFFERENT | No comparable sibling ranking or rejected-candidate denominator |
| Structural direction/setup language | `infrastructure/strategies/setup_engine.py` constructs 15m setups; `infrastructure/strategies/decision_pipeline.py` creates intents | PRESENT_BUT_DIFFERENT | No evidence that sibling rules equal Lynxion rules |
| Numeric SL and variable width | Setup engine derives structural SL with ATR floor; `infrastructure/risk/risk_enforcement.py` checks SL and caps | ALREADY_PRESENT | Sibling stop basis UNKNOWN; runtime behavior unverified |
| Human size reduction for wider stops | `application/risk_management/enterprise_risk_manager.py` contains equity-risk/stop-distance sizing when fixed mode is off; `application/configs/schemas/position_sizing.py` defaults fixed-size mode on | PRESENT_BUT_DIFFERENT | Effective intent-to-order sizing path unverified |
| Variable leverage advice | Risk/execution components constrain intents | NOT_COMPARABLE | No sibling leverage algorithm |
| Published targets | Setup engine has structural target and 1.5 minimum R:R floor, potentially extending TP | PRESENT_BUT_DIFFERENT | Not proof of natural target-space veto |
| Partial TP + BE + runner | `infrastructure/risk/active_position_manager.py` supports BE/ROE trailing and full-position exits; partial closure deliberately avoided there | PRESENT_BUT_DIFFERENT | Sibling behavior varies by operator |
| Macro/HTF discretionary wait | No verified equivalent of operator discretion in examined path | UNKNOWN | No universal sibling gate to copy |
| Correlated-trade risk-splitting advice | Exposure controls exist | NOT_COMPARABLE | One comment cannot establish portfolio rule |
| Broker/account safety | `shared/live_execution_guard.py`, risk enforcement, position management and reconciliation gate execution | ALREADY_PRESENT as code layers | No live behavioral validation here |

The most defensible next question is whether existing stop-distance sizing is selected and preserved through the risk/intent path. This is correctness verification, not an edge claim and not authorization to change defaults.
