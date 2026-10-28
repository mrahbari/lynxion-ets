Integration Migration Planning Task

The goal is NOT to keep the legacy system running indefinitely.

The objective is a clean migration where legacy decision logic is removed after each successful migration.

Do not create parallel permanent paths.
Do not add compatibility layers unless strictly required.
Do not preserve duplicate business logic.

Create a migration plan with these principles:

1. The final production architecture must have ONE decision pipeline.

2. StrategyAdapters may remain as interfaces, but their internal legacy indicator logic must be removed.

3. Migration must be incremental:
    - migrate one strategy
    - validate
    - remove obsolete code
    - continue to next strategy

4. Every migration step must include a cleanup step:
    - files/classes to delete
    - duplicate logic to remove
    - obsolete tests to remove/update

Prioritize migration:

1. Liquidity -> NGLS
2. Mean Reversion -> NGMR
3. OI Footprint -> NGDP
4. Other strategies review for retirement

For each step define:

- Current legacy components involved
- Target production flow
- Files to modify
- Files/classes to remove after migration
- Tests required
- Rollback considerations

Do not write code.
Do not create documentation files.
Keep the repository clean.