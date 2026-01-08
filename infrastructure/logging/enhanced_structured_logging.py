"""
Enhanced structured logging system with correlation IDs, log sampling, and distributed tracing support.
"""
import logging
import uuid
import time
import functools
from typing import Dict, Any, Optional, Callable
from datetime import datetime
from contextvars import ContextVar
from dataclasses import dataclass, field
from enum import Enum
import json
import threading
import hashlib


# Context variable to store correlation ID across async contexts
correlation_id_ctx: ContextVar[str] = ContextVar('correlation_id', default=None)

# Context variable to store trace information
trace_info_ctx: ContextVar[Dict[str, Any]] = ContextVar('trace_info', default_factory=dict)


class LogLevel(Enum):
    """Enhanced log levels with additional categories"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
    BACKGROUND_ACTIVITY = "BACKGROUND_ACTIVITY"
    SIGNAL_PROGRESSION = "SIGNAL_PROGRESSION"
    WATCHER_ANALYSIS = "WATCHER_ANALYSIS"
    ENGINE_PROCESSING = "ENGINE_PROCESSING"
    FUSION_ANALYSIS = "FUSION_ANALYSIS"
    STRATEGY_EVALUATION = "STRATEGY_EVALUATION"
    EXECUTION_STATUS = "EXECUTION_STATUS"


@dataclass
class LogEntry:
    """Structured log entry with enhanced metadata"""
    timestamp: datetime
    level: LogLevel
    component: str
    message: str
    correlation_id: str
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    thread_id: str = field(default_factory=lambda: str(threading.current_thread().ident))
    process_id: str = field(default_factory=lambda: str(threading.get_ident()))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert log entry to dictionary for structured logging"""
        return {
            'timestamp': self.timestamp.isoformat(),
            'level': self.level.value,
            'component': self.component,
            'message': self.message,
            'correlation_id': self.correlation_id,
            'trace_id': self.trace_id,
            'span_id': self.span_id,
            'metadata': self.metadata,
            'thread_id': self.thread_id,
            'process_id': self.process_id
        }
    
    def to_json(self) -> str:
        """Convert log entry to JSON string"""
        return json.dumps(self.to_dict())


class LogSampler:
    """Log sampler to reduce high-volume events"""
    
    def __init__(self, sample_rate: float = 0.1, max_per_second: int = 100):
        """
        Initialize log sampler.
        
        Args:
            sample_rate: Fraction of logs to keep (0.0 to 1.0)
            max_per_second: Maximum logs per second to allow
        """
        self.sample_rate = sample_rate
        self.max_per_second = max_per_second
        self.counts: Dict[str, Dict[str, int]] = {}  # {component: {second: count}}
        self.lock = threading.Lock()
    
    def should_log(self, component: str, message: str) -> bool:
        """
        Determine if a log should be written based on sampling rules.
        
        Args:
            component: Component name
            message: Log message
            
        Returns:
            True if log should be written, False otherwise
        """
        current_time = int(time.time())
        message_hash = hashlib.md5(message.encode()).hexdigest()
        
        with self.lock:
            # Initialize component counts if needed
            if component not in self.counts:
                self.counts[component] = {}
            
            # Clean up old counts (older than 10 seconds)
            current_counts = {k: v for k, v in self.counts[component].items() 
                             if k > current_time - 10}
            self.counts[component] = current_counts
            
            # Check rate limiting
            current_second_count = self.counts[component].get(current_time, 0)
            if current_second_count >= self.max_per_second:
                return False  # Rate limit exceeded
            
            # Check sampling rate
            if self.sample_rate < 1.0:
                # Use message hash to determine if this message should be sampled
                hash_val = int(message_hash[:8], 16)  # Use first 8 hex chars
                should_sample = (hash_val % 1000) < (self.sample_rate * 1000)
                if should_sample:
                    # Increment count for this second
                    self.counts[component][current_time] = current_second_count + 1
                    return True
                else:
                    return False
            else:
                # No sampling, just increment count
                self.counts[component][current_time] = current_second_count + 1
                return True


