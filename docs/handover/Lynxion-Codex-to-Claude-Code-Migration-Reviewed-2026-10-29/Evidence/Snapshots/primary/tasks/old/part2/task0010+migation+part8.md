Before implementing any further strategy migration, perform a Strategy Architecture Cleanup Audit.

Important constraints:
- Do not delete strategies only because the old implementation failed.
- Preserve valuable trading hypotheses.
- Separate "strategy hypothesis failure" from "implementation/timeframe/execution failure".
- The goal is removing legacy code, not removing alpha research.

Answer the following:

1. List all current strategies and classify them:
    - KEEP / MIGRATE / RETIRE
    - Reason based on hypothesis validity, not old code quality.

2. For each MIGRATE strategy:
    - Identify the preserved alpha component.
    - Define its destination pipeline:
      NGLS
      NGMR
      NGDP
      New pipeline if required.

3. Identify strategies that only need adapter replacement versus complete retirement.

4. Audit StrategyManager, registry, configuration and tests:
    - Remove dead registrations.
    - Remove unreachable code.
    - Avoid duplicate decision paths.

5. Do not create new markdown files.
6. Do not create new abstractions unless required.
7. Keep existing architecture frozen.

Before coding, answer the four engineering questions:
- What production problem does this solve?
- Why is this necessary now?
- Why is current implementation insufficient?
- Why is this the simplest correct solution?

Only after approval implement changes.