#!/usr/bin/env python3
"""Report C-35 signal collection pace without opening outcome economics."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from scripts.record_c35_decision import read_decisions
    from scripts.update_c35_signals import _load_panel, verify_decision_bindings
    from scripts.verify_c35_candle_ledger import verify_path
    from scripts.verify_c35_signal_ledger import verify as verify_signals
except ModuleNotFoundError:  # Direct `python scripts/...` execution.
    from record_c35_decision import read_decisions
    from update_c35_signals import _load_panel, verify_decision_bindings
    from verify_c35_candle_ledger import verify_path
    from verify_c35_signal_ledger import verify as verify_signals


FIRST_CHECKPOINT = 168
TARGET_OUTCOMES = 240


def throughput(decisions: dict[int, dict[str, Any]], events: list[dict[str, Any]]) -> dict[str, Any]:
    signals = [row for row in events if row.get("kind") == "SIGNAL"]
    hours = len(decisions)
    signals_per_day = len(signals) * 24 / hours if hours else 0.0
    projected_days = TARGET_OUTCOMES / signals_per_day if signals_per_day > 0 else None
    return {
        "candidate": "C-35",
        "verdict": "COLLECTING",
        "aggregate_economics": "SEALED",
        "decision_hours": hours,
        "signals": len(signals),
        "signals_per_day": signals_per_day,
        "projected_days_to_240_at_observed_rate": projected_days,
        "first_rate_checkpoint_due": hours >= FIRST_CHECKPOINT,
        "next_rate_checkpoint_decisions": FIRST_CHECKPOINT if hours < FIRST_CHECKPOINT else None,
    }


def _events(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("data/research/c35"))
    args = parser.parse_args()
    root = args.root
    candle_path = root / "candles.jsonl"
    verify_path(candle_path)
    panel = _load_panel(candle_path)
    decisions = read_decisions(root / "decisions.jsonl")
    verify_decision_bindings(panel, decisions)
    events = _events(root / "signals.jsonl")
    verify_signals(events)
    print(json.dumps(throughput(decisions, events), sort_keys=True))


if __name__ == "__main__":
    main()
