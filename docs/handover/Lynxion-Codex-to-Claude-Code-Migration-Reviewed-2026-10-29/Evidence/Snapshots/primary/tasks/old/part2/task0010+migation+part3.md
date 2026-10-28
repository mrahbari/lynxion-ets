We are entering the production migration phase of Lynxion-ETS v2.

Important constraints:
- Architecture is frozen.
- Do not create new markdown files, reports, abstractions, wrappers, adapters, or duplicate entities.
- Prefer modifying existing production code.
- Legacy code must not remain as a parallel active path.
- Any temporary coexistence must have an explicit removal plan.
- Keep the repository clean and production-oriented.

Before coding, answer these four questions:

1. What production problem does this solve?
2. Why is this change necessary now?
3. Why is the current implementation insufficient?
4. Why is this the simplest correct solution?

Task: Integrate the new MTF decision pipeline into the real execution path.

Scope:

Phase 1: Wire the new pipeline without deleting legacy code yet.

1. Identify the current production decision flow:
    - StrategySelectionService
    - StrategyManager
    - ExecutionIntent creation
    - Backtester path
    - Live execution path

2. Replace only the active signal generation path for NGLS:

Current:
liquidity_strategy_adapter.py
sweep_scalper_strategy_adapter.py

Target:
Market Structure Engine
|
v
SetupEngine
|
v
ExecutionConfirmationEngine
|
v
ExecutionOptimizer
|
v
ExecutionIntent


Requirements:

- CandidateSetup must be created only by SetupEngine.
- ExecutionIntent must be created only after confirmation and optimization.
- StrategyAdapters must not generate competing signals.
- Backtester and live execution must use the same orchestration path.
- BingX remains the only execution broker.
- Binance/MEXC/Phemex remain data providers only.

Implementation rules:

1. Reuse existing:
    - StrategyPort
    - ExecutionIntent
    - RiskManager
    - BrokerPort
    - bootstrap/container.py

2. Do NOT:
    - create migration frameworks
    - create feature flags unless already existing
    - duplicate orchestration logic
    - create new strategy abstractions

3. Add only required tests:
    - verify NGLS path creates CandidateSetup
    - verify confirmation is required before ExecutionIntent
    - verify optimizer modifies execution parameters
    - verify realistic_backtester uses the same path

After implementation:
- Run complete test suite.
- Report:
    - files modified
    - production flow before/after
    - legacy code still active?
    - remaining cleanup steps

Do not proceed to NGMR/NGDP migration until NGLS production path is fully integrated and verified.