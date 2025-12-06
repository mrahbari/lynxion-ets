from typing import Optional, Dict, Any
import logging
from logging.handlers import RotatingFileHandler
import os
from datetime import datetime
import json


def create_logger(name: str):
    os.makedirs("logs", exist_ok=True)
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    handler = RotatingFileHandler("logs/system.log", maxBytes=1_000_000, backupCount=5)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    logger.addHandler(console)

    return logger


class EnhancedLogger:
    """Enhanced logger with structured logging and metrics collection"""
    
    def __init__(self, name: str = 'HedgeFund', log_file: Optional[str] = "logs/trading_system.log"):
        self.logger = create_logger(name)
        self.metrics = {}
    
    def info(self, message: str, **context):
        """Log an info message with optional context"""
        if context:
            context_str = " | ".join([f"{k}={v}" for k, v in context.items()])
            self.logger.info(f"{message} | {context_str}")
        else:
            self.logger.info(message)
    
    def error(self, message: str, **context):
        """Log an error message with optional context"""
        if context:
            context_str = " | ".join([f"{k}={v}" for k, v in context.items()])
            self.logger.error(f"{message} | {context_str}")
        else:
            self.logger.error(message)
    
    def warning(self, message: str, **context):
        """Log a warning message with optional context"""
        if context:
            context_str = " | ".join([f"{k}={v}" for k, v in context.items()])
            self.logger.warning(f"{message} | {context_str}")
        else:
            self.logger.warning(message)
    
    def debug(self, message: str, **context):
        """Log a debug message with optional context"""
        if context:
            context_str = " | ".join([f"{k}={v}" for k, v in context.items()])
            self.logger.debug(f"{message} | {context_str}")
        else:
            self.logger.debug(message)
    
    def log_component_event(self, component: str, event: str, status: str, **context):
        """Log a component-specific event"""
        self.info(f"[{component}] {event} - {status}", **context)
    
    def log_performance(self, operation: str, duration: float, **context):
        """Log performance metrics for an operation"""
        self.info(f"PERFORMANCE: {operation} took {duration:.4f}s", duration=duration, **context)
    
    def log_strategy_signal(self, strategy: str, symbol: str, signal_type: str, confidence: float, **context):
        """Log strategy signal generation"""
        self.info(f"STRATEGY_SIGNAL: {strategy} generated {signal_type} for {symbol} with {confidence:.2%} confidence",
                 strategy=strategy, symbol=symbol, signal_type=signal_type, confidence=confidence, **context)
    
    def log_execution(self, order_id: str, symbol: str, side: str, quantity: float, price: float, **context):
        """Log order execution"""
        self.info(f"EXECUTION: Order {order_id} executed for {symbol} {side} {quantity}@{price}",
                 order_id=order_id, symbol=symbol, side=side, quantity=quantity, price=price, **context)

    def log_error_with_context(self, error: Exception, context: dict, component: str = "Unknown"):
        """Log an error with context information"""
        self.error(f"ERROR in {component}: {str(error)}", error_type=type(error).__name__, **context)


# Global logger instance
logger = EnhancedLogger()
