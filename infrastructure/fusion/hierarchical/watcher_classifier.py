"""
Hierarchical Watcher Classification System
Implements the hedge-fund-grade multi-watcher architecture with role-based decision making.
"""
from enum import Enum
from typing import Dict, List, Set, Optional
from domain.entities.signal_entities import MarketObservation


class WatcherRole(Enum):
    """Classification of watcher roles in the hierarchical system"""
    REGIME = "REGIME"          # Global Capital Governor
    DISCOVERY = "DISCOVERY"    # Symbol Universe Expansion  
    DIRECTION = "DIRECTION"    # Symbol Bias Authority
    EXECUTION = "EXECUTION"    # Entry Timing & Veto


class WatcherClassifier:
    """Classifies watchers into their hierarchical roles"""
    
    # Define the watcher role mapping based on the task requirements
    WATCHER_ROLE_MAPPING = {
        # REGIME (Global Capital Governor)
        'market_pulse': WatcherRole.REGIME,
        'volatility': WatcherRole.REGIME,
        'funding_rate': WatcherRole.REGIME,
        'cmc_screener': WatcherRole.REGIME,  # For macro sentiment only
        
        # DISCOVERY (Symbol Universe Expansion)
        'anomaly_ml': WatcherRole.DISCOVERY,
        'cmc_screener_discovery': WatcherRole.DISCOVERY,  # Separate for discovery role
        
        # DIRECTION (Symbol Bias Authority)
        'trend_mtf': WatcherRole.DIRECTION,
        'liquidity': WatcherRole.DIRECTION,
        'historical_candle': WatcherRole.DIRECTION,
        
        # EXECUTION (Entry Timing & Veto)
        'orderflow_ws': WatcherRole.EXECUTION,
        'tick_watcher': WatcherRole.EXECUTION,
        'anomaly_ml_execution': WatcherRole.EXECUTION,  # Separate for execution role
    }
    
    # Define which watchers can be both discovery and other roles
    MULTI_ROLE_WATCHERS = {
        'cmc_screener': [WatcherRole.REGIME, WatcherRole.DISCOVERY],
        'anomaly_ml': [WatcherRole.DISCOVERY, WatcherRole.EXECUTION],
    }
    
    @classmethod
    def get_watcher_role(cls, watcher_name: str) -> Optional[WatcherRole]:
        """Get the primary role of a watcher"""
        # Handle multi-role watchers
        if watcher_name in cls.MULTI_ROLE_WATCHERS:
            # For multi-role watchers, return the primary role based on naming convention
            if 'discovery' in watcher_name:
                return WatcherRole.DISCOVERY
            elif 'execution' in watcher_name:
                return WatcherRole.EXECUTION
            else:
                # Default to first role in the list for regime watchers
                return cls.MULTI_ROLE_WATCHERS[watcher_name][0]
        
        return cls.WATCHER_ROLE_MAPPING.get(watcher_name)
    
    @classmethod
    def get_watchers_by_role(cls) -> Dict[WatcherRole, List[str]]:
        """Get all watchers grouped by their role"""
        role_mapping = {}
        for watcher, role in cls.WATCHER_ROLE_MAPPING.items():
            if role not in role_mapping:
                role_mapping[role] = []
            role_mapping[role].append(watcher)
        
        # Handle multi-role watchers
        for watcher, roles in cls.MULTI_ROLE_WATCHERS.items():
            for role in roles:
                if role not in role_mapping:
                    role_mapping[role] = []
                if watcher not in role_mapping[role]:
                    role_mapping[role].append(watcher)
        
        return role_mapping
    
    @classmethod
    def is_regime_watcher(cls, watcher_name: str) -> bool:
        """Check if a watcher is a regime watcher"""
        role = cls.get_watcher_role(watcher_name)
        return role == WatcherRole.REGIME
    
    @classmethod
    def is_discovery_watcher(cls, watcher_name: str) -> bool:
        """Check if a watcher is a discovery watcher"""
        role = cls.get_watcher_role(watcher_name)
        return role == WatcherRole.DISCOVERY
    
    @classmethod
    def is_direction_watcher(cls, watcher_name: str) -> bool:
        """Check if a watcher is a direction watcher"""
        role = cls.get_watcher_role(watcher_name)
        return role == WatcherRole.DIRECTION
    
    @classmethod
    def is_execution_watcher(cls, watcher_name: str) -> bool:
        """Check if a watcher is an execution watcher"""
        role = cls.get_watcher_role(watcher_name)
        return role == WatcherRole.EXECUTION


