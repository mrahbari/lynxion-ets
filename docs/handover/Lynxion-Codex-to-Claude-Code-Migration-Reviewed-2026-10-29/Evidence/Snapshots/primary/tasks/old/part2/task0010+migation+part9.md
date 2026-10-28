Implement the approved Strategy Registry Cleanup only.

Scope:
- Remove retired strategies:
    - scalping
    - momentum

Remove them from:
- StrategyManager registry
- strategy_config.py
- dependency injection registrations
- obsolete unit tests

Constraints:
- Do not migrate trend, breakout, or OI strategies yet.
- Do not create new pipelines.
- Do not rename existing adapters.
- Do not modify StrategyPort or ExecutionIntent contracts.
- Preserve all valid strategy hypotheses.

Before coding answer:
1. What production problem does this solve?
2. Why is this necessary now?
3. Why is current implementation insufficient?
4. Why is this the simplest correct solution?

After implementation:
- Run complete test suite.
- Report changed files only.
- Report remaining migration candidates.