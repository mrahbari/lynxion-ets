#!/usr/bin/env python3
"""
Resync Runner - thin entry point (E2.T4b - Composition Root Hardening).

The full resync orchestration (downloader -> timeframes -> retune) now lives in
``application.use_cases.sync_market_data.SyncMarketDataUseCase``. This module only
owns the canonical CLI ``main()`` shim; it imports no infrastructure and
constructs no adapters directly.
"""
import os
import sys

# Add project root to path to import modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    """Backward-compatible entry point.

    Argument parsing, composition-root wiring, and process I/O live in
    :mod:`interface.cli.resync`. This shim delegates so existing invocations keep
    working unchanged while the canonical path runs through the container-wired
    ``SyncMarketDataUseCase``.
    """
    from interface.cli.resync import main as cli_main
    return cli_main()


if __name__ == "__main__":
    exit(main())