class WatcherAuthority:
    """Defines the authority and rules for each watcher role"""
    
    @staticmethod
    def get_role_authority(role: WatcherRole) -> Dict[str, any]:
        """Get the authority rules for a specific role"""
        authorities = {
            WatcherRole.REGIME: {
                'can_buy_sell': False,  # Cannot BUY or SELL
                'can_override': True,   # Can override other decisions
                'can_add_symbols': False,  # Cannot add symbols
                'can_determine_direction': False,  # Cannot determine direction
                'can_veto': False,  # Controls global regime, not individual vetoes
                'description': 'Global Capital Governor - decides IF system can trade'
            },
            WatcherRole.DISCOVERY: {
                'can_buy_sell': False,  # Cannot BUY or SELL
                'can_override': False,  # Cannot override other decisions
                'can_add_symbols': True,  # Can add symbols to pipeline
                'can_determine_direction': False,  # Cannot determine direction
                'can_veto': False,  # Cannot veto trades
                'description': 'Symbol Universe Expansion - decides WHICH symbols deserve attention'
            },
            WatcherRole.DIRECTION: {
                'can_buy_sell': True,   # Can propose BUY/SELL
                'can_override': False,  # Cannot override regime
                'can_add_symbols': False,  # Cannot add symbols
                'can_determine_direction': True,  # Can determine direction
                'can_veto': False,  # Cannot veto, only propose direction
                'description': 'Symbol Bias Authority - decides DIRECTION if regime allows'
            },
            WatcherRole.EXECUTION: {
                'can_buy_sell': False,  # Cannot create BUY/SELL
                'can_override': False,  # Cannot override higher levels
                'can_add_symbols': False,  # Cannot add symbols
                'can_determine_direction': False,  # Cannot determine direction
                'can_veto': True,  # Can veto trades
                'description': 'Entry Timing & Veto - decides WHEN, not WHETHER'
            }
        }
        return authorities.get(role, {})


class ObservationClassifier:
    """Classifies observations based on watcher role and content"""
    
    @staticmethod
    def classify_observation(observation: MarketObservation, watcher_name: str) -> Dict[str, any]:
        """Classify an observation based on the watcher that generated it"""
        role = WatcherClassifier.get_watcher_role(watcher_name)
        
        if not role:
            return {
                'role': None,
                'valid': False,
                'reason': f'Unknown watcher: {watcher_name}',
                'authority': {}
            }
        
        authority = WatcherAuthority.get_role_authority(role)
        
        # Validate the observation based on watcher role
        is_valid = ObservationClassifier._validate_observation_for_role(
            observation, role, watcher_name
        )
        
        return {
            'role': role,
            'valid': is_valid,
            'authority': authority,
            'watcher_name': watcher_name,
            'observation_type': observation.observation_type,
            'confidence': float(observation.confidence.value)
        }
    
    @staticmethod
    def _validate_observation_for_role(observation: MarketObservation, role: WatcherRole, watcher_name: str) -> bool:
        """Validate if an observation is appropriate for the watcher's role"""
        observation_type = observation.observation_type.lower()
        
        # Regime watchers should produce regime-related observations
        if role == WatcherRole.REGIME:
            regime_indicators = [
                'market_pulse', 'volatility', 'funding_rate', 
                'regime', 'macro', 'sentiment', 'risk'
            ]
            return any(indicator in observation_type for indicator in regime_indicators)
        
        # Discovery watchers should produce discovery-related observations
        elif role == WatcherRole.DISCOVERY:
            discovery_indicators = [
                'discovery', 'opportunity', 'anomaly', 'screener',
                'new', 'potential', 'candidate'
            ]
            return any(indicator in observation_type for indicator in discovery_indicators)
        
        # Direction watchers should produce directional observations
        elif role == WatcherRole.DIRECTION:
            direction_indicators = [
                'trend', 'direction', 'bias', 'momentum', 'signal',
                'bullish', 'bearish', 'positive', 'negative'
            ]
            return any(indicator in observation_type for indicator in direction_indicators)
        
        # Execution watchers should produce execution-related observations
        elif role == WatcherRole.EXECUTION:
            execution_indicators = [
                'entry', 'exit', 'timing', 'flow', 'tick', 'execution',
                'confirm', 'reject', 'wait', 'trigger'
            ]
            return any(indicator in observation_type for indicator in execution_indicators)
        
        return True  # Default to valid if role is unknown