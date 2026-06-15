"""
Hierarchical Fusion Service for Hedge-Fund-Grade Multi-Watcher Architecture
Implements the complete hierarchical decision-making system with all required components.
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from decimal import Decimal

from domain.entities import MarketObservation, FusedSignal, SignalType
from domain.value_objects import Symbol, Percentage
from .watcher_classifier import WatcherClassifier, WatcherRole, ObservationClassifier
from .confidence_thresholds import ConfidenceThresholds, ConfidenceValidator, RegimeConfidenceManager
from .conflict_resolution import HierarchicalSignalFuser, ConflictResolutionRules
from .symbol_state_machine import HierarchicalSymbolManager, SymbolState
from .hierarchical_logger import hierarchical_logger


class HierarchicalFusionService:
    """Main fusion service implementing the hierarchical multi-watcher architecture"""
    
    def __init__(self):
        self.watcher_classifier = WatcherClassifier()
        self.confidence_validator = ConfidenceValidator()
        self.conflict_resolver = ConflictResolutionRules()
        self.signal_fuser = HierarchicalSignalFuser()
        self.symbol_manager = HierarchicalSymbolManager()
        self.logger = hierarchical_logger
        
        # Track symbol states and decisions
        self.symbol_regime_states = {}
        self.symbol_direction_states = {}
        self.symbol_execution_states = {}
    
    def fuse_signals_hierarchically(self, observations_with_watchers: List[Dict[str, Any]], symbol: Symbol) -> Optional[FusedSignal]:
        """
        Main method to fuse signals using the hierarchical architecture.
        Implements the required flow: DISCOVERY → REGIME CHECK → DIRECTION CONFIRMATION → EXECUTION CONFIRMATION
        """
        if not observations_with_watchers:
            self.logger.log_decision(
                symbol=symbol,
                raised_by="system",
                regime_state="NEUTRAL",
                direction_signals={},
                execution_signals={},
                final_decision="WAIT",
                reason="no_observations"
            )
            return None
        
        # Step 1: Classify all observations by watcher role
        classified_observations = []
        for obs_data in observations_with_watchers:
            observation = obs_data['observation']
            watcher_name = obs_data['watcher_name']
            
            classification = ObservationClassifier.classify_observation(observation, watcher_name)
            
            if not classification['valid']:
                self.logger.log_confidence_filtering(
                    watcher_name=watcher_name,
                    confidence=float(observation.confidence.value),
                    threshold=0.0,  # No threshold check for classification
                    action="DISCARDED_INVALID_CLASSIFICATION",
                    symbol=symbol.value
                )
                continue
            
            classified_observations.append({
                **obs_data,
                'classification': classification
            })
        
        # Step 2: Validate confidence thresholds
        confident_observations, discarded_observations = ConfidenceValidator.filter_confident_observations(
            [{'observation': obs['observation'], 'watcher_name': obs['watcher_name']} for obs in classified_observations]
        )
        
        # Log discarded observations
        for disc_obs in discarded_observations:
            self.logger.log_confidence_filtering(
                watcher_name=disc_obs['watcher_name'],
                confidence=float(disc_obs['observation'].confidence.value),
                threshold=ConfidenceThresholds.get_threshold(disc_obs['watcher_name']),
                action="DISCARDED_BELOW_THRESHOLD",
                symbol=symbol.value
            )
        
        # Step 3: Apply symbol state machine to manage the lifecycle
        self.symbol_manager.process_discovery(symbol, discovered_by="system")
        
        # Step 4: Determine regime state first (highest priority)
        regime_state, regime_confidence = RegimeConfidenceManager.get_regime_state_from_observations(
            [{'observation': obs['observation'], 'watcher_name': obs['watcher_name']} for obs in confident_observations]
        )
        
        # Apply regime decision to symbol
        self.symbol_manager.apply_regime_decision(symbol, regime_state, regime_confidence)
        
        self.logger.log_regime_state(
            symbol=symbol,
            regime_state=regime_state,
            confidence=regime_confidence,
            reason="aggregated_from_regime_watchers"
        )
        
        # Step 5: If regime blocks trading, return early
        if regime_state in ['RISK_OFF', 'OVERHEATED']:
            self.logger.log_decision(
                symbol=symbol,
                raised_by="regime_system",
                regime_state=regime_state,
                direction_signals={},
                execution_signals={},
                final_decision="WAIT",
                reason=f"regime_block_{regime_state}"
            )
            return self._create_neutral_fused_signal(symbol, regime_state, regime_confidence, "regime_blocked")
        
        # Step 6: Process direction signals
        direction_observations = []
        for obs_data in confident_observations:
            watcher_name = obs_data['watcher_name']
            if self.watcher_classifier.is_direction_watcher(watcher_name):
                direction_observations.append(obs_data)
        
        # Determine direction based on direction watchers
        direction_result = self.conflict_resolver._resolve_direction_conflicts(direction_observations, regime_state)
        
        # Apply direction decision to symbol
        self.symbol_manager.apply_direction_decision(
            symbol, 
            direction_result['direction'], 
            direction_result['confidence']
        )
        
        self.logger.log_direction_analysis(
            symbol=symbol,
            direction_signals={obs['watcher_name']: obs['observation'].observation_type for obs in direction_observations},
            final_direction=direction_result['direction'] or "NONE",
            confidence=direction_result['confidence'],
            reason=direction_result['reason']
        )
        
        # Step 7: If no direction, return neutral
        if not direction_result['has_direction']:
            self.logger.log_decision(
                symbol=symbol,
                raised_by="direction_system",
                regime_state=regime_state,
                direction_signals={obs['watcher_name']: obs['observation'].observation_type for obs in direction_observations},
                execution_signals={},
                final_decision="WAIT",
                reason=direction_result['reason']
            )
            return self._create_neutral_fused_signal(symbol, regime_state, direction_result['confidence'], "no_direction")
        
        # Step 8: Process execution signals
        execution_observations = []
        for obs_data in confident_observations:
            watcher_name = obs_data['watcher_name']
            if self.watcher_classifier.is_execution_watcher(watcher_name):
                execution_observations.append(obs_data)
        
        # Determine execution action
        execution_result = self.conflict_resolver._resolve_execution_conflicts(execution_observations)
        
        # Apply execution decision to symbol
        self.symbol_manager.apply_execution_decision(
            symbol,
            execution_result['action'],
            execution_result['confidence']
        )
        
        self.logger.log_execution_decision(
            symbol=symbol,
            action=execution_result['action'],
            confidence=execution_result['confidence'],
            reason=execution_result['reason'],
            execution_signals={obs['watcher_name']: obs['observation'].observation_type for obs in execution_observations}
        )
        
        # Step 9: Apply conflict resolution to get final decision
        resolution_result = self.conflict_resolver.resolve_conflicts(confident_observations, symbol.value)
        
        self.logger.log_conflict_resolution(symbol, resolution_result)
        
        # Step 10: Create final fused signal based on resolution
        final_signal = self.signal_fuser.fuse_signals_hierarchically(confident_observations, symbol)
        
        # Log the final decision
        self.logger.log_decision(
            symbol=symbol,
            raised_by="hierarchical_fusion",
            regime_state=regime_state,
            direction_signals={obs['watcher_name']: obs['observation'].observation_type for obs in direction_observations},
            execution_signals={obs['watcher_name']: obs['observation'].observation_type for obs in execution_observations},
            final_decision=resolution_result['final_decision'],
            reason=resolution_result['reason']
        )
        
        # Log the complete flow
        self.logger.log_full_flow(
            symbol=symbol.value,
            watcher="Multiple Watchers",
            engine="Hierarchical Engine",
            fusion="Hierarchical Fusion Service",
            strategy="StrategyManager",
            broker="MultiBroker",
            decision=f"Fused Signal: {final_signal.dominant_bias.name if final_signal else 'NONE'}",
            confidence=regime_confidence if final_signal else 0.0,
            reason=resolution_result['reason']
        )
        
        return final_signal
    
    def _create_neutral_fused_signal(self, symbol: Symbol, regime_context: str, confidence: float, reason: str) -> FusedSignal:
        """Create a neutral fused signal"""
        return FusedSignal(
            symbol=symbol,
            dominant_bias=SignalType.NEUTRAL,
            direction=0.0,
            dominance_score=0.0,
            regime_context=regime_context,
            confidence=Percentage(Decimal(str(confidence))),
            timestamp=datetime.now(),
            metadata={
                'reason': reason,
                'hierarchical_fusion': True,
                'regime_context': regime_context
            }
        )
    
    def get_symbol_status(self, symbol: Symbol) -> Dict[str, Any]:
        """Get the status of a symbol in the hierarchical system"""
        return self.symbol_manager.get_symbol_status(symbol)
    
    def get_regime_state(self, symbol: Symbol) -> str:
        """Get the current regime state for a symbol"""
        status = self.symbol_manager.get_symbol_status(symbol)
        return status['current_context'].get('regime_state', 'NEUTRAL')


# Global hierarchical fusion service instance
hierarchical_fusion_service = HierarchicalFusionService()