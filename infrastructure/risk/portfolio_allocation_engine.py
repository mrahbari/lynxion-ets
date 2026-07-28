"""
Pure, Deterministic Portfolio Allocation Engine.

Computes multi-asset portfolio weights using configurable allocation models
(Equal Weight, Fractional Kelly / Quarter-Kelly).

Design Principles:
- Stateless, pure, thread-safe, and side-effect free.
- Never raises uncaught exceptions into the trading pipeline.
- Fails closed to deterministic Equal Weight fallback upon invalid/NaN inputs.
"""
import math
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class AllocationMode(str, Enum):
    """Supported portfolio allocation methodologies."""
    EQUAL_WEIGHT = "EQUAL_WEIGHT"
    FRACTIONAL_KELLY = "FRACTIONAL_KELLY"
    RISK_PARITY = "RISK_PARITY"
    EQUAL_RISK_CONTRIBUTION = "EQUAL_RISK_CONTRIBUTION"


@dataclass(frozen=True)
class AssetPerformanceStats:
    """Historical trade performance statistics for an individual asset."""
    symbol: str
    win_rate: float           # Trade win rate p in [0.0, 1.0]
    win_loss_ratio: float     # Average win / average loss ratio b > 0.0
    volatility: Optional[float] = None  # Trade return volatility (optional)

    def is_valid(self) -> bool:
        """Check whether stats are mathematically valid and finite."""
        if not math.isfinite(self.win_rate) or not (0.0 <= self.win_rate <= 1.0):
            return False
        if not math.isfinite(self.win_loss_ratio) or self.win_loss_ratio <= 0.0:
            return False
        if self.volatility is not None and (not math.isfinite(self.volatility) or self.volatility < 0.0):
            return False
        return True


@dataclass(frozen=True)
class AllocationResult:
    """Immutable portfolio weight allocation result."""
    weights: Dict[str, float]
    mode: AllocationMode
    is_fallback: bool
    reason: str

    def is_valid(self) -> bool:
        """Validate that all weights are finite, non-negative, and sum to 1.0 within tolerance."""
        if not self.weights:
            return False
        total = sum(self.weights.values())
        if not math.isfinite(total) or abs(total - 1.0) > 1e-3:
            return False
        return all(math.isfinite(w) and w >= 0.0 for w in self.weights.values())


