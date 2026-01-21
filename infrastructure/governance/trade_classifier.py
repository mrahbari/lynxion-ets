"""
Trade Classification System for Enterprise Hedge Fund Trading System
Classifies trades as SCIENTIFIC, PROBATIONARY, or RANDOM based on statistical validity
"""
from enum import Enum
from typing import Dict, Any
from datetime import datetime
import logging


class TradeClassification(Enum):
    SCIENTIFIC = "SCIENTIFIC"
    PROBATIONARY = "PROBATIONARY"
    RANDOM = "RANDOM"


class TradeClassifier:
    """
    Classifies trades based on statistical and forensic criteria
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def classify_trade(self, 
                      authority_score: float, 
                      p_value: float, 
                      sample_size: int,
                      defensibility_score: float,
                      contributor_diversity_score: float = 1.0,
                      oos_validation_passed: bool = True,
                      maturity_status: str = "mature") -> TradeClassification:
        """
        Classify a trade based on multiple statistical and forensic criteria
        """
        # Check statistical significance
        statistically_significant = p_value < 0.05 if p_value is not None else False
        
        # Check sample adequacy
        adequate_sample = sample_size >= 50  # Minimum 50 samples for scientific classification
        
        # Check authority threshold
        sufficient_authority = authority_score >= 0.7 if authority_score is not None else False
        
        # Check defensibility
        defensible = defensibility_score >= 0.7 if defensibility_score is not None else False
        
        # Check contributor diversity (for fusion layer)
        diverse_contributors = contributor_diversity_score >= 0.5 if contributor_diversity_score is not None else True
        
        # Check OOS validation
        oos_validated = oos_validation_passed
        
        # Check maturity
        is_mature = maturity_status == "mature"
        
        # Classification logic
        if (statistically_significant and 
            adequate_sample and 
            sufficient_authority and 
            defensible and 
            diverse_contributors and 
            oos_validated and 
            is_mature):
            return TradeClassification.SCIENTIFIC
            
        elif (statistically_significant and 
              sample_size >= 20 and 
              authority_score >= 0.5 and 
              defensibility_score >= 0.5):
            return TradeClassification.PROBATIONARY
        else:
            return TradeClassification.RANDOM
    
    def get_classification_reasons(self, 
                                 authority_score: float, 
                                 p_value: float, 
                                 sample_size: int,
                                 defensibility_score: float,
                                 contributor_diversity_score: float = 1.0,
                                 oos_validation_passed: bool = True,
                                 maturity_status: str = "mature") -> Dict[str, Any]:
        """
        Get detailed reasons for the classification
        """
        reasons = {
            "authority_score": {
                "value": authority_score,
                "passing": authority_score >= 0.7 if authority_score is not None else False,
                "threshold": 0.7
            },
            "statistical_significance": {
                "value": p_value,
                "passing": p_value < 0.05 if p_value is not None else False,
                "threshold": 0.05
            },
            "sample_size": {
                "value": sample_size,
                "passing": sample_size >= 50,
                "threshold": 50
            },
            "defensibility_score": {
                "value": defensibility_score,
                "passing": defensibility_score >= 0.7 if defensibility_score is not None else False,
                "threshold": 0.7
            },
            "contributor_diversity": {
                "value": contributor_diversity_score,
                "passing": contributor_diversity_score >= 0.5 if contributor_diversity_score is not None else True,
                "threshold": 0.5
            },
            "oos_validation": {
                "value": oos_validation_passed,
                "passing": oos_validation_passed,
                "threshold": True
            },
            "maturity_status": {
                "value": maturity_status,
                "passing": maturity_status == "mature",
                "threshold": "mature"
            }
        }
        
        return reasons


# Global instance
trade_classifier = TradeClassifier()