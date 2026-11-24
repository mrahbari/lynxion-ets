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
    assert meta["regime"] == "ranging" and meta["signal_ts"] == "2026-11-24T10:00:00"


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
