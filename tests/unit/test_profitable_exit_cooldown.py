"""Offline regression checks for verified profitable VST position exits."""

from datetime import datetime, timezone
from types import SimpleNamespace

from infrastructure.brokers.adapters.bingx_adapter import BingXBrokerAdapter
from infrastructure.risk.symbol_cooldown_gate import SymbolCooldownGate


def test_bingx_adapter_exposes_formatted_order_history_without_network():
    calls = []
    adapter = object.__new__(BingXBrokerAdapter)
    adapter._broker = SimpleNamespace(
        get_order_history=lambda symbol, limit: (calls.append((symbol, limit)), [{"orderId": "OID"}])[1]
    )

    assert adapter.get_order_history("ADAUSDT", limit=20) == [{"orderId": "OID"}]
    assert calls == [("ADA-USDT", 20)]


def test_verified_profit_clears_existing_lockout_without_spacing(tmp_path):
    gate = SymbolCooldownGate(
        journal_path=str(tmp_path / "cooldown.json"),
        trade_journal_path=str(tmp_path / "trades.csv"),
    )
    now = datetime(2026, 10, 4, 20, 24, tzinfo=timezone.utc)
    gate.record_stop_loss_exit("ADAUSDT", exit_time=now)
    assert "ADAUSDT" in gate._sl_cooldowns

    gate.record_take_profit_exit("ADAUSDT", exit_time=now)

    assert "ADAUSDT" not in gate._sl_cooldowns
    assert gate._symbol_loss_history["ADAUSDT"] == []


def test_repeated_unverified_exits_do_not_create_a_false_24h_loss_breaker(tmp_path):
    gate = SymbolCooldownGate(
        journal_path=str(tmp_path / "cooldown.json"),
        trade_journal_path=str(tmp_path / "trades.csv"),
    )
    now = datetime(2026, 10, 4, 20, 24, tzinfo=timezone.utc)
    gate.record_unverified_exit("ADAUSDT", exit_time=now)
    gate.record_unverified_exit("ADAUSDT", exit_time=now)

    assert gate._symbol_loss_history.get("ADAUSDT") in (None, [])
    assert gate._sl_cooldowns["ADAUSDT"] == now.timestamp() + 3600
