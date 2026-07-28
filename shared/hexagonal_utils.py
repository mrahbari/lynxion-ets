"""
Updated shared utilities for hexagonal architecture.

This module contains shared utilities specifically designed to support
the hexagonal architecture pattern, including event handling, logging,
and other cross-cutting concerns that are common across all layers.
"""
from typing import Callable, Dict, List, Any, Optional, Protocol
import logging
from logging.handlers import RotatingFileHandler
import os
import threading
import queue
import json
from datetime import datetime
from enum import Enum


class DomainEventHandler(Protocol):
    """Protocol for domain event handlers in hexagonal architecture"""
    
    def handle(self, event_data: Dict[str, Any]) -> bool:
        """Handle a domain event and return success status"""
        ...


class LoggerInterface(Protocol):
    """Protocol defining the interface for logging in hexagonal architecture"""
    
    def info(self, message: str, extra: Optional[Dict] = None):
        """Log an info message"""
        ...
    
    def warning(self, message: str, extra: Optional[Dict] = None):
        """Log a warning message"""
        ...
    
    def error(self, message: str, extra: Optional[Dict] = None):
        """Log an error message"""
        ...
    
    def debug(self, message: str, extra: Optional[Dict] = None):
        """Log a debug message"""
        ...


class EventInterface(Protocol):
    """Protocol defining the interface for events in hexagonal architecture"""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary"""
        ...


def create_hexagonal_logger(name: str, log_file: str = "hexagonal_system.log") -> logging.Logger:
    """Create a logger instance for hexagonal architecture"""
    os.makedirs("logs", exist_ok=True)
    
    from shared.logger import get_configured_log_level
    log_level_str = get_configured_log_level()
    log_level = getattr(logging, log_level_str, logging.INFO)
    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    
    # Prevent duplicate handlers
    if logger.handlers:
        for h in logger.handlers:
            h.setLevel(log_level)
        return logger
    
    # File handler with rotation
    log_path = os.path.join("logs", log_file)
    file_handler = RotatingFileHandler(log_path, maxBytes=10_000_000, backupCount=5)
    file_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_formatter = logging.Formatter("%(levelname)s - %(message)s")
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    return logger


# Global logger instance for the hexagonal architecture system
hexagonal_logger = create_hexagonal_logger("HexagonalHedgeFund")


class HexagonalEventBus:
    """Event bus specifically designed for hexagonal architecture"""
    
    def __init__(self, logger_instance: Optional[logging.Logger] = None):
        self.subscribers: Dict[str, List[Callable]] = {}
        self.event_queue = queue.Queue()
        self.running = True
        self.logger = logger_instance or hexagonal_logger
        self._internal_thread: Optional[threading.Thread] = None
    
    def subscribe(self, event_type: str, callback: Callable):
        """Subscribe to an event type"""
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(callback)
        self.logger.info(f"Subscribed to event: {event_type}")
    
    def unsubscribe(self, event_type: str, callback: Callable):
        """Unsubscribe from an event type"""
        if event_type in self.subscribers:
            try:
                self.subscribers[event_type].remove(callback)
                self.logger.info(f"Unsubscribed from event: {event_type}")
            except ValueError:
                self.logger.warning(f"Callback not found in subscribers for event: {event_type}")
    
    def publish(self, event_type: str, data: Any):
        """Publish an event to the bus"""
        event_payload = {
            'event_type': event_type,
            'data': data,
            'timestamp': datetime.now().isoformat()
        }
        self.event_queue.put(event_payload)
        self.logger.debug(f"Published event: {event_type}")
    
    def _process_events(self):
        """Internal method to process events in a separate thread"""
        while self.running:
            try:
                event_payload = self.event_queue.get(timeout=0.1)
                event_type = event_payload['event_type']
                
                # Notify all subscribers of this event type
                if event_type in self.subscribers:
                    for callback in self.subscribers[event_type]:
                        try:
                            callback(event_payload['data'])
                        except Exception as e:
                            self.logger.error(f"Error in event callback for {event_type}: {e}", 
                                            extra={'event_type': event_type, 'error': str(e)})
                
                self.event_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.error(f"Error processing event: {e}")
    
    def start(self):
        """Start the event processing thread"""
        if not self._internal_thread or not self._internal_thread.is_alive():
            self._internal_thread = threading.Thread(target=self._process_events, daemon=True)
            self._internal_thread.start()
            self.logger.info("Event bus started")
    
    def stop(self):
        """Stop the event bus"""
        self.running = False
        if self._internal_thread and self._internal_thread.is_alive():
            self._internal_thread.join(timeout=2.0)
        self.logger.info("Event bus stopped")


class HexagonalEventBusAdapter:
    """Adapter to provide event bus functionality in a hexagonal architecture"""
    
    def __init__(self):
        self.event_bus = HexagonalEventBus()
        self.event_bus.start()
    
    def emit_event(self, event_type: str, data: Any):
        """Emit an event through the event bus"""
        self.event_bus.publish(event_type, data)
    
    def register_handler(self, event_type: str, handler: Callable):
        """Register an event handler"""
        self.event_bus.subscribe(event_type, handler)


# Global event bus adapter instance
hexagonal_event_bus = HexagonalEventBusAdapter()


def safe_execute(func: Callable, *args, **kwargs) -> Any:
    """Safely execute a function and handle any exceptions"""
    try:
        return func(*args, **kwargs)
    except Exception as e:
        hexagonal_logger.error(f"Error executing function {func.__name__}: {e}")
        return None


def validate_domain_invariant(condition: bool, message: str):
    """Validate a domain invariant and raise an exception if violated"""
    if not condition:
        error_msg = f"Domain invariant violation: {message}"
        hexagonal_logger.error(error_msg)
        raise ValueError(error_msg)


def measure_execution_time(func: Callable) -> Callable:
    """Decorator to measure execution time of functions"""
    def wrapper(*args, **kwargs):
        start_time = datetime.now()
        try:
            result = func(*args, **kwargs)
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            hexagonal_logger.debug(
                f"Function {func.__name__} executed in {duration:.4f} seconds",
                extra={'execution_time': duration, 'function': func.__name__}
            )
            return result
        except Exception as e:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            hexagonal_logger.error(
                f"Function {func.__name__} failed after {duration:.4f} seconds: {e}",
                extra={'execution_time': duration, 'function': func.__name__, 'error': str(e)}
            )
            raise
    return wrapper


class AsyncResult:
    """Utility class for handling asynchronous results in hexagonal architecture"""
    
    def __init__(self):
        self._result = None
        self._completed = False
        self._error = None
        self._condition = threading.Condition()
    
    def set_result(self, result: Any):
        """Set the result and mark as completed"""
        with self._condition:
            self._result = result
            self._completed = True
            self._condition.notify_all()
    
    def set_error(self, error: Exception):
        """Set an error and mark as completed"""
        with self._condition:
            self._error = error
            self._completed = True
            self._condition.notify_all()
    
    def get(self, timeout: Optional[float] = None) -> Any:
        """Get the result, blocking until completion or timeout"""
        with self._condition:
            while not self._completed:
                if not self._condition.wait(timeout):
                    raise TimeoutError(f"Operation timed out after {timeout} seconds")
            
            if self._error:
                raise self._error
            return self._result


# Initialize the event bus
hexagonal_event_bus.event_bus.start()