"""Platform review 2026-11-24: regime + signal time reach the INTENT; corrupt SL/TP are not reported."""
from datetime import datetime
from types import SimpleNamespace

from infrastructure.brokers.multi_broker_service import extract_order_journal_metadata
from infrastructure.execution.trade_feature_collector import TradeFeatureCollector


def test_regime_and_signal_time_come_from_the_fused_signal():
    fused = SimpleNamespace(regime_context="ranging", timestamp=datetime(2026, 11, 24, 10, 0, 0))
    intent = SimpleNamespace(fused_signal=fused, metadata={}, risk_parameters={}, strategy_name="TrendFollow",
                             intent_confidence=None)
    order = SimpleNamespace(parent_execution_intent=intent, metadata=None, risk_parameters=None)
    meta = extract_order_journal_metadata(order)
    assert meta["regime"] == "ranging" and meta["signal_ts"].startswith("2026-11-24T10:00:00")
    assert datetime.fromisoformat(meta["signal_ts"]).tzinfo is not None


def test_record_intent_keeps_signal_ts(tmp_path):
    from infrastructure.execution.live_order_journal import LiveOrderJournal
    j = LiveOrderJournal(str(tmp_path / "j.json"))
    ref = j.record_intent("BTCUSDT", "BUY", 1, "bingx", "x1", signal_ts="2026-11-24T10:00:00")
    assert j._orders[ref]["signal_ts"] == "2026-11-24T10:00:00"


def test_cross_symbol_levels_are_rejected():
    ok = TradeFeatureCollector._protection_levels_plausible
    assert ok("2.579", "2.50", "2.75", "BUY")
    assert not ok("2.579", "79.0938", "85.92", "BUY")          # 2026-11-22 EVAA row
    assert not ok("100", "105", "90", "BUY")                    # wrong side
    assert ok("100", "105", "90", "SELL")
    assert ok("100", "", "", "BUY")


def test_signal_price_reaches_the_intent(tmp_path):
    from infrastructure.execution.live_order_journal import LiveOrderJournal
    intent = SimpleNamespace(fused_signal=None, metadata={}, risk_parameters={"trigger_price": 1.2345},
                             strategy_name="VWAPReversal", intent_confidence=None, timestamp=None)
    meta = extract_order_journal_metadata(SimpleNamespace(parent_execution_intent=intent, metadata=None,
                                                          risk_parameters=None))
    assert meta["signal_price"] == 1.2345
    j = LiveOrderJournal(str(tmp_path / "j.json"))
    ref = j.record_intent("BTCUSDT", "BUY", 1, "bingx", "x1", **meta)
    assert j._orders[ref]["signal_price"] == "1.2345"


def test_late_reconstructed_loss_uses_its_exit_time(tmp_path, monkeypatch):
    from datetime import timezone
    from infrastructure.risk.symbol_cooldown_gate import SymbolCooldownGate
    import infrastructure.risk.symbol_cooldown_gate as g
    gate = SymbolCooldownGate(journal_path=str(tmp_path / "cd.json"), trade_journal_path=str(tmp_path / "x.csv"))
    monkeypatch.setattr(g, "symbol_cooldown_gate", gate, raising=False)
    old = datetime(2026, 11, 24, 5, 0, tzinfo=timezone.utc)
    gate.record_stop_loss_exit("AVAXUSDT", old)
    c = TradeFeatureCollector.__new__(TradeFeatureCollector)
    c._recorded_ids, c.csv_path, c.alt_csv_path = set(), str(tmp_path / "t.csv"), None
    c._append_row({"trade_id": "1", "symbol": "AVAXUSDT", "pnl_usdt": "-2.5",
                   "exit_timestamp": old.isoformat(), "is_execution_unwind": "False"})
    assert len(gate._symbol_loss_history["AVAXUSDT"]) == 1     # same exit, not a 2nd loss -> no 24 h lockout


def test_signal_price_comes_from_the_intent_when_order_has_its_own_risk_dict():
    # as built by DecisionPipeline: trigger price in metadata, SL/TP in risk_parameters
    intent = SimpleNamespace(fused_signal=None, metadata={"trigger_price": 2.5},
                             risk_parameters={"stop_loss": 2.4, "take_profit": 2.8},
                             strategy_name="TrendFollow", intent_confidence=None, timestamp=None)
    order = SimpleNamespace(parent_execution_intent=intent, metadata=None,
                            risk_parameters={"stop_loss": 2.4, "take_profit": 2.8})
    assert extract_order_journal_metadata(order)["signal_price"] == 2.5
