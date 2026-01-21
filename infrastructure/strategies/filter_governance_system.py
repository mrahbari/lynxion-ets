"""
Advanced Filter Governance System for Volatility Breakout Strategy
Implements comprehensive filter accountability, contribution scoring, and regime-adaptive filtering
"""
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum
from dataclasses import dataclass
from collections import defaultdict
import numpy as np
from pathlib import Path
import pandas as pd
from scipy.stats import linregress

from shared.logger import EnhancedLogger
from infrastructure.logging.forensic_logger import forensic_logger


class FilterType(Enum):
    ALPHA_PROTECTIVE = "alpha_protective"
    ALPHA_NEUTRAL = "alpha_neutral"
    ALPHA_SUPPRESSIVE = "alpha_suppressive"
    NOISE_BASED = "noise_based"
    REGIME_MISALIGNED = "regime_misaligned"


class RegimeType(Enum):
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    CHOPPY = "choppy"
    NORMAL = "normal"


@dataclass
class FilterMetrics:
    """Data class to store filter metrics"""
    rejection_rate: float
    alpha_impact: float  # Positive if protective, negative if suppressive
    effectiveness_score: float
    regime_specific_performance: Dict[str, float]
    contribution_score: float
    classification: FilterType


class FilterAccountabilityReport:
    """Generates comprehensive reports on filter performance and accountability"""
    
    def __init__(self):
        self.logger = EnhancedLogger("FilterAccountability")
        self.rejection_data = defaultdict(list)
        self.filter_performance = {}
        
    def generate_report(self, filter_results: Dict[str, Any], market_regime: RegimeType) -> Dict[str, Any]:
        """Generate comprehensive filter accountability report"""
        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "market_regime": market_regime.value,
            "rejection_analysis": {},
            "filter_contributions": {},
            "regime_specific_performance": {},
            "recommendations": []
        }
        
        # Calculate rejection rates by filter
        for filter_name, results in filter_results.items():
            total_signals = results.get("total_signals", 1)
            rejected_signals = results.get("rejected_signals", 0)
            rejection_rate = rejected_signals / total_signals if total_signals > 0 else 0
            
            report["rejection_analysis"][filter_name] = {
                "rejection_rate": rejection_rate,
                "total_signals": total_signals,
                "rejected_signals": rejected_signals,
                "accepted_signals": total_signals - rejected_signals
            }
            
            # Calculate regime-specific performance
            regime_perf = results.get("regime_performance", {}).get(market_regime.value, {})
            report["regime_specific_performance"][filter_name] = regime_perf
        
        # Generate recommendations based on analysis
        for filter_name, analysis in report["rejection_analysis"].items():
            if analysis["rejection_rate"] > 0.8:
                report["recommendations"].append({
                    "filter": filter_name,
                    "issue": "High rejection rate (>80%)",
                    "action": "Consider weakening or removing filter"
                })
            elif analysis["rejection_rate"] < 0.05:
                report["recommendations"].append({
                    "filter": filter_name,
                    "issue": "Low rejection rate (<5%)",
                    "action": "Consider strengthening filter"
                })
        
        return report


class FilterContributionScorer:
    """Calculates contribution scores for each filter"""
    
    def __init__(self):
        self.logger = EnhancedLogger("FilterContribution")
        
    def calculate_contribution(self, 
                            filter_name: str, 
                            pnl_with_filter: float, 
                            pnl_without_filter: float,
                            opportunity_cost: float,
                            variance_with_filter: float,
                            variance_without_filter: float) -> float:
        """
        Calculate filter contribution score based on:
        (Expected_PnL_with_filter - Expected_PnL_without_filter)
        adjusted by opportunity cost and variance impact
        """
        # Base contribution from PnL difference
        base_contribution = pnl_with_filter - pnl_without_filter
        
        # Adjust for opportunity cost
        opportunity_adjustment = -abs(opportunity_cost)
        
        # Adjust for variance impact (prefer lower variance)
        variance_adjustment = -(variance_with_filter - variance_without_filter) * 0.1
        
        # Weighted combination
        contribution_score = (
            0.6 * base_contribution +
            0.2 * opportunity_adjustment +
            0.2 * variance_adjustment
        )
        
        return contribution_score


