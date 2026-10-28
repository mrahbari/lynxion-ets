Before implementing Step 1 (Liquidity → NGLS), perform an Integration Contract Review.

Do not modify code.
Do not create files.
Do not remove legacy adapters.

Define the exact runtime contract between:

Market Data
->
Feature Pipeline
->
MTF Engines
->
CandidateSetup
->
ExecutionConfirmation
->
Risk Management
->
ExecutionIntent
->
Broker Execution


Answer:

1. Who owns creation of CandidateSetup?

2. Who converts CandidateSetup into ExecutionIntent?

3. Does StrategyAdapter still have a responsibility after migration?

4. How will NGLS replace liquidity_strategy_adapter without creating duplicate decision paths?

5. How will backtesting consume the exact same pipeline as live execution?

6. Which existing interfaces can be preserved?

7. What is the minimum code change required for Step 1?

Important constraints:

- No permanent parallel legacy path.
- No duplicate signal generation.
- No new abstraction unless required.
- Existing architecture must remain frozen.

Output only the integration contract and migration risks.