As Technical Lead, I am initiating Stage 8 — Post-Remediation Runtime Validation.

The remediation phase has been completed and all unit, integration, contract, and end-to-end tests passed. At this stage, do NOT implement any code changes unless a defect is conclusively identified.

The objective is to validate that the recent fixes behave correctly under real runtime conditions and that no regressions or hidden edge cases remain.

────────────────────────────────────────

### Validation Scope

Validate the following five areas:

1. Strategy Freshness Validation
2. Startup Signal Replay Elimination
3. Heartbeat Lifecycle & Recovery
4. Stop Loss / Take Profit Consistency
5. MAX_ORDER_NOTIONAL_USD Enforcement

────────────────────────────────────────

### Runtime Command

Run the trading system in TESTNET/VST mode using multiple symbols:

python run_trading_system.py --mode production --auto-detect --symbols BTCUSDT,ETHUSDT,SOLUSDT,XLMUSDT

Run continuously for at least 20–30 minutes.

Do not manually interfere with the execution.

────────────────────────────────────────

## Validation 1 — Startup Replay

Determine whether historical setups are still replayed after startup.

Collect:

• Number of ExecutionIntents generated during the first five minutes.
• Strategy names that generated those intents.
• Timestamp of each generated signal.
• Timestamp of the setup that created each signal.
• Timestamp of the latest candle.

Verify that every generated signal corresponds to the latest candle only.

Report:

PASS if no historical setup generated a live signal.

FAIL if any setup originated from historical replay.

────────────────────────────────────────

## Validation 2 — Strategy Diversity

Collect statistics for every registered strategy.

For each strategy report:

• Number of evaluations
• Number of generated signals
• Number of rejected signals
• Number of ExecutionIntents
• Number of executed trades

Explain why any strategy produced zero signals.

Confirm whether zero activity is due to market conditions rather than routing, fusion, regime filtering, or execution defects.

────────────────────────────────────────

## Validation 3 — Heartbeat Lifecycle

Monitor heartbeat behavior during the entire runtime.

Collect:

• heartbeat age
• market data updates
• watcher updates
• websocket status
• reconnect events
• stale detections

Specifically verify:

• heartbeat timestamps update whenever fresh market data is received
• heartbeat is no longer dependent on MarketObservation emission
• no false-positive HEARTBEAT GUARD VETO events occur

If any HEARTBEAT GUARD VETO occurs, include:

• symbol
• stale duration
• last market update
• websocket status
• watcher status
• exact root cause

────────────────────────────────────────

## Validation 4 — Stop Loss / Take Profit Integrity

For every generated order, trace the complete lifecycle.

Verify that:

Strategy
↓

ExecutionIntent
↓

Risk Engine
↓

SignalProcessor
↓

Broker Adapter
↓

Exchange Payload
↓

ExecutionTruthLedger

contains identical:

• Entry Price
• Stop Loss
• Take Profit

Report any mutation.

Any SL/TP modification after the Strategy layer is considered a failure.

────────────────────────────────────────

## Validation 5 — MAX_ORDER_NOTIONAL_USD

Enable:

MAX_ORDER_NOTIONAL_USD=100

If no order naturally exceeds the limit, simulate one.

For every capped order report:

• calculated quantity
• calculated notional
• capped quantity
• capped notional
• cap reason

Verify:

• leverage unchanged
• direction unchanged
• SL unchanged
• TP unchanged

Only quantity may change.

────────────────────────────────────────

## Runtime Statistics

Provide:

• runtime duration
• processed market ticks
• observations generated
• execution intents
• accepted orders
• rejected orders
• capped orders
• heartbeat vetoes
• websocket reconnects
• exceptions
• warnings

────────────────────────────────────────

## Final Assessment

Produce a structured report containing:

1. Startup Replay Validation
   PASS / FAIL

2. Strategy Diversity
   PASS / FAIL

3. Heartbeat Lifecycle
   PASS / FAIL

4. SL/TP Consistency
   PASS / FAIL

5. Order Cap Enforcement
   PASS / FAIL

6. Runtime Stability
   PASS / FAIL

For every FAIL include:

• exact root cause
• supporting runtime evidence
• affected files/classes
• minimal remediation proposal

Do not modify any code automatically.

Do not suggest architectural redesign.

Preserve the current architecture.

Only identify defects that are supported by runtime evidence.