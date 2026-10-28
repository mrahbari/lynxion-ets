Before proceeding to NGMR or NGDP migration, perform a cleanup review of the NGLS migration.

Architecture constraints:
- Architecture remains frozen.
- Do not create unnecessary files or abstractions.
- Do not generate documentation files.
- Keep repository clean.
- Legacy strategy adapters must not become permanent owners of decision logic.

Answer the four questions:

1. What production problem does this cleanup solve?
2. Why is this cleanup necessary before migrating other strategies?
3. Why is the current implementation insufficient?
4. Why is this the simplest correct solution?

Task:

Review the current NGLS integration.

The current flow is:

Market Data
-> LiquidityStrategyAdapter / SweepScalperStrategyAdapter
-> MarketStructureEngine
-> SetupEngine
-> ExecutionConfirmationEngine
-> ExecutionOptimizer
-> ExecutionIntent

Evaluate whether decision logic has leaked into StrategyAdapters.

If yes:

Refactor minimally:

1. Keep StrategyAdapters only as compatibility/orchestration entry points.
2. Move NGLS decision pipeline ownership outside adapters.
3. Reuse existing services and ports.
4. Do not create duplicate strategy frameworks.
5. Preserve StrategyPort and ExecutionIntent contracts.
6. Ensure realistic_backtester and live execution still share the same path.

Do not migrate NGMR or NGDP yet.

After changes:
- run full tests
- report:
    - final NGLS execution flow
    - remaining legacy code
    - whether StrategyAdapters still own business logic
    - cleanup required before next migration