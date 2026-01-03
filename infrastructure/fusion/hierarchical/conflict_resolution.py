"""
Conflict Resolution System for Hierarchical Multi-Watcher Architecture
Implements the required conflict resolution rules for the hedge-fund-grade system.
"""
from typing import List, Dict, Any, Optional, Tuple
from domain.entities.signal_entities import MarketObservation, FusedSignal, SignalType
from .watcher_classifier import WatcherClassifier, WatcherRole
from .confidence_thresholds import ConfidenceThresholds, ConfidenceValidator


class ConflictResolutionRules:
    """Implements the conflict resolution rules as specified in the task"""
    
    @staticmethod
    def resolve_conflicts(observations_with_watchers: List[Dict[str, Any]], symbol: str) -> Dict[str, Any]:
        """
        Resolve conflicts according to the hierarchical rules:
        1. Regime overrides everything
        2. Low confidence signals are discarded
        3. Execution can veto, never initiate
        4. Any unresolved conflict → WAIT
        """
        # First, filter out low confidence observations
        confident_observations, discarded_observations = ConfidenceValidator.filter_confident_observations(
            observations_with_watchers
        )
        
        if not confident_observations:
            return {
                'final_decision': 'WAIT',
                'confidence': 0.0,
                'reason': 'No confident observations',
                'regime_state': 'NEUTRAL',
                'discarded_count': len(discarded_observations),
                'resolved_by': 'no_confident_signals'
            }
        
        # Separate observations by role
        regime_obs = []
        discovery_obs = []
        direction_obs = []
        execution_obs = []
        
        for obs_data in confident_observations:
            watcher_name = obs_data['watcher_name']
            role = WatcherClassifier.get_watcher_role(watcher_name)
            
            if role == WatcherRole.REGIME:
                regime_obs.append(obs_data)
            elif role == WatcherRole.DISCOVERY:
                discovery_obs.append(obs_data)
            elif role == WatcherRole.DIRECTION:
                direction_obs.append(obs_data)
            elif role == WatcherRole.EXECUTION:
                execution_obs.append(obs_data)
        
        # Determine regime state first (highest priority)
        regime_state, regime_confidence = ConflictResolutionRules._determine_regime_state(regime_obs)
        
        # If regime is RISK_OFF or OVERHEATED, no trading allowed regardless of other signals
        if regime_state in ['RISK_OFF', 'OVERHEATED']:
            return {
                'final_decision': 'WAIT',
                'confidence': regime_confidence,
                'reason': f'Regime state {regime_state} blocks all trading',
                'regime_state': regime_state,
                'discarded_count': len(discarded_observations),
                'resolved_by': 'regime_override'
            }
        
        # Check for direction signals if regime allows trading
        direction_result = ConflictResolutionRules._resolve_direction_conflicts(direction_obs, regime_state)
        
        # Check for execution signals
        execution_result = ConflictResolutionRules._resolve_execution_conflicts(execution_obs)
        
        # If we have direction but execution says REJECT, then WAIT
        if direction_result['has_direction'] and execution_result['action'] == 'REJECT':
            return {
                'final_decision': 'WAIT',
                'confidence': min(direction_result['confidence'], execution_result['confidence']),
                'reason': 'Execution veto on direction signal',
                'regime_state': regime_state,
                'discarded_count': len(discarded_observations),
                'resolved_by': 'execution_veto'
            }
        
        # If we have direction and execution confirms, make the trade
        if direction_result['has_direction'] and execution_result['action'] == 'CONFIRM':
            return {
                'final_decision': direction_result['direction'],
                'confidence': min(direction_result['confidence'], execution_result['confidence']),
                'reason': f'Direction {direction_result["direction"]} confirmed by execution',
                'regime_state': regime_state,
                'discarded_count': len(discarded_observations),
                'resolved_by': 'direction_execution_alignment'
            }
        
        # If we have direction but no execution confirmation, wait
        if direction_result['has_direction'] and execution_result['action'] == 'WAIT':
            return {
                'final_decision': 'WAIT',
                'confidence': direction_result['confidence'],
                'reason': 'Direction signal waiting for execution confirmation',
                'regime_state': regime_state,
                'discarded_count': len(discarded_observations),
                'resolved_by': 'pending_execution'
            }
        
        # If no direction signals, wait
        return {
            'final_decision': 'WAIT',
            'confidence': regime_confidence,
            'reason': 'No valid direction signals after regime check',
            'regime_state': regime_state,
            'discarded_count': len(discarded_observations),
            'resolved_by': 'no_direction_signals'
        }
    
    @staticmethod
    def _determine_regime_state(regime_observations: List[Dict[str, Any]]) -> Tuple[str, float]:
        """Determine the regime state from regime observations"""
        if not regime_observations:
            return 'NEUTRAL', 0.5  # Default regime
        
        # Aggregate regime signals
        total_confidence = 0.0
        risk_on_signals = 0
        risk_off_signals = 0
        neutral_signals = 0
        overheated_signals = 0
        
        for obs_data in regime_observations:
            obs = obs_data['observation']
            conf = float(obs.confidence.value)
            obs_type = obs.observation_type.lower()
            
            total_confidence += conf
            
            # Classify regime signal based on observation type
            if any(indicator in obs_type for indicator in ['risk_on', 'positive', 'bullish', 'market_pulse_positive']):
                risk_on_signals += 1
            elif any(indicator in obs_type for indicator in ['risk_off', 'negative', 'bearish', 'volatile']):
                risk_off_signals += 1
            elif any(indicator in obs_type for indicator in ['overheated', 'extreme']):
                overheated_signals += 1
            else:
                neutral_signals += 1
        
        if total_confidence == 0:
            return 'NEUTRAL', 0.5
        
        # Determine regime based on majority of confident signals
        if overheated_signals > risk_on_signals and overheated_signals > risk_off_signals:
            return 'OVERHEATED', 0.8
        elif risk_on_signals >= risk_off_signals:
            if risk_on_signals > risk_off_signals:
                return 'RISK_ON', 0.7
            else:
                return 'WEAK_RISK_ON', 0.6  # Equal but positive bias
        elif risk_off_signals > risk_on_signals:
            return 'RISK_OFF', 0.7
        else:
            return 'NEUTRAL', 0.5
    
    @staticmethod
    def _resolve_direction_conflicts(direction_observations: List[Dict[str, Any]], regime_state: str) -> Dict[str, Any]:
        """Resolve conflicts among direction observations"""
        if not direction_observations:
            return {
                'has_direction': False,
                'direction': None,
                'confidence': 0.0,
                'reason': 'no_direction_observations'
            }
        
        # Count BUY vs SELL signals
        buy_signals = []
        sell_signals = []
        neutral_signals = []
        
        for obs_data in direction_observations:
            obs = obs_data['observation']
            obs_type = obs.observation_type.lower()
            
            # Classify direction based on observation type
            if any(indicator in obs_type for indicator in ['buy', 'positive', 'bullish', 'up', 'trend_positive']):
                buy_signals.append(obs)
            elif any(indicator in obs_type for indicator in ['sell', 'negative', 'bearish', 'down', 'trend_negative']):
                sell_signals.append(obs)
            else:
                neutral_signals.append(obs)
        
        # Apply regime filter - only allow directions that align with regime
        if regime_state in ['RISK_ON', 'WEAK_RISK_ON']:
            # Both directions allowed in risk-on regime
            valid_buy_signals = buy_signals
            valid_sell_signals = sell_signals
        elif regime_state == 'NEUTRAL':
            # Only strong signals allowed in neutral regime
            valid_buy_signals = [obs for obs in buy_signals if float(obs.confidence.value) > 0.7]
            valid_sell_signals = [obs for obs in sell_signals if float(obs.confidence.value) > 0.7]
        else:
            # No directional trading in risk-off regimes
            valid_buy_signals = []
            valid_sell_signals = []
        
        # Check if we have minimum 2 aligned signals as required
        if len(valid_buy_signals) >= 2:
            avg_confidence = sum(float(obs.confidence.value) for obs in valid_buy_signals) / len(valid_buy_signals)
            return {
                'has_direction': True,
                'direction': 'BUY',
                'confidence': avg_confidence,
                'reason': f'multiple_buy_signals_aligned ({len(valid_buy_signals)})'
            }
        elif len(valid_sell_signals) >= 2:
            avg_confidence = sum(float(obs.confidence.value) for obs in valid_sell_signals) / len(valid_sell_signals)
            return {
                'has_direction': True,
                'direction': 'SELL',
                'confidence': avg_confidence,
                'reason': f'multiple_sell_signals_aligned ({len(valid_sell_signals)})'
            }
        else:
            return {
                'has_direction': False,
                'direction': None,
                'confidence': 0.0,
                'reason': 'insufficient_aligned_direction_signals'
            }
    
    @staticmethod
    def _resolve_execution_conflicts(execution_observations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Resolve conflicts among execution observations"""
        if not execution_observations:
            # If no execution signals, default to CONFIRM to allow direction to proceed
            return {
                'action': 'CONFIRM',
                'confidence': 0.5,
                'reason': 'no_execution_signals_default_confirm'
            }
        
        confirm_signals = []
        reject_signals = []
        wait_signals = []
        
        for obs_data in execution_observations:
            obs = obs_data['observation']
            obs_type = obs.observation_type.lower()
            
            # Classify execution action based on observation type
            if any(indicator in obs_type for indicator in ['confirm', 'entry', 'execute', 'go']):
                confirm_signals.append(obs)
            elif any(indicator in obs_type for indicator in ['reject', 'reject_signal', 'avoid', 'stop']):
                reject_signals.append(obs)
            else:
                wait_signals.append(obs)
        
        # Execution hierarchy: REJECT > CONFIRM > WAIT
        if reject_signals:
            avg_confidence = sum(float(obs.confidence.value) for obs in reject_signals) / len(reject_signals)
            return {
                'action': 'REJECT',
                'confidence': avg_confidence,
                'reason': f'execution_reject_signals ({len(reject_signals)})'
            }
        elif confirm_signals:
            avg_confidence = sum(float(obs.confidence.value) for obs in confirm_signals) / len(confirm_signals)
            return {
                'action': 'CONFIRM',
                'confidence': avg_confidence,
                'reason': f'execution_confirm_signals ({len(confirm_signals)})'
            }
        else:
            # Only wait signals or neutral signals
            if wait_signals:
                avg_confidence = sum(float(obs.confidence.value) for obs in wait_signals) / len(wait_signals)
                return {
                    'action': 'WAIT',
                    'confidence': avg_confidence,
                    'reason': f'execution_wait_signals ({len(wait_signals)})'
                }
            else:
                return {
                    'action': 'CONFIRM',
                    'confidence': 0.5,
                    'reason': 'no_clear_execution_signal_default_confirm'
                }


class HierarchicalSignalFuser:
    """Main fuser that implements the hierarchical decision making"""
    
    def __init__(self):
        self.conflict_resolver = ConflictResolutionRules()
    
    def fuse_signals_hierarchically(self, observations_with_watchers: List[Dict[str, Any]], symbol: str) -> Optional[FusedSignal]:
        """Fuse signals using hierarchical decision making"""
        if not observations_with_watchers:
            return None
        
        # Apply conflict resolution
        resolution_result = self.conflict_resolver.resolve_conflicts(observations_with_watchers, symbol)
        
        # Map the resolution result to a FusedSignal
        if resolution_result['final_decision'] == 'WAIT':
            # Return a neutral signal with low confidence to indicate waiting
            from datetime import datetime
            from domain.value_objects import Percentage
            from decimal import Decimal
            
            return FusedSignal(
                symbol=symbol,
                dominant_bias=SignalType.NEUTRAL,
                direction=0.0,
                dominance_score=0.0,
                regime_context=resolution_result['regime_state'],
                confidence=Percentage(Decimal('0.1')),  # Low confidence for WAIT
                timestamp=datetime.now(),
                metadata={
                    'resolution_reason': resolution_result['reason'],
                    'resolved_by': resolution_result['resolved_by'],
                    'discarded_count': resolution_result['discarded_count'],
                    'regime_state': resolution_result['regime_state'],
                    'hierarchical_fusion': True
                }
            )
        elif resolution_result['final_decision'] in ['BUY', 'SELL']:
            from datetime import datetime
            from domain.value_objects import Percentage, Symbol
            from decimal import Decimal
            
            # Map string decision to SignalType
            signal_type = SignalType.BUY if resolution_result['final_decision'] == 'BUY' else SignalType.SELL
            direction = 1.0 if resolution_result['final_decision'] == 'BUY' else -1.0
            
            return FusedSignal(
                symbol=symbol,
                dominant_bias=signal_type,
                direction=direction,
                dominance_score=resolution_result['confidence'],
                regime_context=resolution_result['regime_state'],
                confidence=Percentage(Decimal(str(resolution_result['confidence']))),
                timestamp=datetime.now(),
                metadata={
                    'resolution_reason': resolution_result['reason'],
                    'resolved_by': resolution_result['resolved_by'],
                    'discarded_count': resolution_result['discarded_count'],
                    'regime_state': resolution_result['regime_state'],
                    'hierarchical_fusion': True
                }
            )
        else:
            # Unknown decision, return neutral
            from datetime import datetime
            from domain.value_objects import Percentage
            from decimal import Decimal
            
            return FusedSignal(
                symbol=symbol,
                dominant_bias=SignalType.NEUTRAL,
                direction=0.0,
                dominance_score=0.0,
                regime_context=resolution_result['regime_state'],
                confidence=Percentage(Decimal('0.3')),  # Low-medium confidence
                timestamp=datetime.now(),
                metadata={
                    'resolution_reason': resolution_result['reason'],
                    'resolved_by': resolution_result['resolved_by'],
                    'discarded_count': resolution_result['discarded_count'],
                    'regime_state': resolution_result['regime_state'],
                    'hierarchical_fusion': True,
                    'unknown_decision': resolution_result['final_decision']
                }
            )