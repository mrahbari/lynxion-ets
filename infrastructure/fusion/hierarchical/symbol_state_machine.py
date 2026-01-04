"""
Symbol State Machine for Hierarchical Multi-Watcher Architecture
Implements the required symbol lifecycle from discovery to execution.
"""
from enum import Enum
from typing import Dict, Any, Optional, List
from datetime import datetime
from domain.value_objects import Symbol


class SymbolState(Enum):
    """States in the symbol lifecycle"""
    DISCOVERED = "DISCOVERED"
    REGIME_BLOCKED = "REGIME_BLOCKED"
    REGIME_ALLOWED = "REGIME_ALLOWED"
    DIRECTION_PENDING = "DIRECTION_PENDING"
    DIRECTION_CONFIRMED = "DIRECTION_CONFIRMED"
    EXECUTION_PENDING = "EXECUTION_PENDING"
    READY_TO_TRADE = "READY_TO_TRADE"
    TRADE_EXECUTED = "TRADE_EXECUTED"
    TRADE_CLOSED = "TRADE_CLOSED"
    SUSPENDED = "SUSPENDED"


class SymbolStateMachine:
    """Manages the state transitions for symbols in the hierarchical system"""
    
    # Define valid state transitions
    VALID_TRANSITIONS = {
        SymbolState.DISCOVERED: [SymbolState.REGIME_BLOCKED, SymbolState.REGIME_ALLOWED],
        SymbolState.REGIME_BLOCKED: [SymbolState.SUSPENDED, SymbolState.DISCOVERED],  # Can be unblocked
        SymbolState.REGIME_ALLOWED: [SymbolState.DIRECTION_PENDING, SymbolState.DIRECTION_CONFIRMED, SymbolState.SUSPENDED],
        SymbolState.DIRECTION_PENDING: [SymbolState.DIRECTION_CONFIRMED, SymbolState.SUSPENDED, SymbolState.REGIME_BLOCKED],
        SymbolState.DIRECTION_CONFIRMED: [SymbolState.EXECUTION_PENDING, SymbolState.SUSPENDED, SymbolState.DIRECTION_PENDING],
        SymbolState.EXECUTION_PENDING: [SymbolState.READY_TO_TRADE, SymbolState.SUSPENDED, SymbolState.DIRECTION_PENDING],
        SymbolState.READY_TO_TRADE: [SymbolState.TRADE_EXECUTED, SymbolState.SUSPENDED, SymbolState.EXECUTION_PENDING],
        SymbolState.TRADE_EXECUTED: [SymbolState.TRADE_CLOSED, SymbolState.SUSPENDED],
        SymbolState.TRADE_CLOSED: [SymbolState.DISCOVERED],  # Can be rediscovered for new trades
        SymbolState.SUSPENDED: [SymbolState.DISCOVERED, SymbolState.REGIME_ALLOWED, SymbolState.REGIME_BLOCKED],
    }
    
    def __init__(self):
        self.symbol_states: Dict[str, SymbolState] = {}
        self.state_history: Dict[str, List[Dict[str, Any]]] = {}
        self.state_contexts: Dict[str, Dict[str, Any]] = {}  # Store context for each symbol's state
    
    def initialize_symbol(self, symbol: Symbol, initial_state: SymbolState = SymbolState.DISCOVERED) -> bool:
        """Initialize a symbol with an initial state"""
        symbol_str = symbol.value
        if symbol_str in self.symbol_states:
            return False  # Symbol already exists
        
        self.symbol_states[symbol_str] = initial_state
        self.state_history[symbol_str] = [{
            'state': initial_state,
            'timestamp': datetime.now(),
            'reason': 'initialization',
            'context': {}
        }]
        self.state_contexts[symbol_str] = {}
        return True
    
    def get_state(self, symbol: Symbol) -> Optional[SymbolState]:
        """Get the current state of a symbol"""
        return self.symbol_states.get(symbol.value)
    
    def can_transition(self, symbol: Symbol, new_state: SymbolState) -> bool:
        """Check if a state transition is valid"""
        current_state = self.get_state(symbol)
        if not current_state:
            return False
        
        valid_next_states = self.VALID_TRANSITIONS.get(current_state, [])
        return new_state in valid_next_states
    
    def transition(self, symbol: Symbol, new_state: SymbolState, reason: str = "", context: Optional[Dict[str, Any]] = None) -> bool:
        """Transition a symbol to a new state if valid"""
        symbol_str = symbol.value
        
        if not self.can_transition(symbol, new_state):
            return False
        
        old_state = self.symbol_states[symbol_str]
        self.symbol_states[symbol_str] = new_state
        
        # Record the transition in history
        transition_record = {
            'from_state': old_state,
            'to_state': new_state,
            'timestamp': datetime.now(),
            'reason': reason,
            'context': context or {}
        }
        
        if symbol_str not in self.state_history:
            self.state_history[symbol_str] = []
        self.state_history[symbol_str].append(transition_record)
        
        # Update context if provided
        if context:
            if symbol_str not in self.state_contexts:
                self.state_contexts[symbol_str] = {}
            self.state_contexts[symbol_str].update(context)
        
        return True
    
    def get_history(self, symbol: Symbol) -> List[Dict[str, Any]]:
        """Get the state transition history for a symbol"""
        return self.state_history.get(symbol.value, [])
    
    def get_context(self, symbol: Symbol) -> Dict[str, Any]:
        """Get the current context for a symbol"""
        return self.state_contexts.get(symbol.value, {})
    
    def reset_symbol(self, symbol: Symbol) -> bool:
        """Reset a symbol to the initial DISCOVERED state"""
        return self.transition(symbol, SymbolState.DISCOVERED, "reset")
    
    def is_tradable(self, symbol: Symbol) -> bool:
        """Check if a symbol is in a tradable state"""
        current_state = self.get_state(symbol)
        return current_state in [SymbolState.READY_TO_TRADE, SymbolState.TRADE_EXECUTED]
    
    def is_blocked_by_regime(self, symbol: Symbol) -> bool:
        """Check if a symbol is blocked by regime"""
        current_state = self.get_state(symbol)
        return current_state in [SymbolState.REGIME_BLOCKED, SymbolState.SUSPENDED]


