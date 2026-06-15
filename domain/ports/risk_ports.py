"""Risk engine ports for the consolidated risk module (E3.T4).

Splits the canonical risk decisions into two distinct interfaces so that
**stop-loss / take-profit logic is separated from portfolio risk**:

* :class:`PortfolioRiskEnginePort` — portfolio-level governance: exposure
  admission, drawdown, and the kill-switch / trading-allowed gate.
* :class:`StopLossTakeProfitPort` — per-position SL/TP exit evaluation.

These are distinct from the trading-flow contracts
``domain.ports.engine_ports.RiskGovernorPort`` and
``domain.ports.trading_ports.RiskManagementPort`` (signal/order admission), in
the same way ``PositionSizingEnginePort`` is distinct from ``PositionSizingPort``
(E3.T3). A single consolidated adapter implements both ports over one risk
engine instance, preserving every kill-switch / drawdown / exposure decision
exactly.
"""
from abc import abstractmethod
from typing import Protocol, Optional, Tuple


class PortfolioRiskEnginePort(Protocol):
    """Canonical portfolio-risk governance decisions (E3.T4).

    Owns exposure admission, drawdown measurement, and the kill-switch /
    trading-allowed gate. Decisions mirror the consolidated risk engine
    byte-for-byte.
    """

    @abstractmethod
    def validate_position_entry(self, symbol: str, size: float, entry_price: float) -> bool:
        """Return True iff a new position passes position/portfolio exposure limits."""
        pass

    @abstractmethod
    def is_trading_allowed(self) -> bool:
        """Return True iff trading is permitted (kill-switch / drawdown / daily-loss gate)."""
        pass

    @abstractmethod
    def calculate_drawdown(self) -> float:
        """Return the current drawdown as a fraction of peak equity."""
        pass

    @abstractmethod
    def get_total_exposure(self) -> float:
        """Return total portfolio exposure (sum of size * entry_price)."""
        pass


class StopLossTakeProfitPort(Protocol):
    """Canonical SL/TP exit evaluation, separated from portfolio risk (E3.T4)."""

    @abstractmethod
    def check_stop_loss_take_profit(self, symbol: str, candle_high: float,
                                    candle_low: float) -> Tuple[Optional[float], Optional[str]]:
        """Return ``(exit_price, exit_type)`` for a hit SL/TP, else ``(None, None)``."""
        pass
