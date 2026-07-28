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
from typing import Optional, Tuple, Any

from domain.ports.risk_ports import PortfolioRiskEnginePort, StopLossTakeProfitPort
from domain.ports.portfolio_ports import PositionSizingPort


class ConsolidatedRiskEngineAdapter(PortfolioRiskEnginePort, StopLossTakeProfitPort, PositionSizingPort):
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

    # --- PositionSizingPort (capital allocation / dynamic sizing) -------------

    def calculate_position_size(self, symbol: Any, account_balance: float, risk_percentage: float) -> float:
        """Compatibility method for standard interface."""
        return self._risk_manager.calculate_position_size(
            entry_price=1.0,
            stop_loss=0.98,
            portfolio_equity=account_balance,
            risk_percentage=risk_percentage
        )

    def calculate_dynamic_size(
        self,
        intent: Any,
        portfolio: Any,
        volatility: Optional[float] = None
    ) -> float:
        """Calculate dynamic position size based on drawdown, correlation, and volatility (NGDP)."""
        limit_price = float(intent.risk_parameters.get('limit_price', 0.0))
        stop_loss = float(intent.risk_parameters.get('stop_loss', 0.0))
        
        if limit_price <= 0.0:
            return 0.0

        portfolio_equity = float(portfolio.total_value.amount)
        
        # 1. Volatility
        vol = volatility
        
        # 2. Regime
        regime_context = getattr(intent.fused_signal, 'regime_context', None) if intent.fused_signal else None
        
        # 3. Drawdown Factor
        drawdown_factor = self._risk_manager.calculate_drawdown_factor()
        
        # 4. Correlation Penalty
        portfolio_symbols = [pos.symbol.value for pos in portfolio.positions]
        correlation_penalty = self._risk_manager.calculate_correlation_penalty(intent.symbol.value, portfolio_symbols)
        
        # 5. Confidence Adjustment
        confidence = float(intent.intent_confidence.value) if intent.intent_confidence else 1.0
        risk_percentage = self._risk_manager.max_risk_per_trade * confidence
        
        # Calculate size using EnterpriseRiskManager's implementation
        size = self._risk_manager.calculate_position_size(
            entry_price=limit_price,
            stop_loss=stop_loss,
            portfolio_equity=portfolio_equity,
            risk_percentage=risk_percentage,
            regime_context=regime_context,
            volatility=vol,
            correlation_penalty=correlation_penalty,
            drawdown_factor=drawdown_factor
        )
        
        # Explainability and Audit logging using structured forensic logger
        try:
            from infrastructure.logging.forensic_logger import forensic_logger
            forensic_logger.log_position_sizing(
                symbol=intent.symbol.value,
                portfolio_equity=portfolio_equity,
                target_risk_pct=risk_percentage,
                volatility_factor=vol if vol is not None else 0.0,
                atr_normalization=abs(limit_price - stop_loss),
                drawdown_multiplier=drawdown_factor,
                correlation_penalty=correlation_penalty,
                setup_confidence=confidence,
                final_position_size=size
            )
        except Exception:
            pass  # Logging failures must not halt execution path
            
        return size

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
