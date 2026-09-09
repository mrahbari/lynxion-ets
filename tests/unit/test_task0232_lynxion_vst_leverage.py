from pathlib import Path
from types import SimpleNamespace

import pytest


def test_tracked_lynxion_launcher_pins_both_leverage_ceilings_to_ten():
    launcher = (Path(__file__).resolve().parents[2] / "lynxion").read_text(encoding="utf-8")
    assert "RISK_MAX_LEVERAGE=10" in launcher
    assert "MAX_LEVERAGE=10" in launcher
    assert launcher.index("RISK_MAX_LEVERAGE=10") < launcher.index("python run_trading_system.py")
    assert launcher.index("MAX_LEVERAGE=10") < launcher.index("python run_trading_system.py")


def _position(mark_price):
    return SimpleNamespace(
        symbol="BTCUSDT",
        side=SimpleNamespace(value="BUY"),
        quantity=1.0,
        entry_price=100.0,
        mark_price=mark_price,
        leverage=10.0,
        isolated=True,
    )


def test_default_exit_contract_is_economically_consistent_at_ten_x(monkeypatch):
    """10x must retain the intended 6%/10% ROE profit-protection contract."""
    from infrastructure.risk.active_position_manager import ActivePositionManager

    manager = ActivePositionManager()
    synced = []
    monkeypatch.setattr(
        manager,
        "_sync_sl_to_exchange",
        lambda broker, symbol, is_long, quantity, stop, **kwargs: synced.append(stop) or True,
    )
    broker = SimpleNamespace(get_all_positions=lambda: [_position(100.0)])

    assert manager.evaluate_open_positions(broker) == []

    broker.get_all_positions = lambda: [_position(100.6)]
    breakeven = manager.evaluate_open_positions(broker)
    assert [action["type"] for action in breakeven] == ["BREAKEVEN_ACTIVATED"]
    assert breakeven[0]["roe_pct"] == pytest.approx(6.0)
    assert breakeven[0]["new_sl_price"] == pytest.approx(100.35)

    broker.get_all_positions = lambda: [_position(101.0)]
    trailing = manager.evaluate_open_positions(broker)
    assert [action["type"] for action in trailing] == ["TRAILING_STOP_RATCHET"]
    assert trailing[0]["roe_pct"] == pytest.approx(10.0)
    assert trailing[0]["locked_roe_pct"] == pytest.approx(4.95)
