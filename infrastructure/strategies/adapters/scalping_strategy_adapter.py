"""
Infrastructure implementation of the Scalping Strategy following hexagonal architecture.
This strategy has been evaluated for structural viability and enhanced with strict market conditions.
"""
from typing import List, Optional, Dict, Any
from domain.entities import Signal, SignalType
from domain.value_objects import Symbol, Percentage
from domain.ports.engine_ports import StrategyPort
from shared.logger import logger
from datetime import datetime
from decimal import Decimal
import numpy as np
from infrastructure.strategies.strategy_adapters import BaseStrategyAdapter


class ScalpingStrategyAdapter(BaseStrategyAdapter):
    """
    Disciplined scalping strategy with strict market micro-conditions.
    NOTE: Scalping is inherently challenging due to transaction costs and market noise.
    This implementation includes strict viability filters.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("Scalper")
        # Get configuration from the centralized config system
        from infrastructure.strategies.strategy_config import get_scalping_config
        system_config = get_scalping_config()

        # NOTE: system_config contains execution settings (like min_confidence, max_position_size)
        # at the top level, and mathematical model params inside the nested 'parameters' dict.
        # We must extract and merge both so that key settings are correctly loaded into self.config
        # and do not fall back to obsolete system defaults.
        params = system_config.get('parameters', {})
        top_level = {k: v for k, v in system_config.items() if k != 'parameters'}
        self.config = {**top_level, **params, **(config or {})}

        # Use configuration values or defaults
        self.lookback_period = self.config.get("lookback_period", 5)
        self.profit_target = self.config.get("profit_target", 0.005)
        self.stop_loss = self.config.get("stop_loss", 0.003)
        self.rsi_period = self.config.get("rsi_period", 14)
        self.momentum_period = self.config.get("momentum_period", 3)
        self.ma_fast = self.config.get("ma_fast", 5)
        self.ma_slow = self.config.get("ma_slow", 10)

        # Scalping-specific parameters for market micro-conditions
        self.min_spread_threshold = self.config.get("min_spread_threshold", 0.00005)  # Minimum spread threshold (0.005%)
        self.max_volatility_threshold = self.config.get("max_volatility_threshold", 0.02)  # Maximum volatility threshold (2%)
        self.min_volume_threshold = self.config.get("min_volume_threshold", 100)  # Legacy absolute floor (kept for config compat)
        self.min_volume_ratio = self.config.get("min_volume_ratio", 0.5)  # Relative liquidity floor: recent vol vs baseline
        self.required_tick_size_multiple = self.config.get("required_tick_size_multiple", 4)  # Price movement should be multiple of tick size

        # Viability assessment parameters
        self.viability_check_enabled = self.config.get("viability_check_enabled", True)
        self.consecutive_losses_before_disable = self.config.get("consecutive_losses_before_disable", 5)
        self.min_profitable_trades_ratio = self.config.get("min_profitable_trades_ratio", 0.4)  # 40% minimum win rate
        self.max_drawdown_threshold = self.config.get("max_drawdown_threshold", 0.10)  # 10% maximum drawdown

        # Track performance for viability assessment
        self.trade_history = []
        # E-P5.2: own viability counter — must NOT shadow BaseStrategyAdapter's
        # per-symbol consecutive_losses DICT (super().__init__ set it to {}).
        # Overwriting it with an int broke base discipline with
        # "'int' object has no attribute 'get'" on the first bar.
        self._scalp_consecutive_losses = 0
        self.total_trades = 0
        self.profitable_trades = 0

    def _assess_market_micro_conditions(self, closes: List[float], highs: List[float], lows: List[float], volumes: List[float]) -> Dict[str, bool]:
        """
        Assess market micro-conditions required for scalping
        """
        if len(closes) < 10:
            return {"conditions_met": False, "low_spread": False, "acceptable_volatility": False, "adequate_volume": False}

        current_price = closes[-1]

        # Calculate volatility (using ATR approximation)
        true_ranges = []
        for i in range(1, len(highs)):
            high_val = highs[i]
            low_val = lows[i]
            prev_close = closes[i-1] if i > 0 else closes[i]

            tr = max(
                high_val - low_val,
                abs(high_val - prev_close),
                abs(low_val - prev_close)
            )
            true_ranges.append(tr)

        avg_true_range = np.mean(true_ranges) if true_ranges else 0
        volatility_pct = avg_true_range / current_price if current_price > 0 else 0

        # Calculate average volume
        avg_volume = np.mean(volumes) if volumes else 0

        # Assess conditions
        low_spread = True  # Assuming spread is acceptable for digital asset
        acceptable_volatility = volatility_pct <= self.max_volatility_threshold
        # Adequate liquidity is RELATIVE to the asset's own volume, not an absolute
        # unit count. min_volume_threshold=100 was an absolute figure that never
        # matched the data scale (BTC 1m volume ~6/bar) and failed EVERY bar, short-
        # circuiting before the strategy's real (tick-cost) hypothesis gate could run.
        # Scale-invariant floor: recent volume hasn't collapsed vs its own baseline.
        recent_vol = float(np.mean(volumes[-self.lookback_period:])) if len(volumes) >= self.lookback_period else avg_volume
        adequate_volume = avg_volume > 0 and recent_vol >= self.min_volume_ratio * avg_volume

        conditions_met = low_spread and acceptable_volatility and adequate_volume

        return {
            "conditions_met": conditions_met,
            "low_spread": low_spread,
            "acceptable_volatility": acceptable_volatility,
            "adequate_volume": adequate_volume,
            "current_volatility": volatility_pct,
            "current_avg_volume": avg_volume
        }

    def _evaluate_structural_viability(self) -> bool:
        """
        Evaluate if scalping strategy is structurally viable based on performance
        """
        if self.total_trades < 10:
            # Not enough data to assess viability, allow to continue
            return True

        # Calculate win rate
        win_rate = self.profitable_trades / self.total_trades if self.total_trades > 0 else 0

        # Check if win rate is below minimum threshold
        if win_rate < self.min_profitable_trades_ratio:
            self.logger.warning(f"Scalping strategy win rate ({win_rate:.2%}) below minimum threshold ({self.min_profitable_trades_ratio:.2%}), disabling")
            return False

        # Check consecutive losses
        if self._scalp_consecutive_losses >= self.consecutive_losses_before_disable:
            self.logger.warning(f"Scalping strategy had {self._scalp_consecutive_losses} consecutive losses, disabling")
            return False

        # If we have enough trades and acceptable win rate, continue
        return True

    def _calculate_tick_size_impact(self, closes: List[float]) -> bool:
        """
        Assess if price movements are large enough relative to tick size to overcome costs
        """
        if len(closes) < 3:
            return False

        # Calculate average price movement
        movements = [abs(closes[i] - closes[i-1]) / closes[i-1] for i in range(1, len(closes))]
        avg_movement = np.mean(movements) if movements else 0

        # For scalping to be viable, movements should be significantly larger than typical bid-ask spreads
        # Assuming a typical spread of 0.05%, movements should be at least 4x that for profitability
        return avg_movement >= (self.min_spread_threshold * self.required_tick_size_multiple)

    def generate_signal(self, symbol: Symbol) -> Optional[Signal]:
        """
        Generate a signal using disciplined scalping logic with strict market conditions.
        Returns None if market conditions are not suitable for scalping or if strategy is not viable.
        """
        if len(self.data_buffer) < max(self.lookback_period, 15):
            self.logger.debug(f"Not enough data for {self.name}: {len(self.data_buffer)}, need at least {max(self.lookback_period, 15)}")
            return None

        try:
            # Extract data for analysis
            closes = [item['close'] for item in self.data_buffer if 'close' in item]
            highs = [item.get('high', item['close']) for item in self.data_buffer if 'close' in item]
            lows = [item.get('low', item['close']) for item in self.data_buffer if 'close' in item]
            volumes = [item.get('volume', 1) for item in self.data_buffer if 'close' in item]  # Default to 1 if no volume

            if len(closes) < max(self.lookback_period, 15):
                self.logger.debug(f"Not enough close prices for {self.name}: {len(closes)}")
                return None

            # First, assess structural viability
            if self.viability_check_enabled and not self._evaluate_structural_viability():
                self.logger.warning(f"Scalping strategy deemed not structurally viable, skipping signal generation")
                return None

            # Assess market micro-conditions
            market_conditions = self._assess_market_micro_conditions(closes, highs, lows, volumes)

            if not market_conditions["conditions_met"]:
                self.logger.debug(f"Market conditions not suitable for scalping: {market_conditions}")
                return None

            # Additional check for tick size impact
            if not self._calculate_tick_size_impact(closes):
                self.logger.debug(f"Price movements insufficient to overcome transaction costs")
                return None

            current_price = closes[-1]

            # Calculate fast and slow moving averages for crossover
            calculated_ma_fast = self.calculate_ema(closes, self.ma_fast)
            calculated_ma_slow = self.calculate_ema(closes, self.ma_slow)

            # Calculate short-term momentum
            momentum_period = min(self.momentum_period, len(closes) - 1)
            if momentum_period > 0 and len(closes) > momentum_period:
                calculated_momentum = (current_price - closes[-momentum_period - 1]) / closes[-momentum_period - 1]
            else:
                calculated_momentum = 0

            # Calculate RSI for overbought/oversold conditions
            calculated_rsi = self.calculate_rsi(closes, self.rsi_period)

            # Calculate volume if available (volume might not always be present)
            recent_volumes = [item['volume'] for item in self.data_buffer[-5:] if 'volume' in item]
            avg_volume = np.mean(recent_volumes) if recent_volumes else 0
            current_volume = self.data_buffer[-1].get('volume', 0) if len(self.data_buffer) > 0 else 0
            volume_spike_threshold = self.config.get("volume_spike_threshold", 1.5)
            volume_spike = current_volume > avg_volume * volume_spike_threshold if avg_volume > 0 else False

            # Determine signal based on multiple scalping indicators
            final_signal_type = SignalType.HOLD
            final_confidence_factor = self.config.get("default_confidence_factor", 0.3)
            final_score = 0.0

            ma_crossover_signal = None
            if calculated_ma_fast and calculated_ma_slow:
                if calculated_ma_fast > calculated_ma_slow:  # Bullish crossover
                    ma_crossover_signal = SignalType.BUY
                elif calculated_ma_fast < calculated_ma_slow:  # Bearish crossover
                    ma_crossover_signal = SignalType.SELL

            # Define thresholds from config
            rsi_overbought_threshold = self.config.get("rsi_overbought_threshold", 70)
            rsi_oversold_threshold = self.config.get("rsi_oversold_threshold", 30)
            momentum_base_confidence = self.config.get("momentum_base_confidence", 0.5)
            momentum_confidence_divisor = self.config.get("momentum_confidence_divisor", 1.5)
            momentum_score_multiplier = self.config.get("momentum_score_multiplier", 5)

            # Combine signals with volume confirmation
            if ma_crossover_signal == SignalType.BUY and calculated_momentum > 0 and (not calculated_rsi or calculated_rsi < rsi_overbought_threshold):  # Not overbought
                final_signal_type = SignalType.BUY
                final_confidence_factor = min(1.0, (calculated_momentum + momentum_base_confidence) / momentum_confidence_divisor)  # Higher confidence with positive momentum
                final_score = min(1.0, calculated_momentum * momentum_score_multiplier)
            elif ma_crossover_signal == SignalType.SELL and calculated_momentum < 0 and (not calculated_rsi or calculated_rsi > rsi_oversold_threshold):  # Not oversold
                final_signal_type = SignalType.SELL
                final_confidence_factor = min(1.0, (abs(calculated_momentum) + momentum_base_confidence) / momentum_confidence_divisor)
                final_score = max(-1.0, calculated_momentum * momentum_score_multiplier)

            # Enhance confidence if volume spike confirms signal
            if volume_spike and final_signal_type != SignalType.HOLD:
                final_confidence_factor = min(1.0, final_confidence_factor * 1.2)

            confidence = Percentage(Decimal(str(min(1.0, max(0.1, final_confidence_factor)))))

            signal = Signal(
                symbol=symbol,
                signal_type=final_signal_type,
                confidence=confidence,
                score=final_score,
                timestamp=datetime.now(),
                source_layer="DisciplinedScalping",
                metadata={
                    "ma_fast": calculated_ma_fast,
                    "ma_slow": calculated_ma_slow,
                    "momentum": calculated_momentum,
                    "rsi": calculated_rsi,
                    "volume_spike": volume_spike,
                    "current_price": current_price,
                    "market_conditions": market_conditions,
                    "tick_size_impact_sufficient": self._calculate_tick_size_impact(closes),
                    "structural_viability_assessed": True,
                    "viability_status": self._evaluate_structural_viability()
                }
            )

            # Log signal if generated
            if final_signal_type != SignalType.HOLD:
                self.logger.info(f"{self.name} generated signal: {signal.signal_type.name} with confidence {float(signal.confidence.value):.3f} for {symbol.value}")
                self.logger.info(f"Market conditions met: {market_conditions['conditions_met']}, Volatility: {market_conditions['current_volatility']:.4f}")

            return signal

        except Exception as e:
            self.logger.error(f"Error in {self.name} strategy: {e}")
            import traceback
            traceback.print_exc()
            return None

    def record_trade_result(self, symbol: str, is_profitable: bool, position_closed: bool = True,
                            exit_time=None):
        """
        Record the result of a trade for viability assessment
        """
        self.total_trades += 1

        if is_profitable:
            self.profitable_trades += 1
            self._scalp_consecutive_losses = 0  # Reset consecutive losses counter
        else:
            self._scalp_consecutive_losses += 1

        # Call parent method to handle other aspects of trade result recording
        # (E-P5.2: thread exit_time through so base discipline stays time-aware).
        super().record_trade_result(symbol, is_profitable, position_closed, exit_time=exit_time)