You must comply with all rules and requirements defined in:
./tasks/task0-force-to-cover.md

CRITICAL CONSTRAINTS:
• Prefer modifying and extending EXISTING code files.
• Creating new files is allowed ONLY if existing files cannot be safely extended.
• Any new file must be explicitly justified.
• No architectural rewrites without necessity.



## ✅ FINAL PROMPT — Hyperopt-Ready Backtest Hardening (Corrected)

> **System Context**
> I am preparing a strategy backtesting system for **Hyperparameter Optimization (Hyperopt)**.
>
> The system already:
>
> * executes strategies correctly
> * produces real trades
> * follows the intended architectural flow
>
> This step is strictly focused on making the backtest engine **stable, deterministic, and optimization-safe**.
>
> ---
>
> ## 🎯 Objective (This Step Only)
>
> Ensure that the backtest engine is:
>
> 1. Fully deterministic across repeated runs
> 2. Free of hidden state or cross-run leakage
> 3. Producing performance metrics that are safe to optimize
>
> This step must **not** change trading behavior.
>
> ---
>
> ## 🔍 Hardening Requirements
>
> ### 1. Run Isolation
>
> * All runtime state must reset between runs:
>
>   * positions
>   * equity
>   * indicators
>   * caches
> * No shared or static state across strategy executions
>
> ### 2. Deterministic Execution
>
> * Remove or fix all sources of randomness
> * Identical inputs must produce identical outputs
>
> ### 3. Trade Density Validation
>
> * Detect and explicitly reject:
>
>   * near-zero trade strategies
>   * pathological overtrading
> * Invalid runs must fail fast and be excluded from optimization
>
> ### 4. Metric Integrity
>
> * Metrics must be computed **only** from executed trades
> * Metrics must reset per run
> * Guard against NaN, infinity, or division-by-zero
>
> ### 5. Performance Constraints
>
> * Backtests must be fast enough for repeated Hyperopt iterations
> * Heavy logging must be optional or disabled by default
>
> ---
>
> ## 🚫 Explicit Non-Goals
>
> * Do NOT introduce new execution abstractions
> * Do NOT add live trading or broker logic
> * Do NOT refactor architecture
> * Do NOT optimize or change strategy logic
>
> ---
>
> ## ✅ Expected Outcome
>
> * Stable and repeatable backtest results
> * Metrics suitable as Hyperopt objectives
> * Clear rejection of invalid optimization runs
>
> If any requirement cannot be met without changing system behavior, it must be reported explicitly.