class DynamicFilterGovernanceLayer:
    """Main governance layer that manages filter behavior dynamically"""
    
    def __init__(self):
        self.logger = EnhancedLogger("DynamicFilterGovernance")
        self.filters = {}
        self.filter_weights = {}
        self.effectiveness_history = defaultdict(list)
        self.accountability_reporter = FilterAccountabilityReport()
        self.contribution_scorer = FilterContributionScorer()
        self.active_filters = set()
        
    def register_filter(self, 
                       name: str, 
                       filter_func, 
                       initial_weight: float = 1.0,
                       classification: FilterType = FilterType.ALPHA_NEUTRAL):
        """Register a new filter with the governance system"""
        self.filters[name] = {
            "function": filter_func,
            "weight": initial_weight,
            "classification": classification,
            "enabled": True,
            "self_disabled": False,
            "performance_history": []
        }
        self.filter_weights[name] = initial_weight
        self.active_filters.add(name)
        
    def evaluate_filters(self, 
                        signal_data: Dict[str, Any], 
                        market_regime: RegimeType) -> Tuple[Dict[str, bool], Dict[str, Any]]:
        """
        Evaluate all registered filters and return results
        Returns: (filter_decisions, filter_metadata)
        """
        decisions = {}
        metadata = {
            "applied_filters": [],
            "rejected_by": [],
            "total_signals_processed": 1,
            "regime": market_regime.value
        }
        
        for filter_name, filter_info in self.filters.items():
            if not filter_info["enabled"] or filter_info["self_disabled"]:
                continue
                
            # Check if filter is regime-appropriate
            if not self._is_regime_appropriate(filter_name, market_regime):
                continue
                
            try:
                # Apply the filter function
                result = filter_info["function"](signal_data)
                
                # Apply weight to the result
                weighted_result = result if filter_info["weight"] >= 0.5 else not result
                
                decisions[filter_name] = weighted_result
                metadata["applied_filters"].append(filter_name)
                
                if not weighted_result:
                    metadata["rejected_by"].append(filter_name)
                    
            except Exception as e:
                self.logger.error(f"Error evaluating filter {filter_name}: {e}")
                decisions[filter_name] = False  # Default to rejection on error
                metadata["applied_filters"].append(filter_name)
                metadata["rejected_by"].append(filter_name)
        
        return decisions, metadata
    
    def _is_regime_appropriate(self, filter_name: str, regime: RegimeType) -> bool:
        """Check if a filter is appropriate for the current market regime"""
        # Define regime-specific filter applicability
        regime_filters = {
            RegimeType.HIGH_VOLATILITY: [
                "price_volatility_filter",  # May need adjustment in high vol
                "sr_proximity_filter"      # Still relevant
            ],
            RegimeType.LOW_VOLATILITY: [
                "volume_confirmation_filter",  # Important in low vol
                "momentum_alignment_filter",   # Important in low vol
                "consolidation_filter"         # Important in low vol
            ],
            RegimeType.TRENDING_UP: [
                "momentum_alignment_filter",   # Very important in trending markets
                "volume_confirmation_filter"   # Important in trending markets
            ],
            RegimeType.TRENDING_DOWN: [
                "momentum_alignment_filter",   # Very important in trending markets
                "volume_confirmation_filter"   # Important in trending markets
            ],
            RegimeType.CHOPPY: [
                "sr_proximity_filter",         # Very important in choppy markets
                "consolidation_filter"         # Important in choppy markets
            ],
            RegimeType.NORMAL: [
                "price_volatility_filter",     # Standard filtering
                "volume_confirmation_filter",
                "momentum_alignment_filter",
                "sr_proximity_filter",
                "consolidation_filter"
            ]
        }

        # If the filter is in the list for this regime, it's appropriate
        return filter_name in regime_filters.get(regime, [])
    
    def update_filter_effectiveness(self, 
                                  filter_name: str, 
                                  performance_metric: float, 
                                  regime: RegimeType):
        """Update the effectiveness history for a filter"""
        self.effectiveness_history[filter_name].append({
            "timestamp": datetime.utcnow(),
            "performance": performance_metric,
            "regime": regime.value,
            "weight": self.filters[filter_name]["weight"] if filter_name in self.filters else 1.0
        })
        
        # Keep only recent history (last 100 entries)
        if len(self.effectiveness_history[filter_name]) > 100:
            self.effectiveness_history[filter_name] = self.effectiveness_history[filter_name][-100:]
    
    def self_manage_filters(self):
        """Allow filters to self-manage based on historical effectiveness"""
        for filter_name, history in self.effectiveness_history.items():
            if not history or filter_name not in self.filters:
                continue
                
            # Calculate recent performance
            recent_performance = [h["performance"] for h in history[-10:]]
            avg_performance = sum(recent_performance) / len(recent_performance)
            
            # Self-downgrade if consistently poor performing
            if avg_performance < -0.1:  # Poor performance threshold
                self._self_downgrade_filter(filter_name)
            # Self-disable if extremely poor performing
            elif avg_performance < -0.3:
                self._self_disable_filter(filter_name)
            # Self-weight adjustment based on performance
            else:
                self._adjust_filter_weight(filter_name, avg_performance)
    
    def _self_downgrade_filter(self, filter_name: str):
        """Reduce filter's impact due to poor performance"""
        if filter_name in self.filters:
            old_weight = self.filters[filter_name]["weight"]
            new_weight = max(0.1, old_weight * 0.7)  # Reduce by 30%
            self.filters[filter_name]["weight"] = new_weight
            self.logger.warning(f"Filter {filter_name} self-downgraded from {old_weight:.2f} to {new_weight:.2f}")
    
    def _self_disable_filter(self, filter_name: str):
        """Temporarily disable filter due to very poor performance"""
        if filter_name in self.filters:
            self.filters[filter_name]["self_disabled"] = True
            self.logger.warning(f"Filter {filter_name} self-disabled due to poor performance")
    
    def _adjust_filter_weight(self, filter_name: str, performance: float):
        """Adjust filter weight based on performance"""
        if filter_name in self.filters:
            current_weight = self.filters[filter_name]["weight"]
            # Adjust weight proportionally to performance (positive performance increases weight)
            adjustment = performance * 0.1
            new_weight = max(0.1, min(2.0, current_weight + adjustment))
            self.filters[filter_name]["weight"] = new_weight


