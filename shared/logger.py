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
from enum import Enum
import json
import threading
import hashlib
from logging.handlers import RotatingFileHandler
import os
import sys
from typing import Optional as TypingOptional, Dict as TypingDict, Any as TypingAny


# Context variable to store correlation ID across async contexts
correlation_id_ctx: ContextVar[str] = ContextVar('correlation_id', default=None)


def create_logger(name: str):
    """Create a basic logger with rotating file handler and colored console output."""
    from shared.log_paths import logs_dir, log_path
    logs_dir()  # ensure <project-root>/logs exists (anchored, not cwd-relative)
    logger = logging.getLogger(name)

    # Check if logger already has handlers to prevent duplicate handlers
    if logger.handlers:
        return logger

    log_level_str = os.environ.get("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_str, logging.INFO)
    logger.setLevel(log_level)

    # Create the rotating file handler with a safer approach to prevent rotation errors
    # Ensure the main log file exists first to avoid issues during rotation
    log_file_path = log_path("system.log")  # project-root-anchored

    # Ensure the directory exists right before we try to touch the file
    # this provides extra safety against race conditions or transient FS issues
    try:
        log_dir = os.path.dirname(log_file_path)
        if not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)

        # Touch the main log file to ensure it exists
        if not os.path.exists(log_file_path):
            with open(log_file_path, 'a'):
                pass
    except (OSError, IOError) as e:
        # If we can't create the log file, we'll continue anyway 
        # (RotatingFileHandler might still succeed or we'll at least have console logs)
        print(f"⚠️ Warning: Could not initialize log file at {log_file_path}: {e}", file=sys.stderr)

    # Create the rotating file handler
    # The backupCount specifies how many backup files to keep, but the rotation
    # mechanism can sometimes fail if intermediate files are missing
    handler = RotatingFileHandler(log_file_path, maxBytes=1_000_000, backupCount=5)

    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    console = logging.StreamHandler()
    # Use enhanced colored formatter for console
    if sys.stdout.isatty():
        console.setFormatter(ColoredFormatter())
    else:
        console.setFormatter(formatter)
    logger.addHandler(console)

    return logger


class ColoredFormatter(logging.Formatter):
    """Custom colored formatter for console output"""

    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'        # Reset to default
    }

    # Emojis for different log types
    EMOJIS = {
        'INFO': 'ℹ️',
        'WARNING': '⚠️',
        'ERROR': '❌',
        'DEBUG': '🐞',
        'CRITICAL': '🚨'
    }

    def format(self, record):
        # Add color to level name
        level_color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        level_emoji = self.EMOJIS.get(record.levelname, '📄')
        reset_color = self.COLORS['RESET']

        # Format the basic message
        log_message = f"{self.formatTime(record)} {level_color}{level_emoji}{record.levelname}{reset_color} {record.name} - {record.getMessage()}"

        return log_message


