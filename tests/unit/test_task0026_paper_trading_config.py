"""
Unit tests for Task 0026 — Paper Trading Configuration Layer & Derivatives Risk Gate.
Verifies configuration schemas, direction_mode signal suppression, risk gate evaluation, and paper safety locks.
"""

import pytest
from pydantic import ValidationError
from application.configs.schemas.strategy import StrategyConfig
from application.configs.schemas.risk import RiskConfig, DerivativesRiskGateConfig
from domain.entities.feature import DerivativesFeatureVector
from infrastructure.risk.derivatives_risk_gate import (
    DerivativesRiskGate,
    RiskGateDecision,
)
from infrastructure.strategies.adapters.mean_reversion_strategy_adapter import (
    MeanReversionStrategyAdapter,
)


def test_strategy_config_direction_mode_defaults():
    """Verify default direction_mode is 'BOTH' and invalid modes raise ValidationError."""
    cfg = StrategyConfig(strategy_name="mean_reversion")
    assert cfg.direction_mode == "BOTH"

    cfg_long = StrategyConfig(strategy_name="mean_reversion", direction_mode="LONG_ONLY")
    assert cfg_long.direction_mode == "LONG_ONLY"

    with pytest.raises(ValidationError):
        StrategyConfig(strategy_name="mean_reversion", direction_mode="INVALID_MODE")


def test_risk_config_derivatives_gate_defaults():
    """Verify default DerivativesRiskGateConfig values and integration into RiskConfig."""
    gate_cfg = DerivativesRiskGateConfig()
    assert gate_cfg.enabled is False
    assert gate_cfg.oi_zscore_hard_block_threshold == 2.0
    assert gate_cfg.oi_zscore_soft_warning_threshold == 1.0
    assert gate_cfg.soft_position_multiplier == 0.5
    assert gate_cfg.lvi_hard_block_threshold == 25.0
    assert gate_cfg.max_daily_drawdown_percent == 3.0

    risk_cfg = RiskConfig(
        max_position_size=1000.0,
        max_drawdown=0.10,
        max_risk_per_trade=0.02,
        max_correlation=0.6,
        max_leverage=3.0,
        stop_loss_percentage=0.02,
        take_profit_percentage=0.04,
    )
    assert risk_cfg.derivatives_risk_gate.enabled is False


def test_mean_reversion_adapter_direction_mode_filtering():
    """Verify MeanReversionStrategyAdapter suppresses SHORT setups when direction_mode == 'LONG_ONLY'."""
    from unittest.mock import MagicMock, patch
    from domain.value_objects import Symbol

    adapter = MeanReversionStrategyAdapter(config={"direction_mode": "LONG_ONLY"})
    adapter.data_buffer = [{"close": 100.0 + i} for i in range(30)]

    mock_setup_sell = MagicMock()
    mock_setup_sell.setup_type = "NGMR_REVERSION"
    mock_setup_sell.direction = "SELL"

    with patch.object(adapter.market_structure_engine, "calculate_market_structure", return_value={"val": 95.0, "vah": 105.0, "poc": 100.0}), \
         patch.object(adapter.setup_engine, "scan_for_setups", return_value=[mock_setup_sell]), \
         patch.object(adapter, "_is_setup_fresh", return_value=True):

        # Signal generation should return None because direction_mode is LONG_ONLY and setup is SELL
        sig = adapter.generate_signal(Symbol("BTCUSDT"))
        assert sig is None

        # Test BUY (Long) setup is allowed
        mock_setup_buy = MagicMock()
        mock_setup_buy.setup_type = "NGMR_REVERSION"
        mock_setup_buy.direction = "BUY"
        adapter.setup_engine.scan_for_setups.return_value = [mock_setup_buy]

        sig_buy = adapter.generate_signal(Symbol("BTCUSDT"))
        assert sig_buy is not None
        assert sig_buy.signal_type.name == "BUY"


def test_derivatives_risk_gate_disabled():
    """Verify DerivativesRiskGate allows everything when disabled."""
    gate = DerivativesRiskGate(config=DerivativesRiskGateConfig(enabled=False))
    res = gate.evaluate("LONG", None, 0.0)
    assert res.decision == RiskGateDecision.ALLOW
    assert res.reason_code == "RISK_GATE_DISABLED"
    assert res.position_multiplier == 1.0


