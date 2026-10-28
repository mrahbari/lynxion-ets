# TASK-0085: Prospective Validation Cohort #2 Execution Roadmap (N = 100)

> **Status**: IN PROGRESS — Active Live Execution
> **Cohort Lock Timestamp**: `2026-08-17T18:35:00+00:00`
> **Target Sample Size**: $N = 100$ Verified Live Trades
> **Execution Engine**: ActivePositionManager (Breakeven + Dynamic Trailing Stop) + 24h Circuit Breaker Health Gate

---

## 1. Objectives & Validation Gates

Cohort #2 is established to evaluate the strategy under the fully hardened, upgraded production architecture:

1. **Breakeven Protection Validation**: Verify that 100% of trades reaching **+5.0% ROE** (+0.5% price gain @ 10x leverage) never exit in negative territory.
2. **Dynamic Trailing Stop Validation**: Verify that trades reaching **+10.0% ROE** continuously lock in gains by trailing 0.5% behind the peak price.
3. **Execution Realism & Zero Anomaly Invariant**: Ensure zero repeated entry-fail-unwind loops across all 34 perpetual assets.
4. **Target Statistical Thresholds**:
   - **Target Win Rate**: $\ge 50.0\%$
   - **Target Profit Factor**: $\ge 1.40$
   - **Net Realized PnL**: Positive Expectancy ($E > \$0.20 \text{ VST / trade}$)
   - **Max Drawdown Limit**: $\le 10.0\%$

---

## 2. Checkpoint Schedule for Cohort #2

| Checkpoint | Completed Sample ($N$) | Evaluation Focus |
| :--- | :--- | :--- |
| **Checkpoint #1** | $N = 17$ Trades | Initial Trailing Stop / Breakeven Verification & Cooldown Health |
| **Checkpoint #2** | $N = 33$ Trades | Mid-Sample Win Rate & Fee Drag Assessment |
| **Checkpoint #3** | $N = 56$ Trades | Statistical Expectancy & Drawdown Variance Test |
| **Checkpoint #4** | $N = 81$ Trades | Pre-Acceptance Stability & Regime Distribution Audit |
| **Final Acceptance** | $N = 100$ Trades | Formal Live Readiness Sign-Off |

---

## 3. Active Daemon & Observation Infrastructure

- **Production Trading Daemon**: Running autonomously with real-time market data feed (`run_trading_system.py --mode production --auto-detect`).
- **Real-Time Position Management Loop**: 5-second tick loop in `AutoDetectionOrchestrator` calling `ActivePositionManager.evaluate_open_positions()`.
- **Durable Logging**: Every fill, breakeven ratchet, trailing stop exit, and cooldown trigger is appended to `data/trade_journal.csv` and `data/sl_cooldown_journal.json`.
- **Autonomous Progress**: Execution proceeds continuously without human intervention until the 100-trade acceptance gate is achieved.
