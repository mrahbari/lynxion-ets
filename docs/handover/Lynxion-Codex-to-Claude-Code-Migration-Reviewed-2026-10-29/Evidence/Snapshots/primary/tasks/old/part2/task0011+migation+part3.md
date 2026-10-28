The audit confirms that the orchestration logic is duplicated.

However, before implementing the refactor, simplify the architecture one step further.

The DecisionPipeline must NOT know anything about:

- strategy names
- setup type strings
- configuration identifiers
- concrete strategies

Its responsibility is only:

CandidateSetup
→
ExecutionConfirmationEngine
→
ExecutionOptimizer
→
ExecutionIntent

Move all setup discovery responsibility into SetupEngine.

Adapters may request CandidateSetup objects from SetupEngine, but the DecisionPipeline should receive an already selected CandidateSetup and execute only the confirmation and optimization stages.

Avoid string-based programming such as:

strategy_name="Trend"
setup_types=["NGTREND"]

Prefer domain objects or enums instead of raw strings.

The objective is to minimize duplicated orchestration while keeping the DecisionPipeline completely strategy-agnostic.

After the refactor:

- remove duplicate pipelines
- preserve behavior
- preserve live/backtest parity
- remove dead code immediately
- keep tests green

Do not introduce unnecessary abstractions.
Prefer the smallest production-quality solution.