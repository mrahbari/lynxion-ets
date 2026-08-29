#!/usr/bin/env python3
"""Read-only derived-state report for the append-only live-order journal."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from infrastructure.execution.live_order_journal import LiveOrderJournal


def build_report(path: str) -> Dict[str, Any]:
    """Return current lifecycle state without writing to the supplied journal."""
    journal = LiveOrderJournal(path)
    recovered = journal.recover()
    in_flight = recovered["in_flight"]
    return {
        "journal_path": str(Path(path)),
        "unique_orders": recovered["total_orders"],
        "status_counts": recovered["status_counts"],
        "in_flight_count": len(in_flight),
        "in_flight_without_order_id": sum(not order.get("order_id") for order in in_flight),
        "order_exchange_map_count": len(recovered["order_exchange_map"]),
        "net_positions": {symbol: str(quantity) for symbol, quantity in journal.net_positions().items()},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--journal",
        default="data/live_order_journal.json",
        help="Path to the JSONL live-order journal (default: %(default)s)",
    )
    args = parser.parse_args()
    print(json.dumps(build_report(args.journal), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
