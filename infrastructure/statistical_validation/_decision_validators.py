"""E5.T5 (infra-only mechanical split): per-stage decision validators extracted from
``DecisionDefensibilityValidator``.

Behavior-preserving mixin — the 6 ``validate_*_decision`` methods moved verbatim
(signatures, ``self`` semantics, returned reports UNCHANGED) and composed via inheritance.
The public ``DecisionDefensibilityReport`` dataclass moves here too and is re-exported from
``decision_defensibility_validator`` to preserve its import path (no circular import).
Conservative top-level imports. No layer move, no logic change.
"""
import numpy as np
import pandas as pd
from scipy import stats
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import hashlib
import json


@dataclass
class DecisionDefensibilityReport:
    """Represents the defensibility validation report for a decision"""
    decision_id: str
    component: str
    is_defensible: bool
    validation_results: Dict[str, Any]
    supporting_evidence: List[Dict[str, Any]]
    timestamp: datetime
    audit_trail: str


class _DecisionValidatorsMixin:
    """Per-stage public validate_*_decision orchestration."""

    def validate_watcher_decision(self, watcher_data: Dict[str, Any], 
                                historical_data: List[Dict[str, Any]]) -> DecisionDefensibilityReport:
        """
        Validate defensibility of watcher decision
        """
        decision_id = self._generate_decision_id(watcher_data)
        validation_results = {}
        supporting_evidence = []
        
        # Test 1: Statistical significance of observation
        sig_result = self._test_statistical_significance(watcher_data, historical_data)
        validation_results['statistical_significance'] = sig_result
        if sig_result['passed']:
            supporting_evidence.append({
                'type': 'statistical_significance',
                'metric': 'p_value',
                'value': sig_result['p_value'],
                'threshold': sig_result['threshold'],
                'passed': True
            })
        
        # Test 2: Historical accuracy validation
        acc_result = self._test_historical_accuracy(watcher_data, historical_data)
        validation_results['historical_accuracy'] = acc_result
        if acc_result['passed']:
            supporting_evidence.append({
                'type': 'historical_accuracy',
                'metric': 'accuracy_rate',
                'value': acc_result['accuracy_rate'],
                'threshold': acc_result['threshold'],
                'passed': True
            })
        
        # Test 3: Signal-to-noise ratio
        snr_result = self._test_signal_to_noise_ratio(watcher_data, historical_data)
        validation_results['signal_to_noise_ratio'] = snr_result
        if snr_result['passed']:
            supporting_evidence.append({
                'type': 'signal_to_noise_ratio',
                'metric': 'snr',
                'value': snr_result['snr'],
                'threshold': snr_result['threshold'],
                'passed': True
            })
        
        # Overall defensibility assessment
        passed_tests = sum(1 for result in validation_results.values() if result.get('passed', False))
        total_tests = len(validation_results)
        evidence_score = passed_tests / total_tests if total_tests > 0 else 0.0
        
        is_defensible = evidence_score >= self.minimum_evidence_threshold
        
        # Create audit trail
        audit_trail = self._create_audit_trail(decision_id, 'WATCHER', validation_results, supporting_evidence)
        
        return DecisionDefensibilityReport(
            decision_id=decision_id,
            component='WATCHER',
            is_defensible=is_defensible,
            validation_results=validation_results,
            supporting_evidence=supporting_evidence,
            timestamp=datetime.utcnow(),
            audit_trail=audit_trail
        )
    
    def validate_engine_decision(self, engine_data: Dict[str, Any], 
                               historical_data: List[Dict[str, Any]]) -> DecisionDefensibilityReport:
        """
        Validate defensibility of engine decision
        """
        decision_id = self._generate_decision_id(engine_data)
        validation_results = {}
        supporting_evidence = []
        
        # Test 1: Statistical significance of interpretation
        sig_result = self._test_engine_interpretation_significance(engine_data, historical_data)
        validation_results['interpretation_significance'] = sig_result
        if sig_result['passed']:
            supporting_evidence.append({
                'type': 'interpretation_significance',
                'metric': 'p_value',
                'value': sig_result['p_value'],
                'threshold': sig_result['threshold'],
                'passed': True
            })
        
        # Test 2: False positive rate validation
        fp_result = self._test_false_positive_rate(engine_data, historical_data)
        validation_results['false_positive_rate'] = fp_result
        if fp_result['passed']:
            supporting_evidence.append({
                'type': 'false_positive_rate',
                'metric': 'fp_rate',
                'value': fp_result['fp_rate'],
                'threshold': fp_result['threshold'],
                'passed': True
            })
        
        # Test 3: Confidence interval validation
        ci_result = self._test_confidence_intervals(engine_data, historical_data)
        validation_results['confidence_intervals'] = ci_result
        if ci_result['passed']:
            supporting_evidence.append({
                'type': 'confidence_intervals',
                'metric': 'interval_width',
                'value': ci_result['interval_width'],
                'threshold': ci_result['threshold'],
                'passed': True
            })
        
        # Overall defensibility assessment
        passed_tests = sum(1 for result in validation_results.values() if result.get('passed', False))
        total_tests = len(validation_results)
        evidence_score = passed_tests / total_tests if total_tests > 0 else 0.0
        
        is_defensible = evidence_score >= self.minimum_evidence_threshold
        
        # Create audit trail
        audit_trail = self._create_audit_trail(decision_id, 'ENGINE', validation_results, supporting_evidence)
        
        return DecisionDefensibilityReport(
            decision_id=decision_id,
            component='ENGINE',
            is_defensible=is_defensible,
            validation_results=validation_results,
            supporting_evidence=supporting_evidence,
            timestamp=datetime.utcnow(),
            audit_trail=audit_trail
        )
    
    def validate_fusion_decision(self, fusion_data: Dict[str, Any], 
                               historical_data: List[Dict[str, Any]]) -> DecisionDefensibilityReport:
        """
        Validate defensibility of fusion decision
        """
        decision_id = self._generate_decision_id(fusion_data)
        validation_results = {}
        supporting_evidence = []
        
        # Test 1: Statistical significance of fusion
        sig_result = self._test_fusion_significance(fusion_data, historical_data)
        validation_results['fusion_significance'] = sig_result
        if sig_result['passed']:
            supporting_evidence.append({
                'type': 'fusion_significance',
                'metric': 'p_value',
                'value': sig_result['p_value'],
                'threshold': sig_result['threshold'],
                'passed': True
            })
        
        # Test 2: Correlation validation between contributors
        corr_result = self._test_contributor_correlation(fusion_data, historical_data)
        validation_results['contributor_correlation'] = corr_result
        if corr_result['passed']:
            supporting_evidence.append({
                'type': 'contributor_correlation',
                'metric': 'max_correlation',
                'value': corr_result['max_correlation'],
                'threshold': corr_result['threshold'],
                'passed': True
            })
        
        # Test 3: Value-addition test (does fusion improve over individual signals?)
        va_result = self._test_fusion_value_addition(fusion_data, historical_data)
        validation_results['value_addition'] = va_result
        if va_result['passed']:
            supporting_evidence.append({
                'type': 'value_addition',
                'metric': 'improvement_rate',
                'value': va_result['improvement_rate'],
                'threshold': va_result['threshold'],
                'passed': True
            })
        
        # Overall defensibility assessment
        passed_tests = sum(1 for result in validation_results.values() if result.get('passed', False))
        total_tests = len(validation_results)
        evidence_score = passed_tests / total_tests if total_tests > 0 else 0.0
        
        is_defensible = evidence_score >= self.minimum_evidence_threshold
        
        # Create audit trail
        audit_trail = self._create_audit_trail(decision_id, 'FUSION', validation_results, supporting_evidence)
        
        return DecisionDefensibilityReport(
            decision_id=decision_id,
            component='FUSION',
            is_defensible=is_defensible,
            validation_results=validation_results,
            supporting_evidence=supporting_evidence,
            timestamp=datetime.utcnow(),
            audit_trail=audit_trail
        )
    
    def validate_strategy_decision(self, strategy_data: Dict[str, Any], 
                                 historical_data: List[Dict[str, Any]]) -> DecisionDefensibilityReport:
        """
        Validate defensibility of strategy decision
        """
        decision_id = self._generate_decision_id(strategy_data)
        validation_results = {}
        supporting_evidence = []
        
        # Test 1: Statistical significance of strategy selection
        sig_result = self._test_strategy_significance(strategy_data, historical_data)
        validation_results['strategy_significance'] = sig_result
        if sig_result['passed']:
            supporting_evidence.append({
                'type': 'strategy_significance',
                'metric': 'p_value',
                'value': sig_result['p_value'],
                'threshold': sig_result['threshold'],
                'passed': True
            })
        
        # Test 2: Out-of-sample validation
        oos_result = self._test_out_of_sample_validation(strategy_data, historical_data)
        validation_results['out_of_sample_validation'] = oos_result
        if oos_result['passed']:
            supporting_evidence.append({
                'type': 'out_of_sample_validation',
                'metric': 'oos_performance',
                'value': oos_result['oos_performance'],
                'threshold': oos_result['threshold'],
                'passed': True
            })
        
        # Test 3: Risk-adjusted returns validation
        rar_result = self._test_risk_adjusted_returns(strategy_data, historical_data)
        validation_results['risk_adjusted_returns'] = rar_result
        if rar_result['passed']:
            supporting_evidence.append({
                'type': 'risk_adjusted_returns',
                'metric': 'sharpe_ratio',
                'value': rar_result['sharpe_ratio'],
                'threshold': rar_result['threshold'],
                'passed': True
            })
        
        # Overall defensibility assessment
        passed_tests = sum(1 for result in validation_results.values() if result.get('passed', False))
        total_tests = len(validation_results)
        evidence_score = passed_tests / total_tests if total_tests > 0 else 0.0
        
        is_defensible = evidence_score >= self.minimum_evidence_threshold
        
        # Create audit trail
        audit_trail = self._create_audit_trail(decision_id, 'STRATEGY', validation_results, supporting_evidence)
        
        return DecisionDefensibilityReport(
            decision_id=decision_id,
            component='STRATEGY',
            is_defensible=is_defensible,
            validation_results=validation_results,
            supporting_evidence=supporting_evidence,
            timestamp=datetime.utcnow(),
            audit_trail=audit_trail
        )
    
    def validate_broker_decision(self, broker_data: Dict[str, Any], 
                               historical_data: List[Dict[str, Any]]) -> DecisionDefensibilityReport:
        """
        Validate defensibility of broker decision
        """
        decision_id = self._generate_decision_id(broker_data)
        validation_results = {}
        supporting_evidence = []
        
        # Test 1: Execution quality validation
        eq_result = self._test_execution_quality(broker_data, historical_data)
        validation_results['execution_quality'] = eq_result
        if eq_result['passed']:
            supporting_evidence.append({
                'type': 'execution_quality',
                'metric': 'quality_score',
                'value': eq_result['quality_score'],
                'threshold': eq_result['threshold'],
                'passed': True
            })
        
        # Test 2: Slippage control validation
        slip_result = self._test_slippage_control(broker_data, historical_data)
        validation_results['slippage_control'] = slip_result
        if slip_result['passed']:
            supporting_evidence.append({
                'type': 'slippage_control',
                'metric': 'avg_slippage',
                'value': slip_result['avg_slippage'],
                'threshold': slip_result['threshold'],
                'passed': True
            })
        
        # Test 3: Order validation completeness
        ov_result = self._test_order_validation_completeness(broker_data, historical_data)
        validation_results['order_validation_completeness'] = ov_result
        if ov_result['passed']:
            supporting_evidence.append({
                'type': 'order_validation_completeness',
                'metric': 'validation_score',
                'value': ov_result['validation_score'],
                'threshold': ov_result['threshold'],
                'passed': True
            })
        
        # Overall defensibility assessment
        passed_tests = sum(1 for result in validation_results.values() if result.get('passed', False))
        total_tests = len(validation_results)
        evidence_score = passed_tests / total_tests if total_tests > 0 else 0.0
        
        is_defensible = evidence_score >= self.minimum_evidence_threshold
        
        # Create audit trail
        audit_trail = self._create_audit_trail(decision_id, 'BROKER', validation_results, supporting_evidence)
        
        return DecisionDefensibilityReport(
            decision_id=decision_id,
            component='BROKER',
            is_defensible=is_defensible,
            validation_results=validation_results,
            supporting_evidence=supporting_evidence,
            timestamp=datetime.utcnow(),
            audit_trail=audit_trail
        )
    
    def validate_broker_close_decision(self, close_data: Dict[str, Any], 
                                     historical_data: List[Dict[str, Any]]) -> DecisionDefensibilityReport:
        """
        Validate defensibility of broker close decision
        """
        decision_id = self._generate_decision_id(close_data)
        validation_results = {}
        supporting_evidence = []
        
        # Test 1: Exit timing optimality
        et_result = self._test_exit_timing_optimality(close_data, historical_data)
        validation_results['exit_timing_optimality'] = et_result
        if et_result['passed']:
            supporting_evidence.append({
                'type': 'exit_timing_optimality',
                'metric': 'optimality_score',
                'value': et_result['optimality_score'],
                'threshold': et_result['threshold'],
                'passed': True
            })
        
        # Test 2: PnL calculation accuracy
        pnl_result = self._test_pnl_calculation_accuracy(close_data, historical_data)
        validation_results['pnl_calculation_accuracy'] = pnl_result
        if pnl_result['passed']:
            supporting_evidence.append({
                'type': 'pnl_calculation_accuracy',
                'metric': 'calculation_error',
                'value': pnl_result['calculation_error'],
                'threshold': pnl_result['threshold'],
                'passed': True
            })
        
        # Test 3: Exit reason validation
        er_result = self._test_exit_reason_validation(close_data, historical_data)
        validation_results['exit_reason_validation'] = er_result
        if er_result['passed']:
            supporting_evidence.append({
                'type': 'exit_reason_validation',
                'metric': 'reason_confidence',
                'value': er_result['reason_confidence'],
                'threshold': er_result['threshold'],
                'passed': True
            })
        
        # Overall defensibility assessment
        passed_tests = sum(1 for result in validation_results.values() if result.get('passed', False))
        total_tests = len(validation_results)
        evidence_score = passed_tests / total_tests if total_tests > 0 else 0.0
        
        is_defensible = evidence_score >= self.minimum_evidence_threshold
        
        # Create audit trail
        audit_trail = self._create_audit_trail(decision_id, 'BROKER_CLOSE', validation_results, supporting_evidence)
        
        return DecisionDefensibilityReport(
            decision_id=decision_id,
            component='BROKER_CLOSE',
            is_defensible=is_defensible,
            validation_results=validation_results,
            supporting_evidence=supporting_evidence,
            timestamp=datetime.utcnow(),
            audit_trail=audit_trail
        )
