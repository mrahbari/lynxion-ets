You must comply with all rules and requirements defined in:
./tasks/task0-force-to-cover.md

CRITICAL CONSTRAINTS:
• Prefer modifying and extending EXISTING code files.
• Creating new files is allowed ONLY if existing files cannot be safely extended.
• Any new file must be explicitly justified.
• No architectural rewrites without necessity.

## 🧠 FINAL ARCHITECTURE-AWARE AUDIT PROMPT (Evidence-Based)

> **System Context**
> I am operating a professional trading system built on a strict **Hexagonal (Ports & Adapters) Architecture** with the following immutable execution flows:
> Check the ./runner_backtest.py and Readme.md file to understand the current implementations

> * **Watcher → Engine → Fusion → Strategy → Broker**
> * **Watcher → Engine → Fusion → Strategy → Aggregator → Broker**
>
> A full 360-day multi-strategy backtest on **BTCUSDT** has been executed, and the resulting logs demonstrate **systemic execution failure**, not strategy failure.
>
> ---
>
> ## 🔍 Empirical Evidence from Backtest Logs
>
> * ~4670 candles evaluated per strategy
> * Thousands of strategy signals generated
> * Yet:
>
>   * Most strategies executed **0–2 trades**
>   * Multiple strategies reported **“No trades executed”**
>   * All strategies reported the **same Sharpe ratio (-0.28)**
>   * Signal counts vastly exceed executed orders
>
> These results are **statistically impossible** in a correctly wired execution system and strongly indicate:
>
> * strategy output is ignored or overridden
> * execution is gated by hidden logic
> * or the Broker layer is never reached
>
> ---
>
> ## 🎯 Objective
>
> Perform a **deep, non-invasive architectural audit** to:
>
> 1. Identify where strategy intent is discarded
> 2. Enforce a single, unified execution flow
> 3. Restore full backtest ↔ live parity
> 4. Preserve architectural integrity at all costs
>
> This audit must be completed **without breaking or refactoring the Hexagonal Architecture**.
>
> ---
>
> ## 🧱 Strict Architectural Constraints
>
> * No layer may be removed, merged, or bypassed
> * No cross-layer logic is allowed
> * All fixes must be:
>
>   * additive
>   * trace-based
>   * contract-driven
>
> Layer responsibilities are **strict**:
>
> * **Watcher**: market data only
> * **Engine**: orchestration only
> * **Fusion**: feature/context synthesis only
> * **Strategy**: the **only source of trade intent**
> * **Aggregator**: explicit signal combination only
> * **Broker**: execution only (simulated or BingX VST)
>
> ---
>
> ## 🚨 Mandatory Execution Guarantees
>
> 1. **Strategy → Broker Causality**
>
>    * Every executed trade must be directly traceable to a strategy signal
>    * If a signal is not executed, the exact rejection reason must be logged
> 2. **Zero Silent Failures**
>
>    * “No trades executed” without architectural explanation is unacceptable
>    * Any execution blockage must:
>
>      * be explicit
>      * be observable
>      * fail fast if unintended
> 3. **Backtest = Live Contract**
>
>    * Backtest must use the **exact same execution contract** as:
>
>      * paper trading
>      * BingX VST live trading
>    * Only the Broker adapter may differ
> 4. **Metric Integrity**
>
>    * Metrics must be derived exclusively from executed trades
>    * Identical metrics across distinct strategies must be treated as a failure signal
> 5. **BingX VST Verification**
>
>    * When running in live or VST mode:
>
>      * orders must be successfully placed on BingX
>      * broker responses must be returned upstream
>      * order IDs must be logged and verifiable
>
> Any state where signals exist but no broker orders are created is a **critical system failure**.
>
> ---
>
> ## 🧠 Expected Outcome
>
> * Verified end-to-end execution path:
>
>   ```
>   Watcher → Engine → Fusion → Strategy → (Aggregator) → Broker
>   ```
> * Realistic trade counts over multi-month data
> * Strategy differentiation visible in metrics
> * System safe for:
>
>   * Hyperopt
>   * Walk-forward analysis
>   * Live capital deployment
>
> ---
>
> **Important**
> This system is intended for real trading.
> Any hidden logic, implicit execution gates, or silent overrides invalidate the research and must be eliminated.
