import json

from infrastructure.observability.position_identity_snapshot import (
    PositionIdentitySnapshot,
    deterministic_record_id,
)
from scripts.audit_forward_exit_cohort import audit


def _manifest(root, boundary="2026-09-05T00:00:00+00:00"):
    root.mkdir(parents=True, exist_ok=True)
    (root / "activation.json").write_text(json.dumps({
        "schema_version": 1,
        "run_id": "run-1",
        "activation_boundary_utc": boundary,
        "commit": "abc123",
        "historical_import_allowed": False,
    }))


def _identity(root, state="OPEN"):
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
