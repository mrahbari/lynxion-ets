"""
Forensic Attribution Model for Enterprise Hedge Fund Trading System
Allocates responsibility for gains/losses across system components
"""
from typing import Dict, Any, List
from datetime import datetime
import numpy as np
import logging


class ForensicAttributionModel:
    """
    Attributes gains/losses to specific system components using counterfactual analysis
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def attribute_loss(self, 
                      trade_data: Dict[str, Any], 
                      pnl: float, 
                      attribution_factors: Dict[str, float] = None) -> Dict[str, float]:
        """
        Attribute loss/profit to different system components
        """
        if attribution_factors is None:
            # Default attribution weights based on system layer
            attribution_factors = {
                'watcher': 0.15,    # Market observation quality
                'engine': 0.20,     # Signal interpretation
                'fusion': 0.20,     # Signal combination
                'strategy': 0.25,   # Strategy selection
                'broker': 0.10,     # Execution quality
                'risk_management': 0.10  # Risk controls
            }
        
        # Calculate base attribution
        base_attribution = {}
        for component, weight in attribution_factors.items():
            base_attribution[component] = pnl * weight
        
        # Adjust attribution based on specific trade characteristics
        adjusted_attribution = self._adjust_attribution_for_trade_characteristics(
            base_attribution, trade_data, pnl
        )
        
        # Normalize to ensure sum equals total PnL
        total_attributed = sum(adjusted_attribution.values())
        if total_attributed != 0 and pnl != 0:
            normalization_factor = pnl / total_attributed
            for component in adjusted_attribution:
                adjusted_attribution[component] *= normalization_factor
        
        return adjusted_attribution
    
    def _adjust_attribution_for_trade_characteristics(self, 
                                                   base_attribution: Dict[str, float], 
                                                   trade_data: Dict[str, Any], 
                                                   pnl: float) -> Dict[str, float]:
        """
        Adjust attribution based on specific trade characteristics and performance metrics
        """
        adjusted = base_attribution.copy()
        
        # Adjust for watcher performance if available
        if 'watcher_performance' in trade_data:
            watcher_perf = trade_data['watcher_performance']
            # If watcher signal was poor, increase watcher attribution for loss
            if pnl < 0 and watcher_perf < 0.5:  # Poor watcher performance
                adjustment = abs(pnl) * 0.1
                adjusted['watcher'] += adjustment if pnl < 0 else -adjustment
        
        # Adjust for engine interpretation quality
        if 'engine_confidence' in trade_data:
            engine_conf = trade_data['engine_confidence']
            # If engine confidence was low but trade was made anyway, adjust attribution
            if engine_conf < 0.5 and abs(pnl) > 0:
                adjustment = abs(pnl) * 0.05
                adjusted['engine'] += adjustment if pnl < 0 else -adjustment
        
        # Adjust for fusion effectiveness
        if 'fusion_effectiveness' in trade_data:
            fusion_eff = trade_data['fusion_effectiveness']
            if fusion_eff < 0.6 and pnl < 0:  # Poor fusion, negative result
                adjustment = abs(pnl) * 0.08
                adjusted['fusion'] += adjustment if pnl < 0 else -adjustment
        
        # Adjust for strategy selection
        if 'strategy_performance' in trade_data:
            strat_perf = trade_data['strategy_performance']
            if strat_perf < 0.5 and pnl < 0:  # Poor strategy, negative result
                adjustment = abs(pnl) * 0.1
                adjusted['strategy'] += adjustment if pnl < 0 else -adjustment
        
        # Adjust for execution quality
        if 'execution_slippage' in trade_data:
            slippage = trade_data['execution_slippage']
            if abs(slippage) > 0.01 and pnl < 0:  # High slippage, negative result
                adjustment = abs(pnl) * 0.05
                adjusted['broker'] += adjustment if pnl < 0 else -adjustment
        
        # Adjust for risk management
        if 'risk_violations' in trade_data and trade_data['risk_violations']:
            # If risk was violated and trade was bad, increase RM attribution
            adjustment = abs(pnl) * 0.07
            adjusted['risk_management'] += adjustment if pnl < 0 else -adjustment
        
        return adjusted
    
    def calculate_counterfactual_analysis(self, 
                                       trade_data: Dict[str, Any], 
                                       actual_pnl: float) -> Dict[str, Any]:
        """
        Perform counterfactual analysis to determine what would have happened
        with different system component decisions
        """
        counterfactual_results = {}
        
        # Analyze what would have happened if watcher had been different
        if 'watcher_signals' in trade_data:
            # Simulate alternative watcher outcomes
            counterfactual_results['watcher_alternatives'] = self._analyze_watcher_alternatives(
                trade_data, actual_pnl
            )
        
        # Analyze what would have happened if engine had been different
        if 'engine_interpretations' in trade_data:
            counterfactual_results['engine_alternatives'] = self._analyze_engine_alternatives(
                trade_data, actual_pnl
            )
        
        # Analyze what would have happened if fusion had been different
        if 'fusion_combinations' in trade_data:
            counterfactual_results['fusion_alternatives'] = self._analyze_fusion_alternatives(
                trade_data, actual_pnl
            )
        
        # Analyze what would have happened if strategy had been different
        if 'alternative_strategies' in trade_data:
            counterfactual_results['strategy_alternatives'] = self._analyze_strategy_alternatives(
                trade_data, actual_pnl
            )
        
        return counterfactual_results
    
    def _analyze_watcher_alternatives(self, trade_data: Dict[str, Any], actual_pnl: float) -> List[Dict[str, Any]]:
        """
        Analyze alternative watcher signals and their potential outcomes
        """
        alternatives = []
        # This would typically involve historical simulation
        # For now, we'll return a placeholder
        return alternatives
    
    def _analyze_engine_alternatives(self, trade_data: Dict[str, Any], actual_pnl: float) -> List[Dict[str, Any]]:
        """
        Analyze alternative engine interpretations and their potential outcomes
        """
        alternatives = []
        # This would typically involve historical simulation
        # For now, we'll return a placeholder
        return alternatives
    
    def _analyze_fusion_alternatives(self, trade_data: Dict[str, Any], actual_pnl: float) -> List[Dict[str, Any]]:
        """
        Analyze alternative fusion combinations and their potential outcomes
        """
        alternatives = []
        # This would typically involve historical simulation
        # For now, we'll return a placeholder
        return alternatives
    
    def _analyze_strategy_alternatives(self, trade_data: Dict[str, Any], actual_pnl: float) -> List[Dict[str, Any]]:
        """
        Analyze alternative strategy selections and their potential outcomes
        """
        alternatives = []
        # This would typically involve historical simulation
        # For now, we'll return a placeholder
        return alternatives
    
    def calculate_regret_metrics(self, 
                               trade_data: Dict[str, Any], 
                               actual_pnl: float) -> Dict[str, float]:
        """
        Calculate regret metrics for the trade
        """
        regret_metrics = {
            'opportunity_cost': 0.0,
            'execution_regret': 0.0,
            'timing_regret': 0.0,
            'strategy_regret': 0.0
        }
        
        # Calculate opportunity cost if best alternative is known
        if 'best_alternative_pnl' in trade_data:
            regret_metrics['opportunity_cost'] = trade_data['best_alternative_pnl'] - actual_pnl
        
        # Calculate execution regret if ideal execution price is known
        if 'ideal_execution_pnl' in trade_data:
            regret_metrics['execution_regret'] = trade_data['ideal_execution_pnl'] - actual_pnl
        
        # Calculate timing regret if better timing existed
        if 'better_timing_pnl' in trade_data:
            regret_metrics['timing_regret'] = trade_data['better_timing_pnl'] - actual_pnl
        
        # Calculate strategy regret if better strategy existed
        if 'better_strategy_pnl' in trade_data:
            regret_metrics['strategy_regret'] = trade_data['better_strategy_pnl'] - actual_pnl
        
        return regret_metrics


# Global instance
forensic_attribution_model = ForensicAttributionModel()