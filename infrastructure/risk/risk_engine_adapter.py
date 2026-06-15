"""Consolidated risk-engine adapter (E3.T4).

A single adapter behind the risk-engine ports
(:class:`domain.ports.risk_ports.PortfolioRiskEnginePort` and
:class:`domain.ports.risk_ports.StopLossTakeProfitPort`) that exposes the
canonical risk decisions as one module, with **SL/TP separated from portfolio
risk** at the interface level.

Decisions are preserved **byte-for-byte** by delegating to the existing
``application.risk_management.enterprise_risk_manager.EnterpriseRiskManager`` —
the only risk engine with live consumers (backtest, execution, optimization,
strategy adapters). The parallel ``infrastructure/risk_management`` portfolio
manager and the unreferenced ``infrastructure/risk/risk_adapters.py`` placeholder
adapters were removed in E8 cleanup (commits E8.T1a/E8.T1b). The kill-switch /
drawdown / exposure logic itself is unchanged.

This adapter deliberately wraps a single engine instance so the portfolio-risk
view and the SL/TP view share consistent position state while remaining distinct
ports.
"""
from typing import Optional, Tuple

from domain.ports.risk_ports import PortfolioRiskEnginePort, StopLossTakeProfitPort


class ConsolidatedRiskEngineAdapter(PortfolioRiskEnginePort, StopLossTakeProfitPort):
    """Single, container-managed risk engine.

    Delegates to the canonical ``EnterpriseRiskManager`` without altering any
    decision. The canonical engine is built by the composition root and injected
    here (the adapter no longer self-constructs it), so infrastructure carries no
    import of the application-layer risk manager. The composition root injects an
    ``EnterpriseRiskManager()`` whose defaults are
    (max_portfolio_exposure=100000, max_position_exposure=50000,
    max_risk_per_trade=0.01, max_daily_loss_pct=0.05, max_drawdown_pct=0.15).
    """

    def __init__(self, risk_manager):
        self._risk_manager = risk_manager

    # --- PortfolioRiskEnginePort (exposure / drawdown / kill-switch) ----------

    def validate_position_entry(self, symbol: str, size: float, entry_price: float) -> bool:
        return self._risk_manager.validate_position_entry(symbol, size, entry_price)

    def is_trading_allowed(self) -> bool:
        return self._risk_manager.is_trading_allowed()

    def calculate_drawdown(self) -> float:
        return self._risk_manager.calculate_drawdown()

    def get_total_exposure(self) -> float:
        return self._risk_manager.get_total_exposure()

    # --- StopLossTakeProfitPort (separated SL/TP) -----------------------------

    def check_stop_loss_take_profit(self, symbol: str, candle_high: float,
                                    candle_low: float) -> Tuple[Optional[float], Optional[str]]:
        return self._risk_manager.check_stop_loss_take_profit(symbol, candle_high, candle_low)