class DistributedTracer:
    """Distributed tracing support for cross-component tracking"""
    
    def __init__(self):
        self.active_spans: Dict[str, Dict[str, Any]] = {}
        self.lock = threading.Lock()
    
    def start_span(self, operation_name: str, parent_trace_id: Optional[str] = None) -> str:
        """
        Start a new tracing span.
        
        Args:
            operation_name: Name of the operation being traced
            parent_trace_id: Parent trace ID (if any)
            
        Returns:
            Span ID for the new span
        """
        span_id = str(uuid.uuid4())
        trace_id = parent_trace_id or str(uuid.uuid4())
        
        with self.lock:
            self.active_spans[span_id] = {
                'trace_id': trace_id,
                'span_id': span_id,
                'operation_name': operation_name,
                'start_time': time.time(),
                'parent_trace_id': parent_trace_id
            }
        
        return span_id
    
    def end_span(self, span_id: str) -> Optional[Dict[str, Any]]:
        """
        End a tracing span and return its information.
        
        Args:
            span_id: ID of the span to end
            
        Returns:
            Span information or None if not found
        """
        with self.lock:
            span_info = self.active_spans.pop(span_id, None)
            if span_info:
                span_info['duration'] = time.time() - span_info['start_time']
                span_info['end_time'] = time.time()
            return span_info
    
    def get_trace_info(self, span_id: str) -> Optional[Dict[str, Any]]:
        """Get current trace information for a span."""
        with self.lock:
            return self.active_spans.get(span_id)


