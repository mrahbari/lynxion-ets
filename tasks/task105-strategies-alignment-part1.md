You must comply with all rules and requirements defined in:
./tasks/task0-force-to-cover.md

CRITICAL CONSTRAINTS:
• Prefer modifying and extending EXISTING code files.
• Creating new files is allowed ONLY if existing files cannot be safely extended.
• Any new file must be explicitly justified.
• No architectural rewrites without necessity.

This is actually **very good news**, even though it feels frustrating.
I’ll be very direct and precise, because at this point ambiguity is the real enemy.

---

## ✅ STRATEGY → EXECUTIONINTENT MINIMAL BRIDGE PROMPT

> **System Context**
>
> The execution layer is now correct and strict:
> no trades are executed unless a Strategy emits an explicit `ExecutionIntent`.
>
> Current state:
>
> * Strategies generate raw signals
> * No ExecutionIntent is being emitted
> * Backtester correctly fails fast
>
> ---
>
> ## 🎯 Objective (This Step Only)
>
> Implement a **minimal, explicit, and testable ExecutionIntent emission path** for **ONE strategy only** (`crypto_breakout`).
>
> This is not optimization.
> This is a wiring and ownership step.
>
> ---
>
> ## 🔧 Step 1 — Identify Strategy Output Contract
>
> Inspect the `crypto_breakout` strategy and answer:
>
> * What does it currently return?
>
>   * signal?
>   * dict?
>   * None?
>
> Explicitly document the return type.
>
> ---
>
> ## 🔧 Step 2 — Add Explicit Intent Emission
>
> Modify `crypto_breakout` so that:
>
> * When a valid entry condition occurs:
>
>   * it constructs an `ExecutionIntent` directly
>   * with minimal required fields (side, size, price reference)
> * When conditions are not met:
>
>   * it returns `None`
>
> No other layer may create intents for this strategy.
>
> ---
>
> ## 🔒 Constraints
>
> * Modify ONLY the `crypto_breakout` strategy
> * No new files unless unavoidable
> * No parameter tuning
> * No filters added
>
> ---
>
> ## 🧪 Step 3 — Verification
>
> Run a short BTCUSDT backtest and confirm:
>
> * At least some ExecutionIntents are emitted
> * Backtester executes trades
> * Fail-fast no longer triggers
>
> If zero trades still occur:
>
> * print/log when intent creation is attempted
> * explain why it returns None
>
> ---
>
> ## 🚫 Explicit Non-Goals
>
> * Do NOT improve performance
> * Do NOT change other strategies
> * Do NOT soften execution validation
>
> This step exists purely to prove **Strategy-owned execution**.

---
