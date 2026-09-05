import json

from infrastructure.observability.position_identity_snapshot import (
    PositionIdentitySnapshot,
    deterministic_record_id,
)
from scripts.audit_forward_exit_cohort import audit, evaluate_gates


def _manifest(root, boundary="2026-09-05T00:00:00+00:00"):
    root.mkdir(parents=True, exist_ok=True)
    (root / "activation.json").write_text(json.dumps({
        "schema_version": 1,
        "run_id": "run-1",
        "activation_boundary_utc": boundary,
        "commit": "abc123",
        "historical_import_allowed": False,
    }))


def _identity(root, state="OPEN", terminal_order_id=None):
    first = "2026-09-05T00:01:00+00:00"
    record = {
        "schema_version": 1,
        "record_id": deterministic_record_id("BTCUSDT:LONG:100", "run-1", first),
        "position_key": "BTCUSDT:LONG:100",
        "symbol": "BTCUSDT",
        "side": "LONG",
        "entry_price": 100.0,
        "quantity": 1.0,
        "exchange_leverage": 10.0,
        "first_observed_utc": first,
        "last_observed_utc": first,
        "observer_run_id": "run-1",
        "exchange_position_id": None,
        "exchange_order_id": None,
        "lifecycle_state": state,
    }
    if terminal_order_id is not None:
        record["terminal_order_id"] = terminal_order_id
    PositionIdentitySnapshot(root / "position_identities.json").upsert(record)


def _event(root, *, event_time="2026-09-05T00:02:00+00:00", run_id="run-1"):
    event = {
        "schema_version": 1, "event_id": "event-1", "event_type": "POSITION_OBSERVED",
        "event_time_utc": event_time, "run_id": run_id, "evaluation_id": "eval-1",
        "position_key": "BTCUSDT:LONG:100", "symbol": "BTCUSDT", "side": "LONG",
        "quantity": 1.0, "entry_price": 100.0, "current_price": 101.0,
        "price_source": "broker", "configured_leverage": None, "requested_leverage": None,
        "exchange_leverage": 10.0, "roe_pct": 10.0, "peak_price": 101.0,
        "peak_roe_pct": 10.0, "manager_state_before": None, "manager_state_after": None,
        "error": None,
    }
    path = root / "events" / "2026-09-05.jsonl"
    path.parent.mkdir()
    path.write_text(json.dumps(event) + "\n")


def _write_events(root, events):
    path = root / "events" / "2026-09-05.jsonl"
    path.parent.mkdir(exist_ok=True)
    path.write_text("".join(json.dumps(event) + "\n" for event in events))


def _base_event(event_id, event_type, minute, **extra):
    event = {
        "schema_version": 1, "event_id": event_id, "event_type": event_type,
        "event_time_utc": f"2026-09-05T00:{minute:02d}:00+00:00", "run_id": "run-1",
        "evaluation_id": "eval-1", "position_key": "BTCUSDT:LONG:100",
        "symbol": "BTCUSDT", "side": "LONG", "quantity": 1.0, "entry_price": 100.0,
        "current_price": 101.0, "price_source": "broker", "configured_leverage": None,
        "requested_leverage": None, "exchange_leverage": 10.0, "roe_pct": 10.0,
        "peak_price": 101.0, "peak_roe_pct": 10.0, "manager_state_before": None,
        "manager_state_after": None, "error": None,
    }
    event.update(extra)
    return event


def test_valid_partial_cohort_is_collecting(tmp_path):
    _manifest(tmp_path)
    _identity(tmp_path)
    _event(tmp_path)
    report = audit(tmp_path)
    assert report["verdict"] == "COLLECTING"
    assert report["counts"]["identities"] == 1
    assert report["counts"]["event_types"] == {"POSITION_OBSERVED": 1}
    assert report["violations"] == {}


def test_pre_boundary_event_is_data_invalid(tmp_path):
    _manifest(tmp_path)
    _event(tmp_path, event_time="2026-09-05T00:00:00+00:00")
    report = audit(tmp_path)
    assert report["verdict"] == "DATA_INVALID"
    assert report["violations"]["pre_boundary_events"] == 1


def test_foreign_run_event_is_data_invalid(tmp_path):
    _manifest(tmp_path)
    _event(tmp_path, run_id="run-2")
    report = audit(tmp_path)
    assert report["verdict"] == "DATA_INVALID"
    assert report["violations"]["foreign_run_events"] == 1


def test_corrupt_manifest_fails_closed(tmp_path):
    tmp_path.mkdir(exist_ok=True)
    (tmp_path / "activation.json").write_text("not-json")
    report = audit(tmp_path)
    assert report["verdict"] == "DATA_INVALID"
    assert report["violations"]["manifest_invalid"] == 1


