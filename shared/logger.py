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

    def __init__(self, name: str = 'HedgeFund', log_file: Optional[str] = "logs/trading_system.log",
                 comprehensive_mode: bool = False):
        self.logger = create_logger(name)
        self.metrics = {}
        self.name = name
        self.flow_tracker = {}  # Track flow IDs and their status
        self.comprehensive_mode = comprehensive_mode  # Enable comprehensive logging

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

    def log_flow_start(self, flow_id: str, symbol: str, initial_source: str, **context):
        """Log the start of a trading flow"""
        flow_info = {
            'symbol': symbol,
            'source': initial_source,
            'start_time': datetime.now().isoformat(),
            'status': 'started',
            'steps': []
        }
        self.flow_tracker[flow_id] = flow_info

        self.info(f"🚀 FLOW STARTED: {initial_source} → {symbol} | Flow ID: {flow_id}",
                 flow_id=flow_id, symbol=symbol, source=initial_source, **context)

    def log_flow_step(self, flow_id: str, step: str, result: str, reason: str = "", **context):
        """Log a step in the trading flow with decision reason"""
        if flow_id in self.flow_tracker:
            step_info = {
                'step': step,
                'result': result,
                'reason': reason,
                'timestamp': datetime.now().isoformat()
            }
            self.flow_tracker[flow_id]['steps'].append(step_info)

            # Determine emoji based on result
            result_emoji = "✅" if result.lower() in ['accepted', 'passed', 'success', 'approved'] else \
                          "❌" if result.lower() in ['rejected', 'failed', 'denied', 'error'] else \
                          "🔄"

            self.info(f"  {result_emoji} FLOW STEP: {step} → {result} | Reason: {reason}",
                     flow_id=flow_id, step=step, result=result, reason=reason, **context)
        else:
            # Log without flow tracking if flow ID not found
            result_emoji = "✅" if result.lower() in ['accepted', 'passed', 'success', 'approved'] else \
                          "❌" if result.lower() in ['rejected', 'failed', 'denied', 'error'] else \
                          "🔄"

            self.info(f"  {result_emoji} FLOW STEP: {step} → {result} | Reason: {reason}",
                     flow_id=flow_id, step=step, result=result, reason=reason, **context)

    def log_flow_complete(self, flow_id: str, final_result: str, **context):
        """Log the completion of a trading flow"""
        if flow_id in self.flow_tracker:
            self.flow_tracker[flow_id]['status'] = 'completed'
            self.flow_tracker[flow_id]['end_time'] = datetime.now().isoformat()
            self.flow_tracker[flow_id]['final_result'] = final_result

            # Determine emoji based on final result
            result_emoji = "✅" if final_result.lower() in ['executed', 'success', 'completed'] else \
                          "❌" if final_result.lower() in ['rejected', 'failed', 'cancelled'] else \
                          "🔄"

            self.info(f"🏁 FLOW COMPLETED: {final_result} | Flow ID: {flow_id}",
                     flow_id=flow_id, final_result=final_result, **context)
        else:
            # Log without flow tracking if flow ID not found
            result_emoji = "✅" if final_result.lower() in ['executed', 'success', 'completed'] else \
                          "❌" if final_result.lower() in ['rejected', 'failed', 'cancelled'] else \
                          "🔄"

            self.info(f"🏁 FLOW COMPLETED: {final_result} | Flow ID: {flow_id}",
                     flow_id=flow_id, final_result=final_result, **context)

    def log_full_flow(self, symbol: str, watcher: str, engine: str, fusion: str, strategy: str,
                     broker: str, decision: str, confidence: float, reason: str, **context):
        """Log the complete flow from watcher to broker with all details"""
        flow_id = f"{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"

        # Log the full flow in a single comprehensive message
        self.info(f"📊 FULL FLOW: {watcher} → {engine} → {fusion} → {strategy} → {broker} | "
                 f"Decision: {decision} | Conf: {confidence:.2%} | Reason: {reason}",
                 flow_id=flow_id, symbol=symbol, watcher=watcher, engine=engine,
                 fusion=fusion, strategy=strategy, broker=broker, decision=decision,
                 confidence=confidence, reason=reason, **context)

    def log_complete_signal_flow(self, symbol: str, signal_type: str, confidence: float,
                               watcher: str, engine: str, fusion: str, strategy: str, broker: str,
                               execution_status: str, execution_id: str = None, **context):
        """Log the complete signal flow from detection to execution with detailed status tracking"""
        flow_id = f"{symbol}_SIGNAL_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"

        # Log the complete flow with visual indicators
        status_emoji = "✅" if execution_status.lower() in ['executed', 'success', 'filled'] else \
                      "❌" if execution_status.lower() in ['rejected', 'failed', 'cancelled', 'error'] else \
                      "🔄"

        self.info(f"{status_emoji} SIGNAL FLOW: {watcher} → {engine} → {fusion} → {strategy} → {broker} | "
                 f"Signal: {signal_type} | Conf: {confidence:.2%} | Status: {execution_status} | "
                 f"ID: {execution_id or 'N/A'}",
                 flow_id=flow_id, symbol=symbol, signal_type=signal_type, confidence=confidence,
                 watcher=watcher, engine=engine, fusion=fusion, strategy=strategy, broker=broker,
                 execution_status=execution_status, execution_id=execution_id, **context)

    def log_signal_progression(self, symbol: str, stage: str, status: str, details: str = "",
                             confidence: float = None, **context):
        """Log the progression of a signal through each stage with detailed information"""
        stage_emoji = {
            'watcher': '👁️',
            'engine': '⚙️',
            'fusion': '🔗',
            'strategy': '🎯',
            'broker': '⚡'
        }.get(stage.lower(), '🔄')

        status_emoji = "✅" if status.lower() in ['success', 'accepted', 'passed', 'completed'] else \
                      "❌" if status.lower() in ['failed', 'rejected', 'error'] else \
                      "🔄"

        if confidence is not None:
            self.info(f"  {stage_emoji} {stage.upper()}: {status_emoji} {status} | {details} | Conf: {confidence:.2%}",
                     symbol=symbol, stage=stage, status=status, details=details,
                     confidence=confidence, **context)
        else:
            self.info(f"  {stage_emoji} {stage.upper()}: {status_emoji} {status} | {details}",
                     symbol=symbol, stage=stage, status=status, details=details, **context)

    def log_watcher_to_engine_flow(self, symbol: str, watcher_name: str, signal_generated: bool,
                                  signal_type: str, confidence: float, reason: str, **context):
        """Log the flow from watcher to engine with detailed information"""
        flow_id = f"{symbol}_W2E_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"

        self.log_flow_start(flow_id, symbol, f"Watcher({watcher_name})", **context)

        if signal_generated:
            self.log_flow_step(flow_id, "Watcher", "Signal Generated", f"Signal: {signal_type}, Conf: {confidence:.2%}", **context)
            self.log_flow_step(flow_id, "Engine", "Accepted", reason, **context)
        else:
            self.log_flow_step(flow_id, "Watcher", "No Signal", reason, **context)
            self.log_flow_step(flow_id, "Engine", "Rejected", "No signal from watcher", **context)

        final_status = "Accepted" if signal_generated else "Rejected"
        self.log_flow_complete(flow_id, final_status, **context)

    def log_engine_to_fusion_flow(self, symbol: str, engine_name: str, signal_processed: bool,
                                 signal_type: str, confidence: float, reason: str, **context):
        """Log the flow from engine to fusion with detailed information"""
        flow_id = f"{symbol}_E2F_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"

        self.log_flow_start(flow_id, symbol, f"Engine({engine_name})", **context)

        if signal_processed:
            self.log_flow_step(flow_id, "Engine", "Signal Processed", f"Signal: {signal_type}, Conf: {confidence:.2%}", **context)
            self.log_flow_step(flow_id, "Fusion", "Accepted", reason, **context)
        else:
            self.log_flow_step(flow_id, "Engine", "Signal Rejected", reason, **context)
            self.log_flow_step(flow_id, "Fusion", "Skipped", "No valid signal from engine", **context)

        final_status = "Processed" if signal_processed else "Rejected"
        self.log_flow_complete(flow_id, final_status, **context)

    def log_fusion_to_strategy_flow(self, symbol: str, fusion_name: str, fused_signal: bool,
                                   signal_type: str, confidence: float, reason: str, **context):
        """Log the flow from fusion to strategy with detailed information"""
        flow_id = f"{symbol}_F2S_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"

        self.log_flow_start(flow_id, symbol, f"Fusion({fusion_name})", **context)

        if fused_signal:
            self.log_flow_step(flow_id, "Fusion", "Signal Fused", f"Signal: {signal_type}, Conf: {confidence:.2%}", **context)
            self.log_flow_step(flow_id, "Strategy", "Accepted", reason, **context)
        else:
            self.log_flow_step(flow_id, "Fusion", "No Fusion", reason, **context)
            self.log_flow_step(flow_id, "Strategy", "Rejected", "No fused signal from fusion", **context)

        final_status = "Fused" if fused_signal else "Rejected"
        self.log_flow_complete(flow_id, final_status, **context)

    def log_strategy_to_broker_flow(self, symbol: str, strategy_name: str, trade_executed: bool,
                                   signal_type: str, confidence: float, reason: str, **context):
        """Log the flow from strategy to broker with detailed information"""
        flow_id = f"{symbol}_S2B_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"

        self.log_flow_start(flow_id, symbol, f"Strategy({strategy_name})", **context)

        if trade_executed:
            self.log_flow_step(flow_id, "Strategy", "Trade Approved", f"Signal: {signal_type}, Conf: {confidence:.2%}", **context)
            self.log_flow_step(flow_id, "Broker", "Executed", reason, **context)
        else:
            self.log_flow_step(flow_id, "Strategy", "Trade Rejected", reason, **context)
            self.log_flow_step(flow_id, "Broker", "Skipped", "No trade approved by strategy", **context)

        final_status = "Executed" if trade_executed else "Rejected"
        self.log_flow_complete(flow_id, final_status, **context)

    def log_decision_reason(self, component: str, symbol: str, decision: str, reason: str,
                          confidence: float = None, **context):
        """Log detailed decision reasons at each component"""
        if confidence is not None:
            self.info(f"🧠 {component.upper()} DECISION: {decision} for {symbol} | Reason: {reason} | Conf: {confidence:.2%}",
                     component=component, symbol=symbol, decision=decision, reason=reason,
                     confidence=confidence, **context)
        else:
            self.info(f"🧠 {component.upper()} DECISION: {decision} for {symbol} | Reason: {reason}",
                     component=component, symbol=symbol, decision=decision, reason=reason, **context)

    def set_comprehensive_mode(self, enabled: bool):
        """Enable or disable comprehensive logging mode"""
        self.comprehensive_mode = enabled
        status = "ENABLED" if enabled else "DISABLED"
        self.info(f"📋 COMPREHENSIVE LOGGING: {status}")

    def log_background_activity(self, activity_type: str, details: str, **context):
        """Log background activities with comprehensive mode support"""
        if self.comprehensive_mode:
            self.info(f"🔄 BACKGROUND ACTIVITY: {activity_type} | Details: {details}",
                     activity_type=activity_type, details=details, **context)


# Global logger instance
logger = EnhancedLogger()
