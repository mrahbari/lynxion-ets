"""Optional, runtime-disabled manager identity capture for TASK-0144."""

from infrastructure.observability.position_identity_snapshot import PositionIdentitySnapshot
from tests.unit.test_task0137_exit_observer import _position


class PositionBroker:
    def __init__(self):
        self.position_calls = 0

    def get_all_positions(self):
        self.position_calls += 1
        return [_position(price=100.0)]


def test_disabled_identity_capture_preserves_evaluation_and_creates_no_file(tmp_path):
    from infrastructure.risk.active_position_manager import ActivePositionManager

    path = tmp_path / "identities.json"
    broker = PositionBroker()
    manager = ActivePositionManager()

    assert manager.evaluate_open_positions(broker) == []
    assert broker.position_calls == 1
    assert manager.identity_store_failures == 0
    assert not path.exists()


def test_enabled_capture_creates_one_deterministic_authoritative_open_identity(tmp_path):
    from infrastructure.risk.active_position_manager import ActivePositionManager

    snapshot = PositionIdentitySnapshot(tmp_path / "identities.json")
    broker = PositionBroker()
    manager = ActivePositionManager(
        position_identity_store=snapshot,
        observer_run_id="identity-run",
    )

    assert manager.evaluate_open_positions(broker) == []
    report = snapshot.validate_file()
    identity = snapshot.resolve_open("BTCUSDT", "LONG")
    assert report["records"] == 1
    assert identity["position_key"] == "BTCUSDT:LONG:100"
    assert identity["entry_price"] == 100.0
    assert identity["quantity"] == 1.0
    assert identity["exchange_leverage"] == 5.0
    assert identity["observer_run_id"] == "identity-run"
    assert identity["lifecycle_state"] == "OPEN"


def test_repeated_capture_advances_time_without_duplicate(tmp_path):
    from infrastructure.risk.active_position_manager import ActivePositionManager

    snapshot = PositionIdentitySnapshot(tmp_path / "identities.json")
    broker = PositionBroker()
    manager = ActivePositionManager(
        position_identity_store=snapshot,
        observer_run_id="identity-run",
    )

    manager.evaluate_open_positions(broker)
    first = snapshot.resolve_open("BTCUSDT", "LONG")
    manager.evaluate_open_positions(broker)
    second = snapshot.resolve_open("BTCUSDT", "LONG")
    assert snapshot.validate_file()["records"] == 1
    assert second["record_id"] == first["record_id"]
    assert second["first_observed_utc"] == first["first_observed_utc"]
    assert second["last_observed_utc"] >= first["last_observed_utc"]


def test_corrupt_store_failure_isolated_from_manager_decision(tmp_path):
    from infrastructure.risk.active_position_manager import ActivePositionManager

    path = tmp_path / "identities.json"
    path.write_text("not-json", encoding="utf-8")
    broker = PositionBroker()
    manager = ActivePositionManager(
        position_identity_store=PositionIdentitySnapshot(path),
        observer_run_id="identity-run",
    )

    assert manager.evaluate_open_positions(broker) == []
    assert broker.position_calls == 1
    assert manager.identity_store_failures == 1
    assert path.read_text(encoding="utf-8") == "not-json"


def test_conflicting_open_identity_isolated_from_manager_decision(tmp_path):
    from infrastructure.risk.active_position_manager import ActivePositionManager

    snapshot = PositionIdentitySnapshot(tmp_path / "identities.json")
    broker = PositionBroker()
    ActivePositionManager(
        position_identity_store=snapshot,
        observer_run_id="prior-run",
    ).evaluate_open_positions(broker)
    manager = ActivePositionManager(
        position_identity_store=snapshot,
        observer_run_id="current-run",
    )

    assert manager.evaluate_open_positions(broker) == []
    assert broker.position_calls == 2
    assert manager.identity_store_failures == 1
    assert snapshot.validate_file()["records"] == 1


def test_store_write_failure_does_not_change_manager_decision():
    from infrastructure.risk.active_position_manager import ActivePositionManager

    class BrokenStore:
        @staticmethod
        def resolve_open(symbol, side):
            return None

        @staticmethod
        def upsert(record):
            raise OSError("disk unavailable")

    broker = PositionBroker()
    manager = ActivePositionManager(
        position_identity_store=BrokenStore(),
        observer_run_id="identity-run",
    )

    assert manager.evaluate_open_positions(broker) == []
    assert broker.position_calls == 1
    assert manager.identity_store_failures == 1