class VolatilityBreakoutFilterGovernance:
    """Specialized governance system for volatility breakout strategy"""
    
    def __init__(self):
        self.logger = EnhancedLogger("VolatilityBreakoutGovernance")
        self.governance_layer = DynamicFilterGovernanceLayer()
        self.accountability_reporter = FilterAccountabilityReport()
        self.contribution_scorer = FilterContributionScorer()
        self.performance_tracker = defaultdict(lambda: {"with_filter": [], "without_filter": []})
        
        # Register default filters for volatility breakout strategy
        self._register_default_filters()
    
    def _register_default_filters(self):
        """Register default filters for volatility breakout strategy"""
        # Price volatility filter
        self.governance_layer.register_filter(
            "price_volatility_filter",
            self._price_volatility_filter,
            initial_weight=1.0,
            classification=FilterType.ALPHA_PROTECTIVE
        )
        
        # Volume confirmation filter
        self.governance_layer.register_filter(
            "volume_confirmation_filter",
            self._volume_confirmation_filter,
            initial_weight=0.8,
            classification=FilterType.ALPHA_PROTECTIVE
        )
        
        # Momentum alignment filter
        self.governance_layer.register_filter(
            "momentum_alignment_filter",
            self._momentum_alignment_filter,
            initial_weight=0.9,
            classification=FilterType.ALPHA_PROTECTIVE
        )
        
        # Support/resistance proximity filter
        self.governance_layer.register_filter(
            "sr_proximity_filter",
            self._sr_proximity_filter,
            initial_weight=0.7,
            classification=FilterType.ALPHA_PROTECTIVE
        )
        
        # Consolidation filter
        self.governance_layer.register_filter(
            "consolidation_filter",
            self._consolidation_filter,
            initial_weight=1.0,
            classification=FilterType.ALPHA_PROTECTIVE
        )
    
    def _price_volatility_filter(self, signal_data: Dict[str, Any]) -> bool:
        """Filter based on price volatility conditions"""
        current_atr = signal_data.get("atr", 0)
        avg_atr = signal_data.get("avg_atr", 1)
        
        # If volatility is too high, reject the signal
        if current_atr > avg_atr * 2.0:
            return False  # Reject signal due to excessive volatility
        
        # If volatility is too low, also reject (may not have enough movement)
        if current_atr < avg_atr * 0.3:
            return False  # Reject signal due to insufficient volatility
        
        return True  # Accept signal
    
    def _volume_confirmation_filter(self, signal_data: Dict[str, Any]) -> bool:
        """Filter based on volume confirmation"""
        current_volume = signal_data.get("current_volume", 0)
        avg_volume = signal_data.get("avg_volume", 1)
        
        # Require volume to be above average for confirmation
        return current_volume > avg_volume * 0.8
    
    def _momentum_alignment_filter(self, signal_data: Dict[str, Any]) -> bool:
        """Filter based on momentum alignment with breakout direction"""
        momentum = signal_data.get("momentum", 0)
        signal_direction = signal_data.get("signal_direction", "neutral")
        
        # For buy signals, momentum should be positive
        if signal_direction == "buy" and momentum < 0.01:
            return False
        
        # For sell signals, momentum should be negative
        if signal_direction == "sell" and momentum > -0.01:
            return False
        
        return True
    
    def _sr_proximity_filter(self, signal_data: Dict[str, Any]) -> bool:
        """Filter based on proximity to support/resistance levels"""
        current_price = signal_data.get("current_price", 0)
        resistance = signal_data.get("resistance", 0)
        support = signal_data.get("support", 0)
        
        # If price is too close to resistance/support, reject (unclear direction)
        if resistance > 0 and abs(current_price - resistance) / resistance < 0.01:
            return False  # Too close to resistance
        
        if support > 0 and abs(current_price - support) / support < 0.01:
            return False  # Too close to support
        
        return True
    
    def _consolidation_filter(self, signal_data: Dict[str, Any]) -> bool:
        """Filter based on consolidation criteria"""
        is_consolidating = signal_data.get("is_consolidating", False)
        consolidation_period = signal_data.get("consolidation_period", 10)
        
        # Only accept signals that come after sufficient consolidation
        return is_consolidating and consolidation_period >= 5
    
    def process_signal(self, signal_data: Dict[str, Any], market_regime: RegimeType) -> Tuple[bool, Dict[str, Any]]:
        """
        Process a signal through all registered filters
        Returns: (accept_signal, filter_metadata)
        """
        # Evaluate all filters
        filter_decisions, metadata = self.governance_layer.evaluate_filters(signal_data, market_regime)

        # Determine if signal should be accepted (all filters must pass)
        accept_signal = all(filter_decisions.values()) if filter_decisions else True

        # Update effectiveness tracking
        for filter_name, decision in filter_decisions.items():
            # Log performance impact of each filter
            self.governance_layer.update_filter_effectiveness(
                filter_name,
                1.0 if decision else -0.5,  # Positive for acceptance, negative for rejection
                market_regime
            )

        # Add detailed filter results to metadata
        metadata["filter_decisions"] = filter_decisions
        metadata["accept_signal"] = accept_signal

        # Log the filter governance decision to forensic logs
        self._log_filter_governance_decision(signal_data, filter_decisions, accept_signal, market_regime)

        return accept_signal, metadata

    def _log_filter_governance_decision(self, signal_data: Dict[str, Any], filter_decisions: Dict[str, bool],
                                       accept_signal: bool, market_regime: RegimeType):
        """Log filter governance decision to forensic logs"""
        try:
            # Prepare forensic log data
            forensic_log_data = {
                "component": "FilterGovernance",
                "action": "FilterDecision",
                "market_regime": market_regime.value,
                "signal_data_summary": {
                    "symbol": signal_data.get("symbol", "UNKNOWN"),
                    "current_price": signal_data.get("current_price"),
                    "atr": signal_data.get("atr"),
                    "momentum": signal_data.get("momentum"),
                    "is_consolidating": signal_data.get("is_consolidating", False)
                },
                "filter_decisions": filter_decisions,
                "accept_signal": accept_signal,
                "timestamp": datetime.utcnow().isoformat()
            }

            # Add to forensic logger if available
            from infrastructure.logging.forensic_logger import forensic_logger
            if forensic_logger and forensic_logger.enabled:
                # Log as a custom event in the forensic system
                forensic_logger.logger.info(f"FILTER_GOVERNANCE: {forensic_log_data}")

        except Exception as e:
            self.logger.error(f"Error logging filter governance decision: {e}")
    
    def generate_filter_accountability_report(self, market_regime: RegimeType) -> Dict[str, Any]:
        """Generate comprehensive filter accountability report"""
        # Collect current filter statistics
        filter_results = {}
        for filter_name, filter_info in self.governance_layer.filters.items():
            # This would be populated with actual performance data
            filter_results[filter_name] = {
                "total_signals": len(self.governance_layer.effectiveness_history[filter_name]),
                "rejected_signals": sum(1 for h in self.governance_layer.effectiveness_history[filter_name] 
                                      if h["performance"] < 0),
                "regime_performance": {regime.value: [] for regime in RegimeType}
            }
        
        return self.accountability_reporter.generate_report(filter_results, market_regime)
    
    def calculate_filter_contributions(self) -> Dict[str, float]:
        """Calculate contribution scores for all filters"""
        contributions = {}
        
        for filter_name in self.governance_layer.filters.keys():
            # Get performance data for this filter
            with_filter_pnl = np.mean(self.performance_tracker[filter_name]["with_filter"]) if self.performance_tracker[filter_name]["with_filter"] else 0
            without_filter_pnl = np.mean(self.performance_tracker[filter_name]["without_filter"]) if self.performance_tracker[filter_name]["without_filter"] else 0
            
            # Calculate opportunity cost and variance
            opportunity_cost = len(self.performance_tracker[filter_name]["without_filter"]) * 0.01  # Simplified
            variance_with = np.var(self.performance_tracker[filter_name]["with_filter"]) if len(self.performance_tracker[filter_name]["with_filter"]) > 1 else 0
            variance_without = np.var(self.performance_tracker[filter_name]["without_filter"]) if len(self.performance_tracker[filter_name]["without_filter"]) > 1 else 0
            
            # Calculate contribution score
            contribution = self.contribution_scorer.calculate_contribution(
                filter_name, with_filter_pnl, without_filter_pnl,
                opportunity_cost, variance_with, variance_without
            )
            
            contributions[filter_name] = contribution
        
        return contributions
    
    def get_filter_classifications(self) -> Dict[str, FilterType]:
        """Get classifications for all filters"""
        return {
            name: info["classification"] 
            for name, info in self.governance_layer.filters.items()
        }
    
    def update_filter_performance(self, filter_name: str, pnl_with: float, pnl_without: float):
        """Update performance tracking for a filter"""
        self.performance_tracker[filter_name]["with_filter"].append(pnl_with)
        self.performance_tracker[filter_name]["without_filter"].append(pnl_without)
        
        # Keep only recent performance data (last 50 entries)
        if len(self.performance_tracker[filter_name]["with_filter"]) > 50:
            self.performance_tracker[filter_name]["with_filter"] = self.performance_tracker[filter_name]["with_filter"][-50:]
            self.performance_tracker[filter_name]["without_filter"] = self.performance_tracker[filter_name]["without_filter"][-50:]
    
    def get_science_verdict(self) -> Dict[str, Any]:
        """Generate scientific verdict on strategy status"""
        contributions = self.calculate_filter_contributions()
        classifications = self.get_filter_classifications()
        accountability_report = self.generate_filter_accountability_report(RegimeType.NORMAL)
        
        # Calculate overall strategy metrics
        avg_rejection_rate = np.mean([
            analysis["rejection_rate"] 
            for analysis in accountability_report.get("rejection_analysis", {}).values()
        ]) if accountability_report.get("rejection_analysis") else 0
        
        # Determine scientific verdict
        verdict = "Balanced"
        if avg_rejection_rate > 0.7:
            verdict = "Over-selective"
        elif avg_rejection_rate < 0.1:
            verdict = "Under-selective"
        elif any(c == FilterType.ALPHA_SUPPRESSIVE for c in classifications.values()):
            verdict = "Alpha-suppressive"
        elif any(c == FilterType.NOISE_BASED for c in classifications.values()):
            verdict = "Noise-based"
        
        return {
            "verdict": verdict,
            "average_rejection_rate": avg_rejection_rate,
            "filter_contributions": contributions,
            "filter_classifications": {k: v.value for k, v in classifications.items()},
            "recommendations": accountability_report.get("recommendations", []),
            "belief_areas": self._identify_belief_based_areas()
        }
    
    def _identify_belief_based_areas(self) -> List[str]:
        """Identify areas where system trades on belief instead of proof"""
        beliefs = []
        
        # Check if any filter has no performance data
        for filter_name, history in self.governance_layer.effectiveness_history.items():
            if not history:
                beliefs.append(f"Filter '{filter_name}' has no performance validation")
        
        # Check if any filter has been unchanged for too long
        for filter_name, filter_info in self.governance_layer.filters.items():
            if filter_info["weight"] == 1.0 and not self.governance_layer.effectiveness_history[filter_name]:
                beliefs.append(f"Filter '{filter_name}' has default weight with no adaptation")
        
        return beliefs


