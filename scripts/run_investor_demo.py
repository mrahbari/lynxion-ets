#!/usr/bin/env python3
"""Run the broker-free Lynxion investor execution-safety demonstration."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()

    os.environ["BROKER_PAPER_TRADING"] = "true"
    os.environ.pop("LIVE_TRADING", None)
    banner = {
        "broker_execution_enabled": False,
        "evidence_class": "DETERMINISTIC_VST_SHADOW_DEMO",
        "mode": "PAPER",
        "network_enabled": False,
        "profitability_claim": False,
    }
    print(f"LYNXION_INVESTOR_DEMO {json.dumps(banner, sort_keys=True)}", file=sys.stderr)

    from scripts.phase10_paper_trading_burst import main as run_scenario
    return run_scenario()


if __name__ == "__main__":
    raise SystemExit(main())
