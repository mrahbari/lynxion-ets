"""
Main Forensic Governance Module for Enterprise Hedge Fund Trading System
Coordinates all forensic governance components
"""
from infrastructure.governance.decision_gate_controller import decision_gate_controller
from infrastructure.governance.trade_classifier import trade_classifier
from infrastructure.governance.forensic_attribution_model import forensic_attribution_model

# Note: We don't import forensic_governance_layer here to avoid circular imports
# The forensic_governance_layer is imported in other modules where needed

from infrastructure.governance.forensic_governance_layer_separate import forensic_governance_layer

__all__ = [
    'decision_gate_controller',
    'trade_classifier',
    'forensic_attribution_model',
    'forensic_governance_layer',
]