The research and audit phases are now complete.

From this point onward, stop producing strategic reports.

You are now responsible for executing the approved R&D roadmap one milestone at a time.

Current milestone:
Priority 0 – Backtest Engine Certification and Short Execution Fix.

Objectives:

1. Fix the verified short-position tracking bug in realistic_backtester.py.
2. Certify the backtest engine for production-grade quantitative research.

Do not implement any new trading strategies.

Do not modify strategy logic.

Do not optimize parameters.

Tasks:

- Fix short position lifecycle management.
- Ensure long/short execution parity.
- Validate stop-loss and take-profit execution for short positions.
- Validate PnL calculations for long and short trades.
- Validate equity curve calculations.
- Validate fee and slippage application.
- Verify deterministic reproducibility.
- Add regression tests covering every identified bug.
- Produce a Backtest Engine Certification Report.

The report must include:

- Fixed defects
- Remaining limitations
- Test coverage
- Mathematical validation
- Before vs. after comparison
- Residual risks
- Certification decision (PASS / FAIL)

Do not proceed to Priority 1 or any other roadmap item until this milestone is fully completed and validated.