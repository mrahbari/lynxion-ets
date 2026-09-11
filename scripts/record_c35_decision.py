#!/usr/bin/env python3
"""Append the result of one causal C-35 decision evaluation."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

try:
    from scripts.evaluate_c35_compression_release import BOUNDARY_EPOCH, INTERVAL_SECONDS, UNIVERSE
except ModuleNotFoundError:  # Direct `python scripts/...` execution.
    from evaluate_c35_compression_release import BOUNDARY_EPOCH, INTERVAL_SECONDS, UNIVERSE


def read_decisions(path: Path) -> dict[int, dict[str, Any]]:
    decisions = {}
    if not path.exists():
        return decisions
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        try:
            row = json.loads(line)
            decision_time = int(row["decision_time"])
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"invalid C-35 decision line {number}") from exc
        if row.get("kind") != "DECISION" or row.get("candidate") != "C-35":
            raise ValueError(f"invalid C-35 decision identity at line {number}")
        if decision_time in decisions:
            raise ValueError(f"duplicate C-35 decision at line {number}")
        decisions[decision_time] = row
    return decisions


def append_decision(
    path: Path,
    *,
    decision_time: int,
    input_sha256: str,
    signal: dict[str, Any] | None,
) -> bool:
    if decision_time % 3600 or decision_time - INTERVAL_SECONDS <= BOUNDARY_EPOCH:
        raise ValueError("invalid C-35 decision boundary or timing")
    if len(input_sha256) != 64 or any(char not in "0123456789abcdef" for char in input_sha256):
        raise ValueError("invalid C-35 decision input hash")
    decisions = read_decisions(path)
    if decision_time in decisions:
        return False
    selected = None
    if signal is not None:
        if signal.get("candidate") != "C-35" or signal.get("symbol") not in UNIVERSE:
            raise ValueError("invalid C-35 selected signal")
        if int(signal.get("decision_time", -1)) != decision_time:
            raise ValueError("C-35 selected signal time mismatch")
        selected = {key: signal[key] for key in (
            "symbol", "side", "decision_normalized_true_range", "compression_median",
            "compression_threshold", "entry_open_time", "exit_open_time",
        )}
    event = {
        "kind": "DECISION",
        "candidate": "C-35",
        "decision_time": decision_time,
        "input_sha256": input_sha256,
        "verdict": "SIGNAL" if selected else "NO_SIGNAL",
        "selected": selected,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as target:
        target.write(json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n")
        target.flush()
        os.fsync(target.fileno())
    return True
