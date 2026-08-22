"""Generate a read-only prospective edge report from the trade journal."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Permit direct ``python scripts/...`` execution from any working directory.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from infrastructure.monitoring.prospective_edge_monitor import generate_prospective_edge_report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cohort-start", required=True, help="ISO-8601 UTC deployment boundary")
    parser.add_argument("--journal", default="data/trade_journal.csv")
    parser.add_argument("--output", default="data/reports/prospective_edge_report.json")
    args = parser.parse_args()
    report = generate_prospective_edge_report(args.journal, args.cohort_start, args.output)
    print(json.dumps({"verdict": report["verdict"], "output": args.output}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
