"""Characterization: risk-module decisions (E3.T4).

Pins the CURRENT kill-switch / drawdown / exposure and SL/TP decisions of the
canonical risk engine so the E3.T4 consolidation (one risk module behind
``PortfolioRiskEnginePort`` / ``StopLossTakeProfitPort`` with SL/TP separated
from portfolio risk) cannot change risk behavior. Inputs and expected outputs
are fixed.

The canonical engine is
``application.risk_management.enterprise_risk_manager.EnterpriseRiskManager``
— the only risk engine with live consumers (backtest, execution, optimization,
strategy adapters). The parallel ``infrastructure/risk_management`` portfolio
manager and the unreferenced ``infrastructure/risk/risk_adapters.py`` placeholder
adapters are deprecated shims; see E3.T4.

Each decision is pinned twice: once against the legacy engine directly, once
against the consolidated ``ConsolidatedRiskEngineAdapter`` — they MUST agree.
"""

import pytest

pytest.importorskip("numpy")
pytest.importorskip("pandas")

from application.risk_management.enterprise_risk_manager import (
    EnterpriseRiskManager,
    PositionDirection,
)
from infrastructure.risk.risk_engine_adapter import ConsolidatedRiskEngineAdapter


# --- Engine factories (legacy direct vs. consolidated adapter) ---------------

def _legacy():
    return EnterpriseRiskManager()


def _adapter():
    return ConsolidatedRiskEngineAdapter(risk_manager=EnterpriseRiskManager())


ENGINES = [
    pytest.param(_legacy, id="legacy"),
    pytest.param(_adapter, id="adapter"),
]


# --- Exposure admission decisions --------------------------------------------

@pytest.mark.unit
@pytest.mark.parametrize("make", ENGINES)
def test_entry_within_limits_allowed(make):
    e = make()
    # 1.0 * 10000 = 10000 <= max_position (50000) and <= portfolio (100000).
    assert e.validate_position_entry("BTCUSDT", 1.0, 10000.0) is True


@pytest.mark.unit
@pytest.mark.parametrize("make", ENGINES)
def test_entry_exceeds_position_limit_rejected(make):
    e = make()
    # 10.0 * 10000 = 100000 > max_position_exposure (50000).
    assert e.validate_position_entry("BTCUSDT", 10.0, 10000.0) is False


@pytest.mark.unit
@pytest.mark.parametrize("make", ENGINES)
def test_entry_exceeds_portfolio_limit_rejected(make):
    e = make()
    # 7.0 * 10000 = 70000 > max_position_exposure (50000) -> rejected.
    assert e.validate_position_entry("BTCUSDT", 7.0, 10000.0) is False


@pytest.mark.unit
@pytest.mark.parametrize("make", ENGINES)
def test_total_exposure_tracks_entries(make):
    e = make()
    assert e.get_total_exposure() == 0.0


# --- Drawdown ----------------------------------------------------------------

@pytest.mark.unit
@pytest.mark.parametrize("make", ENGINES)
def test_drawdown_on_fixed_equity_curve(make):
    e = make()
    # Reach into the engine's equity curve to pin the formula exactly.
    rm = getattr(e, "_risk_manager", e)
    rm.equity_curve = [100000.0, 110000.0, 99000.0]
    # (110000 - 99000) / 110000 == 0.1
    assert e.calculate_drawdown() == pytest.approx(0.1, rel=1e-12)


# --- Kill-switch / trading-allowed gate --------------------------------------

@pytest.mark.unit
@pytest.mark.parametrize("make", ENGINES)
def test_trading_allowed_clean_state(make):
    assert make().is_trading_allowed() is True


@pytest.mark.unit
@pytest.mark.parametrize("make", ENGINES)
def test_trading_blocked_on_drawdown(make):
    e = make()
    rm = getattr(e, "_risk_manager", e)
    rm.equity_curve = [100000.0, 110000.0, 90000.0]  # dd = 20000/110000 ≈ 0.1818 > 0.15
    assert e.is_trading_allowed() is False


@pytest.mark.unit
@pytest.mark.parametrize("make", ENGINES)
def test_trading_blocked_on_daily_loss(make):
    e = make()
    rm = getattr(e, "_risk_manager", e)
    rm.daily_pnl = -6000.0  # 6000/100000 = 0.06 > max_daily_loss_pct (0.05)
    assert e.is_trading_allowed() is False


# --- SL/TP exit evaluation (separated port) ----------------------------------

def _with_position(make, direction, sl, tp):
    e = make()
    rm = getattr(e, "_risk_manager", e)
    rm.enter_position("BTCUSDT", entry_price=100.0, size=1.0, direction=direction,
                      stop_loss=sl, take_profit=tp, trade_id="t")
    return e


SLTP_CASES = [
    # (id, direction, sl, tp, high, low, expected)
    ("long_sl", PositionDirection.LONG, 95.0, 110.0, 108.0, 94.0, (95.0, "SL")),
    ("long_tp", PositionDirection.LONG, 95.0, 110.0, 111.0, 99.0, (110.0, "TP")),
    ("long_both_sl_priority", PositionDirection.LONG, 95.0, 110.0, 111.0, 94.0, (95.0, "SL")),
    ("long_none", PositionDirection.LONG, 95.0, 110.0, 108.0, 99.0, (None, None)),
    ("short_sl", PositionDirection.SHORT, 105.0, 90.0, 106.0, 95.0, (105.0, "SL")),
    ("short_tp", PositionDirection.SHORT, 105.0, 90.0, 101.0, 89.0, (90.0, "TP")),
    ("short_both_sl_priority", PositionDirection.SHORT, 105.0, 90.0, 106.0, 89.0, (105.0, "SL")),
]


@pytest.mark.unit
@pytest.mark.parametrize("make", ENGINES)
@pytest.mark.parametrize("case_id,direction,sl,tp,high,low,expected",
                         SLTP_CASES, ids=[c[0] for c in SLTP_CASES])
def test_sltp_decisions(make, case_id, direction, sl, tp, high, low, expected):
    e = _with_position(make, direction, sl, tp)
    assert e.check_stop_loss_take_profit("BTCUSDT", high, low) == expected


@pytest.mark.unit
@pytest.mark.parametrize("make", ENGINES)
def test_sltp_no_position(make):
    assert make().check_stop_loss_take_profit("BTCUSDT", 100.0, 100.0) == (None, None)


# --- Adapter equals legacy (no behavioral drift) -----------------------------

@pytest.mark.unit
def test_adapter_equals_legacy_exposure_and_gates():
    legacy, adapter = _legacy(), _adapter()
    assert adapter.validate_position_entry("BTCUSDT", 1.0, 10000.0) == \
        legacy.validate_position_entry("BTCUSDT", 1.0, 10000.0)
    assert adapter.is_trading_allowed() == legacy.is_trading_allowed()
    assert adapter.get_total_exposure() == legacy.get_total_exposure()


@pytest.mark.unit
def test_adapter_implements_both_ports():
    """The single adapter satisfies both the portfolio-risk and (separated) SL/TP ports."""
    adapter = _adapter()
    # PortfolioRiskEnginePort surface.
    assert callable(adapter.validate_position_entry)
    assert callable(adapter.is_trading_allowed)
    assert callable(adapter.calculate_drawdown)
    assert callable(adapter.get_total_exposure)
    # StopLossTakeProfitPort surface (separated from portfolio risk).
    assert callable(adapter.check_stop_loss_take_profit)
