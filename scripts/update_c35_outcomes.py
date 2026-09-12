#!/usr/bin/env python3
"""Resolve mature C-35 signals while keeping aggregate economics sealed."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

try:
    from scripts.record_c35_signal import _read_state, append_outcome
    from scripts.resolve_c35_outcome import resolve_outcome
    from scripts.verify_c35_candle_ledger import verify_path as verify_candles
    from scripts.verify_c35_funding_ledger import verify as verify_funding
    from scripts.verify_c35_signal_ledger import verify as verify_signals
except ModuleNotFoundError:  # Direct `python scripts/...` execution.
    from record_c35_signal import _read_state, append_outcome
    from resolve_c35_outcome import resolve_outcome
    from verify_c35_candle_ledger import verify_path as verify_candles
    from verify_c35_funding_ledger import verify as verify_funding
    from verify_c35_signal_ledger import verify as verify_signals


def _jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _funding_covered(coverage: list[dict[str, Any]], symbol: str, entry: int, exit_: int) -> bool:
    return any(
        row.get("symbol") == symbol
        and row.get("status") == "COMPLETE_PUBLIC_RESPONSE"
        and int(row["requested_start_ms"]) <= (entry + 1) * 1000
        and int(row["requested_end_ms"]) >= exit_ * 1000
        for row in coverage
    )


def find_resolvable(
    signal_events: list[dict[str, Any]],
    candles: list[dict[str, Any]],
    funding: list[dict[str, Any]],
    coverage: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    signals = {row["signal_key"]: row for row in signal_events if row.get("kind") == "SIGNAL"}
    resolved = {row["signal_key"] for row in signal_events if row.get("kind") == "OUTCOME"}
    candles_by_symbol: dict[str, list[dict[str, Any]]] = defaultdict(list)
    funding_by_symbol: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in candles:
        candles_by_symbol[row["symbol"]].append(row)
    for row in funding:
        funding_by_symbol[row["symbol"]].append(row)
    outcomes = []
    for key, signal in sorted(signals.items(), key=lambda item: int(item[1]["decision_time"])):
        if key in resolved:
            continue
        symbol = signal["symbol"]
        entry, exit_ = int(signal["entry_open_time"]), int(signal["exit_open_time"])
        if not any(int(row["open_time"]) == exit_ for row in candles_by_symbol[symbol]):
            continue
        if not _funding_covered(coverage, symbol, entry, exit_):
            continue
        outcomes.append(resolve_outcome(
            signal,
            candles_by_symbol[symbol],
            funding_by_symbol[symbol],
            funding_coverage_complete=True,
        ))
    return outcomes


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default="data/research/c35")
    parser.add_argument("--commit-outcomes", action="store_true")
    args = parser.parse_args()
    root = Path(args.root)
    candle_path = root / "candles.jsonl"
    funding = _jsonl(root / "funding.jsonl")
    coverage = _jsonl(root / "funding_coverage.jsonl")
    verify_candles(candle_path)
    verify_funding(funding, coverage)
    signal_path = root / "signals.jsonl"
    events = _jsonl(signal_path)
    verify_signals(events)
    signals, resolved = _read_state(signal_path)
    outcomes = find_resolvable(events, _jsonl(candle_path), funding, coverage)
    appended = 0
    if args.commit_outcomes:
        for outcome in outcomes:
            appended += append_outcome(signal_path, outcome)
    print(json.dumps({
        "candidate": "C-35",
        "aggregate_economics": "SEALED",
        "signals": len(signals),
        "previously_completed_outcomes": len(resolved),
        "newly_resolvable_outcomes": len(outcomes),
        "outcomes_appended": appended,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
