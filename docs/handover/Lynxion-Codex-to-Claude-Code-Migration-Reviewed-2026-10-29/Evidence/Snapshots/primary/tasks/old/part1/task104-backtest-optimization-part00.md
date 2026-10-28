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
Same result with different start end time which shows that backtest result is wrong. help me to resolve it.
python runner_backtest.py --all-strategies --start 5d --end today --symbols BTCUSDT
python runner_backtest.py --all-strategies --start 30d --end today --symbols BTCUSDT
python runner_backtest.py --all-strategies --start 300d --end today --symbols BTCUSDT

>
> ---
>
> ## 🎯 Objective (Baseline Only)
>
> Prove that the backtest engine:
>
> 1. Executes **only and exactly** the selected system strategies
> 2. Follows the architectural flow without bypasses
> 3. Produce trades solely as a consequence of strategy logic
> 4.Check the ./runner_backtest.py and Readme.md file to understand the current implementations


### Sample of all different baktests
✅ Backtest completed with validation
   ✅ crypto_breakout backtest completed

🏆 STRATEGY COMPARISON RESULTS
   Best Performing Strategy: sweep_scalper (Return: -0.04%)

   All Strategies Ranked by Return:
   1. sweep_scalper        Return: -0.04%, Sharpe: -0.28, Drawdown: -0.00%, Trades: 1
   2. vwap_reversal        Return: -4.26%, Sharpe: -0.28, Drawdown: -4.26%, Trades: 2
   3. breakout             Return: -7.40%, Sharpe: -0.28, Drawdown: -7.40%, Trades: 2
   4. mean_reversion       Return: -11.77%, Sharpe: -0.28, Drawdown: -11.77%, Trades: 2
   5. trend_following      Return: -14.82%, Sharpe: -0.28, Drawdown: -14.82%, Trades: 2
   6. scalping             Return: -15.15%, Sharpe: -0.28, Drawdown: -15.15%, Trades: 2
   7. crypto_breakout      Return: -17.13%, Sharpe: -0.28, Drawdown: -17.13%, Trades: 2
