#!/usr/bin/env python3
"""Read-only TASK-0151 forward-exit cohort gate auditor."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from infrastructure.observability.exit_event_ledger import ExitEventLedger
from infrastructure.observability.position_identity_snapshot import PositionIdentitySnapshot


DEFAULT_ROOT = Path("data/observability/forward_exit")
LIFECYCLE_ORDER = {"OPEN": 0, "CLOSURE_OBSERVED": 1, "TERMINAL_EVIDENCE_COMPLETE": 2}


def _utc(value: Any) -> datetime:
    if not isinstance(value, str):
        raise ValueError("timestamp must be an ISO-8601 string")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ValueError("timestamp must be UTC")
    return parsed


def evaluate_gates(counts: dict[str, Any], terminal: dict[str, Any],
                   stop_chains: dict[str, int]) -> dict[str, bool]:
    sides = counts["completed_by_side"]
    return {
        "minimum_completed_identities": counts["completed_identities"] >= 100,
        "minimum_trailing_eligible_completed": counts["trailing_eligible_completed"] >= 30,
        "minimum_completed_utc_weeks": len(counts["completed_utc_weeks"]) >= 8,
        "minimum_completed_symbols": len(counts["completed_by_symbol"]) >= 5,
        "minimum_long_completed": sides.get("LONG", 0) >= 15,
        "minimum_short_completed": sides.get("SHORT", 0) >= 15,
        "terminal_linkage": terminal["linkage_pct"] is not None and terminal["linkage_pct"] >= 0.95,
        "authoritative_terminal_fields": (
            terminal["authoritative_fields_pct"] is not None
            and terminal["authoritative_fields_pct"] >= 0.90
        ),
        "verified_stop_chains_committed": (
            stop_chains.get("complete", 0) == stop_chains.get("visibility_verified", 0)
            and stop_chains.get("verified_missing_or_ambiguous_state_commit", 0) == 0
        ),
    }


def select_verdict(gates: dict[str, bool], violations: dict[str, int]) -> str:
    if sum(violations.values()):
        return "DATA_INVALID"
    if all(gates.values()):
        return "ELIGIBLE_FOR_POLICY_PREREGISTRATION"
    return "COLLECTING"


def audit(root: Path | str = DEFAULT_ROOT) -> dict[str, Any]:
    root = Path(root)
    violations = Counter()
    manifest: dict[str, Any] = {}
    identities: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = []

    try:
        manifest = json.loads((root / "activation.json").read_text(encoding="utf-8"))
        required = {"schema_version", "run_id", "activation_boundary_utc", "commit", "historical_import_allowed"}
        if not required <= set(manifest) or manifest.get("schema_version") != 1:
            raise ValueError("activation manifest is invalid")
        if manifest.get("historical_import_allowed") is not False:
            violations["historical_import_allowed"] += 1
        boundary = _utc(manifest["activation_boundary_utc"])
    except Exception:
        violations["manifest_invalid"] += 1
        boundary = datetime.max.replace(tzinfo=timezone.utc)

    snapshot_path = root / "position_identities.json"
    try:
        PositionIdentitySnapshot(snapshot_path).validate_file()
        if snapshot_path.exists():
            payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
            identities = list(payload["records"].values())
    except Exception as error:
        if "sensitive" in str(error):
            violations["sensitive_field_violations"] += 1
        else:
            violations["snapshot_corrupt"] += 1

    known_ids: set[str] = set()
    previous_time: datetime | None = None
    lifecycle_by_position: dict[str, int] = {}
    for path in sorted((root / "events").glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                event = json.loads(line)
                event_time = _utc(event.get("event_time_utc"))
                ExitEventLedger.validate_event(event, known_ids)
                if event["event_id"] in known_ids:
                    violations["duplicate_event_ids"] += 1
                if previous_time is not None and event_time < previous_time:
                    violations["event_time_regressions"] += 1
                if event_time <= boundary:
                    violations["pre_boundary_events"] += 1
                if manifest and event.get("run_id") != manifest.get("run_id"):
                    violations["foreign_run_events"] += 1
                lifecycle = event.get("manager_state_after")
                if isinstance(lifecycle, str) and lifecycle in LIFECYCLE_ORDER:
                    previous_lifecycle = lifecycle_by_position.get(event["position_key"], -1)
                    if LIFECYCLE_ORDER[lifecycle] < previous_lifecycle:
                        violations["lifecycle_regressions"] += 1
                    lifecycle_by_position[event["position_key"]] = max(
                        previous_lifecycle, LIFECYCLE_ORDER[lifecycle]
                    )
                known_ids.add(event["event_id"])
                previous_time = event_time
                events.append(event)
            except Exception as error:
                message = str(error)
                if "causal_event_id" in message:
                    violations["unknown_causal_references"] += 1
                elif "sensitive" in message:
                    violations["sensitive_field_violations"] += 1
                else:
                    violations["corrupt_events"] += 1

    completed = [item for item in identities if item.get("lifecycle_state") in {
        "CLOSURE_OBSERVED", "TERMINAL_EVIDENCE_COMPLETE"
    }]
    terminal_events = [event for event in events if event.get("event_type") == "EXIT_FILL_OBSERVED"]
    terminal_by_position: dict[str, list[dict[str, Any]]] = {}
    for event in terminal_events:
        terminal_by_position.setdefault(event["position_key"], []).append(event)
    terminal_linked = [item for item in completed if item.get("terminal_order_id") not in (None, "")]
    terminal_fields = ("fill_price", "fill_quantity", "realized_pnl", "fees", "fill_time_utc")
    terminal_complete = [
        item for item in completed
        if any(all(event.get(field) is not None for field in terminal_fields)
               for event in terminal_by_position.get(item["position_key"], []))
    ]
    trailing_eligible = []
    for identity in completed:
        observations = [event for event in events if event.get("position_key") == identity["position_key"]]
        eligible = any(
            isinstance(event.get("manager_thresholds"), dict)
            and isinstance(event.get("peak_roe_pct"), (int, float))
            and event["peak_roe_pct"] >= event["manager_thresholds"].get(
                "trailing_trigger_roe_pct", float("inf")
            )
            for event in observations
        )
        if eligible:
            trailing_eligible.append(identity)
    completed_weeks = sorted({
        f"{stamp.isocalendar().year}-W{stamp.isocalendar().week:02d}"
        for event in terminal_events
        for stamp in [_utc(event.get("fill_time_utc") or event["event_time_utc"])]
    })
    sides = Counter(item.get("side") for item in completed)
    symbols = Counter(item.get("symbol") for item in completed)
    event_types = Counter(item.get("event_type") for item in events)
    exit_types = Counter(event.get("exit_order_type") for event in terminal_events)
    by_cause: dict[str, list[dict[str, Any]]] = {}
    for event in events:
        causal = event.get("causal_event_id")
        if causal:
            by_cause.setdefault(causal, []).append(event)

    chain_counts = Counter()
    requests = [event for event in events if event.get("event_type") == "STOP_REPLACE_REQUESTED"]
    for request in requests:
        chain_counts["requests"] += 1
        responses = [event for event in by_cause.get(request["event_id"], [])
                     if event.get("event_type") == "STOP_REPLACE_RESPONDED"]
        if len(responses) != 1:
            chain_counts["missing_or_ambiguous_response"] += 1
            continue
        response = responses[0]
        if not response.get("accepted"):
            chain_counts["rejected_responses"] += 1
            continue
        chain_counts["accepted_responses"] += 1
        visibility = [event for event in by_cause.get(response["event_id"], [])
                      if event.get("event_type") in {
                          "STOP_VISIBILITY_VERIFIED", "STOP_VISIBILITY_FAILED"
                      }]
        if len(visibility) != 1:
            chain_counts["accepted_missing_or_ambiguous_visibility"] += 1
            continue
        if visibility[0]["event_type"] == "STOP_VISIBILITY_FAILED":
            chain_counts["visibility_failed"] += 1
            continue
        chain_counts["visibility_verified"] += 1
        commits = [event for event in by_cause.get(visibility[0]["event_id"], [])
                   if event.get("event_type") == "STATE_COMMITTED"]
        if len(commits) != 1:
            chain_counts["verified_missing_or_ambiguous_state_commit"] += 1
            continue
        chain_counts["complete"] += 1

    counts = {
        "identities": len(identities),
        "completed_identities": len(completed),
        "trailing_eligible_completed": len(trailing_eligible),
        "completed_utc_weeks": completed_weeks,
        "events": len(events),
        "event_types": dict(sorted(event_types.items())),
        "completed_by_symbol": dict(sorted(symbols.items())),
        "completed_by_side": dict(sorted(sides.items())),
        "exit_types": dict(sorted(exit_types.items())),
        "observer_run_ids": sorted({event.get("run_id") for event in events}),
    }
    terminal = {
        "linked": len(terminal_linked),
        "authoritative_fields_complete": len(terminal_complete),
        "linkage_pct": (len(terminal_linked) / len(completed)) if completed else None,
        "authoritative_fields_pct": (len(terminal_complete) / len(completed)) if completed else None,
    }
    stop_chain_report = dict(sorted(chain_counts.items()))
    gates = evaluate_gates(counts, terminal, stop_chain_report)
    verdict = select_verdict(gates, violations)
    report = {
        "schema_version": 1,
        "manifest": {
            key: manifest.get(key) for key in (
                "run_id", "activation_boundary_utc", "commit", "historical_import_allowed"
            )
        },
        "counts": counts,
        "terminal_completeness": terminal,
        "stop_chains": stop_chain_report,
        "gates": gates,
        "violations": dict(sorted(violations.items())),
        "verdict": verdict,
    }
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    args = parser.parse_args()
    print(json.dumps(audit(args.root), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
