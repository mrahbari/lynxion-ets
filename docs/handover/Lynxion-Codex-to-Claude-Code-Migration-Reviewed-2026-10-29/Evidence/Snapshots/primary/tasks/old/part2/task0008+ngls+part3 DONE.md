Using every scientific finding produced throughout this project, redesign the Lynxion-ETS trading decision pipeline.

Do NOT implement code.

Produce the final production architecture.

The design must integrate:

- 4H Macro Regime Engine
- 1H Market Structure Engine
- 15m Setup Engine
- 5m Execution Confirmation Engine
- optional 1m Execution Optimization

Map every existing Watcher, Engine, Fusion component, Strategy Adapter and Broker interaction into this new architecture.

For each component specify:

- Responsibility
- Inputs
- Outputs
- Timeframe
- Required features
- Dependencies

Identify:

- Components to remove
- Components to merge
- Components to split
- Components that become obsolete

Design the complete execution flow from market data to BingX order execution.

The output should become the production blueprint for Lynxion-ETS v2.

Do not write implementation code.

Focus on architecture, responsibilities, interfaces and migration strategy.