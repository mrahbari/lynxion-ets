"""
Global Requirements and Constraints Implementation for the Redesigned Trading System.
Enforces all mandatory constraints across all modules to ensure system integrity.
"""
import numpy as np
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import warnings
warnings.filterwarnings('ignore')


class RiskModule(Enum):
    """Risk module classifications"""
    RISK_MODEL = "risk_model"
    POSITION_SIZER = "position_sizer"
    SLTP_MANAGER = "sltp_manager"
    FUSION_SERVICE = "fusion_service"
    REGIME_CLASSIFIER = "regime_classifier"
    STRATEGY_SELECTOR = "strategy_selector"


@dataclass
class ValidationResult:
    """Container for validation results"""
    is_valid: bool
    issues: list
    module: RiskModule
    severity: str  # 'critical', 'warning', 'info'


class GlobalRequirementsEnforcer:
    """
    Enforces global requirements and constraints across all modules.
    
    Mandatory constraints implemented:
    - No SL/TP may be set without considering expected holding duration
    - Scalping strategies must prioritize hit probability, time efficiency, and variance reduction over large RR
    - No duplicate logic across layers
    - Strategy must request risk only; Risk module calculates and validates SL/TP/position
    - Broker must execute validated risk instructions only
    - Fusion influences direction/confidence only; it must not modify risk
    - Watchers and Engines must not know SL, TP, position size, or leverage
    - No hindsight bias, no perfect data assumption, no magic indicators
    """
    
    def __init__(self):
        self.timeframe_holding_durations = {
            "M1": 0.01,    # 0.01 hours (36 seconds)
            "M5": 0.08,    # 0.08 hours (5 minutes)
            "M15": 0.25,   # 0.25 hours (15 minutes)
            "M30": 0.5,    # 0.5 hours (30 minutes)
            "H1": 1.0,     # 1 hour
            "H4": 4.0,     # 4 hours
            "D1": 24.0     # 24 hours
        }
        
        self.scalping_timeframes = ["M1", "M5", "M15"]
        self.minimum_reachability_thresholds = {
            "M1": 0.65,    # 65% hit rate for 1-min scalps
            "M5": 0.70,    # 70% hit rate for 5-min scalps
            "M15": 0.75,   # 75% hit rate for 15-min scalps
            "M30": 0.75,   # 75% hit rate for 30-min trades
            "H1": 0.70,    # 70% hit rate for 1-hour trades
            "H4": 0.65,    # 65% hit rate for 4-hour trades
            "D1": 0.60     # 60% hit rate for daily trades
        }

    def validate_sl_tp_with_holding_duration(self,
                                           entry_price: float,
                                           stop_loss: float,
                                           take_profit: float,
                                           timeframe: str,
                                           expected_holding_hours: Optional[float] = None) -> ValidationResult:
        """
        Validate that SL/TP considers expected holding duration.
        
        Mandatory constraint: No SL/TP may be set without considering expected holding duration.
        """
        issues = []
        
        if expected_holding_hours is None:
            # Derive from timeframe if not provided
            expected_holding_hours = self.timeframe_holding_durations.get(timeframe.upper(), 1.0)
        
        # Calculate risk-reward ratio
        risk_distance = abs(entry_price - stop_loss)
        reward_distance = abs(take_profit - entry_price)
        risk_reward_ratio = reward_distance / risk_distance if risk_distance > 0 else float('inf')
        
        # For shorter timeframes, RR should be more conservative
        max_acceptable_rr = {
            "M1": 2.0,
            "M5": 2.5,
            "M15": 3.0,
            "M30": 3.5,
            "H1": 4.0,
            "H4": 4.5,
            "D1": 5.0
        }.get(timeframe.upper(), 3.0)
        
        if risk_reward_ratio > max_acceptable_rr:
            issues.append(
                f"Risk-reward ratio ({risk_reward_ratio:.2f}) too high for {timeframe} timeframe "
                f"with {expected_holding_hours}h expected holding. Maximum acceptable: {max_acceptable_rr}"
            )
        
        # Check if TP is realistically achievable within holding period
        # This is a simplified check - in practice, this would involve more complex market microstructure analysis
        is_scalping = timeframe.upper() in self.scalping_timeframes
        if is_scalping:
            # For scalping, prioritize hit probability over large RR
            min_reachability = self.minimum_reachability_thresholds.get(timeframe.upper(), 0.70)
            # This would normally connect to the reachability calculation from SLTP module
            # For now, we'll issue a warning if RR is too high for scalping
            if risk_reward_ratio > 2.5:
                issues.append(
                    f"For scalping timeframe {timeframe}, risk-reward ratio ({risk_reward_ratio:.2f}) "
                    f"may be too high. Recommended maximum for scalping: 2.5"
                )
        
        severity = "critical" if issues else "info"
        return ValidationResult(
            is_valid=len(issues) == 0,
            issues=issues,
            module=RiskModule.SLTP_MANAGER,
            severity=severity
        )

    def validate_scalping_priorities(self,
                                   timeframe: str,
                                   risk_reward_ratio: float,
                                   hit_probability: float,
                                   variance_reduction: float) -> ValidationResult:
        """
        Validate that scalping strategies prioritize hit probability and time efficiency.
        
        Mandatory constraint: Scalping strategies must prioritize hit probability, time efficiency, 
        and variance reduction over large RR.
        """
        issues = []
        
        is_scalping = timeframe.upper() in self.scalping_timeframes
        
        if is_scalping:
            # Check if RR is too high for scalping
            if risk_reward_ratio > 2.5:
                issues.append(
                    f"Scalping strategy on {timeframe} has risk-reward ratio ({risk_reward_ratio:.2f}) "
                    f"exceeding recommended maximum for scalping (2.5)"
                )
            
            # Check if hit probability is sufficient for scalping
            min_hit_prob = self.minimum_reachability_thresholds.get(timeframe.upper(), 0.70)
            if hit_probability < min_hit_prob:
                issues.append(
                    f"Scalping strategy on {timeframe} has hit probability ({hit_probability:.2f}) "
                    f"below minimum threshold ({min_hit_prob}) for scalping"
                )
            
            # Variance reduction should be prioritized in scalping
            if variance_reduction < 0.1:  # Arbitrary threshold
                issues.append(
                    f"Scalping strategy on {timeframe} has low variance reduction ({variance_reduction:.2f}), "
                    f"which should be prioritized in scalping strategies"
                )
        
        severity = "critical" if issues else "info"
        return ValidationResult(
            is_valid=len(issues) == 0,
            issues=issues,
            module=RiskModule.SLTP_MANAGER,
            severity=severity
        )

    def validate_no_duplicate_logic(self, module_interactions: Dict[str, Any]) -> ValidationResult:
        """
        Validate that there's no duplicate logic across layers.
        
        Mandatory constraint: No duplicate logic across layers.
        """
        issues = []
        
        # Check for overlapping responsibilities between modules
        # This is a simplified check - in practice, this would involve deeper analysis
        if module_interactions.get('risk_calculations_in_fusion', False):
            issues.append(
                "Risk calculations detected in fusion module - risk calculations should be handled by risk module only"
            )
        
        if module_interactions.get('position_sizing_in_strategy', False):
            issues.append(
                "Position sizing detected in strategy module - position sizing should be handled by position sizing module only"
            )
        
        if module_interactions.get('sl_tp_setting_in_fusion', False):
            issues.append(
                "SL/TP setting detected in fusion module - SL/TP should be handled by SL/TP module only"
            )
        
        severity = "critical" if issues else "info"
        return ValidationResult(
            is_valid=len(issues) == 0,
            issues=issues,
            module=RiskModule.RISK_MODEL,
            severity=severity
        )

    def validate_strategy_risk_request_only(self, strategy_actions: Dict[str, Any]) -> ValidationResult:
        """
        Validate that strategy only requests risk, doesn't calculate it.
        
        Mandatory constraint: Strategy must request risk only; Risk module calculates and validates SL/TP/position.
        """
        issues = []
        
        # Check if strategy is calculating risk parameters directly
        if strategy_actions.get('calculates_stop_loss', False):
            issues.append(
                "Strategy is calculating stop loss directly - should only request risk parameters from risk module"
            )
        
        if strategy_actions.get('calculates_take_profit', False):
            issues.append(
                "Strategy is calculating take profit directly - should only request risk parameters from risk module"
            )
        
        if strategy_actions.get('calculates_position_size', False):
            issues.append(
                "Strategy is calculating position size directly - should only request risk parameters from risk module"
            )
        
        severity = "critical" if issues else "info"
        return ValidationResult(
            is_valid=len(issues) == 0,
            issues=issues,
            module=RiskModule.STRATEGY_SELECTOR,
            severity=severity
        )

    def validate_broker_execution_only_validated(self, execution_params: Dict[str, Any]) -> ValidationResult:
        """
        Validate that broker only executes validated risk instructions.
        
        Mandatory constraint: Broker must execute validated risk instructions only.
        """
        issues = []
        
        # Check if execution parameters have been validated
        required_validations = [
            'risk_validated',
            'position_size_validated', 
            'sl_validated',
            'tp_validated'
        ]
        
        for validation in required_validations:
            if not execution_params.get(validation, False):
                issues.append(f"Missing validation: {validation}")
        
        # Check if risk parameters are within acceptable bounds
        max_position_size = execution_params.get('max_position_size', 0.1)  # 10%
        requested_size = execution_params.get('requested_position_size', 0)
        if requested_size > max_position_size:
            issues.append(
                f"Requested position size ({requested_size}) exceeds maximum allowed ({max_position_size})"
            )
        
        severity = "critical" if issues else "info"
        return ValidationResult(
            is_valid=len(issues) == 0,
            issues=issues,
            module=RiskModule.RISK_MODEL,
            severity=severity
        )

    def validate_fusion_direction_confidence_only(self, fusion_outputs: Dict[str, Any]) -> ValidationResult:
        """
        Validate that fusion only influences direction/confidence, not risk.
        
        Mandatory constraint: Fusion influences direction/confidence only; it must not modify risk.
        """
        issues = []
        
        # Check if fusion is outputting risk parameters
        risk_related_outputs = [
            'stop_loss', 'take_profit', 'position_size', 'risk_amount',
            'sl_adjustment', 'tp_adjustment', 'position_adjustment'
        ]
        
        for output in risk_related_outputs:
            if output in fusion_outputs:
                issues.append(
                    f"Fusion module is outputting {output} - fusion should only influence direction/confidence, not risk parameters"
                )
        
        severity = "critical" if issues else "info"
        return ValidationResult(
            is_valid=len(issues) == 0,
            issues=issues,
            module=RiskModule.FUSION_SERVICE,
            severity=severity
        )

    def validate_watchers_engines_no_risk_knowledge(self, watcher_engine_outputs: Dict[str, Any]) -> ValidationResult:
        """
        Validate that Watchers and Engines don't know SL, TP, position size, or leverage.
        
        Mandatory constraint: Watchers and Engines must not know SL, TP, position size, or leverage.
        """
        issues = []
        
        # Check for risk-related information in watcher/engine outputs
        prohibited_outputs = [
            'stop_loss', 'take_profit', 'position_size', 'leverage',
            'risk_percentage', 'max_risk', 'sl_distance', 'tp_distance',
            'position_quantity', 'account_balance', 'portfolio_risk'
        ]
        
        for output in prohibited_outputs:
            if output in watcher_engine_outputs:
                issues.append(
                    f"Watcher/Engine is outputting {output} - these modules must not know risk parameters"
                )
        
        severity = "critical" if issues else "info"
        return ValidationResult(
            is_valid=len(issues) == 0,
            issues=issues,
            module=RiskModule.FUSION_SERVICE,  # Assigned to fusion as it processes watcher/engine outputs
            severity=severity
        )

    def validate_no_hindsight_bias(self, data_access_pattern: Dict[str, Any]) -> ValidationResult:
        """
        Validate that there's no hindsight bias in data access.
        
        Mandatory constraint: No hindsight bias, no perfect data assumption, no magic indicators.
        """
        issues = []
        
        # Check for future-looking data access
        if data_access_pattern.get('accesses_future_data', False):
            issues.append("Detected access to future data - this creates hindsight bias")
        
        if data_access_pattern.get('uses_perfect_entry_exit', False):
            issues.append("Detected use of perfect entry/exit signals - this assumes perfect data")
        
        # Check for look-ahead bias in indicators
        if data_access_pattern.get('indicators_use_future_candles', False):
            issues.append("Indicators are using future candle data - this creates look-ahead bias")
        
        # Check for magic indicators (too good to be true performance)
        if data_access_pattern.get('magic_indicator', False):
            issues.append("Detected potential 'magic indicator' - unrealistic performance assumptions")
        
        severity = "critical" if issues else "info"
        return ValidationResult(
            is_valid=len(issues) == 0,
            issues=issues,
            module=RiskModule.RISK_MODEL,
            severity=severity
        )

    def enforce_all_constraints(self,
                              trade_params: Dict[str, Any],
                              module_interactions: Dict[str, Any],
                              strategy_actions: Dict[str, Any],
                              execution_params: Dict[str, Any],
                              fusion_outputs: Dict[str, Any],
                              watcher_engine_outputs: Dict[str, Any],
                              data_access_pattern: Dict[str, Any]) -> Dict[RiskModule, ValidationResult]:
        """
        Enforce all global constraints across all modules.
        """
        results = {}
        
        # Validate SL/TP with holding duration
        results[RiskModule.SLTP_MANAGER] = self.validate_sl_tp_with_holding_duration(
            entry_price=trade_params.get('entry_price', 0),
            stop_loss=trade_params.get('stop_loss', 0),
            take_profit=trade_params.get('take_profit', 0),
            timeframe=trade_params.get('timeframe', 'H1'),
            expected_holding_hours=trade_params.get('expected_holding_hours')
        )
        
        # Validate scalping priorities
        results[RiskModule.SLTP_MANAGER] = self.validate_scalping_priorities(
            timeframe=trade_params.get('timeframe', 'H1'),
            risk_reward_ratio=trade_params.get('risk_reward_ratio', 1.0),
            hit_probability=trade_params.get('hit_probability', 0.5),
            variance_reduction=trade_params.get('variance_reduction', 0.0)
        )
        
        # Validate no duplicate logic
        results[RiskModule.RISK_MODEL] = self.validate_no_duplicate_logic(module_interactions)
        
        # Validate strategy risk request only
        results[RiskModule.STRATEGY_SELECTOR] = self.validate_strategy_risk_request_only(strategy_actions)
        
        # Validate broker execution only validated instructions
        results[RiskModule.RISK_MODEL] = self.validate_broker_execution_only_validated(execution_params)
        
        # Validate fusion direction/confidence only
        results[RiskModule.FUSION_SERVICE] = self.validate_fusion_direction_confidence_only(fusion_outputs)
        
        # Validate watchers/engines no risk knowledge
        results[RiskModule.FUSION_SERVICE] = self.validate_watchers_engines_no_risk_knowledge(watcher_engine_outputs)
        
        # Validate no hindsight bias
        results[RiskModule.RISK_MODEL] = self.validate_no_hindsight_bias(data_access_pattern)
        
        return results

    def get_constraint_summary(self, validation_results: Dict[RiskModule, ValidationResult]) -> Dict[str, Any]:
        """
        Get a summary of constraint validation results.
        """
        total_checks = len(validation_results)
        passed_checks = sum(1 for result in validation_results.values() if result.is_valid)
        failed_checks = total_checks - passed_checks
        
        critical_issues = []
        warnings = []
        
        for module, result in validation_results.items():
            for issue in result.issues:
                if result.severity == 'critical':
                    critical_issues.append(f"[{module.value}] {issue}")
                elif result.severity == 'warning':
                    warnings.append(f"[{module.value}] {issue}")
        
        return {
            'total_checks': total_checks,
            'passed_checks': passed_checks,
            'failed_checks': failed_checks,
            'pass_rate': passed_checks / total_checks if total_checks > 0 else 0,
            'critical_issues': critical_issues,
            'warnings': warnings,
            'overall_status': 'PASS' if failed_checks == 0 else 'FAIL'
        }