class EnhancedLogger(logging.Logger):
    """Enhanced logger with correlation IDs, sampling, and distributed tracing"""
    
    def __init__(self, name: str, level: int = logging.INFO, sample_rate: float = 0.1, max_logs_per_second: int = 100):
        super().__init__(name, level)
        
        # Set up the handler with structured formatting
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')
        handler.setFormatter(formatter)
        self.addHandler(handler)
        
        # Initialize enhanced features
        self.sampler = LogSampler(sample_rate=sample_rate, max_per_second=max_logs_per_second)
        self.tracer = DistributedTracer()
        self.component_name = name
        
        # Set up structured logging handler
        self._setup_structured_logging()
    
    def _setup_structured_logging(self):
        """Set up structured logging with JSON output"""
        # Remove default handlers to replace with structured handler
        self.handlers.clear()
        
        # Create structured handler
        structured_handler = logging.StreamHandler()
        structured_formatter = StructuredLogFormatter()
        structured_handler.setFormatter(structured_formatter)
        self.addHandler(structured_handler)
    
    def _create_log_entry(self, level: LogLevel, message: str, metadata: Dict[str, Any] = None) -> LogEntry:
        """Create a structured log entry."""
        correlation_id = correlation_id_ctx.get() or str(uuid.uuid4())
        trace_info = trace_info_ctx.get()
        
        return LogEntry(
            timestamp=datetime.now(),
            level=level,
            component=self.component_name,
            message=message,
            correlation_id=correlation_id,
            trace_id=trace_info.get('trace_id') if trace_info else None,
            span_id=trace_info.get('span_id') if trace_info else None,
            metadata=metadata or {}
        )
    
    def _log_if_allowed(self, level: LogLevel, message: str, metadata: Dict[str, Any] = None):
        """Log entry only if sampling allows it."""
        if self.sampler.should_log(self.component_name, message):
            log_entry = self._create_log_entry(level, message, metadata)
            # Convert to standard logging format for compatibility
            structured_msg = log_entry.to_json()
            super().log(getattr(logging, level.value), structured_msg)
    
    def info_with_correlation(self, message: str, correlation_id: str = None, metadata: Dict[str, Any] = None):
        """Log info message with correlation ID."""
        if correlation_id:
            token = correlation_id_ctx.set(correlation_id)
        else:
            token = None
        
        try:
            self._log_if_allowed(LogLevel.INFO, message, metadata)
        finally:
            if token:
                correlation_id_ctx.reset(token)
    
    def log_background_activity(self, activity_type: str, details: str, **kwargs):
        """Log background activity with correlation ID."""
        metadata = {
            'activity_type': activity_type,
            'details': details,
            **kwargs
        }
        self._log_if_allowed(LogLevel.BACKGROUND_ACTIVITY, f"Background Activity: {activity_type} - {details}", metadata)
    
    def log_signal_progression(self, symbol: str, stage: str, status: str, details: str = "", confidence: float = None):
        """Log signal progression through the system."""
        metadata = {
            'symbol': symbol,
            'stage': stage,
            'status': status,
            'details': details,
            'confidence': confidence
        }
        message = f"Signal Progression: {symbol} - {stage} - {status}"
        self._log_if_allowed(LogLevel.SIGNAL_PROGRESSION, message, metadata)
    
    def log_watcher_analysis(self, watcher: str, symbol: str, result: str, confidence: float = None, signal_type: str = None):
        """Log watcher analysis results."""
        metadata = {
            'watcher': watcher,
            'symbol': symbol,
            'result': result,
            'confidence': confidence,
            'signal_type': signal_type
        }
        message = f"Watcher Analysis: {watcher} - {symbol} - {result}"
        self._log_if_allowed(LogLevel.WATCHER_ANALYSIS, message, metadata)
    
    def log_engine_processing(self, engine: str, input_type: str, output_type: str, processing_time: float = None):
        """Log engine processing activities."""
        metadata = {
            'engine': engine,
            'input_type': input_type,
            'output_type': output_type,
            'processing_time': processing_time
        }
        message = f"Engine Processing: {engine} - {input_type} -> {output_type}"
        self._log_if_allowed(LogLevel.ENGINE_PROCESSING, message, metadata)
    
    def log_fusion_analysis(self, fusion_method: str, input_count: int, output_quality: str, confidence: float = None):
        """Log fusion analysis results."""
        metadata = {
            'fusion_method': fusion_method,
            'input_count': input_count,
            'output_quality': output_quality,
            'confidence': confidence
        }
        message = f"Fusion Analysis: {fusion_method} - {input_count} inputs -> {output_quality}"
        self._log_if_allowed(LogLevel.FUSION_ANALYSIS, message, metadata)
    
    def log_strategy_evaluation(self, strategy: str, signal_type: str, decision: str, confidence: float = None):
        """Log strategy evaluation results."""
        metadata = {
            'strategy': strategy,
            'signal_type': signal_type,
            'decision': decision,
            'confidence': confidence
        }
        message = f"Strategy Evaluation: {strategy} - {signal_type} -> {decision}"
        self._log_if_allowed(LogLevel.STRATEGY_EVALUATION, message, metadata)
    
    def log_execution_status(self, execution_id: str, status: str, details: str = "", execution_time: float = None):
        """Log execution status updates."""
        metadata = {
            'execution_id': execution_id,
            'status': status,
            'details': details,
            'execution_time': execution_time
        }
        message = f"Execution Status: {execution_id} - {status}"
        self._log_if_allowed(LogLevel.EXECUTION_STATUS, message, metadata)
    
    def log_decision_reason(self, component: str, symbol: str, decision: str, reason: str, confidence: float = None):
        """Log decision-making process with reasons."""
        metadata = {
            'component': component,
            'symbol': symbol,
            'decision': decision,
            'reason': reason,
            'confidence': confidence
        }
        message = f"Decision Reason: {component} - {symbol} - {decision} - {reason}"
        self._log_if_allowed(LogLevel.INFO, message, metadata)
    
    def start_trace(self, operation_name: str, parent_trace_id: Optional[str] = None) -> str:
        """Start a new distributed trace span."""
        span_id = self.tracer.start_span(operation_name, parent_trace_id)
        
        # Store trace info in context
        trace_info = {
            'trace_id': self.tracer.active_spans[span_id]['trace_id'],
            'span_id': span_id,
            'operation_name': operation_name
        }
        token = trace_info_ctx.set(trace_info)
        
        # Log the trace start
        self.info_with_correlation(
            f"TRACE START: {operation_name}",
            correlation_id=trace_info['trace_id'],
            metadata={'span_id': span_id, 'operation': operation_name}
        )
        
        return span_id
    
    def end_trace(self, span_id: str):
        """End a distributed trace span."""
        span_info = self.tracer.end_span(span_id)
        if span_info:
            self.info_with_correlation(
                f"TRACE END: {span_info['operation_name']} (Duration: {span_info['duration']:.3f}s)",
                correlation_id=span_info['trace_id'],
                metadata=span_info
            )
        
        # Clear trace info from context
        trace_info_ctx.set({})


