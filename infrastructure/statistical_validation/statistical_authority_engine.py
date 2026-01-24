"""
Statistical Authority Score Engine for Enterprise Hedge Fund Trading System
Implements mandatory statistical validation for all trading decisions
"""
import numpy as np
import pandas as pd
from scipy import stats
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import math


class ComponentType(Enum):
    WATCHER = "watcher"
    ENGINE = "engine"
    FUSION = "fusion"
    STRATEGY = "strategy"
    BROKER = "broker"
    BROKER_CLOSE = "broker_close"


@dataclass
class StatisticalAuthorityScore:
    """Represents the statistical authority score for a component"""
    component: ComponentType
    score: float  # 0.0 to 1.0
    p_value: float  # Statistical significance
    confidence_interval: Tuple[float, float]
    sample_size: int
    statistical_test: str
    timestamp: datetime
    validation_status: str  # "PASS", "FAIL", "INSUFFICIENT_DATA"


class StatisticalAuthorityScoreEngine:
    """
    Computes statistical authority scores for all system components
    Ensures all decisions are based on statistically significant evidence
    """
    
    def __init__(self):
        self.minimum_significance_level = 0.05  # 95% confidence
        self.minimum_sample_size = 30  # Minimum for central limit theorem
        self.decay_factor = 0.95  # Decay factor for historical data
        
    def calculate_watcher_authority(self, 
                                  historical_observations: List[Dict[str, Any]],
                                  current_observation: Dict[str, Any]) -> StatisticalAuthorityScore:
        """
        Calculate statistical authority for watcher component
        """
        if len(historical_observations) < self.minimum_sample_size:
            return StatisticalAuthorityScore(
                component=ComponentType.WATCHER,
                score=0.0,
                p_value=1.0,
                confidence_interval=(0.0, 0.0),
                sample_size=len(historical_observations),
                statistical_test="insufficient_data",
                timestamp=datetime.utcnow(),
                validation_status="INSUFFICIENT_DATA"
            )
        
        # Calculate historical accuracy rate
        correct_predictions = sum(1 for obs in historical_observations if obs.get('was_correct', False))
        historical_accuracy = correct_predictions / len(historical_observations) if historical_observations else 0.0
        
        # Perform binomial test for accuracy significance
        n = len(historical_observations)
        k = correct_predictions
        p_null = 0.5  # Null hypothesis: 50% accuracy (random)
        
        # Binomial test
        if k <= n * p_null:
            p_value = stats.binom.cdf(k, n, p_null)
        else:
            p_value = 1 - stats.binom.cdf(k - 1, n, p_null)
        
        # Calculate confidence interval for accuracy
        ci_lower, ci_upper = self._wilson_score_interval(k, n, 0.95)
        
        # Calculate statistical authority score
        score = self._calculate_authority_score(historical_accuracy, p_value, n)
        
        validation_status = "PASS" if (p_value < self.minimum_significance_level and 
                                      historical_accuracy > 0.5) else "FAIL"
        
        return StatisticalAuthorityScore(
            component=ComponentType.WATCHER,
            score=score,
            p_value=p_value,
            confidence_interval=(ci_lower, ci_upper),
            sample_size=n,
            statistical_test="binomial_accuracy_test",
            timestamp=datetime.utcnow(),
            validation_status=validation_status
        )
    
    def calculate_engine_authority(self, 
                                 historical_interpretations: List[Dict[str, Any]],
                                 current_interpretation: Dict[str, Any]) -> StatisticalAuthorityScore:
        """
        Calculate statistical authority for engine component
        """
        if len(historical_interpretations) < self.minimum_sample_size:
            return StatisticalAuthorityScore(
                component=ComponentType.ENGINE,
                score=0.0,
                p_value=1.0,
                confidence_interval=(0.0, 0.0),
                sample_size=len(historical_interpretations),
                statistical_test="insufficient_data",
                timestamp=datetime.utcnow(),
                validation_status="INSUFFICIENT_DATA"
            )
        
        # Calculate interpretation accuracy
        correct_interpretations = sum(1 for interp in historical_interpretations if interp.get('was_correct', False))
        accuracy_rate = correct_interpretations / len(historical_interpretations) if historical_interpretations else 0.0
        
        # Calculate false positive rate
        false_positives = sum(1 for interp in historical_interpretations if interp.get('false_positive', False))
        false_positive_rate = false_positives / len(historical_interpretations) if historical_interpretations else 1.0
        
        # Perform statistical test for accuracy significance
        n = len(historical_interpretations)
        k = correct_interpretations
        p_null = 0.5  # Null hypothesis: 50% accuracy
        
        if k <= n * p_null:
            p_value = stats.binom.cdf(k, n, p_null)
        else:
            p_value = 1 - stats.binom.cdf(k - 1, n, p_null)
        
        # Calculate confidence interval
        ci_lower, ci_upper = self._wilson_score_interval(k, n, 0.95)
        
        # Adjust score based on false positive rate
        score = self._calculate_authority_score(accuracy_rate, p_value, n)
        score *= (1.0 - min(false_positive_rate, 0.5) * 2)  # Penalize high false positive rates
        
        validation_status = "PASS" if (p_value < self.minimum_significance_level and 
                                      accuracy_rate > 0.5 and 
                                      false_positive_rate < 0.2) else "FAIL"
        
        return StatisticalAuthorityScore(
            component=ComponentType.ENGINE,
            score=score,
            p_value=p_value,
            confidence_interval=(ci_lower, ci_upper),
            sample_size=n,
            statistical_test="binomial_accuracy_with_fp_penalty",
            timestamp=datetime.utcnow(),
            validation_status=validation_status
        )
    
    def calculate_fusion_authority(self, 
                                 historical_fusions: List[Dict[str, Any]],
                                 current_fusion: Dict[str, Any]) -> StatisticalAuthorityScore:
        """
        Calculate statistical authority for fusion component
        """
        if len(historical_fusions) < self.minimum_sample_size:
            return StatisticalAuthorityScore(
                component=ComponentType.FUSION,
                score=0.0,
                p_value=1.0,
                confidence_interval=(0.0, 0.0),
                sample_size=len(historical_fusions),
                statistical_test="insufficient_data",
                timestamp=datetime.utcnow(),
                validation_status="INSUFFICIENT_DATA"
            )
        
        # Calculate fusion effectiveness
        correct_fusions = sum(1 for fusion in historical_fusions if fusion.get('was_correct', False))
        effectiveness_rate = correct_fusions / len(historical_fusions) if historical_fusions else 0.0
        
        # Calculate correlation validation (how often fusion adds value vs individual signals)
        value_added = sum(1 for fusion in historical_fusions if fusion.get('fusion_added_value', False))
        value_addition_rate = value_added / len(historical_fusions) if historical_fusions else 0.0
        
        # Perform statistical test
        n = len(historical_fusions)
        k = correct_fusions
        p_null = 0.5  # Null hypothesis: 50% effectiveness
        
        if k <= n * p_null:
            p_value = stats.binom.cdf(k, n, p_null)
        else:
            p_value = 1 - stats.binom.cdf(k - 1, n, p_null)
        
        # Calculate confidence interval
        ci_lower, ci_upper = self._wilson_score_interval(k, n, 0.95)
        
        # Calculate score with value addition consideration
        base_score = self._calculate_authority_score(effectiveness_rate, p_value, n)
        score = base_score * (0.5 + 0.5 * value_addition_rate)  # Boost if fusion adds value
        
        validation_status = "PASS" if (p_value < self.minimum_significance_level and 
                                      effectiveness_rate > 0.5 and 
                                      value_addition_rate > 0.3) else "FAIL"
        
        return StatisticalAuthorityScore(
            component=ComponentType.FUSION,
            score=score,
            p_value=p_value,
            confidence_interval=(ci_lower, ci_upper),
            sample_size=n,
            statistical_test="binomial_effectiveness_with_value_addition",
            timestamp=datetime.utcnow(),
            validation_status=validation_status
        )
    
    def calculate_strategy_authority(self, 
                                   historical_decisions: List[Dict[str, Any]],
                                   current_decision: Dict[str, Any]) -> StatisticalAuthorityScore:
        """
        Calculate statistical authority for strategy component
        """
        if len(historical_decisions) < self.minimum_sample_size:
            return StatisticalAuthorityScore(
                component=ComponentType.STRATEGY,
                score=0.0,
                p_value=1.0,
                confidence_interval=(0.0, 0.0),
                sample_size=len(historical_decisions),
                statistical_test="insufficient_data",
                timestamp=datetime.utcnow(),
                validation_status="INSUFFICIENT_DATA"
            )
        
        # Calculate strategy effectiveness (profitability)
        profitable_decisions = sum(1 for decision in historical_decisions if decision.get('was_profitable', False))
        effectiveness_rate = profitable_decisions / len(historical_decisions) if historical_decisions else 0.0
        
        # Calculate Sharpe ratio for risk-adjusted returns
        returns = [decision.get('return_pct', 0.0) for decision in historical_decisions if 'return_pct' in decision]
        if len(returns) >= 2:
            sharpe_ratio = np.mean(returns) / (np.std(returns) if np.std(returns) != 0 else 1.0) if returns else 0.0
        else:
            sharpe_ratio = 0.0
        
        # Perform statistical test for profitability significance
        if len(returns) >= 2:
            t_stat, p_value = stats.ttest_1samp(returns, 0.0)  # Test if mean return > 0
            p_value = min(p_value, 1.0)  # Ensure p-value is valid
        else:
            p_value = 1.0
        
        # Calculate confidence interval for returns
        if len(returns) >= 2:
            mean_return = np.mean(returns)
            std_return = np.std(returns)
            n = len(returns)
            se = std_return / np.sqrt(n)
            ci_lower = mean_return - 1.96 * se
            ci_upper = mean_return + 1.96 * se
        else:
            ci_lower, ci_upper = (0.0, 0.0)
        
        # Calculate score based on profitability and risk-adjusted returns
        base_score = self._calculate_authority_score(effectiveness_rate, p_value, len(returns))
        risk_adjusted_score = max(0.0, min(1.0, (sharpe_ratio + 2.0) / 4.0))  # Normalize Sharpe ratio
        score = 0.6 * base_score + 0.4 * risk_adjusted_score
        
        validation_status = "PASS" if (p_value < self.minimum_significance_level and 
                                      effectiveness_rate > 0.5 and 
                                      sharpe_ratio > 0.1) else "FAIL"
        
        return StatisticalAuthorityScore(
            component=ComponentType.STRATEGY,
            score=score,
            p_value=p_value,
            confidence_interval=(ci_lower, ci_upper),
            sample_size=len(returns),
            statistical_test="ttest_profitability_with_sharpe",
            timestamp=datetime.utcnow(),
            validation_status=validation_status
        )
    
    def calculate_broker_authority(self, 
                                 historical_executions: List[Dict[str, Any]],
                                 current_execution: Dict[str, Any]) -> StatisticalAuthorityScore:
        """
        Calculate statistical authority for broker component
        """
        if len(historical_executions) < self.minimum_sample_size:
            return StatisticalAuthorityScore(
                component=ComponentType.BROKER,
                score=0.0,
                p_value=1.0,
                confidence_interval=(0.0, 0.0),
                sample_size=len(historical_executions),
                statistical_test="insufficient_data",
                timestamp=datetime.utcnow(),
                validation_status="INSUFFICIENT_DATA"
            )
        
        # Calculate execution quality metrics
        slippage_values = [exec.get('slippage_pct', 0.0) for exec in historical_executions if 'slippage_pct' in exec]
        success_rates = [exec.get('execution_success', False) for exec in historical_executions]
        
        success_rate = sum(success_rates) / len(success_rates) if success_rates else 0.0
        avg_slippage = np.mean(slippage_values) if slippage_values else 0.0
        std_slippage = np.std(slippage_values) if slippage_values else 0.0
        
        # Perform statistical test for execution success significance
        n = len(success_rates)
        k = sum(success_rates)
        p_null = 0.9  # Null hypothesis: 90% success rate
        
        if k <= n * p_null:
            p_value = stats.binom.cdf(k, n, p_null)
        else:
            p_value = 1 - stats.binom.cdf(k - 1, n, p_null)
        
        # Calculate confidence interval for success rate
        ci_lower, ci_upper = self._wilson_score_interval(k, n, 0.95)
        
        # Calculate score based on success rate and slippage control
        success_score = self._calculate_authority_score(success_rate, p_value, n)
        slippage_score = max(0.0, min(1.0, 1.0 - abs(avg_slippage) / 0.02))  # Penalty for >2% slippage
        score = 0.7 * success_score + 0.3 * slippage_score
        
        validation_status = "PASS" if (p_value < self.minimum_significance_level and 
                                      success_rate > 0.85 and 
                                      abs(avg_slippage) < 0.01) else "FAIL"
        
        return StatisticalAuthorityScore(
            component=ComponentType.BROKER,
            score=score,
            p_value=p_value,
            confidence_interval=(ci_lower, ci_upper),
            sample_size=n,
            statistical_test="binomial_success_with_slippage",
            timestamp=datetime.utcnow(),
            validation_status=validation_status
        )
    
    def calculate_broker_close_authority(self, 
                                       historical_closures: List[Dict[str, Any]],
                                       current_closure: Dict[str, Any]) -> StatisticalAuthorityScore:
        """
        Calculate statistical authority for broker close component
        """
        if len(historical_closures) < self.minimum_sample_size:
            return StatisticalAuthorityScore(
                component=ComponentType.BROKER_CLOSE,
                score=0.0,
                p_value=1.0,
                confidence_interval=(0.0, 0.0),
                sample_size=len(historical_closures),
                statistical_test="insufficient_data",
                timestamp=datetime.utcnow(),
                validation_status="INSUFFICIENT_DATA"
            )
        
        # Calculate exit effectiveness
        optimal_exits = sum(1 for closure in historical_closures if closure.get('exit_was_optimal', False))
        effectiveness_rate = optimal_exits / len(historical_closures) if historical_closures else 0.0
        
        # Calculate regret metrics (difference from optimal exit)
        regret_values = [closure.get('regret_metric', 0.0) for closure in historical_closures if 'regret_metric' in closure]
        avg_regret = np.mean(regret_values) if regret_values else 0.0
        
        # Perform statistical test for optimality significance
        n = len(historical_closures)
        k = optimal_exits
        p_null = 0.5  # Null hypothesis: 50% optimal exits (random)
        
        if k <= n * p_null:
            p_value = stats.binom.cdf(k, n, p_null)
        else:
            p_value = 1 - stats.binom.cdf(k - 1, n, p_null)
        
        # Calculate confidence interval
        ci_lower, ci_upper = self._wilson_score_interval(k, n, 0.95)
        
        # Calculate score based on optimality and regret
        optimality_score = self._calculate_authority_score(effectiveness_rate, p_value, n)
        regret_score = max(0.0, min(1.0, 1.0 - abs(avg_regret) / 0.02))  # Penalty for high regret
        score = 0.6 * optimality_score + 0.4 * regret_score
        
        validation_status = "PASS" if (p_value < self.minimum_significance_level and 
                                      effectiveness_rate > 0.6 and 
                                      abs(avg_regret) < 0.01) else "FAIL"
        
        return StatisticalAuthorityScore(
            component=ComponentType.BROKER_CLOSE,
            score=score,
            p_value=p_value,
            confidence_interval=(ci_lower, ci_upper),
            sample_size=n,
            statistical_test="binomial_optimality_with_regret",
            timestamp=datetime.utcnow(),
            validation_status=validation_status
        )
    
    def _wilson_score_interval(self, k: int, n: int, confidence_level: float = 0.95) -> Tuple[float, float]:
        """
        Calculate Wilson score interval for proportion confidence interval
        """
        if n == 0:
            return (0.0, 0.0)
        
        z = stats.norm.ppf(1 - (1 - confidence_level) / 2)  # Z-score for confidence level
        p_hat = k / n
        
        denominator = 1 + z**2 / n
        centre_adjusted_probability = (p_hat + z**2 / (2 * n)) / denominator
        adjusted_standard_deviation = math.sqrt((p_hat * (1 - p_hat) + z**2 / (4 * n)) / n) / denominator
        
        lower = centre_adjusted_probability - z * adjusted_standard_deviation
        upper = centre_adjusted_probability + z * adjusted_standard_deviation
        
        return (max(0.0, lower), min(1.0, upper))
    
    def _calculate_authority_score(self, accuracy: float, p_value: float, sample_size: int) -> float:
        """
        Calculate normalized authority score based on accuracy, significance, and sample size
        """
        if p_value >= self.minimum_significance_level:
            return 0.0  # Not statistically significant
        
        if sample_size < self.minimum_sample_size:
            return 0.0  # Insufficient sample size
        
        # Base score from accuracy
        base_score = max(0.0, min(1.0, accuracy))
        
        # Apply significance penalty (lower p-value = higher confidence)
        significance_factor = max(0.0, min(1.0, 1.0 - p_value / self.minimum_significance_level))
        
        # Apply sample size bonus (larger samples = more reliable)
        sample_size_factor = min(1.0, sample_size / (self.minimum_sample_size * 4))
        
        # Combine factors
        score = base_score * (0.7 + 0.3 * significance_factor) * (0.8 + 0.2 * sample_size_factor)
        
        return max(0.0, min(1.0, score))


# Global instance
statistical_authority_engine = StatisticalAuthorityScoreEngine()