import json

from infrastructure.execution.broker_reconciliation import (
    ACTIVE_POSITIONS_JOURNAL_PATH, BrokerReconciliationService,
)


def test_explicit_active_position_journals_are_isolated(tmp_path):
    left_path = tmp_path / "left.json"
    right_path = tmp_path / "right.json"
    left_path.write_text(json.dumps({"active_symbols": ["BTCUSDT"]}), encoding="utf-8")
    left = BrokerReconciliationService(
        halt_fn=lambda _: None, active_positions_journal_path=str(left_path),
    )
    right = BrokerReconciliationService(
        halt_fn=lambda _: None, active_positions_journal_path=str(right_path),
    )
    assert left._previous_active_symbols == {"BTCUSDT"}
    assert right._previous_active_symbols == set()
    right._previous_active_symbols.add("ETHUSDT")
    right._save_active_symbols()
    assert json.loads(right_path.read_text(encoding="utf-8")) == {
        "active_symbols": ["ETHUSDT"],
    }
    assert json.loads(left_path.read_text(encoding="utf-8")) == {
        "active_symbols": ["BTCUSDT"],
    }


def test_live_default_journal_path_is_preserved():
    service = BrokerReconciliationService(halt_fn=lambda _: None)
    assert service._active_positions_journal_path == ACTIVE_POSITIONS_JOURNAL_PATH
