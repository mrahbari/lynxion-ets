import json
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock

from domain.entities import ExecutionIntent, FusedSignal
from domain.enums.order_side import OrderSide
from domain.enums.signal_type import SignalType
from domain.value_objects import Money, Percentage, Symbol
from infrastructure.execution.signal_census_journal import SignalCensusJournal


def test_records_point_in_time_accepted_decision(tmp_path):
    signal = FusedSignal(
        symbol=Symbol("BTCUSDT"), dominant_bias=SignalType.BUY, direction=0.7,
        dominance_score=0.8, regime_context="trending_up", confidence=Percentage(Decimal("0.8")),
        timestamp=datetime(2026, 8, 13, tzinfo=timezone.utc),
        metadata={"current_price": 100.0, "atr": 2.0, "timeframe": "1m", "watcher_name": "trend"},
    )
    intent = ExecutionIntent(
        symbol=Symbol("BTCUSDT"), strategy_name="trend_following", side=OrderSide.BUY,
        intent_confidence=Percentage(Decimal("0.85")), risk_parameters={}, timestamp=signal.timestamp,
    )
    intent.stop_loss_price = Money(Decimal("95"), "USDT")
    intent.take_profit_price = Money(Decimal("110"), "USDT")
    path = tmp_path / "census.jsonl"

    SignalCensusJournal(str(path)).record("trend_following", signal, "ACCEPTED", "intent emitted", intent)

    row = json.loads(path.read_text().strip())
    assert row["decision"] == "ACCEPTED"
    assert row["regime"] == "trending_up"
    assert row["expected_reward_risk"] == 2.0
    assert row["stop_loss"] == "95"
    assert row["take_profit"] == "110"


def test_disabled_strategy_rejection_is_censused_without_changing_outcome(monkeypatch):
    from infrastructure.execution.signal_census_journal import signal_census_journal
    from infrastructure.strategies.strategy_adapters import BaseStrategyAdapter, StrategyConfig

    signal = FusedSignal(
        symbol=Symbol("BTCUSDT"), dominant_bias=SignalType.BUY, direction=0.7,
        dominance_score=0.8, regime_context="trending_up", confidence=Percentage(Decimal("0.8")),
        timestamp=datetime.now(timezone.utc), metadata={},
    )
    record = MagicMock()
    monkeypatch.setattr(signal_census_journal, "record", record)
    monkeypatch.setattr(StrategyConfig, "get_strategy_enabled", lambda _: False)

    assert BaseStrategyAdapter("test_census").evaluate_fused_signal(signal) is None
    record.assert_called_once_with("test_census", signal, "REJECTED", "strategy disabled", None)
