You must comply with all rules and requirements defined in:
./tasks/task0-force-to-cover.md

CRITICAL CONSTRAINTS:
• Prefer modifying and extending EXISTING code files.
• Creating new files is allowed ONLY if existing files cannot be safely extended.
• Any new file must be explicitly justified.
• No architectural rewrites without necessity.



## ✅ PRE-HYPEROPT TRADE DENSITY & SIGNAL QUALITY PROMPT

> **System Context**
> I am preparing strategies for **Hyperparameter Optimization**.
>
> The backtest engine is functional and validated, but current results show:
>
> * very low trade counts
> * unstable win rates
> * statistically weak performance metrics
>
> This step focuses exclusively on **trade generation quality**, not optimization.
>
> ---
>
> ## 🎯 Objective (Pre-Hyperopt Only)
>
> Improve strategy configurations so that:
>
> 1. Trade counts reach statistically meaningful levels
> 2. Win/loss distributions are non-degenerate
> 3. Metrics become stable enough for optimization
>
> Architectural integrity must be preserved.
>
> ---
>
> ## 🔍 Required Adjustments
>
> 1. **Signal Frequency Calibration**
>
>    * Review strategy filters that excessively suppress entries
>    * Identify parameters that cause over-constraining
>    * Adjust defaults to allow a reasonable number of trades
> 2. **TP / SL Balance Check**
>
>    * Validate that:
>
>      * TP distance is reachable given ATR
>      * SL is not disproportionately tight
>    * Ensure both wins and losses can realistically occur
> 3. **Minimum Trade Threshold**
>
>    * Enforce a minimum trade count per run (e.g. ≥30 trades)
>    * Runs below this threshold must be flagged as invalid for Hyperopt
> 4. **Metric Sanity Validation**
>
>    * Ensure win rate, Sharpe, and drawdown:
>
>      * are computed from sufficient samples
>      * are reset per strategy
>
> ---
>
> ## 🚫 Explicit Non-Goals
>
> * Do NOT run Hyperopt yet
> * Do NOT change backtest architecture
> * Do NOT add new strategies
> * Do NOT tune parameters aggressively
>
> ---
>
> ## ✅ Expected Outcome
>
> * Strategies that produce:
>
>   * consistent trade counts
>   * non-zero win rates
> * Backtest outputs suitable as input to Hyperopt
>
> If these conditions cannot be met, the strategy must be marked as non-optimizable.

---