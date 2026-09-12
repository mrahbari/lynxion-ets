#!/usr/bin/env python3
"""Run the authorized public-only C-35 hourly pipeline in fail-closed order."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
COMMANDS = (
    ("scripts/verify_c35_activation.py",),
    ("scripts/verify_c35_funding_activation.py",),
    ("scripts/verify_c35_aggregate_activation.py",),
    ("scripts/collect_c35_public_candles.py",),
    ("scripts/collect_c35_public_funding.py",),
    ("scripts/verify_c35_candle_ledger.py", "--ledger", "data/research/c35/candles.jsonl"),
    ("scripts/verify_c35_funding_ledger.py",),
    ("scripts/update_c35_signals.py", "--commit-decisions", "--commit-signal"),
    ("scripts/update_c35_outcomes.py", "--commit-outcomes"),
    ("scripts/evaluate_c35_aggregate.py",),
)


def run_pipeline(
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> dict[str, Any]:
    stages = []
    for parts in COMMANDS:
        command = [sys.executable, *parts]
        result = runner(command, cwd=ROOT, check=False, capture_output=True, text=True)
        if result.returncode:
            raise RuntimeError(f"C-35 hourly stage failed: {parts[0]}: {result.stderr.strip()}")
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"C-35 hourly stage emitted invalid JSON: {parts[0]}") from exc
        stages.append({"stage": parts[0], "result": payload})
    return {"candidate": "C-35", "pipeline": "PASS", "stages": stages}


def main() -> None:
    argparse.ArgumentParser(description=__doc__).parse_args()
    print(json.dumps(run_pipeline(), sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