class EnhancedLogger:
    """Enhanced logger with structured logging, correlation IDs, and distributed tracing support."""

    # Class-level cache to reuse logger instances
    _logger_cache = {}

    def __init__(self, name: str = 'HedgeFund', log_file: TypingOptional[str] = "logs/trading_system.log",
                 comprehensive_mode: bool = False):
        # Use cached logger if it exists, otherwise create new one
        if name in EnhancedLogger._logger_cache:
            self.logger = EnhancedLogger._logger_cache[name]
        else:
            self.logger = create_logger(name)
            EnhancedLogger._logger_cache[name] = self.logger

        self.metrics = {}
        self.name = name
        self.flow_tracker = {}  # Track flow IDs and their status
        self.comprehensive_mode = comprehensive_mode  # Enable comprehensive logging

        # Initialize trace information
        self.active_spans = {}
        self.current_trace_id = None
        self.current_span_id = None

    def _add_correlation_and_trace_info(self, message: str, **context) -> str:
        """Add correlation ID and trace information to the log message"""
        correlation_id = correlation_id_ctx.get()
        if correlation_id:
            message = f"[CORR_ID:{correlation_id}] {message}"
        
        # Add trace information if available
        if self.current_trace_id:
            message = f"[TRACE:{self.current_trace_id}] {message}"
        if self.current_span_id:
            message = f"[SPAN:{self.current_span_id}] {message}"
        
        return message

    def info(self, message: str, **context):
        """Log an info message with optional context"""
        message = self._add_correlation_and_trace_info(message, **context)
        
        if context:
            context_str = " | ".join([f"{k}={v}" for k, v in context.items()])
            self.logger.info(f"{message} | {context_str}")
        else:
            self.logger.info(message)

    def info_with_correlation(self, message: str, correlation_id: str = None, **context):
        """Log an info message with a specific correlation ID"""
        if correlation_id:
            # Temporarily set the correlation ID for this log
            token = correlation_id_ctx.set(correlation_id)
            try:
                self.info(message, **context)
            finally:
                correlation_id_ctx.reset(token)
        else:
            self.info(message, **context)

    def start_trace(self, operation_name: str, parent_trace_id: str = None) -> str:
        """Start a new distributed trace span"""
        trace_id = parent_trace_id or str(uuid.uuid4())
        span_id = str(uuid.uuid4())

        # Store span information
        self.active_spans[span_id] = {
            'trace_id': trace_id,
            'span_id': span_id,
            'operation_name': operation_name,
            'start_time': time.time(),
            'parent_trace_id': parent_trace_id
        }

        # Update current trace/span IDs
        self.current_trace_id = trace_id
        self.current_span_id = span_id

        # Log the trace start
        self.info(f"TRACE START: {operation_name}",
                  trace_id=trace_id, span_id=span_id, operation=operation_name)

        return span_id

    def end_trace(self, span_id: str):
        """End a distributed trace span"""
        if span_id in self.active_spans:
            span_info = self.active_spans.pop(span_id)
            duration = time.time() - span_info['start_time']

            # Log the trace end
            self.info(f"TRACE END: {span_info['operation_name']} (Duration: {duration:.3f}s)",
                      trace_id=span_info['trace_id'],
                      span_id=span_id,
                      duration=duration)

            # Update current trace/span IDs if this was the active span
            if self.current_span_id == span_id:
                self.current_span_id = None
                # If no more spans, clear trace ID
                if not self.active_spans:
                    self.current_trace_id = None

    def log_background_activity(self, activity_type: str, details: str, **context):
        """Log background activity with correlation ID and trace info"""
        message = f"BACKGROUND ACTIVITY: {activity_type} | Details: {details}"
        self.info(message, activity_type=activity_type, details=details, **context)

    def log_signal_progression(self, symbol: str, stage: str, status: str, details: str = "",
                             confidence: float = None, **context):
        """Log signal progression through the system with correlation ID"""
        message = f"SIGNAL PROGRESSION: {symbol} | Stage: {stage} | Status: {status} | Details: {details}"
        if confidence is not None:
            message += f" | Confidence: {confidence:.2%}"

        self.info(message,
                  symbol=symbol,
                  stage=stage,
                  status=status,
                  details=details,
                  confidence=confidence,
                  **context)


    def log_engine_processing(self, engine: str, input_type: str, output_type: str,
                            processing_time: float = None, **context):
        """Log engine processing with correlation ID"""
        message = f"ENGINE PROCESSING: {engine} | Input: {input_type} | Output: {output_type}"
        if processing_time is not None:
            message += f" | Processing Time: {processing_time:.3f}s"

        self.info(message,
                  engine=engine,
                  input_type=input_type,
                  output_type=output_type,
                  processing_time=processing_time,
                  **context)

    def log_fusion_analysis(self, fusion_method: str, input_count: int, output_quality: str,
                          confidence: float = None, **context):
        """Log fusion analysis results with correlation ID"""
        message = f"FUSION ANALYSIS: {fusion_method} | Inputs: {input_count} | Quality: {output_quality}"
        if confidence is not None:
            message += f" | Confidence: {confidence:.2%}"

        self.info(message,
                  fusion_method=fusion_method,
                  input_count=input_count,
                  output_quality=output_quality,
                  confidence=confidence,
                  **context)

    def log_strategy_evaluation(self, strategy: str, signal_type: str, decision: str,
                              confidence: float = None, **context):
        """Log strategy evaluation with correlation ID"""
        message = f"STRATEGY EVALUATION: {strategy} | Signal: {signal_type} | Decision: {decision}"
        if confidence is not None:
            message += f" | Confidence: {confidence:.2%}"

        self.info(message,
                  strategy=strategy,
                  signal_type=signal_type,
                  decision=decision,
                  confidence=confidence,
                  **context)

    def log_execution_status(self, execution_id: str, status: str, details: str = "",
                           execution_time: float = None, **context):
        """Log execution status with correlation ID"""
        message = f"EXECUTION STATUS: {execution_id} | Status: {status} | Details: {details}"
        if execution_time is not None:
            message += f" | Execution Time: {execution_time:.3f}s"

        self.info(message,
                  execution_id=execution_id,
                  status=status,
                  details=details,
                  execution_time=execution_time,
                  **context)

    def log_decision_reason(self, component: str, symbol: str, decision: str, reason: str,
                          confidence: float = None, **context):
        """Log decision-making process with reasons and correlation ID"""
        message = f"DECISION REASON: {component} | Symbol: {symbol} | Decision: {decision} | Reason: {reason}"
        if confidence is not None:
            message += f" | Confidence: {confidence:.2%}"

        self.info(message,
                  component=component,
                  symbol=symbol,
                  decision=decision,
                  reason=reason,
                  confidence=confidence,
                  **context)

    def with_correlation_id(self, correlation_id: str = None):
        """Context manager to set correlation ID for a block of code"""
        class CorrelationContext:
            def __enter__(ctx):
                ctx.token = correlation_id_ctx.set(correlation_id or str(uuid.uuid4()))
                return self

            def __exit__(ctx, exc_type, exc_val, exc_tb):
                correlation_id_ctx.reset(ctx.token)

        return CorrelationContext()

    def with_tracing(self, operation_name: str):
        """Context manager to add distributed tracing to a block of code"""
        class TraceContext:
            def __enter__(ctx):
                ctx.span_id = self.start_trace(operation_name)
                return self

            def __exit__(ctx, exc_type, exc_val, exc_tb):
                self.end_trace(ctx.span_id)

        return TraceContext()

    def error(self, message: str, **context):
        """Log an error message with optional context"""
        message = self._add_correlation_and_trace_info(message, **context)
        
        if context:
            context_str = " | ".join([f"{k}={v}" for k, v in context.items()])
            self.logger.error(f"{message} | {context_str}")
        else:
            self.logger.error(message)

    def warning(self, message: str, **context):
        """Log a warning message with optional context"""
        message = self._add_correlation_and_trace_info(message, **context)

        if context:
            context_str = " | ".join([f"{k}={v}" for k, v in context.items()])
            self.logger.warning(f"{message} | {context_str}")
        else:
            self.logger.warning(message)

    def critical(self, message: str, **context):
        """Log a critical message with optional context (was missing; reconcile-halt logging used it)."""
        message = self._add_correlation_and_trace_info(message, **context)

        if context:
            context_str = " | ".join([f"{k}={v}" for k, v in context.items()])
            self.logger.critical(f"{message} | {context_str}")
        else:
            self.logger.critical(message)

    def debug(self, message: str, **context):
        """Log a debug message with optional context"""
        message = self._add_correlation_and_trace_info(message, **context)
        
        if context:
            context_str = " | ".join([f"{k}={v}" for k, v in context.items()])
            self.logger.debug(f"{message} | {context_str}")
        else:
            self.logger.debug(message)

    def log_with_sampling(self, level: str, component: str, message: str, sample_rate: float = 0.1, **context):
        """
        Log a message with sampling applied to control volume.

        Args:
            level: Log level ('info', 'warning', 'error', etc.)
            component: Component name for sampling
            message: Message to log
            sample_rate: Fraction of logs to keep (0.0 to 1.0)
            **context: Additional context
        """
        # Create a consistent hash for this message type
        message_hash = hashlib.md5(f"{component}:{message}".encode()).hexdigest()
        hash_value = int(message_hash[:8], 16)

        # Only log if within sample rate
        if (hash_value % 1000) < (sample_rate * 1000):
            getattr(self, level)(message, **context)
        else:
            # Track that this was sampled
            self._track_sampled_event(component, message)

    def _track_sampled_event(self, component: str, message: str):
        """Track sampled events for metrics purposes"""
        if 'sampled_events' not in self.metrics:
            self.metrics['sampled_events'] = {}

        key = f"{component}:{message[:50]}"  # Use first 50 chars to avoid long keys
        self.metrics['sampled_events'][key] = self.metrics['sampled_events'].get(key, 0) + 1

    def get_metrics(self) -> TypingDict[str, TypingAny]:
        """Get collected metrics"""
        return self.metrics.copy()

    # The rest of the methods from the original EnhancedLogger would go here...
    # For brevity, I'll add the key trading-related methods

    def log_component_event(self, component: str, event: str, status: str, **context):
        """Log a component-specific event"""
        self.info(f"[{component}] {event} - {status}", **context)

    def log_performance(self, operation: str, duration: float, **context):
        """Log performance metrics for an operation"""
        self.info(f"⏱️ PERFORMANCE: {operation} completed in {duration:.4f}s", 
                 operation=operation, duration=duration, **context)

    def log_strategy_signal(self, strategy: str, symbol: str, signal_type: str, confidence: float, **context):
        """Log strategy signal generation with visual indicators"""
        # Add emoji based on signal type
        signal_emoji = {"BUY": "📈", "SELL": "📉", "HOLD": "⏸️", "NEUTRAL": "⚖️"}.get(signal_type, "❓")
        self.info(f"🎯 {signal_emoji} {strategy.upper()} SIGNAL: {signal_type} on {symbol} | Confidence: {confidence:.2%}",
                 strategy=strategy, symbol=symbol, signal_type=signal_type, confidence=confidence, **context)

    def log_execution(self, order_id: str, symbol: str, side: str, quantity: float, price: float, **context):
        """Log order execution with visual indicators"""
        side_emoji = "🟢BUY" if side.upper() == "BUY" else "🔴SELL"
        self.info(f"⚡ {side_emoji} EXECUTION SUCCESS: #{order_id} | {quantity:,.4f} {symbol} @ ${price:,.4f} | Total: ${quantity * price:,.2f}",
                 order_id=order_id, symbol=symbol, side=side, quantity=quantity, price=price, total_value=quantity * price, **context)

    def log_error_with_context(self, error: Exception, context: dict, component: str = "Unknown"):
        """Log an error with context information"""
        self.error(f"💥 ERROR in {component}: {str(error)}", error_type=type(error).__name__, **context)

    def log_watcher_analysis(self, watcher: str, symbol: str, result: str, confidence: TypingOptional[float] = None, **context):
        """Log watcher analysis results with visual indicators"""
        watcher_emoji = {
            "MarketPulse": "🌊",
            "Volatility": "📊",
            "TrendMTF": "📈",
            "AnomalyML": "🤖",
            "OrderFlow": "🌊",
            "CMCWatcher": "🪙",
            "CMCScreener": "🔍"
        }.get(watcher, "👁️")

        # Add specific emojis based on result
        result_emoji = "✅" if "signal" in result.lower() or "generated" in result.lower() else \
                      "⏳" if "filtered" in result.lower() or "skipped" in result.lower() else \
                      "🔄"

        if confidence is not None:
            # Format the message with better watcher emphasis
            self.info(f"[{watcher_emoji}{watcher}] {result_emoji} {result} | {symbol} | Conf: {confidence:.2%}",
                     watcher=watcher, symbol=symbol, result=result, confidence=confidence, **{k: v for k, v in context.items() if k not in ['watcher', 'symbol', 'result', 'confidence']})
        else:
            # Format the message with better watcher emphasis
            self.info(f"[{watcher_emoji}{watcher}] {result_emoji} {result} | {symbol}",
                     watcher=watcher, symbol=symbol, result=result, **{k: v for k, v in context.items() if k not in ['watcher', 'symbol', 'result', 'confidence']})

    def log_opportunity_detected(self, symbol: str, signal_type: str, confidence: float, strategy: str, **context):
        """Log detected market opportunities"""
        signal_emoji = {"BUY": "📈", "SELL": "📉", "HOLD": "⏸️", "NEUTRAL": "⚖️"}.get(signal_type, "❓")
        self.info(f"💎 OPPORTUNITY DETECTED: {signal_emoji} {signal_type} on {symbol} | Strategy: {strategy} | Confidence: {confidence:.2%}",
                 symbol=symbol, signal_type=signal_type, confidence=confidence, strategy=strategy, **context)

    def log_portfolio_metrics(self, equity: float, pnl: float, drawdown: float, sharpe: float, **context):
        """Log portfolio metrics with visual indicators"""
        drawdown_abs = abs(drawdown)
        if drawdown_abs > 0.15:  # Severe drawdown
            dd_emoji = "🚨"
        elif drawdown_abs > 0.05:  # Moderate drawdown
            dd_emoji = "⚠️"
        else:  # Small or positive
            dd_emoji = "🟢"

        self.info(f"📈 PORTFOLIO: Equity=${equity:,.2f} | PnL=${pnl:,.2f} | {dd_emoji} DD:{drawdown:.2%} | Sharpe:{sharpe:.2f}",
                 equity=equity, pnl=pnl, drawdown=drawdown, sharpe=sharpe, **context)

    def log_risk_alert(self, alert_type: str, message: str, **context):
        """Log risk management alerts"""
        alert_emoji = {
            "critical": "🚨",
            "warning": "⚠️",
            "info": "ℹ️"
        }.get(alert_type.lower(), "🔔")

        self.info(f"{alert_emoji} RISK ALERT ({alert_type.upper()}): {message}", alert_type=alert_type, **context)

    def log_auto_detection_status(self, symbols_monitored: int, active_strategies: int, opportunities_found: int, **context):
        """Log auto-detection system status"""
        self.info(f"🤖 AUTO-DETECTION STATUS: Monitoring {symbols_monitored} symbols | Active strategies: {active_strategies} | Opportunities: {opportunities_found}",
                 symbols_monitored=symbols_monitored, active_strategies=active_strategies, opportunities_found=opportunities_found, **context)

    def set_comprehensive_mode(self, enabled: bool):
        """Enable or disable comprehensive logging mode"""
        self.comprehensive_mode = enabled
        status = "ENABLED" if enabled else "DISABLED"
        self.info(f"📋 COMPREHENSIVE LOGGING: {status}")


# Global logger instance
logger = EnhancedLogger()