"""Consolidated position-sizing engine adapter (E3.T3).

A single adapter behind :class:`domain.ports.portfolio_ports.PositionSizingEnginePort`
that exposes the position-sizing algorithms as named, pluggable strategies.

Formulas are preserved **byte-for-byte** by delegating to the existing
implementations in
``application.position_sizing.enterprise_position_sizing.PositionSizingService``
— the only sizing engine that had a (legacy) consumer. The other historical
sizing modules remain importable as deprecated shims; physical removal is
deferred to E8.

This adapter deliberately does NOT touch the live, risk-governed sizing path
(``risk_service.calculate_position_size`` and the broker/strategy/shadow sizing),
which remains owned by the Risk module (E3.T4).
"""
from typing import List

from domain.ports.portfolio_ports import PositionSizingEnginePort


class PositionSizingEngineAdapter(PositionSizingEnginePort):
    """Single, container-managed position-sizing engine.

    Delegates to the canonical algorithm implementations without altering any
    formula. The canonical ``PositionSizingService`` is built by the composition
    root and injected here (the adapter no longer self-constructs it), so
    infrastructure carries no import of the application-layer sizing service.
    """

    def __init__(self, service):
        self._service = service

    def compute_size(self, algorithm: str, entry_price: float, stop_loss: float,
                     portfolio_equity: float, risk_per_trade: float, **kwargs) -> float:
        """Compute position size (units) using the named algorithm.

        Mirrors ``PositionSizingService.compute_size`` exactly; ``kwargs`` carry
        the optional per-algorithm factors (e.g. ``volatility``,
        ``signal_expectancy``, ``win_rate``).
        """
        return self._service.compute_size(
            algorithm,
            entry_price=entry_price,
            stop_loss=stop_loss,
            portfolio_equity=portfolio_equity,
            risk_per_trade=risk_per_trade,
            **kwargs,
        )

    def available_algorithms(self) -> List[str]:
        return self._service.get_available_models()
