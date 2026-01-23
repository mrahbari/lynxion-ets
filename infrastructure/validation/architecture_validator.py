"""
Validation Module for Redesigned Trading System Architecture
Validates the new architecture against profitability and survival mandates.
"""
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')


@dataclass
class ValidationResults:
    """Container for validation results"""
    survival_rate: float
    profitability_metrics: Dict[str, float]
    risk_metrics: Dict[str, float]
    constraint_compliance: Dict[str, bool]
    overall_score: float
    recommendations: List[str]


class ArchitectureValidator:
    """
    Validates the redesigned trading system architecture against profitability and survival mandates.
    
    Validation criteria:
    - Capital survival must be mathematically enforced
    - Profitability must be statistically scalable
    - Decisions must be evidence-driven
    - Noise must be suppressed
    - Risk must always be priced
    - SL/TP must be reachable and timeframe-consistent
    """
    
    def __init__(self):
        self.survival_threshold = 0.85  # 85% survival rate required
        self.minimum_sharpe_ratio = 0.8  # Minimum Sharpe ratio for profitability
        self.maximum_drawdown = 0.25     # Maximum 25% drawdown allowed
        self.minimum_profit_factor = 1.3 # Minimum 1.3 profit factor
        self.minimum_win_rate = 0.4      # Minimum 40% win rate for scalping strategies

    def validate_survival_mandate(self, portfolio_values: List[float], initial_capital: float) -> Dict[str, Any]:
        """
        Validate that capital survival is mathematically enforced.
        """
        # Calculate drawdowns
        running_max = np.maximum.accumulate(portfolio_values)
        drawdowns = (running_max - portfolio_values) / running_max
        
        # Calculate maximum drawdown
        max_drawdown = float(np.max(drawdowns)) if len(drawdowns) > 0 else 0.0
        
        # Calculate survival rate (percentage of time portfolio is above liquidation threshold)
        liquidation_threshold = initial_capital * 0.7  # 30% loss threshold
        survival_periods = sum(1 for val in portfolio_values if val >= liquidation_threshold)
        survival_rate = survival_periods / len(portfolio_values) if len(portfolio_values) > 0 else 0.0
        
        # Calculate recovery rate (how often portfolio recovers from drawdowns)
        recovery_count = 0
        in_drawdown = False
        for dd in drawdowns:
            if dd > 0.15 and not in_drawdown:  # Deep drawdown (>15%)
                in_drawdown = True
            elif dd < 0.05 and in_drawdown:  # Recovered to <5% drawdown
                recovery_count += 1
                in_drawdown = False
        
        recovery_rate = recovery_count / max(1, len([dd for dd in drawdowns if dd > 0.15]))  # Avoid division by zero
        
        return {
            'survival_rate': survival_rate,
            'max_drawdown': max_drawdown,
            'recovery_rate': recovery_rate,
            'liquidation_events': len(portfolio_values) - survival_periods,
            'meets_survival_threshold': survival_rate >= self.survival_threshold
        }

    def validate_profitability_mandate(self, returns: List[float]) -> Dict[str, float]:
        """
        Validate that profitability is statistically scalable.
        """
        if len(returns) < 10:  # Need sufficient data
            return {
                'sharpe_ratio': 0.0,
                'profit_factor': 1.0,
                'win_rate': 0.0,
                'average_rr': 1.0,
                'total_return': 0.0,
                'meets_minimum_sharpe': False
            }
        
        returns_array = np.array(returns)
        
        # Calculate Sharpe ratio (annualized)
        mean_return = np.mean(returns_array)
        std_return = np.std(returns_array)
        sharpe_ratio = (mean_return / std_return) * np.sqrt(252) if std_return > 0 else 0.0  # Annualized
        
        # Calculate profit factor
        gains = returns_array[returns_array > 0]
        losses = returns_array[returns_array < 0]
        total_profit = np.sum(gains) if len(gains) > 0 else 0.0
        total_loss = abs(np.sum(losses)) if len(losses) > 0 else 1.0  # Avoid division by zero
        profit_factor = total_profit / total_loss if total_loss > 0 else 1.0
        
        # Calculate win rate
        win_rate = len(gains) / len(returns_array) if len(returns_array) > 0 else 0.0
        
        # Calculate average risk-reward ratio
        avg_gain = np.mean(gains) if len(gains) > 0 else 0.0
        avg_loss = abs(np.mean(losses)) if len(losses) > 0 else 1.0
        average_rr = avg_gain / avg_loss if avg_loss > 0 else 1.0
        
        # Calculate total return
        total_return = np.sum(returns_array)
        
        return {
            'sharpe_ratio': float(sharpe_ratio),
            'profit_factor': float(profit_factor),
            'win_rate': float(win_rate),
            'average_rr': float(average_rr),
            'total_return': float(total_return),
            'meets_minimum_sharpe': sharpe_ratio >= self.minimum_sharpe_ratio
        }

    def validate_evidence_driven_decisions(self, decision_log: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate that decisions are evidence-driven.
        """
        if not decision_log:
            return {
                'evidence_based_ratio': 0.0,
                'confidence_correlation': 0.0,
                'meets_evidence_threshold': False
            }
        
        # Count decisions with evidence backing
        evidence_based_count = 0
        total_decisions = len(decision_log)
        
        for decision in decision_log:
            # Decision is evidence-based if it includes confidence scores, supporting indicators, etc.
            has_confidence = 'confidence' in decision and decision['confidence'] is not None
            has_indicators = 'indicators' in decision and len(decision.get('indicators', [])) > 0
            has_regime_context = 'regime_context' in decision and decision['regime_context'] is not None
            
            if has_confidence or has_indicators or has_regime_context:
                evidence_based_count += 1
        
        evidence_based_ratio = evidence_based_count / total_decisions if total_decisions > 0 else 0.0
        
        # Calculate correlation between confidence and outcome (if available)
        confidences = []
        outcomes = []
        for decision in decision_log:
            if 'confidence' in decision and 'outcome' in decision:
                confidences.append(decision['confidence'])
                outcomes.append(1 if decision['outcome'] > 0 else 0)  # 1 for profit, 0 for loss
        
        if len(confidences) > 1 and len(outcomes) > 1:
            try:
                correlation = np.corrcoef(confidences, outcomes)[0, 1]
                confidence_correlation = float(correlation) if not np.isnan(correlation) else 0.0
            except:
                confidence_correlation = 0.0
        else:
            confidence_correlation = 0.0
        
        return {
            'evidence_based_ratio': evidence_based_ratio,
            'confidence_correlation': confidence_correlation,
            'meets_evidence_threshold': evidence_based_ratio >= 0.8  # At least 80% evidence-based
        }

    def validate_noise_suppression(self, signal_quality_log: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Validate that noise is suppressed in the system.
        """
        if not signal_quality_log:
            return {
                'average_signal_noise_ratio': 0.0,
                'noise_suppression_effectiveness': 0.0,
                'meets_noise_threshold': False
            }
        
        # Calculate signal-to-noise ratios
        sn_ratios = []
        for record in signal_quality_log:
            signal_power = record.get('signal_power', 0.0)
            noise_power = record.get('noise_power', 1.0)  # Default to 1 to avoid division by zero
            sn_ratio = signal_power / noise_power if noise_power > 0 else 0.0
            sn_ratios.append(sn_ratio)
        
        avg_sn_ratio = float(np.mean(sn_ratios)) if sn_ratios else 0.0
        
        # Calculate noise suppression effectiveness
        # Compare current SNR to baseline (before noise suppression)
        baseline_snr = 1.0  # Assumed baseline
        noise_suppression_effectiveness = max(0.0, (avg_sn_ratio - baseline_snr) / baseline_snr) if baseline_snr > 0 else 0.0
        
        return {
            'average_signal_noise_ratio': avg_sn_ratio,
            'noise_suppression_effectiveness': noise_suppression_effectiveness,
            'meets_noise_threshold': avg_sn_ratio >= 1.5  # At least 1.5:1 signal-to-noise ratio
        }

    def validate_risk_pricing(self, trade_log: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Validate that risk is always priced appropriately.
        """
        if not trade_log:
            return {
                'risk_reward_realized_ratio': 0.0,
                'risk_pricing_compliance': 0.0,
                'meets_risk_pricing_threshold': False
            }
        
        # Calculate realized risk-reward ratios
        realized_rr_ratios = []
        properly_priced_count = 0
        total_trades = len(trade_log)
        
        for trade in trade_log:
            expected_rr = trade.get('expected_risk_reward', 1.0)
            actual_pnl = trade.get('actual_pnl', 0.0)
            risk_taken = abs(trade.get('risk_amount', 1.0))
            
            if risk_taken > 0:
                # Calculate realized risk-reward based on actual outcome
                realized_rr = abs(actual_pnl) / risk_taken
                realized_rr_ratios.append(realized_rr)
                
                # Check if risk was properly priced (actual outcome roughly matches expectation)
                if abs(actual_pnl) > 0:
                    expected_outcome = expected_rr * risk_taken
                    pricing_error = abs(abs(actual_pnl) - expected_outcome) / expected_outcome if expected_outcome > 0 else float('inf')
                    if pricing_error < 0.5:  # Within 50% of expected
                        properly_priced_count += 1
        
        avg_realized_rr = float(np.mean(realized_rr_ratios)) if realized_rr_ratios else 0.0
        risk_pricing_compliance = properly_priced_count / total_trades if total_trades > 0 else 0.0
        
        return {
            'risk_reward_realized_ratio': avg_realized_rr,
            'risk_pricing_compliance': risk_pricing_compliance,
            'meets_risk_pricing_threshold': risk_pricing_compliance >= 0.7  # 70% of trades properly priced
        }

    def validate_sl_tp_consistency(self, trade_log: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Validate that SL/TP is reachable and timeframe-consistent.
        """
        if not trade_log:
            return {
                'sl_hit_rate': 0.0,
                'tp_hit_rate': 0.0,
                'timeframe_consistency_score': 0.0,
                'reachability_score': 0.0,
                'meets_consistency_threshold': False
            }
        
        sl_hit_count = 0
        tp_hit_count = 0
        total_trades = len(trade_log)
        
        timeframe_consistency_count = 0
        reachability_count = 0
        
        for trade in trade_log:
            # Check if SL was hit
            if trade.get('exit_reason') == 'STOP_LOSS':
                sl_hit_count += 1
            elif trade.get('exit_reason') in ['TAKE_PROFIT', 'TARGET_HIT']:
                tp_hit_count += 1
            
            # Check timeframe consistency
            expected_holding_time = trade.get('expected_holding_time_hours', 1.0)
            actual_holding_time = trade.get('actual_holding_time_hours', 1.0)
            time_diff = abs(actual_holding_time - expected_holding_time) / expected_holding_time
            if time_diff <= 0.5:  # Within 50% of expected time
                timeframe_consistency_count += 1
            
            # Check reachability (if we have reachability estimates)
            expected_success_prob = trade.get('expected_success_probability', 0.5)
            if expected_success_prob >= 0.6:  # Considered reachable if >= 60% probability
                reachability_count += 1
        
        sl_hit_rate = sl_hit_count / total_trades if total_trades > 0 else 0.0
        tp_hit_rate = tp_hit_count / total_trades if total_trades > 0 else 0.0
        timeframe_consistency_score = timeframe_consistency_count / total_trades if total_trades > 0 else 0.0
        reachability_score = reachability_count / total_trades if total_trades > 0 else 0.0
        
        meets_consistency = (timeframe_consistency_score >= 0.7 and 
                           reachability_score >= 0.6 and 
                           tp_hit_rate >= 0.5)  # At least 50% TP hit rate
        
        return {
            'sl_hit_rate': sl_hit_rate,
            'tp_hit_rate': tp_hit_rate,
            'timeframe_consistency_score': timeframe_consistency_score,
            'reachability_score': reachability_score,
            'meets_consistency_threshold': meets_consistency
        }

    def validate_scalping_strategies(self, trade_log: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Validate that scalping strategies prioritize hit probability and time efficiency.
        """
        # Filter for scalping trades (typically short timeframe)
        scalping_trades = [trade for trade in trade_log 
                          if trade.get('timeframe', 'H1') in ['M1', 'M5', 'M15']]
        
        if not scalping_trades:
            return {
                'scalping_win_rate': 0.0,
                'scalping_efficiency_ratio': 0.0,
                'scalping_rr_ratio': 0.0,
                'meets_scalping_criteria': True  # No scalping trades, so no violation
            }
        
        # Calculate scalping-specific metrics
        profitable_trades = [t for t in scalping_trades if t.get('actual_pnl', 0) > 0]
        win_rate = len(profitable_trades) / len(scalping_trades) if scalping_trades else 0.0
        
        # Calculate efficiency (profit per unit time)
        total_profit = sum(t.get('actual_pnl', 0) for t in scalping_trades)
        total_time = sum(t.get('actual_holding_time_hours', 0) for t in scalping_trades)
        efficiency_ratio = total_profit / total_time if total_time > 0 else 0.0
        
        # Calculate average risk-reward for scalping (should be lower than swing trades)
        risk_amounts = [abs(t.get('risk_amount', 1)) for t in scalping_trades]
        profit_amounts = [t.get('actual_pnl', 0) for t in scalping_trades]
        
        avg_rr = 0.0
        if risk_amounts and any(r > 0 for r in risk_amounts):
            valid_pairs = [(p, r) for p, r in zip(profit_amounts, risk_amounts) if r > 0]
            if valid_pairs:
                avg_rr = np.mean([abs(p)/r for p, r in valid_pairs])
        
        meets_criteria = (win_rate >= self.minimum_win_rate and 
                         avg_rr <= 2.5)  # Conservative RR for scalping
        
        return {
            'scalping_win_rate': win_rate,
            'scalping_efficiency_ratio': efficiency_ratio,
            'scalping_rr_ratio': avg_rr,
            'meets_scalping_criteria': meets_criteria
        }

    def run_comprehensive_validation(self, 
                                   portfolio_values: List[float],
                                   returns: List[float],
                                   initial_capital: float,
                                   decision_log: List[Dict[str, Any]],
                                   signal_quality_log: List[Dict[str, Any]],
                                   trade_log: List[Dict[str, Any]]) -> ValidationResults:
        """
        Run comprehensive validation of the redesigned architecture.
        """
        # Validate each mandate
        survival_results = self.validate_survival_mandate(portfolio_values, initial_capital)
        profitability_results = self.validate_profitability_mandate(returns)
        evidence_results = self.validate_evidence_driven_decisions(decision_log)
        noise_results = self.validate_noise_suppression(signal_quality_log)
        risk_results = self.validate_risk_pricing(trade_log)
        sltp_results = self.validate_sl_tp_consistency(trade_log)
        scalping_results = self.validate_scalping_strategies(trade_log)
        
        # Calculate overall score (weighted combination of all validations)
        survival_score = 1.0 if survival_results['meets_survival_threshold'] else 0.0
        profitability_score = 1.0 if profitability_results['meets_minimum_sharpe'] else 0.0
        evidence_score = 1.0 if evidence_results['meets_evidence_threshold'] else 0.0
        noise_score = 1.0 if noise_results['meets_noise_threshold'] else 0.0
        risk_score = 1.0 if risk_results['meets_risk_pricing_threshold'] else 0.0
        sltp_score = 1.0 if sltp_results['meets_consistency_threshold'] else 0.0
        scalping_score = 1.0 if scalping_results['meets_scalping_criteria'] else 0.0
        
        # Weighted overall score (survival and risk pricing are most critical)
        overall_score = (
            survival_score * 0.25 +      # Survival is most important
            risk_score * 0.20 +          # Risk pricing is critical
            profitability_score * 0.15 + # Profitability is important
            sltp_score * 0.15 +          # SL/TP consistency is important
            evidence_score * 0.10 +      # Evidence-based decisions
            noise_score * 0.10 +         # Noise suppression
            scalping_score * 0.05        # Scalping criteria (less weight)
        )
        
        # Generate recommendations based on weaknesses
        recommendations = []
        if not survival_results['meets_survival_threshold']:
            recommendations.append("IMPROVE: Enhance risk management to increase survival rate above 85%")
        if not profitability_results['meets_minimum_sharpe']:
            recommendations.append("IMPROVE: Optimize strategies to achieve minimum Sharpe ratio of 0.8")
        if not evidence_results['meets_evidence_threshold']:
            recommendations.append("IMPROVE: Ensure at least 80% of decisions are evidence-based")
        if not noise_results['meets_noise_threshold']:
            recommendations.append("IMPROVE: Enhance noise suppression to achieve 1.5:1 signal-to-noise ratio")
        if not risk_results['meets_risk_pricing_threshold']:
            recommendations.append("IMPROVE: Improve risk pricing accuracy to properly price at least 70% of trades")
        if not sltp_results['meets_consistency_threshold']:
            recommendations.append("IMPROVE: Enhance SL/TP consistency and reachability")
        if not scalping_results['meets_scalping_criteria']:
            recommendations.append("IMPROVE: Optimize scalping strategies for higher win rates (>=40%)")
        
        if not recommendations:
            recommendations.append("EXCELLENT: All validation criteria met. System is ready for production.")
        
        # Compile risk metrics
        risk_metrics = {
            'max_drawdown': survival_results['max_drawdown'],
            'survival_rate': survival_results['survival_rate'],
            'recovery_rate': survival_results['recovery_rate'],
            'sharpe_ratio': profitability_results['sharpe_ratio'],
            'profit_factor': profitability_results['profit_factor'],
            'risk_pricing_compliance': risk_results['risk_pricing_compliance']
        }
        
        # Compile constraint compliance
        constraint_compliance = {
            'survival_mandate_met': survival_results['meets_survival_threshold'],
            'profitability_mandate_met': profitability_results['meets_minimum_sharpe'],
            'evidence_driven_mandate_met': evidence_results['meets_evidence_threshold'],
            'noise_suppression_mandate_met': noise_results['meets_noise_threshold'],
            'risk_pricing_mandate_met': risk_results['meets_risk_pricing_threshold'],
            'sl_tp_consistency_mandate_met': sltp_results['meets_consistency_threshold'],
            'scalping_criteria_met': scalping_results['meets_scalping_criteria']
        }
        
        return ValidationResults(
            survival_rate=survival_results['survival_rate'],
            profitability_metrics=profitability_results,
            risk_metrics=risk_metrics,
            constraint_compliance=constraint_compliance,
            overall_score=overall_score,
            recommendations=recommendations
        )

    def generate_validation_report(self, results: ValidationResults) -> str:
        """
        Generate a comprehensive validation report.
        """
        report = []
        report.append("="*80)
        report.append("COMPREHENSIVE VALIDATION REPORT FOR REDESIGNED TRADING SYSTEM")
        report.append("="*80)
        report.append("")
        
        report.append("EXECUTIVE SUMMARY:")
        report.append(f"  Overall Score: {results.overall_score:.2f}/1.00")
        report.append(f"  Survival Rate: {results.survival_rate:.2%}")
        report.append(f"  Sharpe Ratio: {results.profitability_metrics['sharpe_ratio']:.2f}")
        report.append(f"  Profit Factor: {results.profitability_metrics['profit_factor']:.2f}")
        report.append("")
        
        report.append("MANDATE COMPLIANCE:")
        for mandate, compliant in results.constraint_compliance.items():
            status = "✓ PASS" if compliant else "✗ FAIL"
            report.append(f"  {mandate.replace('_', ' ').title()}: {status}")
        report.append("")
        
        report.append("RISK METRICS:")
        for metric, value in results.risk_metrics.items():
            if isinstance(value, float):
                report.append(f"  {metric.replace('_', ' ').title()}: {value:.4f}")
            else:
                report.append(f"  {metric.replace('_', ' ').title()}: {value}")
        report.append("")
        
        report.append("RECOMMENDATIONS:")
        for i, rec in enumerate(results.recommendations, 1):
            report.append(f"  {i}. {rec}")
        report.append("")
        
        report.append("="*80)
        report.append("REPORT GENERATED: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        report.append("="*80)
        
        return "\n".join(report)

    def visualize_validation_results(self, portfolio_values: List[float], returns: List[float]):
        """
        Create visualizations for validation results.
        """
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle('Validation Results Visualization', fontsize=16)
        
        # Portfolio value over time
        axes[0, 0].plot(portfolio_values)
        axes[0, 0].set_title('Portfolio Value Over Time')
        axes[0, 0].set_xlabel('Time Period')
        axes[0, 0].set_ylabel('Portfolio Value')
        axes[0, 0].grid(True)
        
        # Drawdown chart
        running_max = np.maximum.accumulate(portfolio_values)
        drawdowns = (running_max - portfolio_values) / running_max
        axes[0, 1].plot(drawdowns, color='red')
        axes[0, 1].set_title('Drawdown Over Time')
        axes[0, 1].set_xlabel('Time Period')
        axes[0, 1].set_ylabel('Drawdown')
        axes[0, 1].grid(True)
        
        # Returns distribution
        axes[1, 0].hist(returns, bins=50, edgecolor='black')
        axes[1, 0].set_title('Distribution of Returns')
        axes[1, 0].set_xlabel('Return')
        axes[1, 0].set_ylabel('Frequency')
        axes[1, 0].grid(True)
        
        # Rolling Sharpe ratio
        if len(returns) > 30:  # Need sufficient data
            window = 30
            rolling_returns = pd.Series(returns).rolling(window=window)
            rolling_sharpe = (rolling_returns.mean() / rolling_returns.std()) * np.sqrt(252)
            axes[1, 1].plot(rolling_sharpe.dropna(), color='green')
            axes[1, 1].set_title(f'Rolling {window}-Period Sharpe Ratio')
            axes[1, 1].set_xlabel('Time Period')
            axes[1, 1].set_ylabel('Sharpe Ratio')
            axes[1, 1].grid(True)
        else:
            axes[1, 1].text(0.5, 0.5, 'Insufficient data\nfor rolling Sharpe', 
                           horizontalalignment='center', verticalalignment='center',
                           transform=axes[1, 1].transAxes)
        
        plt.tight_layout()
        plt.show()


# Example usage and testing
def run_sample_validation():
    """
    Run a sample validation with simulated data to demonstrate the validator.
    """
    validator = ArchitectureValidator()
    
    # Generate sample data for demonstration
    np.random.seed(42)  # For reproducible results
    
    # Simulate portfolio values with realistic drawdowns
    n_periods = 252  # About 1 year of daily data
    daily_returns = np.random.normal(0.0005, 0.02, n_periods)  # Daily return ~0.05%, vol ~2%
    
    # Add some larger drawdowns to make it realistic
    daily_returns[50:55] = np.array([-0.03, -0.04, -0.02, -0.01, -0.02])  # Drawdown event
    daily_returns[150:153] = np.array([-0.05, -0.03, -0.02])  # Another drawdown event
    
    # Calculate portfolio values starting from $100,000
    initial_capital = 100000
    portfolio_values = [initial_capital]
    for ret in daily_returns:
        portfolio_values.append(portfolio_values[-1] * (1 + ret))
    
    # Generate sample decision log
    decision_log = []
    for i in range(n_periods):
        decision_log.append({
            'timestamp': datetime.now() - timedelta(days=n_periods-i),
            'confidence': np.random.beta(2, 2),  # Beta distribution for confidence (0-1)
            'indicators': ['RSI', 'MACD', 'SMA'] if i % 3 == 0 else [],
            'regime_context': np.random.choice(['trending', 'choppy', 'volatile']),
            'outcome': daily_returns[i]  # Simplified: outcome is the return
        })
    
    # Generate sample signal quality log
    signal_quality_log = []
    for i in range(n_periods):
        signal_power = np.random.gamma(2, 0.5)  # Gamma distribution for signal power
        noise_power = np.random.gamma(1.5, 0.7)  # Gamma distribution for noise power
        signal_quality_log.append({
            'timestamp': datetime.now() - timedelta(days=n_periods-i),
            'signal_power': signal_power,
            'noise_power': noise_power
        })
    
    # Generate sample trade log
    trade_log = []
    n_trades = 50
    for i in range(n_trades):
        trade_result = np.random.choice([-1, 1], p=[0.4, 0.6])  # 60% win rate
        risk_amount = initial_capital * 0.01  # 1% risk per trade
        actual_pnl = risk_amount * np.random.gamma(2, 0.5) * trade_result  # Random profit/loss
        
        trade_log.append({
            'trade_id': f'TRADE_{i}',
            'entry_timestamp': datetime.now() - timedelta(days=np.random.randint(1, 365)),
            'exit_timestamp': datetime.now() - timedelta(days=np.random.randint(0, 364)),
            'timeframe': np.random.choice(['M5', 'M15', 'H1', 'H4']),
            'expected_risk_reward': np.random.uniform(1.5, 3.0),
            'risk_amount': risk_amount,
            'actual_pnl': actual_pnl,
            'exit_reason': np.random.choice(['TAKE_PROFIT', 'STOP_LOSS', 'TIMEOUT'], p=[0.4, 0.35, 0.25]),
            'expected_holding_time_hours': np.random.choice([0.1, 0.5, 2, 8]),  # Various holding times
            'actual_holding_time_hours': np.random.exponential(1),
            'expected_success_probability': np.random.beta(2, 1)  # Beta for probability (0-1)
        })
    
    # Run validation
    results = validator.run_comprehensive_validation(
        portfolio_values=portfolio_values[1:],  # Skip initial capital
        returns=list(daily_returns),
        initial_capital=initial_capital,
        decision_log=decision_log,
        signal_quality_log=signal_quality_log,
        trade_log=trade_log
    )
    
    # Print validation report
    report = validator.generate_validation_report(results)
    print(report)
    
    # Show visualization
    # validator.visualize_validation_results(portfolio_values[1:], list(daily_returns))
    
    return results


# Global instance
architecture_validator = ArchitectureValidator()

if __name__ == "__main__":
    print("Running sample validation of redesigned trading system architecture...")
    results = run_sample_validation()
    print(f"\nValidation completed with overall score: {results.overall_score:.2f}")