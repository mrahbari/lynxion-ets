#!/usr/bin/env python3
"""
Multi-timeframe Update Runner - thin entry point (E2.T4b - Composition Root Hardening).

Orchestration and validation now live in
``application.use_cases.sync_market_data.SyncMarketDataUseCase``. This module only
owns the canonical CLI ``main()`` shim plus an application-only symbol helper
(kept here for backward-compatible imports). It imports no infrastructure and
constructs no adapters directly.
"""
import os
import sys
from typing import List

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Add project root to path to import modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from application.symbol_management.centralized_symbol_manager import get_approved_symbols


def load_symbols_from_env() -> List[str]:
    """Load symbols from the centralized symbol manager."""
    # Use ALL approved symbols for multi-timeframe update, not just unified subset
    return list(get_approved_symbols())


def main():
    """Backward-compatible entry point.

    Argument parsing, composition-root wiring, and process I/O live in
    :mod:`interface.cli.multitimeframe_update`. This shim delegates so existing
    invocations keep working unchanged while the canonical path runs through the
    container-wired ``SyncMarketDataUseCase``.
    """
    from interface.cli.multitimeframe_update import main as cli_main
    return cli_main()


if __name__ == "__main__":
    exit(main())
