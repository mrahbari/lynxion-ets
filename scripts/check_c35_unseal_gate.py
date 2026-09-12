#!/usr/bin/env python3
"""Check C-35 minimum evidence coverage without opening aggregate economics."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from scripts.verify_c35_signal_ledger import verify as verify_signal_ledger
except ModuleNotFoundError:  # Direct `python scripts/...` execution.
    from verify_c35_signal_ledger import verify as verify_signal_ledger


MIN_POSITIONS = 240
MIN_SIDE_POSITIONS = 80
MIN_SYMBOL_POSITIONS = 30
MIN_QUALIFYING_SYMBOLS = 4
MIN_UTC_WEEKS = 8


def _utc_week(epoch: int) -> str:
    iso = datetime.fromtimestamp(epoch, timezone.utc).isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def check(events: list[dict[str, Any]]) -> dict[str, Any]:
    signals: set[str] = set()
    outcomes: dict[str, dict[str, Any]] = {}
    for number, row in enumerate(events, 1):
        key = str(row.get("signal_key") or "")
        if row.get("kind") == "SIGNAL":
            if not key or key in signals:
                raise ValueError(f"duplicate or missing signal at line {number}")
            signals.add(key)
        elif row.get("kind") == "OUTCOME":
            if key not in signals or key in outcomes:
                raise ValueError(f"orphan or duplicate outcome at line {number}")
            if row.get("status") != "COMPLETE" or row.get("side") not in {"LONG", "SHORT"}:
                raise ValueError(f"invalid completed outcome at line {number}")
            outcomes[key] = row
        else:
            raise ValueError(f"unknown signal-ledger event at line {number}")

    side_counts = Counter(row["side"] for row in outcomes.values())
    symbol_counts = Counter(str(row.get("symbol") or "") for row in outcomes.values())
    weeks = sorted({_utc_week(int(row["exit_open_time"])) for row in outcomes.values()})
    qualifying_symbols = sum(count >= MIN_SYMBOL_POSITIONS for count in symbol_counts.values())
    gates = {
        "completed_positions": len(outcomes) >= MIN_POSITIONS,
        "utc_weeks": len(weeks) >= MIN_UTC_WEEKS,
        "long_positions": side_counts["LONG"] >= MIN_SIDE_POSITIONS,
        "short_positions": side_counts["SHORT"] >= MIN_SIDE_POSITIONS,
        "qualifying_symbols": qualifying_symbols >= MIN_QUALIFYING_SYMBOLS,
    }
    ready = all(gates.values())
    return {
        "candidate": "C-35",
        "aggregate_economics": "READY_FOR_FROZEN_EVALUATION" if ready else "SEALED",
        "verdict": "MINIMUM_GATE_MET" if ready else "COLLECTING",
        "completed_positions": len(outcomes),
        "represented_utc_weeks": len(weeks),
        "side_counts": {side: side_counts[side] for side in ("LONG", "SHORT")},
        "symbol_counts": dict(sorted(symbol_counts.items())),
        "symbols_at_or_above_30": qualifying_symbols,
        "minimum_gates": gates,
    }


def check_verified(events: list[dict[str, Any]]) -> dict[str, Any]:
    verify_signal_ledger(events)
    return check(events)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--signals", type=Path, default=Path("data/research/c35/signals.jsonl"))
    args = parser.parse_args()
    events = []
    if args.signals.exists():
        events = [json.loads(line) for line in args.signals.read_text(encoding="utf-8").splitlines()]
    print(json.dumps(check_verified(events), sort_keys=True))


if __name__ == "__main__":
    main()
