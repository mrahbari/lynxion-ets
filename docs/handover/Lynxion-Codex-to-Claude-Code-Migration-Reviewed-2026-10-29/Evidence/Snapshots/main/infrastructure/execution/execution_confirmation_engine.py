"""5m Execution Confirmation Engine gating setups using order-flow (OBI and CVD)."""

from domain.entities.research import CandidateSetup


class ExecutionConfirmationEngine:
    """
    5m Execution Confirmation Engine.
    Validates CandidateSetup objects using Order Book Imbalance (OBI) and Cumulative Volume Delta (CVD).
    """

    def __init__(self, obi_threshold: float = 0.1):
        self.obi_threshold = obi_threshold

    def confirm_execution(self, setup: CandidateSetup, obi_ratio: float, cvd: float) -> bool:
        """
        Confirm setup entry using 5m OBI and CVD flow confirmation.
        """
        if setup.direction == "BUY":
            # Flow confirmation for Buy: OBI ratio must exceed positive threshold, CVD must be positive/rising
            return float(obi_ratio) >= self.obi_threshold and float(cvd) >= 0.0
        elif setup.direction == "SELL":
            # Flow confirmation for Sell: OBI ratio must exceed negative threshold, CVD must be negative/falling
            return float(obi_ratio) <= -self.obi_threshold and float(cvd) <= 0.0
        return False