def test_derivatives_risk_gate_daily_drawdown_block():
    """Verify DerivativesRiskGate blocks trades when daily drawdown threshold is breached."""
    gate = DerivativesRiskGate(config=DerivativesRiskGateConfig(enabled=True, max_daily_drawdown_percent=3.0))
    res = gate.evaluate("LONG", None, daily_drawdown_pct=3.5)
    assert res.decision == RiskGateDecision.BLOCK
    assert "DRAWDOWN_EXCEEDED" in res.reason_code
    assert res.position_multiplier == 0.0


def test_derivatives_risk_gate_oi_zscore_hard_block():
    """Verify DerivativesRiskGate blocks LONG trades when OI Z-score >= 2.0."""
    from domain.value_objects import Symbol, ExchangeTimestamp
    gate = DerivativesRiskGate(config=DerivativesRiskGateConfig(enabled=True, oi_zscore_hard_block_threshold=2.0))
    vec = DerivativesFeatureVector(symbol=Symbol("BTCUSDT"), timestamp=ExchangeTimestamp(1000), is_warmed_up=True, oi_zscore_14d=2.15)

    res_long = gate.evaluate("LONG", vec, daily_drawdown_pct=0.0)
    assert res_long.decision == RiskGateDecision.BLOCK
    assert "OI_ZSCORE_HARD_BLOCK" in res_long.reason_code
    assert res_long.position_multiplier == 0.0


def test_derivatives_risk_gate_lvi_hard_block():
    """Verify DerivativesRiskGate blocks trades when LVI >= 25.0."""
    from domain.value_objects import Symbol, ExchangeTimestamp
    gate = DerivativesRiskGate(config=DerivativesRiskGateConfig(enabled=True, lvi_hard_block_threshold=25.0))
    vec = DerivativesFeatureVector(symbol=Symbol("BTCUSDT"), timestamp=ExchangeTimestamp(1000), is_warmed_up=True, oi_zscore_14d=0.5, oi_liquidation_vulnerability_index=28.5)

    res = gate.evaluate("LONG", vec, daily_drawdown_pct=0.0)
    assert res.decision == RiskGateDecision.BLOCK
    assert "LVI_HARD_BLOCK" in res.reason_code
    assert res.position_multiplier == 0.0


def test_derivatives_risk_gate_oi_zscore_soft_warning():
    """Verify DerivativesRiskGate reduces position size to 0.5 when 1.0 <= Z_oi < 2.0."""
    from domain.value_objects import Symbol, ExchangeTimestamp
    gate = DerivativesRiskGate(config=DerivativesRiskGateConfig(enabled=True, oi_zscore_soft_warning_threshold=1.0, soft_position_multiplier=0.5))
    vec = DerivativesFeatureVector(symbol=Symbol("BTCUSDT"), timestamp=ExchangeTimestamp(1000), is_warmed_up=True, oi_zscore_14d=1.45, oi_liquidation_vulnerability_index=10.0)

    res = gate.evaluate("LONG", vec, daily_drawdown_pct=0.0)
    assert res.decision == RiskGateDecision.REDUCE_SIZE
    assert "OI_ZSCORE_SOFT_WARNING" in res.reason_code
    assert res.position_multiplier == 0.5


def test_derivatives_risk_gate_normal_approval():
    """Verify DerivativesRiskGate approves trade with multiplier 1.0 under normal regime."""
    from domain.value_objects import Symbol, ExchangeTimestamp
    gate = DerivativesRiskGate(config=DerivativesRiskGateConfig(enabled=True))
    vec = DerivativesFeatureVector(symbol=Symbol("BTCUSDT"), timestamp=ExchangeTimestamp(1000), is_warmed_up=True, oi_zscore_14d=0.25, oi_liquidation_vulnerability_index=8.0)

    res = gate.evaluate("LONG", vec, daily_drawdown_pct=0.0)
    assert res.decision == RiskGateDecision.ALLOW
    assert res.reason_code == "APPROVED"
    assert res.position_multiplier == 1.0
