#!/usr/bin/env python3
"""
Walk-Forward Runner - Execute walk-forward optimization and analysis.

E2.T4 strangler migration: argument parsing, composition-root wiring, and
process I/O now live in :mod:`interface.cli.walkforward`, and all orchestration
logic lives in :class:`application.use_cases.run_walkforward.RunWalkforwardUseCase`.
This module is now a thin backward-compatible shim that delegates so existing
``python runner_walkforward.py`` invocations keep working unchanged.
"""
import os
import sys

# Add project root to path to import modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    """Backward-compatible entry point delegating to the container-wired CLI."""
    from interface.cli.walkforward import main as cli_main
    return cli_main()


if __name__ == "__main__":
    exit(main())
