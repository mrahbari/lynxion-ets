#!/usr/bin/env python3
"""Fail closed on malformed C-35 signal/outcome ledger state."""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from typing import Any

try:
    from scripts.evaluate_c35_compression_release import BOUNDARY_EPOCH, INTERVAL_SECONDS, UNIVERSE
except ModuleNotFoundError:  # Direct `python scripts/...` execution.
    from evaluate_c35_compression_release import BOUNDARY_EPOCH, INTERVAL_SECONDS, UNIVERSE


SHA256 = re.compile(r"[0-9a-f]{64}")


def verify(events: list[dict[str, Any]]) -> dict[str, Any]:
    signals: dict[str, dict[str, Any]] = {}
    outcomes: set[str] = set()
    for number, row in enumerate(events, 1):
        kind = row.get("kind")
        key = str(row.get("signal_key") or "")
        if kind == "SIGNAL":
            decision = int(row.get("decision_time", -1))
            if (
                row.get("candidate") != "C-35"
                or row.get("symbol") not in UNIVERSE
                or row.get("side") not in {"LONG", "SHORT"}
                or key != f"{row.get('symbol')}:{decision}"
                or key in signals
            ):
                raise ValueError(f"invalid signal identity at line {number}")
            if (
                decision % 3600
                or int(row.get("decision_bar_open", -1)) != decision - INTERVAL_SECONDS
                or int(row.get("entry_open_time", -1)) != decision
                or int(row.get("exit_open_time", -1)) != decision + 8 * INTERVAL_SECONDS
                or decision - INTERVAL_SECONDS <= BOUNDARY_EPOCH
            ):
                raise ValueError(f"invalid signal schedule at line {number}")
            if not SHA256.fullmatch(str(row.get("input_sha256") or "")):
                raise ValueError(f"invalid signal provenance at line {number}")
            signals[key] = row
        elif kind == "OUTCOME":
            signal = signals.get(key)
            if signal is None or key in outcomes:
                raise ValueError(f"orphan or duplicate outcome at line {number}")
            identity_fields = ("candidate", "symbol", "side", "entry_open_time", "exit_open_time")
            if any(row.get(field) != signal.get(field) for field in identity_fields):
                raise ValueError(f"outcome identity mismatch at line {number}")
            numeric = (
                "entry_price", "exit_price", "gross_return", "funding_return",
                "net_return_primary_0_30pct", "net_return_sensitivity_0_20pct",
                "net_return_stress_0_50pct",
            )
            if row.get("status") != "COMPLETE" or not SHA256.fullmatch(str(row.get("evidence_sha256") or "")):
                raise ValueError(f"invalid outcome completion evidence at line {number}")
            if any(
                not isinstance(row.get(field), (int, float))
                or isinstance(row.get(field), bool)
                or not math.isfinite(float(row[field]))
                for field in numeric
            ):
                raise ValueError(f"invalid outcome numeric evidence at line {number}")
            if float(row["entry_price"]) <= 0 or float(row["exit_price"]) <= 0:
                raise ValueError(f"invalid outcome fill at line {number}")
            outcomes.add(key)
        else:
            raise ValueError(f"unknown signal-ledger event at line {number}")
    return {
        "candidate": "C-35",
        "integrity": "PASS",
        "signals": len(signals),
        "completed_outcomes": len(outcomes),
        "unresolved_signals": len(set(signals) - outcomes),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", type=Path, default=Path("data/research/c35/signals.jsonl"))
    args = parser.parse_args()
    events = []
    if args.ledger.exists():
        events = [json.loads(line) for line in args.ledger.read_text(encoding="utf-8").splitlines()]
    print(json.dumps(verify(events), sort_keys=True))


if __name__ == "__main__":
    main()