class HierarchicalSymbolManager:
    """Manages symbols through the hierarchical decision process"""
    
    def __init__(self):
        self.state_machine = SymbolStateMachine()
    
    def process_discovery(self, symbol: Symbol, discovered_by: str = "unknown") -> bool:
        """Process a newly discovered symbol"""
        if not self.state_machine.get_state(symbol):
            # Initialize if not exists
            self.state_machine.initialize_symbol(symbol, SymbolState.DISCOVERED)
        
        # Update context with discovery information
        context = {
            'discovered_by': discovered_by,
            'discovered_at': datetime.now().isoformat()
        }
        
        # Transition to discovered state (or remain if already discovered)
        return self.state_machine.transition(symbol, SymbolState.DISCOVERED, "discovery", context)
    
    def apply_regime_decision(self, symbol: Symbol, regime_state: str, confidence: float) -> bool:
        """Apply regime decision to a symbol"""
        current_state = self.state_machine.get_state(symbol)
        
        if current_state not in [SymbolState.DISCOVERED, SymbolState.REGIME_ALLOWED, SymbolState.REGIME_BLOCKED]:
            # Only apply regime decision to symbols in appropriate states
            return False
        
        # Determine next state based on regime
        if regime_state in ['RISK_OFF', 'OVERHEATED']:
            new_state = SymbolState.REGIME_BLOCKED
            reason = f"blocked_by_regime_{regime_state}"
        else:
            new_state = SymbolState.REGIME_ALLOWED
            reason = f"allowed_by_regime_{regime_state}"
        
        context = {
            'regime_state': regime_state,
            'regime_confidence': confidence,
            'regime_applied_at': datetime.now().isoformat()
        }
        
        return self.state_machine.transition(symbol, new_state, reason, context)
    
    def apply_direction_decision(self, symbol: Symbol, direction: Optional[str], confidence: float) -> bool:
        """Apply direction decision to a symbol"""
        current_state = self.state_machine.get_state(symbol)
        
        if current_state != SymbolState.REGIME_ALLOWED:
            # Can only apply direction if regime allows
            return False
        
        if direction is None:
            # No direction, stay in pending or go back to regime allowed
            return self.state_machine.transition(symbol, SymbolState.DIRECTION_PENDING, "no_direction_signal")
        else:
            context = {
                'direction': direction,
                'direction_confidence': confidence,
                'direction_applied_at': datetime.now().isoformat()
            }
            
            # Transition to direction confirmed if we have a direction
            return self.state_machine.transition(symbol, SymbolState.DIRECTION_CONFIRMED, "direction_confirmed", context)
    
    def apply_execution_decision(self, symbol: Symbol, execution_action: str, confidence: float) -> bool:
        """Apply execution decision to a symbol"""
        current_state = self.state_machine.get_state(symbol)

        if current_state != SymbolState.DIRECTION_CONFIRMED:
            # Can only apply execution if direction is confirmed
            return False

        context = {
            'execution_action': execution_action,
            'execution_confidence': confidence,
            'execution_applied_at': datetime.now().isoformat()
        }

        # First transition to EXECUTION_PENDING (valid transition from DIRECTION_CONFIRMED)
        success = self.state_machine.transition(symbol, SymbolState.EXECUTION_PENDING, "execution_pending", context)
        if not success:
            return False

        # Now the current state is EXECUTION_PENDING, check if we can transition further
        if execution_action == "CONFIRM":
            # From EXECUTION_PENDING, we can transition to READY_TO_TRADE
            return self.state_machine.transition(symbol, SymbolState.READY_TO_TRADE, "execution_confirmed", context)
        elif execution_action == "REJECT":
            # From EXECUTION_PENDING, we can transition to DIRECTION_PENDING
            return self.state_machine.transition(symbol, SymbolState.DIRECTION_PENDING, "execution_rejected")
        else:
            # For WAIT or other actions, stay in EXECUTION_PENDING
            return True  # Already successfully in EXECUTION_PENDING
    
    def execute_trade(self, symbol: Symbol, execution_details: Dict[str, Any]) -> bool:
        """Execute trade for a symbol"""
        current_state = self.state_machine.get_state(symbol)
        
        if current_state != SymbolState.READY_TO_TRADE:
            return False
        
        context = {
            'execution_details': execution_details,
            'executed_at': datetime.now().isoformat()
        }
        
        return self.state_machine.transition(symbol, SymbolState.TRADE_EXECUTED, "trade_executed", context)
    
    def close_trade(self, symbol: Symbol, close_details: Dict[str, Any]) -> bool:
        """Close trade for a symbol"""
        current_state = self.state_machine.get_state(symbol)
        
        if current_state != SymbolState.TRADE_EXECUTED:
            return False
        
        context = {
            'close_details': close_details,
            'closed_at': datetime.now().isoformat()
        }
        
        return self.state_machine.transition(symbol, SymbolState.TRADE_CLOSED, "trade_closed", context)
    
    def get_symbol_status(self, symbol: Symbol) -> Dict[str, Any]:
        """Get comprehensive status of a symbol"""
        current_state = self.state_machine.get_state(symbol)
        history = self.state_machine.get_history(symbol)
        context = self.state_machine.get_context(symbol)
        
        return {
            'symbol': symbol.value,
            'current_state': current_state.value if current_state else None,
            'is_tradable': self.state_machine.is_tradable(symbol),
            'is_blocked_by_regime': self.state_machine.is_blocked_by_regime(symbol),
            'state_history': [
                {
                    'from': h.get('from_state').value if h.get('from_state') else None,
                    'to': h.get('to_state').value if h.get('to_state') else h.get('state').value,
                    'timestamp': h['timestamp'].isoformat() if isinstance(h['timestamp'], datetime) else h['timestamp'],
                    'reason': h['reason'],
                    'context': h['context']
                } for h in history
            ],
            'current_context': context,
            'last_transition': history[-1] if history else None
        }