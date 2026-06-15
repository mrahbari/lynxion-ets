#!/usr/bin/env python3
"""
Comprehensive Portfolio Backtest Runner - Execute advanced multi-strategy,
multi-symbol backtesting with portfolio-level risk management and strategy
selection.

E2.T4 strangler migration: argument parsing, composition-root wiring, and
process I/O now live in :mod:`interface.cli.comprehensive_portfolio_backtest`,
and all orchestration logic lives in
:class:`application.use_cases.validate_portfolio.ValidatePortfolioUseCase`. This
module is now a thin backward-compatible shim that delegates so existing
``python runner_comprehensive_portfolio_backtest.py`` invocations keep working
unchanged.
"""
import os
import sys

# Add project root to path to import modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    """Backward-compatible entry point delegating to the container-wired CLI."""
    from interface.cli.comprehensive_portfolio_backtest import main as cli_main
    return cli_main()


if __name__ == "__main__":
    exit(main())
