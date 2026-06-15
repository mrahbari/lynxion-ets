#!/usr/bin/env python3
"""
Extended Horizon Validation Runner - Execute long-term backtesting across
multiple horizons (180, 360, 720 days) to test alpha durability and regime
stability.

E2.T4 strangler migration: argument parsing, composition-root wiring, and
process I/O now live in :mod:`interface.cli.extended_horizon_validation`, and all
orchestration logic lives in
:class:`application.use_cases.validate_portfolio.ValidatePortfolioUseCase`. This
module is now a thin backward-compatible shim that delegates so existing
``python runner_extended_horizon_validation.py`` invocations keep working
unchanged.
"""
import os
import sys

# Add project root to path to import modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    """Backward-compatible entry point delegating to the container-wired CLI."""
    from interface.cli.extended_horizon_validation import main as cli_main
    return cli_main()


if __name__ == "__main__":
    exit(main())
