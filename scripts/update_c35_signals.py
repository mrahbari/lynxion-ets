#!/usr/bin/env python3
"""Evaluate verified C-35 candles and optionally append the first virtual signal."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable

try:
    from scripts.evaluate_c35_compression_release import BOUNDARY_EPOCH, UNIVERSE, evaluate_decision
    from scripts.record_c35_signal import append_signal
    from scripts.verify_c35_candle_ledger import verify_path
except ModuleNotFoundError:  # Direct `python scripts/...` execution.
    from evaluate_c35_compression_release import BOUNDARY_EPOCH, UNIVERSE, evaluate_decision
    from record_c35_signal import append_signal
    from verify_c35_candle_ledger import verify_path


def _load_panel(path: Path) -> dict[str, list[dict[str, Any]]]:
    panel: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for line in path.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        panel[row["symbol"]].append(row)
    for rows in panel.values():
        rows.sort(key=lambda row: int(row["open_time"]))
    return dict(panel)


def _decision_times(panel: dict[str, list[dict[str, Any]]]) -> list[int]:
    available = None
    for symbol in UNIVERSE:
        symbol_times = {
            int(row["open_time"]) + 900 for row in panel.get(symbol, [])
            if int(row["open_time"]) > BOUNDARY_EPOCH and (int(row["open_time"]) + 900) % 3600 == 0
        }
        available = symbol_times if available is None else available & symbol_times
    return sorted(available or ())


def _input_hash(panel: dict[str, list[dict[str, Any]]], decision_time: int) -> str:
    causal = {
        symbol: [row for row in panel[symbol] if int(row["open_time"]) <= decision_time - 900][-2898:]
        for symbol in UNIVERSE
    }
    encoded = json.dumps(causal, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def find_first_signal(
    panel: dict[str, list[dict[str, Any]]],
    *,
    evaluator: Callable[..., dict[str, Any] | None] = evaluate_decision,
) -> tuple[dict[str, Any] | None, str | None]:
    for decision_time in _decision_times(panel):
        signal = evaluator(panel, decision_time, boundary=BOUNDARY_EPOCH)
        if signal is not None:
            return signal, _input_hash(panel, decision_time)
    return None, None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candles", default="data/research/c35/candles.jsonl")
    parser.add_argument("--signals", default="data/research/c35/signals.jsonl")
    parser.add_argument("--commit-signal", action="store_true")
    args = parser.parse_args()
    candle_path = Path(args.candles)
    integrity = verify_path(candle_path)
    panel = _load_panel(candle_path)
    signal, input_hash = find_first_signal(panel)
    appended = False
    if signal is not None and args.commit_signal:
        appended = append_signal(Path(args.signals), signal, input_sha256=str(input_hash))
    print(json.dumps({
        "integrity": integrity["integrity"],
        "decision_count": len(_decision_times(panel)),
        "signal_found": signal is not None,
        "signal_appended": appended,
        "signal": signal,
        "input_sha256": input_hash,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
