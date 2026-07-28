"""
Pure, deterministic Derivatives Risk Gate evaluation service.
Implements hard blockers and soft position size reducers based on point-in-time derivatives features.
"""

from enum import Enum
from typing import NamedTuple, Optional
from domain.entities.feature import DerivativesFeatureVector
from application.configs.schemas.risk import DerivativesRiskGateConfig


class RiskGateDecision(Enum):
    ALLOW = "ALLOW"
    REDUCE_SIZE = "REDUCE_SIZE"
    BLOCK = "BLOCK"


class RiskGateResult(NamedTuple):
    decision: RiskGateDecision
    reason_code: str
    position_multiplier: float


class DerivativesRiskGate:
    """Evaluates Derivatives Risk Gate rules for trade signals."""

    def __init__(self, config: Optional[DerivativesRiskGateConfig] = None):
        self.config = config or DerivativesRiskGateConfig()

    def evaluate(
        self,
        signal_direction: str,
        feature_vector: Optional[DerivativesFeatureVector] = None,
        daily_drawdown_pct: float = 0.0,
    ) -> RiskGateResult:
        """Evaluate signal against Derivatives Risk Gate rules.

        Outputs:
            ALLOW: multiplier = 1.0
            REDUCE_SIZE: multiplier = soft_position_multiplier (default 0.5)
            BLOCK: multiplier = 0.0
        """
        if not self.config.enabled:
            return RiskGateResult(RiskGateDecision.ALLOW, "RISK_GATE_DISABLED", 1.0)

        # 1. Daily Drawdown Hard Blocker
        if daily_drawdown_pct >= self.config.max_daily_drawdown_percent:
            return RiskGateResult(
                RiskGateDecision.BLOCK,
                f"DRAWDOWN_EXCEEDED (drawdown {daily_drawdown_pct:.1f}% >= max {self.config.max_daily_drawdown_percent:.1f}%)",
                0.0,
            )

        if feature_vector is None:
            return RiskGateResult(RiskGateDecision.ALLOW, "NO_DERIVATIVES_VECTOR", 1.0)

        z_oi = feature_vector.oi_zscore_14d if feature_vector.oi_zscore_14d is not None else 0.0
        lvi = feature_vector.oi_liquidation_vulnerability_index if feature_vector.oi_liquidation_vulnerability_index is not None else 0.0

        # 2. OI Z-score Hard Blocker for LONG trades
        if z_oi >= self.config.oi_zscore_hard_block_threshold:
            if signal_direction in ("LONG", "BUY"):
                return RiskGateResult(
                    RiskGateDecision.BLOCK,
                    f"OI_ZSCORE_HARD_BLOCK (Z_oi {z_oi:.2f} >= threshold {self.config.oi_zscore_hard_block_threshold:.2f})",
                    0.0,
                )

        # 3. LVI Hard Blocker
        if lvi >= self.config.lvi_hard_block_threshold:
            return RiskGateResult(
                RiskGateDecision.BLOCK,
                f"LVI_HARD_BLOCK (LVI {lvi:.1f} >= threshold {self.config.lvi_hard_block_threshold:.1f})",
                0.0,
            )

        # 4. OI Z-score Soft Reducer (1.0 <= Z_oi < 2.0)
        if self.config.oi_zscore_soft_warning_threshold <= z_oi < self.config.oi_zscore_hard_block_threshold:
            return RiskGateResult(
                RiskGateDecision.REDUCE_SIZE,
                f"OI_ZSCORE_SOFT_WARNING (Z_oi {z_oi:.2f} in warning zone)",
                self.config.soft_position_multiplier,
            )

        return RiskGateResult(RiskGateDecision.ALLOW, "APPROVED", 1.0)
