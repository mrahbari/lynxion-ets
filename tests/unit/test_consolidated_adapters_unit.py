"""E6.T5 — Unit pyramid backfill for consolidated infra adapters (risk, engines).

Targets previously-untested infrastructure that was consolidated in E3. Both
adapters under test are thin delegators that receive their collaborator by
constructor injection, so they are exercised here with **port fakes** — no real
risk engine, no signal engine, no I/O. The tests pin the adapter's contract:
arguments are forwarded unchanged and return values are passed back unchanged
(the E3 "decisions preserved byte-for-byte" guarantee at the seam).
"""

from __future__ import annotations

import pytest

from infrastructure.risk.risk_engine_adapter import ConsolidatedRiskEngineAdapter
from infrastructure.engines.engine_port_adapter import EngineServiceAdapter


class _FakeRiskManager:
    """In-memory stand-in for EnterpriseRiskManager — records calls, no I/O."""

    def __init__(self):
        self.calls: list[tuple] = []
        self.entry_ok = True
        self.trading_allowed = True
        self.drawdown = 0.12
        self.exposure = 1234.5
        self.sltp_result = (101.5, "take_profit")

    def validate_position_entry(self, symbol, size, entry_price):
        self.calls.append(("validate_position_entry", symbol, size, entry_price))
        return self.entry_ok

    def is_trading_allowed(self):
        self.calls.append(("is_trading_allowed",))
        return self.trading_allowed

    def calculate_drawdown(self):
        self.calls.append(("calculate_drawdown",))
        return self.drawdown

    def get_total_exposure(self):
        self.calls.append(("get_total_exposure",))
        return self.exposure

    def check_stop_loss_take_profit(self, symbol, candle_high, candle_low):
        self.calls.append(("check_stop_loss_take_profit", symbol, candle_high, candle_low))
        return self.sltp_result


@pytest.mark.unit
def test_risk_adapter_forwards_and_returns_portfolio_decisions():
    fake = _FakeRiskManager()
    adapter = ConsolidatedRiskEngineAdapter(risk_manager=fake)

    assert adapter.validate_position_entry("BTC/USDT", 2.0, 50.0) is True
    assert adapter.is_trading_allowed() is True
    assert adapter.calculate_drawdown() == 0.12
    assert adapter.get_total_exposure() == 1234.5

    assert fake.calls == [
        ("validate_position_entry", "BTC/USDT", 2.0, 50.0),
        ("is_trading_allowed",),
        ("calculate_drawdown",),
        ("get_total_exposure",),
    ]


@pytest.mark.unit
def test_risk_adapter_forwards_sltp_tuple_unchanged():
    fake = _FakeRiskManager()
    fake.sltp_result = (None, None)
    adapter = ConsolidatedRiskEngineAdapter(risk_manager=fake)

    assert adapter.check_stop_loss_take_profit("ETH/USDT", 110.0, 90.0) == (None, None)
    assert fake.calls[-1] == ("check_stop_loss_take_profit", "ETH/USDT", 110.0, 90.0)

    fake.sltp_result = (105.0, "stop_loss")
    assert adapter.check_stop_loss_take_profit("ETH/USDT", 120.0, 100.0) == (105.0, "stop_loss")


@pytest.mark.unit
def test_risk_adapter_reflects_negative_decisions():
    fake = _FakeRiskManager()
    fake.entry_ok = False
    fake.trading_allowed = False
    adapter = ConsolidatedRiskEngineAdapter(risk_manager=fake)

    assert adapter.validate_position_entry("BTC/USDT", 99.0, 70000.0) is False
    assert adapter.is_trading_allowed() is False


class _FakeEngineService:
    """Records the observation it was handed and returns a canned signal."""

    def __init__(self, signal):
        self.signal = signal
        self.seen: list[object] = []

    def process_observation(self, observation):
        self.seen.append(observation)
        return self.signal


@pytest.mark.unit
def test_engine_adapter_delegates_observation_and_returns_signal():
    sentinel_signal = object()
    fake = _FakeEngineService(sentinel_signal)
    adapter = EngineServiceAdapter(fake)

    observation = object()  # opaque payload; the adapter only forwards it
    result = adapter.process_observation(observation)

    assert result is sentinel_signal
    assert fake.seen == [observation]


@pytest.mark.unit
def test_engine_adapter_returns_none_when_service_returns_none():
    fake = _FakeEngineService(None)
    adapter = EngineServiceAdapter(fake)
    assert adapter.process_observation(object()) is None
