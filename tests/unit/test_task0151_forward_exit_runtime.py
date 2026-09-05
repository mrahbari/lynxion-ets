import json
from datetime import datetime, timedelta, timezone

import pytest

from infrastructure.observability.forward_exit_runtime import (
    ForwardExitRuntimeBundle,
    build_forward_exit_runtime_bundle,
)


def _event(event_time):
    return {
        "schema_version": 1, "event_id": "event-1", "event_type": "POSITION_OBSERVED",
        "event_time_utc": event_time, "run_id": "run-1", "evaluation_id": "eval-1",
        "position_key": "BTCUSDT:LONG:100", "symbol": "BTCUSDT", "side": "LONG",
        "quantity": 1.0, "entry_price": 100.0, "current_price": 101.0,
        "price_source": "broker", "configured_leverage": None, "requested_leverage": None,
        "exchange_leverage": 5.0, "roe_pct": 5.0, "peak_price": 101.0,
        "peak_roe_pct": 5.0, "manager_state_before": None, "manager_state_after": None,
        "error": None,
    }


def test_runtime_bundle_is_disabled_by_default(monkeypatch):
    monkeypatch.delenv("LYNXION_FORWARD_EXIT_OBSERVER_ENABLED", raising=False)
    assert build_forward_exit_runtime_bundle() is None


def test_bundle_freezes_manifest_and_accepts_only_post_boundary_events(tmp_path):
    boundary = datetime.now(timezone.utc).replace(microsecond=0)
    bundle = ForwardExitRuntimeBundle(tmp_path, "run-1", boundary.isoformat(), "abc123")
    manifest = json.loads((tmp_path / "activation.json").read_text(encoding="utf-8"))
    assert manifest["historical_import_allowed"] is False
    assert manifest["activation_boundary_utc"] == boundary.isoformat()

    with pytest.raises(ValueError, match="strictly after"):
        bundle.observer.append(_event(boundary.isoformat()))
    bundle.observer.append(_event((boundary + timedelta(seconds=1)).isoformat()))
    path = next((tmp_path / "events").glob("*.jsonl"))
    assert bundle.ledger.validate_file(path)["events"] == 1


def test_existing_manifest_must_match_exact_cohort(tmp_path):
    boundary = "2026-09-05T00:00:00+00:00"
    ForwardExitRuntimeBundle(tmp_path, "run-1", boundary, "abc123")
    ForwardExitRuntimeBundle(tmp_path, "run-1", boundary, "abc123")
    with pytest.raises(ValueError, match="conflicts"):
        ForwardExitRuntimeBundle(tmp_path, "run-2", boundary, "abc123")


def test_enabled_environment_requires_frozen_metadata(monkeypatch, tmp_path):
    monkeypatch.setenv("LYNXION_FORWARD_EXIT_OBSERVER_ENABLED", "true")
    monkeypatch.setenv("LYNXION_FORWARD_EXIT_ROOT", str(tmp_path))
    monkeypatch.delenv("LYNXION_FORWARD_EXIT_RUN_ID", raising=False)
    with pytest.raises(KeyError):
        build_forward_exit_runtime_bundle()
