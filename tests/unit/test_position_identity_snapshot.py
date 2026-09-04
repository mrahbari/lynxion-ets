from copy import deepcopy
from datetime import datetime, timedelta, timezone

import pytest

from infrastructure.observability.position_identity_snapshot import (
    PositionIdentityError,
    PositionIdentitySnapshot,
    deterministic_record_id,
)


def record(position_key="BTCUSDT:LONG:100", first="2026-09-04T00:00:00+00:00"):
    value = {
        "schema_version": 1,
        "record_id": "",
        "position_key": position_key,
        "symbol": "BTCUSDT",
        "side": "LONG",
        "entry_price": 100.0,
        "quantity": 1.0,
        "exchange_leverage": 5.0,
        "first_observed_utc": first,
        "last_observed_utc": first,
        "observer_run_id": "run-1",
        "exchange_position_id": None,
        "exchange_order_id": None,
        "lifecycle_state": "OPEN",
    }
    value["record_id"] = deterministic_record_id(position_key, "run-1", first)
    return value


def test_atomic_snapshot_round_trip_and_deterministic_validation(tmp_path):
    snapshot = PositionIdentitySnapshot(tmp_path / "identities.json")
    path = snapshot.upsert(record())
    first = snapshot.validate_file()
    second = snapshot.validate_file()
    assert path.exists()
    assert first == second
    assert first["records"] == 1
    assert not list(tmp_path.glob("*.tmp.*"))


def test_lifecycle_advances_but_identity_and_time_cannot_regress(tmp_path):
    snapshot = PositionIdentitySnapshot(tmp_path / "identities.json")
    original = record()
    snapshot.upsert(original)
    advanced = deepcopy(original)
    advanced["lifecycle_state"] = "CLOSURE_OBSERVED"
    advanced["last_observed_utc"] = "2026-09-04T00:01:00+00:00"
    snapshot.upsert(advanced)
    with pytest.raises(PositionIdentityError, match="lifecycle regression"):
        snapshot.upsert(original)
    changed = deepcopy(advanced)
    changed["entry_price"] = 101.0
    with pytest.raises(PositionIdentityError, match="immutable"):
        snapshot.upsert(changed)


def test_corruption_sensitive_fields_and_non_deterministic_id_fail(tmp_path):
    path = tmp_path / "identities.json"
    path.write_text("not-json", encoding="utf-8")
    with pytest.raises(PositionIdentityError, match="corrupt"):
        PositionIdentitySnapshot(path).validate_file()
    bad = record()
    bad["metadata"] = {"api_key": "forbidden"}
    with pytest.raises(PositionIdentityError, match="sensitive"):
        PositionIdentitySnapshot.validate_record(bad)
    bad = record()
    bad["record_id"] = "invented"
    with pytest.raises(PositionIdentityError, match="deterministic"):
        PositionIdentitySnapshot.validate_record(bad)


def test_ambiguous_symbol_side_resolution_fails_closed(tmp_path):
    snapshot = PositionIdentitySnapshot(tmp_path / "identities.json")
    snapshot.upsert(record())
    snapshot.upsert(record(position_key="BTCUSDT:LONG:101", first="2026-09-04T00:02:00+00:00"))
    with pytest.raises(PositionIdentityError, match="ambiguous"):
        snapshot.resolve_open("BTCUSDT", "LONG")


def test_unique_open_identity_resolves_without_mutation(tmp_path):
    snapshot = PositionIdentitySnapshot(tmp_path / "identities.json")
    expected = record()
    snapshot.upsert(expected)
    resolved = snapshot.resolve_open("BTCUSDT", "LONG")
    assert resolved == expected
    resolved["quantity"] = 99.0
    assert snapshot.resolve_open("BTCUSDT", "LONG")["quantity"] == 1.0
