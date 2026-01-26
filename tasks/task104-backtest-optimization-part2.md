You must comply with all rules and requirements defined in:
./tasks/task0-force-to-cover.md

CRITICAL CONSTRAINTS:
• Prefer modifying and extending EXISTING code files.
• Creating new files is allowed ONLY if existing files cannot be safely extended.
• Any new file must be explicitly justified.
• No architectural rewrites without necessity.


## ✅ NEXT-STEP PROMPT — Execution-Safe & Architecture-Preserving

> **System Context**
> I am working with a production-grade trading system built on a strict **Hexagonal (Ports & Adapters) Architecture**.
>
> The execution pipelines are immutable:
>
> * **Watcher → Engine → Fusion → Strategy → Broker**
> * **Watcher → Engine → Fusion → Strategy → Aggregator → Broker**
>
> Backtest logs over 360 days on BTCUSDT prove that strategies generate thousands of signals, yet almost no trades are executed.
> This confirms an **execution-layer failure**, not a strategy failure.
>
> ---
>
> ## 🎯 Objective (This Step Only)
>
> Perform a **surgical, non-breaking intervention** to:
>
> 1. Identify the exact code path where **entry intent is discarded**
> 2. Introduce a formal **ExecutionIntent contract**
> 3. Enforce **Backtest ↔ BingX VST execution parity**
>
> This must be done **without refactoring, bypassing, or collapsing any architectural layer**.
>
> ---
>
> ## 🔍 Step 1 — Locate the Entry Kill Zone
>
> Audit the execution flow and explicitly answer:
>
> * Where is a valid strategy entry signal:
>
>   * filtered
>   * short-circuited
>   * ignored
>   * or converted into a no-op
>
> You must:
>
> * name the exact class and method
> * show the conditional logic responsible
> * explain why execution stops
>
> Any logic that:
>
> * checks `backtest_mode`
> * skips broker calls
> * simulates PnL without creating an orderable object
>   must be flagged as **execution-breaking**.
>
> ---
>
> ## 📐 Step 2 — Inject ExecutionIntent (Do Not Replace)
>
> Introduce an **ExecutionIntent** object as an explicit, immutable contract between:
>
> * Strategy → Engine
> * Engine → Broker
>
> Constraints:
>
> * Strategies may **only emit ExecutionIntent**
> * Engine may:
>
>   * accept
>   * reject (with reason)
>   * forward
>     but may not modify intent semantics
> * Broker adapters (Backtest & BingX VST) must:
>
>   * accept the same ExecutionIntent interface
>   * differ only in execution mechanics
>
> No existing strategy logic may be rewritten; intent must be **wrapped around existing outputs**.
>
> ---
>
> ## 🧪 Step 3 — Enforce Backtest ↔ BingX VST Parity
>
> Add parity assertions that guarantee:
>
> 1. Every accepted ExecutionIntent results in:
>
>    * a simulated fill (backtest)
>    * or a real order ID (BingX VST)
> 2. If an intent is rejected:
>
>    * the rejection reason is logged
>    * execution continues safely
> 3. Over multi-month BTC data:
>
>    * executed trade count must be > 0
>    * otherwise the system must fail fast
>
> Silent execution paths are not allowed.
>
> ---
>
> ## 🚨 Non-Negotiable Rules
>
> * Do NOT:
>
>   * refactor architecture
>   * merge layers
>   * introduce side effects
>   * add hardcoded trading logic
> * All changes must be:
>
>   * additive
>   * traceable
>   * reversible
>
> ---
>
> ## ✅ Expected Outcome
>
> * Exact identification of the entry-blocking logic
> * A formal ExecutionIntent pipeline in place
> * Identical strategy behavior across:
>
>   * backtests
>   * simulations
>   * BingX VST live trading
>
> If any step cannot be completed without breaking the architecture, it must be explicitly stated and justified.
>
> ---
>
> **Important**
> This system is used for real capital deployment.
> Execution ambiguity or silent failures are unacceptable.

---