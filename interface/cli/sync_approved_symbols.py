#!/usr/bin/env python3
"""Approved-symbols sync CLI shell (E2.T3).

Entry point for refreshing the approved-symbols list from the exchange API.
Unlike the other data/sync runners, this job has no domain ports to inject
(it performs a direct HTTP fetch and writes JSON), so there is no composition
root to wire — the CLI simply owns process I/O and delegates the fetch/update
logic to the existing ``runner_sync_approved_symbols`` helpers. Behavior and
file paths are preserved byte-identically.
"""

import os
import sys
from typing import List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import runner_sync_approved_symbols as _runner


def main(argv: Optional[List[str]] = None) -> int:
    print("🚀 Fetching BingX perpetual futures symbols...")

    symbols = _runner.fetch_available_symbols()

    if not symbols:
        print("❌ No symbols fetched. Exiting.")
        return 1

    print(f"\n🎯 Total perpetual symbols fetched: {len(symbols)}")

    # Resolve paths relative to the runner module so output locations stay
    # byte-identical to the legacy entry point.
    runner_root = os.path.dirname(os.path.abspath(_runner.__file__))
    symbols_file_path = os.path.join(
        runner_root, "application", "configs", "approved_symbols.json"
    )

    success = _runner.update_approved_symbols_file(symbols, symbols_file_path)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
