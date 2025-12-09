"""
Infrastructure implementations of additional trading engines for the enterprise hedge fund system.
"""
from typing import Dict, Any
import pandas as pd
import numpy as np
from decimal import Decimal

from domain.entities.trading_entities import Signal
from domain.entities.engine_entities import EngineResult
from domain.value_objects import Symbol, Percentage
from domain.ports.engine_ports import EnginePort
from shared.logger import logger


class ATREngineAdapter(EnginePort):
    """Infrastructure implementation of ATR (Average True Range) engine following hexagonal architecture"""

    def __init__(self, atr_period: int = 14, atr_multiplier: float = 2.0):
        self.name = "ATREngine"
        self.atr_period = atr_period
        self.atr_multiplier = atr_multiplier
        self.price_history: list = []
        self.current_atr = 0.0

    def process_signal(self, signal: Signal) -> Signal:
        """Process a signal through ATR analysis"""
        # This engine primarily analyzes market data for risk management
        # rather than modifying signals, but we can adjust confidence based on volatility
        if self.current_atr == 0:
            # No ATR data yet - return signal unchanged
            return Signal(
                symbol=signal.symbol,
                signal_type=signal.signal_type,
                confidence=signal.confidence,
                score=signal.score,
                strategy_name=f"{signal.strategy_name}_atr_aware",
                timestamp=signal.timestamp,
                source_engine=self.name,
                metadata=signal.metadata or {}
            )

        # Calculate volatility-adjusted confidence
        # In high volatility, we might reduce signal confidence slightly
        avg_price = float(signal.confidence.value) * 100 + 50  # approximate to get a price-like reference
        if avg_price > 0:
            volatility_ratio = self.current_atr / avg_price
            
            # Adjust confidence based on volatility level
            if volatility_ratio > 0.03:  # high volatility
                adjustment = Decimal('0.8')
            elif volatility_ratio > 0.015:  # medium volatility
                adjustment = Decimal('0.9')
            else:  # low volatility
                adjustment = Decimal('1.05')
                
            new_confidence_value = signal.confidence.value * adjustment
            new_confidence = Percentage(max(Decimal('0.1'), min(Decimal('1.0'), new_confidence_value)))
            new_score = max(-1.0, min(1.0, signal.score * float(adjustment)))
        else:
            new_confidence = signal.confidence
            new_score = signal.score

        enhanced_signal = Signal(
            symbol=signal.symbol,
            signal_type=signal.signal_type,
            confidence=new_confidence,
            score=new_score,
            strategy_name=f"{signal.strategy_name}_atr_adjusted",
            timestamp=signal.timestamp,
            source_engine=self.name,
            metadata={
                **(signal.metadata or {}),
                'atr_value': self.current_atr,
                'atr_volatility_ratio': volatility_ratio if avg_price > 0 else 0
            }
        )

        logger.info(f"ATREngine processed signal: {signal.signal_type.name}, "
                   f"ATR: {self.current_atr:.4f}, "
                   f"confidence: {float(signal.confidence):.2%} -> {float(enhanced_signal.confidence):.2%}")
        return enhanced_signal

    def should_process_signal(self, signal: Signal) -> bool:
        """Check if this engine should process the signal"""
        return True

    def update_with_market_data(self, data: Dict[str, Any]):
        """Update with new market data to calculate ATR"""
        if not all(key in data for key in ['high', 'low', 'close']):
            return

        high = float(data['high'])
        low = float(data['low'])
        close = float(data['close'])

        # Calculate True Range
        if self.price_history:
            prev_close = self.price_history[-1]
            true_range = max(
                high - low,
                abs(high - prev_close),
                abs(low - prev_close)
            )
        else:
            true_range = high - low

        self.price_history.append(close)
        if len(self.price_history) > self.atr_period * 3:
            self.price_history.pop(0)

        # Calculate ATR
        if len(self.price_history) >= 2:
            # We need at least atr_period TR values to calculate ATR
            if hasattr(self, '_tr_values'):
                self._tr_values.append(true_range)
            else:
                self._tr_values = [true_range]

            if len(self._tr_values) > self.atr_period:
                self._tr_values.pop(0)

            if len(self._tr_values) == self.atr_period:
                # Calculate simple moving average of True Range
                self.current_atr = sum(self._tr_values) / len(self._tr_values)

    def get_engine_name(self) -> str:
        """Get the name of the engine"""
        return self.name


class RiskEngineAdapter(EnginePort):
    """Infrastructure implementation of risk assessment engine following hexagonal architecture"""

    def __init__(self, volatility_threshold: float = 0.02, correlation_threshold: float = 0.7):
        self.name = "RiskEngine"
        self.volatility_threshold = volatility_threshold
        self.correlation_threshold = correlation_threshold
        self.price_history: list = []
        self.position_risk_score = 0.0
        self.market_volatility = 0.0
        self.portfolio_correlation = 0.0

    def process_signal(self, signal: Signal) -> Signal:
        """Process a signal through risk analysis"""
        # Analyze risk factors and potentially modify signal
        risk_factors = []

        # Check market volatility risk
        if self.market_volatility > self.volatility_threshold:
            risk_factors.append("high_market_volatility")
            
        # Calculate risk-adjusted confidence
        if risk_factors:
            # Reduce confidence when risk factors are present
            risk_reduction = Decimal(str(min(0.3, self.market_volatility)))
            new_confidence_value = signal.confidence.value * (Decimal('1.0') - risk_reduction)
            new_confidence = Percentage(max(Decimal('0.1'), new_confidence_value))
            new_score = max(-1.0, min(1.0, signal.score * (1.0 - float(risk_reduction))))
        else:
            # Potentially boost confidence when risk is low
            new_confidence_value = min(Decimal('1.0'), signal.confidence.value * Decimal('1.05'))
            new_confidence = Percentage(new_confidence_value)
            new_score = max(-1.0, min(1.0, signal.score * 1.05))

        enhanced_signal = Signal(
            symbol=signal.symbol,
            signal_type=signal.signal_type,
            confidence=new_confidence,
            score=new_score,
            strategy_name=f"{signal.strategy_name}_risk_aware",
            timestamp=signal.timestamp,
            source_engine=self.name,
            metadata={
                **(signal.metadata or {}),
                'risk_factors': risk_factors,
                'market_volatility': self.market_volatility,
                'risk_score': self.position_risk_score,
                'risk_adjusted': bool(risk_factors)
            }
        )

        logger.info(f"RiskEngine processed signal: {signal.signal_type.name}, "
                   f"risk factors: {risk_factors}, "
                   f"confidence: {float(signal.confidence):.2%} -> {float(enhanced_signal.confidence):.2%}")
        return enhanced_signal

    def should_process_signal(self, signal: Signal) -> bool:
        """Check if this engine should process the signal"""
        return True

    def update_with_market_data(self, data: Dict[str, Any]):
        """Update with new market data for risk assessment"""
        if 'close' in data:
            current_price = float(data['close'])
            self.price_history.append(current_price)
            
            if len(self.price_history) > 30:  # Keep max 30 prices for risk calculation
                self.price_history.pop(0)

            # Calculate market volatility if we have enough data
            if len(self.price_history) >= 10:
                returns = []
                for i in range(1, len(self.price_history)):
                    ret = (self.price_history[i] - self.price_history[i-1]) / self.price_history[i-1]
                    returns.append(ret)
                
                if returns:
                    self.market_volatility = float(np.std(returns))

    def get_engine_name(self) -> str:
        """Get the name of the engine"""
        return self.name