#!/usr/bin/env python3
"""Approved-symbols sync CLI: rebuilds the venue's liquid tradable universe.

Owns process I/O (.env loading, arguments, exit code); the rule and file handling live in
``runner_sync_approved_symbols`` (see its docstring). Scheduled daily by
scripts/launchd/com.lynxion.approved-symbols-sync.plist.

Usage: python interface/cli/sync_approved_symbols.py [--dry-run]
"""

import argparse
import os
import sys
from typing import List, Optional

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

import runner_sync_approved_symbols as _runner  # noqa: E402


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true", help="print the list, write nothing")
    args = ap.parse_args(argv)
    try:
        from dotenv import load_dotenv
        load_dotenv(os.path.join(ROOT, ".env"))       # DEFAULT_BROKER / UNIVERSE_* (process env wins)
    except ImportError:
        pass
    return _runner.sync(dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
