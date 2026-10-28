Proceed with the approved structural migration.

Execution constraints:

- This is a refactoring-only task.
- Do not add new functionality.
- Do not change trading behavior.
- Do not create new documentation files.
- Do not introduce new abstractions.

Before moving files:
1. Run a repository-wide reference search for:
    - class names
    - old module paths
    - dynamic imports

Then perform:

1. Move:
    - market_structure_engine.py
      -> infrastructure/market_structure/

    - setup_engine.py
      -> infrastructure/strategies/

    - execution_confirmation_engine.py
      -> infrastructure/execution/

    - execution_optimizer.py
      -> infrastructure/execution/

2. Update imports and test locations.

3. Remove old empty modules/directories if no longer needed.

4. Run the complete test suite.

Report only:
- Files moved
- References updated
- Tests passed
- Any unexpected dependency found

Do not generate markdown reports.