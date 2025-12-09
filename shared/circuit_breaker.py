"""
Circuit breaker implementation for the enterprise hedge fund trading system.
Provides resilience by preventing repeated failures to external services.
"""
import time
from enum import Enum
from typing import Callable, Any, Optional, Dict
from datetime import datetime, timedelta
from shared.logger import logger


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation, requests pass through
    OPEN = "open"          # Tripped, requests fail fast
    HALF_OPEN = "half_open"  # Testing if service has recovered


class CircuitBreaker:
    """Circuit breaker pattern implementation"""
    
    def __init__(self, 
                 name: str,
                 failure_threshold: int = 5,
                 timeout: int = 60,  # seconds
                 expected_exception: type = Exception):
        self.name = name
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.expected_exception = expected_exception
        
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.open_since: Optional[datetime] = None
        
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute the function with circuit breaker protection"""
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                logger.info(f"Circuit breaker {self.name} entering HALF_OPEN state", 
                           circuit_breaker=self.name)
            else:
                raise Exception(f"Circuit breaker {self.name} is OPEN. Requests blocked.")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise e
        except Exception as e:
            # For other exceptions, we might not want to trip the circuit
            # This allows distinguishing between expected failures and unexpected errors
            logger.warning(f"Unexpected error in circuit breaker {self.name}: {str(e)}",
                          circuit_breaker=self.name)
            raise e
    
    def _on_success(self):
        """Handle successful operation"""
        if self.state != CircuitState.CLOSED:
            logger.info(f"Circuit breaker {self.name} closed after successful operation",
                       circuit_breaker=self.name)
        
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
        self.open_since = None
    
    def _on_failure(self):
        """Handle failed operation"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.state == CircuitState.HALF_OPEN:
            # Failure in half-open state means service is still down
            self._trip()
        elif self.failure_count >= self.failure_threshold:
            # Crossed threshold, trip the circuit
            self._trip()
    
    def _trip(self):
        """Trip the circuit breaker to OPEN state"""
        self.state = CircuitState.OPEN
        self.open_since = datetime.now()
        logger.warning(f"Circuit breaker {self.name} TRIPPED",
                      circuit_breaker=self.name,
                      failure_count=self.failure_count)
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset"""
        if self.open_since is None:
            return False
        return datetime.now() - self.open_since > timedelta(seconds=self.timeout)
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of the circuit breaker"""
        return {
            'name': self.name,
            'state': self.state.value,
            'failure_count': self.failure_count,
            'failure_threshold': self.failure_threshold,
            'last_failure_time': self.last_failure_time.isoformat() if self.last_failure_time else None,
            'open_since': self.open_since.isoformat() if self.open_since else None,
            'timeout': self.timeout,
            'should_reset': self._should_attempt_reset()
        }


class CircuitBreakerManager:
    """Manager for multiple circuit breakers"""
    
    def __init__(self):
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
    
    def register_circuit_breaker(self, circuit_breaker: CircuitBreaker):
        """Register a circuit breaker"""
        self.circuit_breakers[circuit_breaker.name] = circuit_breaker
    
    def get_circuit_breaker(self, name: str) -> Optional[CircuitBreaker]:
        """Get a circuit breaker by name"""
        return self.circuit_breakers.get(name)
    
    def call_with_circuit_breaker(self, circuit_breaker_name: str, func: Callable, *args, **kwargs) -> Any:
        """Execute a function with the specified circuit breaker"""
        cb = self.get_circuit_breaker(circuit_breaker_name)
        if not cb:
            raise ValueError(f"Circuit breaker '{circuit_breaker_name}' not found")
        return cb.call(func, *args, **kwargs)
    
    def get_all_statuses(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all circuit breakers"""
        return {name: cb.get_status() for name, cb in self.circuit_breakers.items()}


# Global circuit breaker manager instance
circuit_breaker_manager = CircuitBreakerManager()


# Convenience decorators
def circuit_breaker(name: str, 
                   failure_threshold: int = 5, 
                   timeout: int = 60,
                   expected_exception: type = Exception):
    """Decorator to add circuit breaker protection to a function"""
    def decorator(func):
        # Register the circuit breaker
        cb = CircuitBreaker(name, failure_threshold, timeout, expected_exception)
        circuit_breaker_manager.register_circuit_breaker(cb)
        
        def wrapper(*args, **kwargs):
            return circuit_breaker_manager.call_with_circuit_breaker(name, func, *args, **kwargs)
        return wrapper
    return decorator