class PortfolioAllocationEngine:
    """
    Stateless Portfolio Allocation Engine calculating optimal multi-asset risk weights.
    """

    def compute_weights(
        self,
        symbols: List[str],
        asset_stats: Optional[Dict[str, AssetPerformanceStats]] = None,
        mode: AllocationMode = AllocationMode.EQUAL_WEIGHT,
        kelly_fraction: float = 0.25,
        min_floor_weight: float = 0.05,
        max_cap_weight: float = 0.40,
    ) -> AllocationResult:
        """
        Compute normalized allocation weights across input symbols.

        Args:
            symbols: List of target asset symbols.
            asset_stats: Optional map of symbol to historical performance stats.
            mode: Allocation methodology enum.
            kelly_fraction: Kelly fraction multiplier (default 0.25 = Quarter Kelly).
            min_floor_weight: Minimum unnormalized floor allocation weight.
            max_cap_weight: Maximum normalized allocation weight cap.

        Returns:
            AllocationResult containing normalized weight dictionary.
        """
        try:
            if not symbols:
                return AllocationResult(
                    weights={},
                    mode=mode,
                    is_fallback=True,
                    reason="Empty symbol list provided."
                )

            # Deduplicate symbols while preserving order
            unique_symbols = list(dict.fromkeys(symbols))
            n = len(unique_symbols)

            if n == 1:
                sym = unique_symbols[0]
                return AllocationResult(
                    weights={sym: 1.0},
                    mode=mode,
                    is_fallback=False,
                    reason="Single asset portfolio."
                )

            if mode == AllocationMode.FRACTIONAL_KELLY:
                return self._compute_fractional_kelly_weights(
                    symbols=unique_symbols,
                    asset_stats=asset_stats,
                    kelly_fraction=kelly_fraction,
                    min_floor_weight=min_floor_weight,
                    max_cap_weight=max_cap_weight,
                )

            # Default to Equal Weight for EQUAL_WEIGHT or unhandled modes
            return self._compute_equal_weights(unique_symbols, mode=mode, reason="Equal Weight allocation executed.")

        except Exception as exc:
            logger.warning(f"PortfolioAllocationEngine exception encountered: {exc}. Falling back to Equal Weight.")
            safe_symbols = list(dict.fromkeys(symbols)) if symbols else []
            return self._compute_equal_weights(
                safe_symbols,
                mode=mode,
                is_fallback=True,
                reason=f"Exception fallback: {str(exc)}"
            )

    def _compute_equal_weights(
        self,
        symbols: List[str],
        mode: AllocationMode = AllocationMode.EQUAL_WEIGHT,
        is_fallback: bool = False,
        reason: str = "Equal Weight allocation."
    ) -> AllocationResult:
        """Compute equal weight allocation (1/N per asset)."""
        if not symbols:
            return AllocationResult(weights={}, mode=mode, is_fallback=True, reason="Empty symbols.")

        n = len(symbols)
        w = round(1.0 / n, 6)
        weights = {s: w for s in symbols}

        # Adjust tiny rounding difference on first element to guarantee exact sum = 1.0
        diff = round(1.0 - sum(weights.values()), 6)
        if diff != 0.0:
            weights[symbols[0]] = round(weights[symbols[0]] + diff, 6)

        return AllocationResult(
            weights=weights,
            mode=mode,
            is_fallback=is_fallback,
            reason=reason
        )

    def _compute_fractional_kelly_weights(
        self,
        symbols: List[str],
        asset_stats: Optional[Dict[str, AssetPerformanceStats]],
        kelly_fraction: float,
        min_floor_weight: float,
        max_cap_weight: float,
    ) -> AllocationResult:
        """
        Compute Fractional Kelly (Quarter-Kelly) portfolio weights.

        Formula:
            f* = (p * b - (1 - p)) / b
            w_raw = max(min_floor_weight, kelly_fraction * f*)
            w_norm = w_raw / sum(w_raw)
        """
        if not asset_stats:
            return self._compute_equal_weights(
                symbols,
                mode=AllocationMode.FRACTIONAL_KELLY,
                is_fallback=True,
                reason="Missing asset_stats dictionary for Fractional Kelly."
            )

        raw_weights = {}
        for sym in symbols:
            stats = asset_stats.get(sym)
            if not stats or not stats.is_valid():
                # Invalid or missing stats fall back to floor weight
                raw_weights[sym] = min_floor_weight
                continue

            p = stats.win_rate
            b = stats.win_loss_ratio
            q = 1.0 - p

            # Full Kelly fraction f*
            f_star = (p * b - q) / b

            # Scale by kelly_fraction and enforce floor
            w_scaled = kelly_fraction * f_star
            raw_w = max(min_floor_weight, w_scaled)
            raw_weights[sym] = raw_w

        total_raw = sum(raw_weights.values())

        if not math.isfinite(total_raw) or total_raw <= 0.0:
            return self._compute_equal_weights(
                symbols,
                mode=AllocationMode.FRACTIONAL_KELLY,
                is_fallback=True,
                reason="Non-finite or non-positive total raw Kelly weight sum."
            )

        # Normalize weights to sum to 1.0
        norm_weights = {}
        for sym, rw in raw_weights.items():
            norm_w = min(max_cap_weight, rw / total_raw)
            norm_weights[sym] = round(norm_w, 6)

        # Re-normalize after capping
        norm_total = sum(norm_weights.values())
        if norm_total > 0.0:
            final_weights = {s: round(w / norm_total, 6) for s, w in norm_weights.items()}
        else:
            return self._compute_equal_weights(
                symbols,
                mode=AllocationMode.FRACTIONAL_KELLY,
                is_fallback=True,
                reason="Zero sum after capping."
            )

        # Fix minor rounding residual
        residual = round(1.0 - sum(final_weights.values()), 6)
        if residual != 0.0:
            final_weights[symbols[0]] = round(final_weights[symbols[0]] + residual, 6)

        return AllocationResult(
            weights=final_weights,
            mode=AllocationMode.FRACTIONAL_KELLY,
            is_fallback=False,
            reason="Fractional Kelly allocation computed successfully."
        )
