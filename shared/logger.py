from typing import Optional, Dict, Any
import logging
from logging.handlers import RotatingFileHandler
import os
from datetime import datetime
import json
import sys


def create_logger(name: str):
    os.makedirs("logs", exist_ok=True)
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    handler = RotatingFileHandler("logs/system.log", maxBytes=1_000_000, backupCount=5)
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
    """Enhanced logger with structured logging and metrics collection"""

    def __init__(self, name: str = 'HedgeFund', log_file: Optional[str] = "logs/trading_system.log"):
        self.logger = create_logger(name)
        self.metrics = {}
        self.name = name

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
        self.info(f"⏱️ PERFORMANCE: {operation} completed in {duration:.4f}s", operation=operation, duration=duration, **context)

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

    def log_watcher_analysis(self, watcher: str, symbol: str, result: str, confidence: Optional[float] = None, **context):
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

        self.info(f"{alert_emoji} RISK ALERT ({alert_type.upper()}): {message}", alert_type=alert_type, message=message, **context)

    def log_auto_detection_status(self, symbols_monitored: int, active_strategies: int, opportunities_found: int, **context):
        """Log auto-detection system status"""
        self.info(f"🤖 AUTO-DETECTION STATUS: Monitoring {symbols_monitored} symbols | Active strategies: {active_strategies} | Opportunities: {opportunities_found}",
                 symbols_monitored=symbols_monitored, active_strategies=active_strategies, opportunities_found=opportunities_found, **context)


# Global logger instance
logger = EnhancedLogger()
