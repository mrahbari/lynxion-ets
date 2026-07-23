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
from typing import List, Optional, Dict, Any

from domain.ports.portfolio_ports import PositionSizingEnginePort


class PositionSizingEngineAdapter(PositionSizingEnginePort):
    """Single, container-managed position-sizing engine.

    Delegates to the canonical algorithm implementations without altering any
    formula. Integrates PortfolioAllocationEngine for multi-asset portfolio
    weight scaling when enabled.
    """

    def __init__(self, service, allocation_engine=None, allocation_config=None):
        self._service = service
        self._allocation_engine = allocation_engine
        self._allocation_config = allocation_config

    def compute_size(self, algorithm: str, entry_price: float, stop_loss: float,
                     portfolio_equity: float, risk_per_trade: float, **kwargs) -> float:
        """Compute position size (units) using the named algorithm.

        Applies PortfolioAllocationEngine weight scaling when enabled.
        """
        symbol = kwargs.get("symbol")
        symbols = kwargs.get("symbols") or ([symbol] if symbol else [])
        asset_stats = kwargs.get("asset_stats")
        risk_gate_multiplier = float(kwargs.get("risk_gate_multiplier", 1.0))

        # 1. Base position sizing
        base_units = self._service.compute_size(
            algorithm,
            entry_price=entry_price,
            stop_loss=stop_loss,
            portfolio_equity=portfolio_equity,
            risk_per_trade=risk_per_trade,
            **kwargs,
        )

        # 2. Portfolio Allocation Engine scaling
        allocation_scale = 1.0
        enabled = False
        if self._allocation_config is not None:
            enabled = getattr(self._allocation_config, "enabled", False)

        if enabled and self._allocation_engine is not None and symbols:
            mode = getattr(self._allocation_config, "allocation_mode", "EQUAL_WEIGHT")
            kelly_fraction = float(getattr(self._allocation_config, "kelly_fraction", 0.25))
            min_floor_weight = float(getattr(self._allocation_config, "min_floor_weight", 0.05))
            max_cap_weight = float(getattr(self._allocation_config, "max_cap_weight", 0.40))

            res = self._allocation_engine.compute_weights(
                symbols=symbols,
                asset_stats=asset_stats,
                mode=mode,
                kelly_fraction=kelly_fraction,
                min_floor_weight=min_floor_weight,
                max_cap_weight=max_cap_weight,
            )
            if symbol and symbol in res.weights:
                n = len(res.weights)
                w_i = res.weights[symbol]
                allocation_scale = w_i * n

        # 3. Apply allocation scale, risk gate multiplier, and execution reserve buffer
        # The execution reserve buffer (e.g. 0.95 to 0.985) reserves capital against positive
        # market order execution slippage to guarantee final_filled_notional <= max_position_notional.
        execution_buffer = float(kwargs.get("execution_buffer", 1.0))
        final_units = base_units * allocation_scale * risk_gate_multiplier * execution_buffer
        return final_units

    def available_algorithms(self) -> List[str]:
        return self._service.get_available_models()
