We are starting NGMR (Next Generation Mean Reversion) migration following the approved NGLS migration pattern.

Architecture rules:
- Architecture is frozen.
- Do not create unnecessary files, reports, markdown documents, wrappers, or duplicate abstractions.
- StrategyAdapters must remain thin compatibility layers only.
- Do not introduce parallel legacy decision paths.
- Any migrated legacy logic must have a cleanup/removal plan.

Before coding, answer:

1. What production problem does this solve?
2. Why is this migration necessary now?
3. Why are the current mean reversion strategies insufficient?
4. Why is this the simplest correct solution?

Goal:

Replace legacy:
- mean_reversion_strategy_adapter.py
- vwap_reversal_strategy_adapter.py

with the NGMR pipeline.

Target flow:

Market Data
|
v
StrategyAdapter
|
v
NGMRDecisionPipeline
|
+--> MarketStructureEngine
|        |
|        +--> Volume Profile POC / VAH / VAL
|        +--> Market boundaries
|
+--> SetupEngine
|        |
|        +--> Mean reversion candidate setup
|
+--> ExecutionConfirmationEngine
|        |
|        +--> OBI / CVD validation
|
+--> ExecutionOptimizer
|
+--> POST_ONLY maker parameters

    |
    v
ExecutionIntent


Implementation requirements:

1. Reuse existing:
- MarketStructureEngine
- SetupEngine
- ExecutionConfirmationEngine
- ExecutionOptimizer
- ExecutionIntent
- StrategyPort
- RiskManager
- bootstrap/container.py

2. Do not:
- keep Bollinger Band 1m signal generation active
- keep VWAP reversal logic as a second path
- duplicate Volume Profile calculations
- create another strategy framework

3. Create NGMRDecisionPipeline only if no existing production service can own this responsibility.

4. StrategyAdapters after migration:
- only maintain compatibility
- delegate decision making
- do not calculate entries/exits

5. Backtest and live must execute:

Market Data
-> Adapter
-> NGMRDecisionPipeline
-> ExecutionIntent
-> Risk
-> Execution


Testing requirements:

Add only required tests:
- NGMR creates CandidateSetup at VAL/VAH boundaries
- Confirmation rejects invalid order-flow conditions
- Optimizer produces maker execution parameters
- Backtester and live orchestration use identical pipeline


After implementation report:

- 4 architectural questions
- production flow before/after
- files modified
- legacy logic removed
- remaining cleanup items
- full test result

Do not start NGDP migration until NGMR is verified and cleaned.