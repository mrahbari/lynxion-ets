"""E5.T5 (infra-only mechanical split): statistical-test suite extracted from
``DecisionDefensibilityValidator``.

Behavior-preserving mixin — the ~20 ``_test_*`` statistical-test methods moved verbatim
(signatures, ``self`` semantics, computed results UNCHANGED) and composed back via
inheritance. Conservative top-level imports. No layer move, no logic change.
"""
import numpy as np
import pandas as pd
from scipy import stats
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import hashlib
import json


class _DecisionTestsMixin:
    """Per-stage statistical-test helpers (_test_* methods)."""

    def _test_statistical_significance(self, current_data: Dict[str, Any], 
                                    historical_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Test statistical significance of current observation"""
        if len(historical_data) < 30:
            return {
                'passed': False,
                'p_value': 1.0,
                'threshold': 0.05,
                'sample_size': len(historical_data),
                'reason': 'insufficient_sample_size'
            }
        
        # Perform one-sample t-test against null hypothesis
        values = [obs.get('value', 0) for obs in historical_data if 'value' in obs]
        if not values:
            return {
                'passed': False,
                'p_value': 1.0,
                'threshold': 0.05,
                'sample_size': 0,
                'reason': 'no_historical_values'
            }
        
        current_value = current_data.get('value', 0)
        t_stat, p_value = stats.ttest_1samp(values, current_value)
        
        passed = p_value < 0.05  # 95% confidence level
        return {
            'passed': passed,
            'p_value': p_value,
            'threshold': 0.05,
            'sample_size': len(values),
            'reason': 'significant' if passed else 'not_significant'
        }
    
    def _test_historical_accuracy(self, current_data: Dict[str, Any], 
                                historical_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Test historical accuracy of watcher"""
        correct_predictions = sum(1 for obs in historical_data if obs.get('was_correct', False))
        total_predictions = len([obs for obs in historical_data if 'was_correct' in obs])
        
        if total_predictions == 0:
            return {
                'passed': False,
                'accuracy_rate': 0.0,
                'threshold': 0.6,
                'total_predictions': 0,
                'reason': 'no_accuracy_data'
            }
        
        accuracy_rate = correct_predictions / total_predictions
        passed = accuracy_rate >= 0.6  # 60% minimum accuracy
        
        return {
            'passed': passed,
            'accuracy_rate': accuracy_rate,
            'threshold': 0.6,
            'total_predictions': total_predictions,
            'reason': 'accurate' if passed else 'inaccurate'
        }
    
    def _test_signal_to_noise_ratio(self, current_data: Dict[str, Any], 
                                  historical_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Test signal-to-noise ratio"""
        if len(historical_data) < 10:
            return {
                'passed': False,
                'snr': 0.0,
                'threshold': 1.0,
                'sample_size': len(historical_data),
                'reason': 'insufficient_data'
            }
        
        # Calculate signal (trend) and noise (variance around trend)
        values = [obs.get('value', 0) for obs in historical_data if 'value' in obs]
        if len(values) < 2:
            return {
                'passed': False,
                'snr': 0.0,
                'threshold': 1.0,
                'sample_size': len(values),
                'reason': 'insufficient_values'
            }
        
        # Simple linear regression to estimate signal vs noise
        x = np.arange(len(values))
        coeffs = np.polyfit(x, values, 1)  # Linear fit
        fitted_values = np.polyval(coeffs, x)
        
        signal_variance = np.var(fitted_values)
        noise_variance = np.var(np.array(values) - fitted_values)
        
        snr = signal_variance / (noise_variance + 1e-8)  # Add small value to avoid division by zero
        passed = snr >= 1.0  # Minimum SNR of 1.0
        
        return {
            'passed': passed,
            'snr': snr,
            'threshold': 1.0,
            'sample_size': len(values),
            'reason': 'good_snr' if passed else 'poor_snr'
        }
    
    def _test_engine_interpretation_significance(self, current_data: Dict[str, Any], 
                                               historical_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Test significance of engine interpretation"""
        if len(historical_data) < 30:
            return {
                'passed': False,
                'p_value': 1.0,
                'threshold': 0.05,
                'sample_size': len(historical_data),
                'reason': 'insufficient_sample_size'
            }
        
        # Test accuracy of interpretations
        correct_interps = sum(1 for interp in historical_data if interp.get('was_correct', False))
        total_interps = len([interp for interp in historical_data if 'was_correct' in interp])
        
        if total_interps == 0:
            return {
                'passed': False,
                'p_value': 1.0,
                'threshold': 0.05,
                'sample_size': 0,
                'reason': 'no_accuracy_data'
            }
        
        # Binomial test for accuracy significance
        n = total_interps
        k = correct_interps
        p_null = 0.5  # Null hypothesis: 50% accuracy (random)
        
        if k <= n * p_null:
            p_value = stats.binom.cdf(k, n, p_null)
        else:
            p_value = 1 - stats.binom.cdf(k - 1, n, p_null)
        
        passed = p_value < 0.05  # Significant improvement over random
        return {
            'passed': passed,
            'p_value': p_value,
            'threshold': 0.05,
            'sample_size': total_interps,
            'reason': 'significant' if passed else 'not_significant'
        }
    
    def _test_false_positive_rate(self, current_data: Dict[str, Any], 
                                historical_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Test false positive rate of engine"""
        false_positives = sum(1 for interp in historical_data if interp.get('false_positive', False))
        total_interps = len([interp for interp in historical_data if 'false_positive' in interp])
        
        if total_interps == 0:
            return {
                'passed': False,
                'fp_rate': 1.0,
                'threshold': 0.2,
                'total_interps': 0,
                'reason': 'no_fp_data'
            }
        
        fp_rate = false_positives / total_interps
        passed = fp_rate <= 0.2  # Max 20% false positive rate
        
        return {
            'passed': passed,
            'fp_rate': fp_rate,
            'threshold': 0.2,
            'total_interps': total_interps,
            'reason': 'acceptable_fp_rate' if passed else 'high_fp_rate'
        }
    
    def _test_confidence_intervals(self, current_data: Dict[str, Any], 
                                 historical_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Test validity of confidence intervals"""
        # Check if confidence intervals are reasonable
        if 'confidence' in current_data:
            confidence = current_data['confidence']
            passed = 0.05 <= confidence <= 0.95  # Reasonable confidence range
            interval_width = 1.0 - confidence
            
            return {
                'passed': passed,
                'interval_width': interval_width,
                'threshold': 0.95,  # Max 95% interval width
                'confidence': confidence,
                'reason': 'valid_interval' if passed else 'invalid_interval'
            }
        
        return {
            'passed': False,
            'interval_width': 1.0,
            'threshold': 0.95,
            'confidence': 0.0,
            'reason': 'no_confidence_data'
        }
    
    def _test_fusion_significance(self, current_data: Dict[str, Any], 
                                historical_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Test significance of fusion decision"""
        if len(historical_data) < 30:
            return {
                'passed': False,
                'p_value': 1.0,
                'threshold': 0.05,
                'sample_size': len(historical_data),
                'reason': 'insufficient_sample_size'
            }
        
        # Test effectiveness of fusions
        correct_fusions = sum(1 for fusion in historical_data if fusion.get('was_correct', False))
        total_fusions = len([fusion for fusion in historical_data if 'was_correct' in fusion])
        
        if total_fusions == 0:
            return {
                'passed': False,
                'p_value': 1.0,
                'threshold': 0.05,
                'sample_size': 0,
                'reason': 'no_accuracy_data'
            }
        
        # Binomial test for effectiveness
        n = total_fusions
        k = correct_fusions
        p_null = 0.5  # Null hypothesis: 50% effectiveness (random)
        
        if k <= n * p_null:
            p_value = stats.binom.cdf(k, n, p_null)
        else:
            p_value = 1 - stats.binom.cdf(k - 1, n, p_null)
        
        passed = p_value < 0.05  # Significant improvement over random
        return {
            'passed': passed,
            'p_value': p_value,
            'threshold': 0.05,
            'sample_size': total_fusions,
            'reason': 'significant' if passed else 'not_significant'
        }
    
    def _test_contributor_correlation(self, current_data: Dict[str, Any], 
                                   historical_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Test correlation between fusion contributors"""
        if 'contributors' not in current_data or len(current_data['contributors']) < 2:
            return {
                'passed': True,  # No correlation to test
                'max_correlation': 0.0,
                'threshold': 0.7,
                'num_contributors': len(current_data.get('contributors', {})),
                'reason': 'insufficient_contributors'
            }
        
        # For this test, we'll assume we have historical correlation data
        # In practice, this would require more complex correlation tracking
        weights = list(current_data['contributors'].values())
        if len(weights) < 2:
            return {
                'passed': True,
                'max_correlation': 0.0,
                'threshold': 0.7,
                'num_contributors': len(weights),
                'reason': 'insufficient_weights'
            }
        
        # Calculate a simple measure of weight similarity as proxy for correlation
        avg_weight = np.mean(weights)
        weight_std = np.std(weights)
        similarity_score = weight_std / (avg_weight + 1e-8)  # Avoid division by zero
        
        # If weights are very similar, contributors might be correlated
        passed = similarity_score > 0.1  # Require some diversity in weights
        return {
            'passed': passed,
            'max_correlation': similarity_score,
            'threshold': 0.7,
            'num_contributors': len(weights),
            'reason': 'diverse_weights' if passed else 'similar_weights'
        }
    
    def _test_fusion_value_addition(self, current_data: Dict[str, Any], 
                                  historical_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Test if fusion adds value over individual signals"""
        value_added = sum(1 for fusion in historical_data if fusion.get('fusion_added_value', False))
        total_fusions = len([fusion for fusion in historical_data if 'fusion_added_value' in fusion])
        
        if total_fusions == 0:
            return {
                'passed': False,
                'improvement_rate': 0.0,
                'threshold': 0.5,
                'total_fusions': 0,
                'reason': 'no_value_addition_data'
            }
        
        improvement_rate = value_added / total_fusions
        passed = improvement_rate >= 0.5  # At least 50% of fusions should add value
        
        return {
            'passed': passed,
            'improvement_rate': improvement_rate,
            'threshold': 0.5,
            'total_fusions': total_fusions,
            'reason': 'adds_value' if passed else 'no_value_addition'
        }
    
    def _test_strategy_significance(self, current_data: Dict[str, Any], 
                                  historical_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Test significance of strategy selection"""
        if len(historical_data) < 30:
            return {
                'passed': False,
                'p_value': 1.0,
                'threshold': 0.05,
                'sample_size': len(historical_data),
                'reason': 'insufficient_sample_size'
            }
        
        # Test profitability of strategy decisions
        profitable_decisions = sum(1 for decision in historical_data if decision.get('was_profitable', False))
        total_decisions = len([decision for decision in historical_data if 'was_profitable' in decision])
        
        if total_decisions == 0:
            return {
                'passed': False,
                'p_value': 1.0,
                'threshold': 0.05,
                'sample_size': 0,
                'reason': 'no_profitability_data'
            }
        
        # Binomial test for profitability significance
        n = total_decisions
        k = profitable_decisions
        p_null = 0.5  # Null hypothesis: 50% profitability (random)
        
        if k <= n * p_null:
            p_value = stats.binom.cdf(k, n, p_null)
        else:
            p_value = 1 - stats.binom.cdf(k - 1, n, p_null)
        
        passed = p_value < 0.05  # Significant improvement over random
        return {
            'passed': passed,
            'p_value': p_value,
            'threshold': 0.05,
            'sample_size': total_decisions,
            'reason': 'significant' if passed else 'not_significant'
        }
    
    def _test_out_of_sample_validation(self, current_data: Dict[str, Any], 
                                     historical_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Test out-of-sample validation of strategy"""
        # Check if strategy was validated out-of-sample
        oos_validated = current_data.get('out_of_sample_validated', False)
        oos_performance = current_data.get('out_of_sample_performance', 0.0)
        
        passed = oos_validated and oos_performance > 0.0
        return {
            'passed': passed,
            'oos_performance': oos_performance,
            'threshold': 0.0,
            'oos_validated': oos_validated,
            'reason': 'oos_validated' if passed else 'not_oos_validated'
        }
    
    def _test_risk_adjusted_returns(self, current_data: Dict[str, Any], 
                                  historical_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Test risk-adjusted returns of strategy"""
        returns = [decision.get('return_pct', 0.0) for decision in historical_data if 'return_pct' in decision]
        
        if len(returns) < 2:
            return {
                'passed': False,
                'sharpe_ratio': 0.0,
                'threshold': 0.1,
                'sample_size': len(returns),
                'reason': 'insufficient_returns_data'
            }
        
        mean_return = np.mean(returns)
        std_return = np.std(returns)
        
        if std_return == 0:
            sharpe_ratio = np.inf if mean_return > 0 else -np.inf
        else:
            sharpe_ratio = mean_return / std_return
        
        passed = sharpe_ratio > 0.1  # Minimum Sharpe ratio of 0.1
        return {
            'passed': passed,
            'sharpe_ratio': sharpe_ratio,
            'threshold': 0.1,
            'sample_size': len(returns),
            'reason': 'good_risk_adjusted_returns' if passed else 'poor_risk_adjusted_returns'
        }
    
    def _test_execution_quality(self, current_data: Dict[str, Any], 
                              historical_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Test execution quality of broker"""
        quality_score = current_data.get('execution_quality_score', 0.0)
        passed = quality_score >= 0.7  # Minimum quality score of 70%
        
        return {
            'passed': passed,
            'quality_score': quality_score,
            'threshold': 0.7,
            'reason': 'good_quality' if passed else 'poor_quality'
        }
    
    def _test_slippage_control(self, current_data: Dict[str, Any], 
                             historical_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Test slippage control of broker"""
        slippage = current_data.get('slippage', 0.0)
        passed = abs(slippage) <= 1.0  # Maximum 1% slippage
        
        return {
            'passed': passed,
            'avg_slippage': slippage,
            'threshold': 1.0,
            'reason': 'good_slippage_control' if passed else 'poor_slippage_control'
        }
    
    def _test_order_validation_completeness(self, current_data: Dict[str, Any], 
                                          historical_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Test completeness of order validation"""
        validation_checks = current_data.get('validation_checks', {})
        required_checks = ['margin_availability_check', 'risk_profile_compliance']
        
        passed = all(check in validation_checks for check in required_checks)
        validation_score = sum(1 for check in required_checks if check in validation_checks) / len(required_checks)
        
        return {
            'passed': passed,
            'validation_score': validation_score,
            'threshold': 1.0,
            'missing_checks': [check for check in required_checks if check not in validation_checks],
            'reason': 'complete_validation' if passed else 'incomplete_validation'
        }
    
    def _test_exit_timing_optimality(self, current_data: Dict[str, Any], 
                                   historical_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Test optimality of exit timing"""
        optimality_score = current_data.get('exit_timing_significance', 0.0)
        passed = optimality_score >= 0.6  # Minimum optimality score of 60%
        
        return {
            'passed': passed,
            'optimality_score': optimality_score,
            'threshold': 0.6,
            'reason': 'optimal_timing' if passed else 'suboptimal_timing'
        }
    
    def _test_pnl_calculation_accuracy(self, current_data: Dict[str, Any], 
                                     historical_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Test accuracy of PnL calculation"""
        # For this test, we'll check if PnL calculation follows proper methodology
        pnl = current_data.get('pnl', 0.0)
        roi_pct = current_data.get('roi_pct', 0.0)
        holding_seconds = current_data.get('holding_seconds', 0)
        
        # Basic validation: if we have ROI and holding time, annualized return should be reasonable
        if holding_seconds > 0 and roi_pct != 0:
            # Annualized return calculation
            years = holding_seconds / (365 * 24 * 3600)
            if years > 0:
                annualized_return = (1 + roi_pct) ** (1 / years) - 1
                passed = abs(annualized_return) < 10  # Less than 1000% annual return (reasonable limit)
            else:
                passed = True  # Very short holding period, hard to validate
        else:
            passed = True  # Insufficient data to validate
        
        return {
            'passed': passed,
            'calculation_error': 0.0 if passed else 1.0,
            'threshold': 0.0,
            'reason': 'accurate_calculation' if passed else 'potential_error'
        }
    
    def _test_exit_reason_validation(self, current_data: Dict[str, Any], 
                                   historical_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Test validation of exit reason"""
        exit_reason = current_data.get('exit_reason', '').upper()
        valid_reasons = ['TAKE_PROFIT', 'STOP_LOSS', 'TIMEOUT', 'MANUAL', 'TRAILING_STOP']
        
        passed = exit_reason in valid_reasons
        reason_confidence = 1.0 if passed else 0.0
        
        return {
            'passed': passed,
            'reason_confidence': reason_confidence,
            'threshold': 0.9,
            'exit_reason': exit_reason,
            'reason': 'valid_reason' if passed else 'invalid_reason'
        }
