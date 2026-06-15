"""
Decision Defensibility Validator for Enterprise Hedge Fund Trading System
Ensures all trading decisions are mathematically provable and auditable
"""
import numpy as np
import pandas as pd
from scipy import stats
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import hashlib
import json
from infrastructure.statistical_validation._decision_tests import _DecisionTestsMixin
from infrastructure.statistical_validation._decision_validators import _DecisionValidatorsMixin, DecisionDefensibilityReport



class DecisionDefensibilityValidator(_DecisionTestsMixin, _DecisionValidatorsMixin):
    """
    Validates that all trading decisions are mathematically defensible
    and can be proven under institutional audit
    """
    
    def __init__(self):
        self.minimum_evidence_threshold = 0.7  # Minimum evidence score for defensibility
        self.required_validation_tests = [
            'statistical_significance',
            'out_of_sample_validation',
            'risk_adjusted_returns',
            'alternative_hypothesis_test'
        ]
    
    def _generate_decision_id(self, data: Dict[str, Any]) -> str:
        """Generate unique decision ID for audit purposes"""
        # Create a hash-based ID from relevant data fields
        relevant_fields = {k: v for k, v in data.items() 
                          if k in ['symbol', 'timestamp', 'value', 'confidence', 'direction', 'strategy']}
        data_str = json.dumps(relevant_fields, sort_keys=True, default=str)
        return hashlib.sha256(data_str.encode()).hexdigest()[:16]
    
    def _create_audit_trail(self, decision_id: str, component: str, 
                           validation_results: Dict[str, Any], 
                           supporting_evidence: List[Dict[str, Any]]) -> str:
        """Create audit trail for the decision validation"""
        audit_data = {
            'decision_id': decision_id,
            'component': component,
            'validation_results': validation_results,
            'supporting_evidence_count': len(supporting_evidence),
            'timestamp': datetime.utcnow().isoformat()
        }
        # default=str so numpy bools/floats in validation_results don't break the
        # hash (matches _compute_input_hash above); without it, intent-based
        # strategy adapters that log forensic decisions raise
        # "Object of type bool is not JSON serializable" mid-backtest.
        return hashlib.sha256(
            json.dumps(audit_data, sort_keys=True, default=str).encode()
        ).hexdigest()


# Global instance
decision_validator = DecisionDefensibilityValidator()