class StructuredLogFormatter(logging.Formatter):
    """Custom formatter for structured logging"""
    
    def format(self, record):
        # Try to parse as JSON first (for structured logs)
        try:
            # If the message is already JSON (structured log), return as-is
            json.loads(record.getMessage())
            return record.getMessage()
        except json.JSONDecodeError:
            # If not JSON, create a structured log entry
            log_entry = {
                'timestamp': datetime.fromtimestamp(record.created).isoformat(),
                'level': record.levelname,
                'component': record.name,
                'message': record.getMessage(),
                'correlation_id': getattr(record, 'correlation_id', str(uuid.uuid4())),
                'thread_id': record.thread,
                'process_id': record.process
            }
            return json.dumps(log_entry)


def with_correlation_id(func: Callable) -> Callable:
    """Decorator to automatically set correlation ID for function execution."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        correlation_id = str(uuid.uuid4())
        token = correlation_id_ctx.set(correlation_id)
        try:
            return func(*args, **kwargs)
        finally:
            correlation_id_ctx.reset(token)
    return wrapper


def with_tracing(operation_name: str):
    """Decorator to add distributed tracing to function execution."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            # Get logger from self if available, otherwise create one
            logger = getattr(self, 'logger', EnhancedLogger(func.__name__))
            
            # Start trace span
            span_id = logger.start_trace(operation_name)
            
            try:
                result = func(self, *args, **kwargs)
                logger.end_trace(span_id)
                return result
            except Exception as e:
                logger.error(f"TRACE ERROR: {operation_name} - {str(e)}")
                logger.end_trace(span_id)
                raise
        return wrapper
    return decorator


# Global logger factory
def create_enhanced_logger(name: str, sample_rate: float = 0.1, max_logs_per_second: int = 100) -> EnhancedLogger:
    """Factory function to create enhanced logger instances."""
    return EnhancedLogger(name, sample_rate=sample_rate, max_logs_per_second=max_logs_per_second)


# Example usage
if __name__ == "__main__":
    # Create an enhanced logger
    logger = create_enhanced_logger("TestComponent", sample_rate=1.0)  # Disable sampling for testing
    
    # Test correlation ID functionality
    logger.info_with_correlation("Test message with correlation ID", correlation_id="test-correlation-123")
    
    # Test structured logging methods
    logger.log_background_activity("Data Fetch", "Fetched market data for BTCUSDT", symbol="BTCUSDT", count=1000)
    logger.log_signal_progression("BTCUSDT", "Watcher", "Processed", "Signal generated", 0.85)
    logger.log_watcher_analysis("MarketPulse", "BTCUSDT", "Strong Buy Signal", 0.92, "BUY")
    
    # Test distributed tracing
    span_id = logger.start_trace("ProcessMarketData")
    time.sleep(0.1)  # Simulate work
    logger.end_trace(span_id)
    
    print("Enhanced logging system test completed successfully!")