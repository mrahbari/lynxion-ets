#!/usr/bin/env python3
"""Deterministic, read-only TASK-0153 stop-visibility attribution."""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
from typing import Any


DEFAULT_ROOT = Path("data/observability/forward_exit")


def attribute(root: Path | str = DEFAULT_ROOT) -> dict[str, Any]:
    event_root = Path(root) / "events"
    events = [
        json.loads(line)
        for path in sorted(event_root.glob("*.jsonl"))
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    by_cause: dict[str, list[dict[str, Any]]] = {}
    for event in events:
        if event.get("causal_event_id"):
            by_cause.setdefault(event["causal_event_id"], []).append(event)

    cells = Counter()
    summary = Counter()
    requests = [event for event in events if event.get("event_type") == "STOP_REPLACE_REQUESTED"]
    for request in requests:
        responses = [event for event in by_cause.get(request["event_id"], [])
                     if event.get("event_type") == "STOP_REPLACE_RESPONDED"]
        if len(responses) != 1:
            response_outcome, visibility_outcome = "MISSING_OR_AMBIGUOUS", "NOT_APPLICABLE"
        else:
            response = responses[0]
            response_outcome = "ACCEPTED" if response.get("accepted") else "REJECTED"
            visibility = [event for event in by_cause.get(response["event_id"], [])
                          if event.get("event_type") in {
                              "STOP_VISIBILITY_VERIFIED", "STOP_VISIBILITY_FAILED"
                          }]
            if response_outcome == "REJECTED":
                visibility_outcome = "NOT_APPLICABLE"
            elif len(visibility) != 1:
                visibility_outcome = "MISSING_OR_AMBIGUOUS"
            elif visibility[0]["event_type"] == "STOP_VISIBILITY_VERIFIED":
                visibility_outcome = "VERIFIED"
            else:
                visibility_outcome = "FAILED"
        key = (request["symbol"], int(request["attempt"]), response_outcome, visibility_outcome)
        cells[key] += 1
        summary[response_outcome.lower()] += 1
        summary[f"visibility_{visibility_outcome.lower()}"] += 1

    return {
        "schema_version": 1,
        "request_count": len(requests),
        "summary": dict(sorted(summary.items())),
        "cells": [
            {
                "symbol": key[0], "attempt": key[1], "response": key[2],
                "visibility": key[3], "count": count,
            }
            for key, count in sorted(cells.items())
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    args = parser.parse_args()
    print(json.dumps(attribute(args.root), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
