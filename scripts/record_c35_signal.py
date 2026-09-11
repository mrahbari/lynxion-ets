#!/usr/bin/env python3
"""Append a verified C-35 virtual signal without any execution capability."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from scripts.evaluate_c35_compression_release import BOUNDARY_EPOCH, INTERVAL_SECONDS, UNIVERSE


def _read_state(path: Path) -> tuple[set[str], set[str]]:
    signals: set[str] = set()
    outcomes: set[str] = set()
    if not path.exists():
        return signals, outcomes
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid signal ledger line {number}") from exc
        key = str(row.get("signal_key") or "")
        if row.get("kind") == "SIGNAL":
            if not key or key in signals:
                raise ValueError(f"duplicate or missing signal at line {number}")
            signals.add(key)
        elif row.get("kind") == "OUTCOME":
            if key not in signals or key in outcomes:
                raise ValueError(f"orphan or duplicate outcome at line {number}")
            outcomes.add(key)
        else:
            raise ValueError(f"unknown signal-ledger event at line {number}")
    return signals, outcomes


def append_signal(path: Path, signal: dict[str, Any], *, input_sha256: str) -> bool:
    if signal.get("candidate") != "C-35" or signal.get("symbol") not in UNIVERSE:
        raise ValueError("signal identity outside frozen C-35 contract")
    decision_time = int(signal.get("decision_time", -1))
    decision_open = int(signal.get("decision_bar_open", -1))
    entry_open = int(signal.get("entry_open_time", -1))
    exit_open = int(signal.get("exit_open_time", -1))
    if decision_time % 3600 or decision_open != decision_time - INTERVAL_SECONDS:
        raise ValueError("invalid C-35 decision timing")
    if decision_open <= BOUNDARY_EPOCH or entry_open != decision_time or exit_open != decision_time + 8 * INTERVAL_SECONDS:
        raise ValueError("invalid C-35 boundary or virtual schedule")
    if signal.get("side") not in {"LONG", "SHORT"}:
        raise ValueError("invalid C-35 side")
    if len(input_sha256) != 64 or any(char not in "0123456789abcdef" for char in input_sha256):
        raise ValueError("invalid C-35 input hash")
    key = f"{signal['symbol']}:{decision_time}"
    signals, outcomes = _read_state(path)
    if key in signals:
        return False
    unresolved = signals - outcomes
    if unresolved:
        raise ValueError("unresolved portfolio signal already exists")
    event = {
        "kind": "SIGNAL",
        "signal_key": key,
        "input_sha256": input_sha256,
        **signal,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as target:
        target.write(json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n")
        target.flush()
        os.fsync(target.fileno())
    return True
