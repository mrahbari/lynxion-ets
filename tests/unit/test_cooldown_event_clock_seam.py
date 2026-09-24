from datetime import datetime, timedelta, timezone

from infrastructure.messaging.clock import LiveClock, ReplayClock
from infrastructure.risk.symbol_cooldown_gate import SymbolCooldownGate


def test_explicit_cooldown_gate_uses_replay_clock_and_isolated_journal(tmp_path):
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    clock = ReplayClock(start)
    gate = SymbolCooldownGate(
        journal_path=str(tmp_path / "cooldown.json"),
        trade_journal_path=str(tmp_path / "trades.csv"),
        clock=clock,
    )
    gate.record_stop_loss_exit("BTCUSDT")
    allowed, reason = gate.is_symbol_allowed("BTCUSDT")
    assert not allowed and "Cooldown" in reason
    clock.advance(start + timedelta(minutes=61))
    allowed, reason = gate.is_symbol_allowed("BTCUSDT")
    assert allowed and reason == "ALLOWED"


def test_live_default_clock_type_with_explicit_temp_paths(tmp_path):
    gate = SymbolCooldownGate(
        journal_path=str(tmp_path / "cooldown.json"),
        trade_journal_path=str(tmp_path / "trades.csv"),
    )
    assert isinstance(gate._clock, LiveClock)
