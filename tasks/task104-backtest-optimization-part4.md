You must comply with all rules and requirements defined in:
./tasks/task0-force-to-cover.md

CRITICAL CONSTRAINTS:
• Prefer modifying and extending EXISTING code files.
• Creating new files is allowed ONLY if existing files cannot be safely extended.
• Any new file must be explicitly justified.
• No architectural rewrites without necessity.


## ✅ FINAL BASELINE PROMPT — BACKTEST EXECUTION ALIGNMENT (PRE-HYPEROPT)

> **System Context**
>
> I am working with a production-grade quantitative trading system built on a strict **Hexagonal (Ports & Adapters) Architecture**.
>
> The execution pipelines are immutable:
>
> * **Watcher → Engine → Fusion → Strategy → Broker**
> * **Watcher → Engine → Fusion → Strategy → Aggregator → Broker**
>
> The system already produces strategy signals, but backtest behavior shows **signal–trade mismatch**, inconsistent trade density, and opaque execution control.
>
> This indicates **execution responsibility leakage**, primarily inside:
>
> * `runner_backtest.py`
> * `backtest/realistic_backtester.py`
>
> ---
>
> ## 🎯 Objective (This Step Only)
>
> Establish a **single, explicit, and debuggable execution contract** so that:
>
> 1. Backtests execute **only trades explicitly emitted by strategies**
> 2. No component outside the Strategy/Engine layer may invent, filter, or infer trades
> 3. Execution behavior becomes **traceable, deterministic, and Hyperopt-safe**
>
> This step is **foundational** and must be completed **before any optimization work**.
>
> ---
>
> ## 🔒 Non-Negotiable Constraints
>
> * Do NOT refactor or rewrite the architecture
> * Do NOT merge or bypass layers
> * Do NOT add live-trading or broker logic
> * Prefer modifying and extending **existing files**
> * New files are allowed **only if strictly unavoidable and justified**
>
> ---
>
> ## 🔍 Step 1 — Enforce Execution Responsibility Boundaries
>
> Audit the full backtest execution flow and **explicitly enforce**:
>
> * **Strategies**
>
>   * May ONLY emit trade intent
>   * May NOT trigger execution directly
> * **Engine**
>
>   * May accept or reject trade intent
>   * Must log rejection reasons explicitly
> * **Backtester**
>
>   * May ONLY execute an accepted trade intent
>   * Must NEVER:
>
>     * infer trades from signals
>     * apply hidden filters
>     * decide whether a trade should exist
>
> Identify and remove any logic in:
>
> * `realistic_backtester.py`
> * `runner_backtest.py`
>
> that:
>
> * creates trades without an explicit intent
> * checks `backtest_mode` to bypass execution
> * simulates PnL without an order-level object
>
> All such logic must be flagged and corrected.
>
> ---
>
> ## 📐 Step 2 — Introduce a Minimal ExecutionIntent Contract
>
> Introduce a **minimal, immutable `ExecutionIntent` object** as a formal contract between:
>
> * Strategy → Engine
> * Engine → Backtester
>
> Constraints:
>
> * ExecutionIntent must be:
>
>   * immutable
>   * data-only
>   * order-level (side, size, price, SL, TP, timestamp)
> * Existing strategy logic must NOT be rewritten
> * Strategy outputs must be **wrapped**, not replaced
>
> The Backtester must:
>
> * accept only `ExecutionIntent`
> * fail loudly if intent is malformed
> * log every accepted and rejected intent
>
> Silent execution paths are forbidden.
>
> ---
>
> ## 🧪 Step 3 — Backtest Determinism & Validation Guards
>
> Harden the backtest engine so that:
>
> 1. Identical inputs produce identical results
> 2. All state resets between runs
> 3. Trade counts are validated:
>
>    * zero-trade runs → FAIL FAST
>    * near-zero trade density → WARN
>
> Metrics must be:
>
> * computed from executed trades only
> * isolated per strategy
> * protected from NaN / divide-by-zero
>
> Heavy logging must be optional and disabled by default.
>
> ---
>
> ## 🚨 Explicit Non-Goals
>
> * Do NOT optimize strategies
> * Do NOT tune parameters
> * Do NOT integrate brokers
> * Do NOT prepare Hyperopt yet
>
> This step is about **execution correctness only**.
>
> ---
>
> ## ✅ Expected Outcome
>
> * A clear, enforceable execution contract
> * Backtests that execute **only what strategies intend**
> * Transparent logs showing:
>
>   * intent emitted
>   * intent accepted / rejected
>   * intent executed
> * A stable foundation suitable for:
>
>   * Hyperopt
>   * simulation
>   * future live execution
>
> If any requirement cannot be satisfied without breaking the architecture, it must be explicitly stated and justified.

