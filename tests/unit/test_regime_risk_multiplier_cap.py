"""E15-G3: a regime label may reduce risk but never increase it."""
from application.risk_management.enterprise_risk_manager import EnterpriseRiskManager


def test_regime_multiplier_never_raises_risk():
    rm = EnterpriseRiskManager()
    rm.fixed_position_size_enabled = False
    base = rm.calculate_position_size(entry_price=100.0, stop_loss=98.0, portfolio_equity=10_000.0, risk_percentage=0.01)
    ranging = rm.calculate_position_size(entry_price=100.0, stop_loss=98.0, portfolio_equity=10_000.0,
                                         risk_percentage=0.01, regime_context="ranging")
    choppy = rm.calculate_position_size(entry_price=100.0, stop_loss=98.0, portfolio_equity=10_000.0,
                                        risk_percentage=0.01, regime_context="choppy")
    assert ranging <= base + 1e-12
    assert choppy < base
