#!/usr/bin/env python3
"""
Retune Runner - Automated hyperparameter retuning for trading strategies.

E2.T4 strangler migration: argument parsing, composition-root wiring, and
process I/O now live in :mod:`interface.cli.retune`, and all orchestration logic
lives in :class:`application.use_cases.optimize_strategy.OptimizeStrategyUseCase`.
This module is now a thin backward-compatible shim that delegates so existing
``python runner_retune.py`` invocations keep working unchanged.
"""
import os
import sys

# Add project root to path to import modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    """Backward-compatible entry point delegating to the container-wired CLI."""
    from interface.cli.retune import main as cli_main
    return cli_main()


if __name__ == "__main__":
    exit(main())