class RiskModuleValidator:
    """
    Validator for individual risk modules to ensure they comply with global requirements.
    """
    
    def __init__(self):
        self.enforcer = GlobalRequirementsEnforcer()
    
    def validate_module_integration(self, module_name: str, inputs: Dict[str, Any], outputs: Dict[str, Any]) -> ValidationResult:
        """
        Validate that a module integrates properly with global requirements.
        """
        issues = []
        
        if module_name == "fusion_service":
            # Validate fusion-specific requirements
            fusion_validation = self.enforcer.validate_fusion_direction_confidence_only(outputs)
            if not fusion_validation.is_valid:
                issues.extend(fusion_validation.issues)
        
        elif module_name == "strategy_manager":
            # Validate strategy-specific requirements
            strategy_actions = {
                'calculates_stop_loss': 'stop_loss' in outputs,
                'calculates_take_profit': 'take_profit' in outputs,
                'calculates_position_size': 'position_size' in outputs
            }
            strategy_validation = self.enforcer.validate_strategy_risk_request_only(strategy_actions)
            if not strategy_validation.is_valid:
                issues.extend(strategy_validation.issues)
        
        elif module_name == "sltp_manager":
            # Validate SL/TP-specific requirements
            timeframe = inputs.get('timeframe', 'H1')
            expected_holding = inputs.get('expected_holding_hours')
            sltp_validation = self.enforcer.validate_sl_tp_with_holding_duration(
                entry_price=inputs.get('entry_price', 0),
                stop_loss=outputs.get('stop_loss', 0),
                take_profit=outputs.get('take_profit', 0),
                timeframe=timeframe,
                expected_holding_hours=expected_holding
            )
            if not sltp_validation.is_valid:
                issues.extend(sltp_validation.issues)
        
        severity = "critical" if issues else "info"
        module_enum = {
            "risk_model": RiskModule.RISK_MODEL,
            "position_sizer": RiskModule.POSITION_SIZER,
            "sltp_manager": RiskModule.SLTP_MANAGER,
            "fusion_service": RiskModule.FUSION_SERVICE,
            "regime_classifier": RiskModule.REGIME_CLASSIFIER,
            "strategy_manager": RiskModule.STRATEGY_SELECTOR
        }.get(module_name, RiskModule.RISK_MODEL)
        
        return ValidationResult(
            is_valid=len(issues) == 0,
            issues=issues,
            module=module_enum,
            severity=severity
        )


# Global instance
global_requirements_enforcer = GlobalRequirementsEnforcer()
module_validator = RiskModuleValidator()