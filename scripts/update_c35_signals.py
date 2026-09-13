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
    from scripts.record_c35_decision import append_decision, read_decisions
    from scripts.record_c35_signal import _read_state, append_signal
    from scripts.verify_c35_candle_ledger import verify_path
except ModuleNotFoundError:  # Direct `python scripts/...` execution.
    from evaluate_c35_compression_release import BOUNDARY_EPOCH, UNIVERSE, evaluate_decision
    from record_c35_decision import append_decision, read_decisions
    from record_c35_signal import _read_state, append_signal
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


def verify_decision_bindings(
    panel: dict[str, list[dict[str, Any]]],
    decisions: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    available = set(_decision_times(panel))
    for decision_time, row in decisions.items():
        if decision_time not in available:
            raise ValueError(f"C-35 decision {decision_time} no longer has complete candle inputs")
        if _input_hash(panel, decision_time) != row["input_sha256"]:
            raise ValueError(f"C-35 decision {decision_time} candle hash mismatch")
    return {"candidate": "C-35", "decision_bindings": len(decisions), "integrity": "PASS"}


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


def evaluate_unrecorded(
    panel: dict[str, list[dict[str, Any]]],
    recorded_times: set[int],
    *,
    evaluator: Callable[..., dict[str, Any] | None] = evaluate_decision,
) -> list[tuple[int, dict[str, Any] | None, str]]:
    results = []
    for decision_time in _decision_times(panel):
        if decision_time in recorded_times:
            continue
        signal = evaluator(panel, decision_time, boundary=BOUNDARY_EPOCH)
        results.append((decision_time, signal, _input_hash(panel, decision_time)))
        if signal is not None:
            break
    return results


def unresolved_signal_keys(path: Path) -> set[str]:
    signals, outcomes = _read_state(path)
    return signals - outcomes


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candles", default="data/research/c35/candles.jsonl")
    parser.add_argument("--decisions", default="data/research/c35/decisions.jsonl")
    parser.add_argument("--signals", default="data/research/c35/signals.jsonl")
    parser.add_argument("--commit-decisions", action="store_true")
    parser.add_argument("--commit-signal", action="store_true")
    args = parser.parse_args()
    candle_path = Path(args.candles)
    integrity = verify_path(candle_path)
    panel = _load_panel(candle_path)
    decision_path = Path(args.decisions)
    recorded = read_decisions(decision_path)
    verify_decision_bindings(panel, recorded)
    unresolved = unresolved_signal_keys(Path(args.signals))
    if unresolved:
        print(json.dumps({
            "integrity": integrity["integrity"],
            "decision_count": len(_decision_times(panel)),
            "previously_recorded_decisions": len(recorded),
            "newly_evaluated_decisions": 0,
            "decisions_appended": 0,
            "signal_found": False,
            "signal_appended": False,
            "signal": None,
            "input_sha256": None,
            "blocked_by_unresolved_signal": sorted(unresolved),
        }, sort_keys=True))
        return
    evaluated = evaluate_unrecorded(panel, set(recorded))
    signal = next((item[1] for item in evaluated if item[1] is not None), None)
    input_hash = next((item[2] for item in evaluated if item[1] is not None), None)
    signal_appended = False
    decisions_appended = 0
    for decision_time, result, digest in evaluated:
        if result is not None:
            if args.commit_signal:
                signal_appended = append_signal(Path(args.signals), result, input_sha256=digest)
                decisions_appended += append_decision(
                    decision_path, decision_time=decision_time, input_sha256=digest, signal=result
                )
            break
        if args.commit_decisions or args.commit_signal:
            decisions_appended += append_decision(
                decision_path, decision_time=decision_time, input_sha256=digest, signal=None
            )
    print(json.dumps({
        "integrity": integrity["integrity"],
        "decision_count": len(_decision_times(panel)),
        "previously_recorded_decisions": len(recorded),
        "newly_evaluated_decisions": len(evaluated),
        "decisions_appended": decisions_appended,
        "signal_found": signal is not None,
        "signal_appended": signal_appended,
        "signal": signal,
        "input_sha256": input_hash,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