class MarketRegimeDetector:
    """Detects current market regime based on technical indicators"""

    def __init__(self):
        self.logger = EnhancedLogger("MarketRegimeDetector")

    def detect_regime(self, price_data: List[float], volume_data: List[float] = None) -> RegimeType:
        """Detect current market regime based on price and volume data"""
        if len(price_data) < 20:
            return RegimeType.NORMAL

        # Calculate volatility (using standard deviation of returns)
        returns = [(price_data[i] - price_data[i-1]) / price_data[i-1] for i in range(1, len(price_data))]
        volatility = np.std(returns) * np.sqrt(252)  # Annualized volatility

        # Calculate trend (using linear regression slope)
        x = np.arange(len(price_data))
        slope, _, _, _, _ = linregress(x, price_data)
        trend_strength = abs(slope) / np.mean(price_data)  # Normalize by mean price

        # Calculate choppiness (using a simplified version of the Choppiness Index)
        if len(price_data) >= 14:
            highest_high = max(price_data[-14:])
            lowest_low = min(price_data[-14:])
            current_range = highest_high - lowest_low
            sum_ranges = sum([abs(price_data[i] - price_data[i-1]) for i in range(1, len(price_data))][-14:])

            if sum_ranges != 0:
                choppiness = 100 * np.log10(current_range / sum_ranges) / np.log10(14)
            else:
                choppiness = 0
        else:
            choppiness = 0.5  # Default to moderate choppiness

        # Determine regime based on calculated metrics
        if volatility > 0.5:  # High annualized volatility
            return RegimeType.HIGH_VOLATILITY
        elif volatility < 0.1:  # Low annualized volatility
            return RegimeType.LOW_VOLATILITY
        elif trend_strength > 0.02 and slope > 0:  # Strong positive trend
            return RegimeType.TRENDING_UP
        elif trend_strength > 0.02 and slope < 0:  # Strong negative trend
            return RegimeType.TRENDING_DOWN
        elif choppiness > 0.6:  # High choppiness indicates ranging/choppy market
            return RegimeType.CHOPPY
        else:
            return RegimeType.NORMAL


# Global instances
market_regime_detector = MarketRegimeDetector()
volatility_breakout_governance = VolatilityBreakoutFilterGovernance()