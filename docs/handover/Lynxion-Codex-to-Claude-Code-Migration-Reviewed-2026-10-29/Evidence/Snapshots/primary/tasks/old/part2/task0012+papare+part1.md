# Task: Production Hardening & Paper Trading Launch Preparation

You are now entering the final stabilization phase of the trading platform.

IMPORTANT:
Do not introduce new strategies.
Do not create new pipelines.
Do not redesign the architecture.
The current architecture is considered frozen.

Your goal is to verify, simplify, harden, and prepare the system for supervised paper trading.

---

## Context

Current architecture:

Market Data
↓
SetupEngine
↓
DecisionPipeline
↓
ExecutionConfirmationEngine
↓
ExecutionOptimizer
↓
ExecutionIntent
↓
NGDP Position Sizing
↓
Risk Enforcement
↓
Broker

Migrated strategies:

- NGLS (Liquidity Sweep)
- NGMR (Mean Reversion)
- NGTrend
- NGBreakout
- NGOI Footprint

All strategies now use the unified DecisionPipeline.

Current validation:

- Live/backtest execution path unified
- Dynamic position sizing implemented
- Risk guards implemented
- Setup attribution implemented
- 507+ tests passing

---

# Phase 1 — Architecture Hardening Audit

Before changing anything, perform a complete audit.

Answer:

1. Are there any remaining strategy-specific decision paths outside:
    - SetupEngine
    - DecisionPipeline
    - ExecutionConfirmationEngine
    - ExecutionOptimizer
    - Risk Engine

2. Are any adapters still doing:
    - indicator calculations?
    - entry decision logic?
    - SL/TP calculation?
    - position sizing?
    - execution routing?

3. Are there duplicated concepts:
    - multiple risk calculations?
    - multiple sizing calculations?
    - duplicate market structure calculations?
    - duplicate configuration sources?

4. Are there migration leftovers:
    - old feature flags
    - unused configs
    - dead imports
    - obsolete helper methods
    - unused tests

DO NOT delete anything yet.
Create an audit report first.

---

# Phase 2 — Code Cleanup

After audit approval:

Clean the repository.

Remove:

- dead strategy registrations
- obsolete configuration keys
- unused adapters
- migration-only classes
- duplicate helpers
- deprecated indicator implementations

Requirements:

- Preserve StrategyPort contract
- Preserve ExecutionIntent contract
- Preserve BrokerPort contract
- Preserve live/backtest parity

Every deletion must have a reason.

---

# Phase 3 — Strategy Attribution Validation

Verify that every trade can be traced:

Setup detection
↓
SetupType
↓
ExecutionIntent
↓
Order
↓
Fill
↓
Closed Trade
↓
PnL Attribution


Validate:

- strategy_name stored
- setup_type stored
- confidence stored
- NGDP sizing parameters stored
- execution result stored


Required metrics:

Per setup:

- total trades
- win rate
- profit factor
- realized PnL
- average holding time
- max drawdown contribution
- average slippage
- fill ratio

---

# Phase 4 — Paper Trading Safety Review

Audit production safety.

Verify:

## Market Data

- websocket heartbeat
- stale data rejection
- reconnect handling

## Execution

- duplicate order prevention
- idempotency
- order lifecycle tracking
- partial fill handling
- cancel/replace handling

## Risk

Verify:

- daily loss limit
- max drawdown limit
- position exposure
- correlation penalty
- portfolio heat
- emergency shutdown


## Broker

Verify:

- API failure handling
- rate limit handling
- exchange rejection handling
- retry policy

---

# Phase 5 — Paper Trading Configuration

Prepare a dedicated paper trading profile.

Requirements:

No code changes required for strategy logic.

Create configuration for:

- exchange test environment
- API credentials
- trading universe
- max capital exposure
- max concurrent positions
- risk limits
- logging level
- alert channels


---

# Phase 6 — Observability Checklist

Verify availability of:

## Trading Metrics

- signals generated
- setups detected
- confirmations accepted/rejected
- orders created
- orders filled
- rejected orders
- cancelled orders

## Execution Metrics

- latency:
  signal → intent
  intent → order
  order → fill

- slippage
- maker fill ratio
- rejected orders

## Risk Metrics

- sizing decisions
- risk multiplier
- correlation penalty
- drawdown multiplier


---

# Phase 7 — Final Production Readiness Report

Produce a final report containing:

## Architecture Status

- Remaining technical debt
- Remaining dead code
- Boundary violations

## Strategy Status

For each strategy:

- hypothesis preserved?
- implementation location
- active/inactive status

## Risk Status

- risk controls
- missing protections

## Paper Trading Decision

Answer:

Is the system ready for supervised paper trading?

If NO:
List exact blockers.

If YES:
Provide:

1. Deployment checklist
2. First paper trading monitoring plan
3. First 30-day evaluation criteria


---

Critical Rules:

- Prefer deletion over adding abstraction.
- Prefer existing components over new components.
- Do not create another pipeline.
- Do not move business logic into adapters.
- Do not optimize for code elegance at the cost of production safety.
- Keep architecture frozen unless a real production risk is discovered.

Start with audit only.
Do not implement changes before identifying concrete issues.