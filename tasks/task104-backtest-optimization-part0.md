You must comply with all rules and requirements defined in:
./tasks/task0-force-to-cover.md

CRITICAL CONSTRAINTS:
• Prefer modifying and extending EXISTING code files.
• Creating new files is allowed ONLY if existing files cannot be safely extended.
• Any new file must be explicitly justified.
• No architectural rewrites without necessity.

## 🟢 BASELINE BACKTEST VALIDATION PROMPT

> **System Context**
> I am working with a modular trading system built on a **Hexagonal Architecture** with the following execution flow:
>
> **Watcher → Engine → Fusion → Strategy → (Aggregator) → Broker**
>
> I am currently in the **baseline validation phase**.
> The goal is NOT optimization, NOT performance, and NOT live trading.
>
> ---
>
> ## 🎯 Objective (Baseline Only)
>
> Prove that the backtest engine:
>
> 1. Executes **only and exactly** the selected system strategies
> 2. Follows the architectural flow without bypasses
> 3. Produces trades solely as a consequence of strategy logic
>
> Nothing else is in scope for this step.
>
> ---
>
> ## 🔍 Validation Requirements
>
> 1. **Strategy Exclusivity**
>
>    * Backtest must fail if a strategy is missing or invalid
>    * No fallback, default, or sample strategy may be used
>    * Strategy selection must be explicit and verifiable
> 2. **Architectural Flow Enforcement**
>
>    * Every candle must pass through:
>
>      ```
>      Watcher → Engine → Fusion → Strategy
>      ```
>    * No layer may:
>
>      * generate trades independently
>      * alter strategy intent
>      * short-circuit execution
> 3. **Minimal Execution Confirmation**
>
>    * When a strategy emits an entry signal:
>
>      * a trade attempt must be recorded
>    * The backtest does NOT need realistic fills or fees at this stage
> 4. **Fail Fast on Silence**
>
>    * A backtest producing zero or near-zero trades over multi-month BTC data
>      must fail explicitly
>    * Silent continuation is not allowed
>
> ---
>
> ## 🚫 Explicit Non-Goals
>
> * Do NOT introduce new abstractions
> * Do NOT refactor architecture
> * Do NOT optimize performance
> * Do NOT add broker integrations
>
> ---
>
> ## ✅ Expected Outcome
>
> * Clear evidence that:
>
>   * strategies are actually executed
>   * trade counts scale logically with data length
> * A trustworthy baseline upon which further execution layers can be safely added
>
> If this baseline cannot be achieved, the system must stop and report why.