def test_stop_chain_counts_complete_failed_and_rejected_paths(tmp_path):
    _manifest(tmp_path)
    events = [
        _base_event("r1", "STOP_REPLACE_REQUESTED", 1, requested_stop_price=101.0, attempt=1),
        _base_event("p1", "STOP_REPLACE_RESPONDED", 2, causal_event_id="r1", accepted=True),
        _base_event("v1", "STOP_VISIBILITY_VERIFIED", 3, causal_event_id="p1", visible_stop_price=101.0),
        _base_event("c1", "STATE_COMMITTED", 4, causal_event_id="v1", causal_event_type="STOP_VISIBILITY_VERIFIED"),
        _base_event("r2", "STOP_REPLACE_REQUESTED", 5, requested_stop_price=102.0, attempt=1),
        _base_event("p2", "STOP_REPLACE_RESPONDED", 6, causal_event_id="r2", accepted=True),
        _base_event("v2", "STOP_VISIBILITY_FAILED", 7, causal_event_id="p2", mismatch_reason="not visible"),
        _base_event("r3", "STOP_REPLACE_REQUESTED", 8, requested_stop_price=103.0, attempt=1),
        _base_event("p3", "STOP_REPLACE_RESPONDED", 9, causal_event_id="r3", accepted=False),
    ]
    _write_events(tmp_path, events)
    report = audit(tmp_path)
    assert report["verdict"] == "COLLECTING"
    assert report["stop_chains"] == {
        "accepted_responses": 2,
        "complete": 1,
        "rejected_responses": 1,
        "requests": 3,
        "visibility_failed": 1,
        "visibility_verified": 1,
    }


def test_terminal_coverage_preserves_incomplete_fields_and_trailing_eligibility(tmp_path):
    _manifest(tmp_path)
    _identity(tmp_path, state="TERMINAL_EVIDENCE_COMPLETE", terminal_order_id="order-1")
    observed = _base_event("o1", "POSITION_OBSERVED", 1, manager_thresholds={
        "trailing_trigger_roe_pct": 10.0,
    }, peak_roe_pct=12.0)
    terminal = _base_event(
        "x1", "EXIT_FILL_OBSERVED", 2, exit_order_type="STOP_MARKET",
        fill_price=101.0, fill_quantity=1.0, realized_pnl=1.0, fees=None,
        fill_time_utc="2026-09-05T00:02:00+00:00",
    )
    _write_events(tmp_path, [observed, terminal])
    report = audit(tmp_path)
    assert report["counts"]["completed_identities"] == 1
    assert report["counts"]["trailing_eligible_completed"] == 1
    assert report["counts"]["completed_utc_weeks"] == ["2026-W36"]
    assert report["counts"]["exit_types"] == {"STOP_MARKET": 1}
    assert report["terminal_completeness"] == {
        "linked": 1,
        "authoritative_fields_complete": 0,
        "linkage_pct": 1.0,
        "authoritative_fields_pct": 0.0,
    }


def test_frozen_gate_thresholds_are_exact_and_only_then_eligible():
    counts = {
        "completed_identities": 100,
        "trailing_eligible_completed": 30,
        "completed_utc_weeks": [f"2026-W{week:02d}" for week in range(1, 9)],
        "completed_by_symbol": {symbol: 20 for symbol in ("A", "B", "C", "D", "E")},
        "completed_by_side": {"LONG": 85, "SHORT": 15},
    }
    terminal = {"linkage_pct": 0.95, "authoritative_fields_pct": 0.90}
    chains = {"visibility_verified": 4, "complete": 4}
    assert all(evaluate_gates(counts, terminal, chains).values())

    counts["completed_by_side"]["SHORT"] = 14
    gates = evaluate_gates(counts, terminal, chains)
    assert gates["minimum_short_completed"] is False
    assert sum(gates.values()) == len(gates) - 1


def test_duplicate_sensitive_unknown_cause_and_lifecycle_regression_are_explicit(tmp_path):
    _manifest(tmp_path)
    events = [
        _base_event("same", "POSITION_OBSERVED", 1),
        _base_event("same", "POSITION_OBSERVED", 2),
        _base_event("secret", "POSITION_OBSERVED", 3, api_key="forbidden"),
        _base_event("unknown", "STOP_REPLACE_RESPONDED", 4,
                    causal_event_id="missing", accepted=True),
        _base_event("closed", "EXIT_FILL_OBSERVED", 5, manager_state_after="CLOSURE_OBSERVED",
                    exit_order_type="STOP_MARKET", fill_price=None, fill_quantity=None),
        _base_event("reopened", "POSITION_OBSERVED", 6, manager_state_after="OPEN"),
    ]
    _write_events(tmp_path, events)
    report = audit(tmp_path)
    assert report["verdict"] == "DATA_INVALID"
    assert report["violations"] == {
        "duplicate_event_ids": 1,
        "lifecycle_regressions": 1,
        "sensitive_field_violations": 1,
        "unknown_causal_references": 1,
    }


def test_audit_is_read_only_and_deterministic(tmp_path):
    _manifest(tmp_path)
    _identity(tmp_path)
    _event(tmp_path)
    before = {path: path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}
    first = audit(tmp_path)
    second = audit(tmp_path)
    after = {path: path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}
    assert first == second
    assert before == after
