#!/usr/bin/env python3
"""Backtest strategy provider (E2.T4b - Composition Root Hardening).

Infrastructure adapter that builds backtest-ready strategy functions. Hosts the
strategy-loading and execution-intent-wrapping logic relocated verbatim from the
legacy ``runner_backtest`` so the application use case can obtain a ready-to-run
strategy through a port instead of importing infrastructure (strategy adapters,
execution intents) directly.
"""
import pandas as pd

from infrastructure.backtest.execution_intent import create_execution_intent, OrderSide


def load_sample_strategy(strategy_name: str, raw_signal: bool = False):
    """Load a sample strategy function based on the strategy name.

    raw_signal=True bypasses the adapter map and returns the strategy's OWN
    raw signal function (the per-strategy trading logic). E-P5.2 Option A uses
    this so each adapter is evaluated against its own signal/hypothesis instead
    of a shared generic mock.
    """

    # Import the strategy adapters
    from infrastructure.strategies.adapters.trend_follow_strategy_adapter import TrendFollowStrategyAdapter
    from infrastructure.strategies.adapters.mean_reversion_strategy_adapter import MeanReversionStrategyAdapter
    from infrastructure.strategies.adapters.scalping_strategy_adapter import ScalpingStrategyAdapter
    from infrastructure.strategies.adapters.breakout_strategy_adapter import BreakoutStrategyAdapter
    from infrastructure.strategies.adapters.liquidity_strategy_adapter import LiquidityStrategyAdapter
    from infrastructure.strategies.adapters.vwap_reversal_strategy_adapter import VWAPReversalStrategyAdapter
    from infrastructure.strategies.adapters.momentum_strategy_adapter import MomentumStrategyAdapter
    from infrastructure.strategies.adapters.mtf_trend_strategy_adapter import MTFTrendStrategyAdapter
    from infrastructure.strategies.adapters.oi_footprint_strategy_adapter import OIFootprintStrategyAdapter
    from infrastructure.strategies.adapters.sweep_scalper_strategy_adapter import SweepScalperAdapter
    from infrastructure.strategies.strategy_adapters import VolatilityBreakoutStrategy

    # Create a mapping from strategy names to adapter classes
    strategy_adapters = {
        'trend_following': TrendFollowStrategyAdapter,
        'mean_reversion': MeanReversionStrategyAdapter,
        'scalping': ScalpingStrategyAdapter,
        'breakout': BreakoutStrategyAdapter,
        'liquidity': LiquidityStrategyAdapter,
        'vwap_reversal': VWAPReversalStrategyAdapter,
        'momentum': MomentumStrategyAdapter,
        'mtf_trend': MTFTrendStrategyAdapter,
        'oi_footprint': OIFootprintStrategyAdapter,
        'sweep_scalper': SweepScalperAdapter,
        'crypto_breakout': BreakoutStrategyAdapter,  # Alias for crypto breakout
        'volatility_breakout': VolatilityBreakoutStrategy,  # ATR breakout (real generate_signal)
    }

    # If the strategy name corresponds to an adapter, return a function that uses it
    if strategy_name in strategy_adapters and not raw_signal:
        adapter_class = strategy_adapters[strategy_name]
        # Create strategy instance with empty config initially
        strategy_instance = adapter_class({})

        # Direction-B: evaluate the strategy through its REAL generate_signal()
        # (its actual trading hypothesis), fed bar-by-bar via update_with_market_data.
        # This is the single authoritative signal path; the prior raw-signal proxy
        # function is no longer used for adapter-backed strategies.
        def strategy_with_discipline(row, params):
            from domain.entities import FusedSignal, SignalType
            from domain.value_objects import Symbol, Percentage
            from datetime import datetime
            from decimal import Decimal

            mock_symbol = Symbol(params.get('symbol', 'BTCUSDT'))
            # Direction-B: generate_signal is the source of truth and already does
            # each strategy's internal regime assessment, so the redundant external
            # regime gate in should_execute must not veto the strategy's own signal.
            # Default regime_context to the strategy name (which contains its regime
            # keyword, e.g. 'mean_reversion' -> 'mean', 'volatility_breakout' ->
            # 'breakout'), so a signal the strategy chose to emit is honored.
            mock_regime = params.get('regime_context') or strategy_name

            # Bar's (simulated) timestamp, not wall-clock — keeps the strategy's
            # daily-trade-limit discipline resetting across simulated days.
            bar_ts = row.get('timestamp', None)
            if bar_ts is None:
                bar_ts = getattr(row, 'name', None)
            if isinstance(bar_ts, (int, float)) and not pd.isna(bar_ts):
                bar_ts = datetime.utcfromtimestamp(bar_ts)
            elif hasattr(bar_ts, 'to_pydatetime'):
                bar_ts = bar_ts.to_pydatetime()
            if not isinstance(bar_ts, datetime):
                bar_ts = datetime.now()

            # Direction-B authoritative path: feed this bar to the strategy's own
            # data buffer, then ask the strategy for a signal via its REAL
            # generate_signal() (its actual hypothesis), and drive the trade from it.
            bar = {
                'open': row.get('open'), 'high': row.get('high'), 'low': row.get('low'),
                'close': row.get('close'), 'volume': row.get('volume', 0),
                'timestamp': bar_ts,
            }
            strategy_instance.update_with_market_data(bar)
            sig = strategy_instance.generate_signal(mock_symbol)
            if sig is None:
                return None
            st_name = getattr(getattr(sig, 'signal_type', None), 'name', '').upper()
            if 'BUY' in st_name or 'LONG' in st_name:
                mock_direction = 1.0
            elif 'SELL' in st_name or 'SHORT' in st_name:
                mock_direction = -1.0
            else:
                return None  # HOLD / no actionable signal
            try:
                conf_val = float(sig.confidence.value)
            except (AttributeError, TypeError, ValueError):
                conf_val = 0.7
            mock_confidence = Percentage(Decimal(str(min(0.99, max(0.1, conf_val)))))
            mock_dominant_bias = SignalType.BUY if mock_direction > 0 else SignalType.SELL

            mock_fused_signal = FusedSignal(
                symbol=mock_symbol,
                dominant_bias=mock_dominant_bias,
                direction=mock_direction,
                dominance_score=abs(mock_direction),
                regime_context=mock_regime,
                confidence=mock_confidence,
                timestamp=bar_ts
            )

            # evaluate_fused_signal applies discipline + risk and forms the ExecutionIntent
            execution_intent = strategy_instance.evaluate_fused_signal(mock_fused_signal)

            # Return the execution intent directly if it's an ExecutionIntent object
            # This allows the execution layer to receive the full intent with risk parameters
            if execution_intent is not None:
                return execution_intent  # Return ExecutionIntent directly
            else:
                return None  # No execution intent (this means discipline rules prevented execution)

        # E-P5.2: expose the adapter's trade-outcome hook so the backtester can
        # feed realised win/loss + exit time back into the strategy discipline
        # (consecutive-loss tracking + post-exit cooldown). Without this the
        # discipline is inactive in backtest and results aren't credible.
        strategy_with_discipline.record_trade_result = strategy_instance.record_trade_result
        return strategy_with_discipline
    else:
        # For strategies not in the adapter system, fall back to original function-based approach
        def simple_rsi_strategy(row, params):
            """Simple RSI-based strategy."""
            rsi = row.get('rsi', 50)
            rsi_oversold = params.get('rsi_oversold', 30)
            rsi_overbought = params.get('rsi_overbought', 70)

            if pd.isna(rsi):
                return 0

            if rsi < rsi_oversold:
                return 1  # Buy
            elif rsi > rsi_overbought:
                return -1  # Sell
            else:
                return 0  # Hold

        def simple_ma_crossover_strategy(row, params):
            """Simple moving average crossover strategy."""
            sma_fast = row.get('sma_10', 0)
            sma_slow = row.get('sma_20', 0)

            if pd.isna(sma_fast) or pd.isna(sma_slow):
                return 0

            if sma_fast > sma_slow:  # Golden cross
                return 1  # Buy
            elif sma_fast < sma_slow:  # Death cross
                return -1  # Sell
            else:
                return 0  # Hold

        def trend_following_strategy(row, params):
            """Regime-aware trend following strategy based on moving averages and momentum."""
            sma_20 = row.get('sma_20', 0)
            sma_50 = row.get('sma_50', 0)
            close = row.get('close', 0)
            roc = row.get('roc_10', 0)  # Rate of change for momentum
            adx = row.get('adx', 20)  # ADX for trend strength
            trend_strength = row.get('trend_strength', 0)

            if pd.isna(sma_20) or pd.isna(sma_50) or pd.isna(close):
                return 0

            # Basic trend conditions - made less restrictive
            trend_bullish = close > sma_20 * 0.999 and sma_20 > sma_50 * 0.999  # Much less strict trend condition
            trend_bearish = close < sma_20 * 1.001 and sma_20 < sma_50 * 1.001  # Much less strict trend condition

            # Add momentum confirmation - made less restrictive
            momentum_bullish = pd.notna(roc) and roc > 0.0001  # Smaller threshold
            momentum_bearish = pd.notna(roc) and roc < -0.0001  # Smaller threshold

            # Regime: Less restrictive trend conditions
            strong_trend = pd.isna(adx) or adx > 15  # Lower ADX threshold
            sufficient_trend_strength = pd.isna(trend_strength) or trend_strength > 0.05  # Lower threshold

            # Allow trades with fewer conditions
            if trend_bullish and (strong_trend or sufficient_trend_strength):
                return 1  # Buy
            elif trend_bearish and (strong_trend or sufficient_trend_strength):
                return -1  # Sell
            elif trend_bullish and momentum_bullish:
                return 1  # Buy with momentum
            elif trend_bearish and momentum_bearish:
                return -1  # Sell with momentum
            else:
                return 0  # Hold

        def mean_reversion_strategy(row, params):
            """Regime-aware mean reversion strategy using RSI and Bollinger Bands."""
            rsi = row.get('rsi', 50)
            bb_upper = row.get('bb_upper', 0)
            bb_lower = row.get('bb_lower', 0)
            close = row.get('close', 0)
            atr = row.get('atr', 0)
            adx = row.get('adx', 20)  # ADX for trend strength
            volatility_regime = row.get('volatility_regime', 0)

            if pd.isna(rsi) or pd.isna(bb_upper) or pd.isna(bb_lower) or pd.isna(close) or pd.isna(atr):
                return 0

            # Calculate how far price is from bands (relative position)
            if bb_upper != bb_lower:  # Avoid division by zero
                bb_position = (close - bb_lower) / (bb_upper - bb_lower)  # 0-1 scale
            else:
                bb_position = 0.5  # Neutral if bands are equal

            # More sensitive thresholds for entry
            rsi_oversold = 40  # Even more sensitive than 35
            rsi_overbought = 60  # Even more sensitive than 65

            # Regime: Less restrictive - allow trading in more market conditions
            weak_trend = pd.isna(adx) or adx < 40  # Higher ADX threshold allows more trading

            # Multiple entry conditions to increase trade frequency
            # Oversold condition with potential bounce from lower band
            rsi_oversold_condition = rsi < rsi_oversold
            rsi_overbought_condition = rsi > rsi_overbought
            near_lower_band = bb_position < 0.45
            near_upper_band = bb_position > 0.55

            if (rsi_oversold_condition and (near_lower_band or weak_trend)):
                return 1  # Buy
            elif (rsi_overbought_condition and (near_upper_band or weak_trend)):
                return -1  # Sell
            # Additional conditions to increase trade frequency
            elif rsi < 30:  # Strong oversold
                return 1
            elif rsi > 70:  # Strong overbought
                return -1
            else:
                return 0  # Hold

        def volatility_breakout_strategy(row, params):
            """Regime-aware volatility breakout strategy using ATR and price movement."""
            atr = row.get('atr', 0)
            high = row.get('high', 0)
            low = row.get('low', 0)
            close = row.get('close', 0)
            sma_20 = row.get('sma_20', 0)
            volume = row.get('volume', 0)
            sma_volume = row.get('sma_volume_20', 0)
            adx = row.get('adx', 20)  # ADX for trend strength
            volatility_percentile = row.get('volatility_percentile', 0.5)  # Volatility regime

            if any(pd.isna(x) for x in [atr, high, low, close, sma_20]):
                return 0

            # Define breakout thresholds based on ATR - made less sensitive
            breakout_threshold = atr * 0.2  # Even more sensitive

            # Bullish/bearish breakout: close breaks beyond the moving average by
            # an ATR-scaled threshold. NOTE: the prior logic compared close to the
            # SAME bar's high/low (`close > max(high, sma_20)`), which can never be
            # true (close <= high, close >= low by definition), so this strategy
            # never produced a signal. Use sma_20 as the recent-range reference.
            bullish_breakout = close > sma_20 + breakout_threshold
            bearish_breakout = close < sma_20 - breakout_threshold

            # Volume confirmation (only if volume data available) - made less strict
            volume_confirmation = True
            if pd.notna(volume) and pd.notna(sma_volume):
                volume_confirmation = volume > sma_volume * 0.7  # Much less strict volume requirement

            # Regime: Less restrictive volatility conditions
            high_volatility = pd.isna(volatility_percentile) or volatility_percentile > 0.3  # Lower threshold

            # Multiple conditions to increase trade frequency
            if bullish_breakout and (volume_confirmation or high_volatility):
                return 1  # Buy
            elif bearish_breakout and (volume_confirmation or high_volatility):
                return -1  # Sell
            # Additional breakout vs the moving average (the prior `close > high`
            # / `close < low` checks compared within a single bar and never fired).
            elif close > sma_20 * 1.001:  # Simple price breakout above SMA
                return 1
            elif close < sma_20 * 0.999:  # Simple price breakdown below SMA
                return -1
            else:
                return 0  # Hold

        def momentum_strategy(row, params):
            """Regime-aware momentum strategy using rate of change and volume."""
            roc = row.get('roc_10', 0)  # Rate of change over 10 periods
            volume = row.get('volume', 0)
            sma_volume = row.get('sma_volume_20', 0)
            rsi = row.get('rsi', 50)
            atr = row.get('atr', 0)
            adx = row.get('adx', 20)  # ADX for trend strength
            volatility_regime = row.get('volatility_regime', 0)

            if pd.isna(roc):
                return 0

            # Volume confirmation (only if available) - made less strict
            volume_ok = True
            if pd.notna(volume) and pd.notna(sma_volume):
                volume_ok = volume > sma_volume * 0.5  # Much less strict volume requirement

            # Regime: Less restrictive trend conditions
            trending_market = pd.isna(adx) or adx > 15  # Lower threshold

            # More sensitive momentum thresholds
            if roc > 0.0005 and (volume_ok or trending_market) and (pd.isna(rsi) or 15 < rsi < 85):  # Less restrictive RSI
                return 1  # Buy
            elif roc < -0.0005 and (volume_ok or trending_market) and (pd.isna(rsi) or 15 < rsi < 85):  # Less restrictive RSI
                return -1  # Sell
            # Additional momentum conditions to increase trade frequency
            elif roc > 0.002:  # Strong momentum
                return 1
            elif roc < -0.002:  # Strong negative momentum
                return -1
            else:
                return 0  # Hold

        def scalping_strategy(row, params):
            """Regime-aware scalping strategy using short-term indicators."""
            rsi = row.get('rsi', 50)
            sma_fast = row.get('sma_5', 0)
            sma_slow = row.get('sma_10', 0)
            close = row.get('close', 0)
            roc = row.get('roc_10', 0)  # For momentum confirmation
            adx = row.get('adx', 20)  # ADX for trend strength
            volatility_regime = row.get('volatility_regime', 0)

            if any(pd.isna(x) for x in [rsi, sma_fast, sma_slow, close]):
                return 0

            # Fast MA crosses above slow MA with momentum confirmation - made less restrictive
            ma_bullish_cross = sma_fast > sma_slow * 0.999  # Very slight difference needed
            ma_bearish_cross = sma_fast < sma_slow * 1.001  # Very slight difference needed

            # Momentum confirmation - made less restrictive
            mom_bullish = pd.isna(roc) or roc > -0.0001  # Allow slightly negative momentum
            mom_bearish = pd.isna(roc) or roc < 0.0001  # Allow slightly positive momentum

            # Regime: Less restrictive volatility conditions
            high_volatility = pd.isna(volatility_regime) or volatility_regime > 0.001  # Much lower threshold

            # Multiple conditions to increase trade frequency
            if ma_bullish_cross and (mom_bullish or high_volatility) and 20 < rsi < 80:  # Wider RSI range
                return 1  # Buy
            elif ma_bearish_cross and (mom_bearish or high_volatility) and 20 < rsi < 80:  # Wider RSI range
                return -1  # Sell
            # Additional conditions to increase trade frequency
            elif sma_fast > sma_slow and rsi < 65:  # Simple MA cross without other conditions
                return 1
            elif sma_fast < sma_slow and rsi > 35:  # Simple MA cross without other conditions
                return -1
            else:
                return 0  # Hold

        def breakout_strategy(row, params):
            """Regime-aware breakout strategy identifying resistance/support breakouts."""
            high_20 = row.get('high_20', 0)  # 20-period high
            low_20 = row.get('low_20', 0)  # 20-period low
            close = row.get('close', 0)
            atr = row.get('atr', 0)
            volume = row.get('volume', 0)
            sma_volume = row.get('sma_volume_20', 0)
            adx = row.get('adx', 20)  # ADX for trend strength
            volatility_percentile = row.get('volatility_percentile', 0.5)  # Volatility regime

            if any(pd.isna(x) for x in [high_20, low_20, close, atr]):
                return 0

            # More sensitive breakout thresholds - made even more sensitive
            breakout_sensitivity = atr * 0.1  # Even more sensitive

            # Clear breakout above resistance with ATR confirmation
            bullish_breakout = close > high_20 + breakout_sensitivity
            bearish_breakout = close < low_20 - breakout_sensitivity

            # Volume confirmation (only if available) - made less strict
            volume_ok = True
            if pd.notna(volume) and pd.notna(sma_volume):
                volume_ok = volume > sma_volume * 0.5  # Much less strict volume requirement

            # Regime: Less restrictive volatility conditions
            high_volatility = pd.isna(volatility_percentile) or volatility_percentile > 0.2  # Lower threshold

            # Multiple conditions to increase trade frequency
            if bullish_breakout and (volume_ok or high_volatility):
                return 1  # Buy
            elif bearish_breakout and (volume_ok or high_volatility):
                return -1  # Sell
            # Additional breakout conditions
            elif close > high_20 * 1.0005:  # Simple breakout without ATR
                return 1
            elif close < low_20 * 0.9995:  # Simple breakdown without ATR
                return -1
            else:
                return 0  # Hold

        def liquidity_strategy(row, params):
            """Regime-aware liquidity-based strategy using volume and volatility."""
            volume = row.get('volume', 0)
            sma_volume = row.get('sma_volume_20', 0)
            atr = row.get('atr', 0)
            sma_atr = row.get('sma_atr_20', 0)
            rsi = row.get('rsi', 50)
            close = row.get('close', 0)
            adx = row.get('adx', 20)  # ADX for trend strength
            volatility_regime = row.get('volatility_regime', 0)

            if pd.isna(volume) or pd.isna(sma_volume):
                return 0

            # Calculate volume and volatility ratios
            volume_ratio = volume / sma_volume if sma_volume > 0 else 1
            vol_ratio = atr / sma_atr if pd.notna(atr) and pd.notna(sma_atr) and sma_atr > 0 else 1

            # Look for high volume and high volatility (liquidity events) - made less strict
            high_liquidity = volume_ratio > 1.1 and (pd.isna(vol_ratio) or vol_ratio > 0.8)  # Much less strict thresholds

            # Regime: Less restrictive market conditions
            trending_market = pd.isna(adx) or adx > 15  # Lower threshold

            # Multiple conditions to increase trade frequency
            if high_liquidity and pd.notna(rsi):
                # In oversold territory - potential buying opportunity
                if rsi < 45:  # More sensitive RSI, removed trending market requirement
                    return 1  # Buy
                # In overbought territory - potential selling opportunity
                elif rsi > 55:  # More sensitive RSI, removed trending market requirement
                    return -1  # Sell
                else:
                    return 0  # Hold in neutral zone
            elif high_liquidity:
                # If no RSI, use price action - if price is relatively low in recent range, buy
                return 1  # Default to buy in high liquidity situations if no other info
            # Additional conditions to increase trade frequency
            elif volume_ratio > 1.05:  # Lower volume threshold
                if rsi < 50:  # Buy when volume is high and RSI is low
                    return 1
                elif rsi > 50:  # Sell when volume is high and RSI is high
                    return -1
            else:
                return 0  # Hold if not high liquidity

        def mtf_trend_strategy(row, params):
            """Regime-aware multi-timeframe trend strategy combining different timeframes."""
            sma_20_short = row.get('sma_20_short', 0)  # Short-term trend
            sma_50_short = row.get('sma_50_short', 0)
            sma_20_long = row.get('sma_20_long', 0)  # Long-term trend
            sma_50_long = row.get('sma_50_long', 0)
            close = row.get('close', 0)
            roc_short = row.get('roc_10', 0)  # Short-term momentum
            adx = row.get('adx', 20)  # ADX for trend strength
            volatility_regime = row.get('volatility_regime', 0)

            if any(pd.isna(x) for x in [sma_20_short, sma_50_short, sma_20_long, sma_50_long, close]):
                return 0

            # Align trends across timeframes - made less strict
            short_trend_bullish = sma_20_short > sma_50_short * 0.999  # Much less strict
            long_trend_bullish = sma_20_long > sma_50_long * 0.999  # Much less strict

            # Momentum confirmation - made less strict
            mom_bullish = pd.isna(roc_short) or roc_short > -0.0001  # Allow slightly negative momentum
            mom_bearish = pd.isna(roc_short) or roc_short < 0.0001  # Allow slightly positive momentum

            # Regime: Less restrictive trend conditions
            strong_trend = pd.isna(adx) or adx > 15  # Lower threshold

            # Multiple conditions to increase trade frequency
            if (short_trend_bullish or long_trend_bullish) and (mom_bullish or strong_trend):
                return 1  # Buy
            elif (not short_trend_bullish or not long_trend_bullish) and (mom_bearish or strong_trend):
                return -1  # Sell
            # Additional conditions to increase trade frequency
            elif short_trend_bullish and close > sma_20_short:
                return 1
            elif not short_trend_bullish and close < sma_20_short:
                return -1
            else:
                return 0  # Hold

        def oi_footprint_strategy(row, params):
            """Regime-aware OI (Open Interest) footprint strategy - using volume/volatility as proxy."""
            # Using volume and volatility as proxies for open interest
            volume = row.get('volume', 0)
            sma_volume = row.get('sma_volume_20', 0)
            atr = row.get('atr', 0)
            sma_atr = row.get('sma_atr_20', 0)
            rsi = row.get('rsi', 50)
            roc = row.get('roc_10', 0)
            adx = row.get('adx', 20)  # ADX for trend strength
            volatility_regime = row.get('volatility_regime', 0)

            if pd.isna(volume) or pd.isna(sma_volume):
                return 0

            # Calculate volume and volatility ratios (proxy for OI changes) - made less strict
            volume_ratio = volume / sma_volume if sma_volume > 0 else 1
            vol_ratio = atr / sma_atr if pd.notna(atr) and pd.notna(sma_atr) and sma_atr > 0 else 1

            # High volume and high volatility often indicate institutional activity - made less strict
            oi_increasing = volume_ratio > 1.2 and (pd.isna(vol_ratio) or vol_ratio > 0.9)  # Much less strict thresholds

            # Regime: Less restrictive market conditions
            trending_market = pd.isna(adx) or adx > 15  # Lower threshold

            # Multiple conditions to increase trade frequency
            if oi_increasing and pd.notna(rsi):
                # If OI proxy is increasing and RSI is oversold - potential accumulation
                if rsi < 50:  # Broader range, removed other conditions
                    return 1  # Buy
                # If OI proxy is increasing and RSI is overbought - potential distribution
                elif rsi > 50:  # Broader range, removed other conditions
                    return -1  # Sell
                else:
                    return 0  # Hold
            # Additional conditions to increase trade frequency
            elif volume_ratio > 1.1:  # Lower threshold for volume spike
                if rsi < 45:  # Buy when volume is high and RSI is low
                    return 1
                elif rsi > 55:  # Sell when volume is high and RSI is high
                    return -1
            else:
                return 0  # Hold if no clear OI signal

        def sweep_scalper_strategy(row, params):
            """Regime-aware sweep scalper strategy targeting liquidity."""
            high = row.get('high', 0)
            low = row.get('low', 0)
            close = row.get('close', 0)
            volume = row.get('volume', 0)
            sma_volume = row.get('sma_volume_20', 0)
            high_5 = row.get('high_5', 0)
            low_5 = row.get('low_5', 0)
            atr = row.get('atr', 0)
            adx = row.get('adx', 20)  # ADX for trend strength
            volatility_regime = row.get('volatility_regime', 0)

            if any(pd.isna(x) for x in [high, low, close, volume, high_5, low_5]):
                return 0

            # Look for high volume near recent highs/lows (potential liquidity sweeps) - made less strict
            volume_spike = pd.notna(volume) and pd.notna(sma_volume) and volume > sma_volume * 1.05  # Much less strict threshold

            # Check if price is near recent extremes - made less strict
            near_high = high >= high_5 * 0.995  # Within 0.5% of 5-period high
            near_low = low <= low_5 * 1.005  # Within 0.5% of 5-period low

            # Check for potential sweep scenarios
            bullish_sweep = volume_spike and near_low and close > low  # Price moved away from low
            bearish_sweep = volume_spike and near_high and close < high  # Price moved away from high

            # Regime: Less restrictive volatility conditions
            high_volatility = pd.isna(volatility_regime) or volatility_regime > 0.001  # Much lower threshold

            # Multiple conditions to increase trade frequency
            if (bullish_sweep or volume_spike) and (high_volatility or close < low_5 * 0.999):  # Additional condition
                return 1  # Buy - potential bullish sweep completed
            elif (bearish_sweep or volume_spike) and (high_volatility or close > high_5 * 1.001):  # Additional condition
                return -1  # Sell - potential bearish sweep completed
            # Additional conditions to increase trade frequency
            elif volume_spike and close < (high_5 + low_5) / 2:  # Volume spike and price is in lower half
                return 1
            elif volume_spike and close > (high_5 + low_5) / 2:  # Volume spike and price is in upper half
                return -1
            else:
                return 0  # Hold

        def vwap_reversal_strategy(row, params):
            """Regime-aware VWAP reversal strategy."""
            close = row.get('close', 0)
            vwap = row.get('vwap', 0)
            rsi = row.get('rsi', 50)
            atr = row.get('atr', 0)
            adx = row.get('adx', 20)  # ADX for trend strength
            volatility_regime = row.get('volatility_regime', 0)

            if pd.isna(close) or pd.isna(vwap):
                return 0

            # Calculate distance from VWAP as percentage
            if vwap != 0:
                vwap_distance = (close - vwap) / vwap
            else:
                vwap_distance = 0

            # More sensitive thresholds for VWAP distance - made even more sensitive
            vwap_deviation_threshold = 0.001  # 0.1% - much more sensitive

            # Regime: Less restrictive ranging market conditions
            ranging_market = pd.isna(adx) or adx < 40  # Higher threshold allows more trading

            # Multiple conditions to increase trade frequency
            # Price above VWAP with overbought RSI - potential reversal down
            if vwap_distance > vwap_deviation_threshold and pd.notna(rsi) and rsi > 55:
                return -1  # Sell
            # Price below VWAP with oversold RSI - potential reversal up
            elif vwap_distance < -vwap_deviation_threshold and pd.notna(rsi) and rsi < 45:
                return 1  # Buy
            # Additional conditions to increase trade frequency
            elif vwap_distance > vwap_deviation_threshold * 2:  # Double threshold for stronger signal
                return -1  # Sell
            elif vwap_distance < -vwap_deviation_threshold * 2:  # Double threshold for stronger signal
                return 1  # Buy
            # Additional VWAP-based conditions without RSI
            elif vwap_distance > vwap_deviation_threshold and ranging_market:
                return -1  # Sell
            elif vwap_distance < -vwap_deviation_threshold and ranging_market:
                return 1  # Buy
            else:
                return 0  # Hold

        strategies = {
            'rsi_strategy': simple_rsi_strategy,
            'ma_crossover_strategy': simple_ma_crossover_strategy,
            'crypto_breakout': simple_rsi_strategy,  # Default fallback
            'trend_following': trend_following_strategy,
            'mean_reversion': mean_reversion_strategy,
            'volatility_breakout': volatility_breakout_strategy,
            'momentum': momentum_strategy,
            'scalping': scalping_strategy,
            'breakout': breakout_strategy,
            'liquidity': liquidity_strategy,
            'mtf_trend': mtf_trend_strategy,
            'oi_footprint': oi_footprint_strategy,
            'sweep_scalper': sweep_scalper_strategy,
            'vwap_reversal': vwap_reversal_strategy
        }

        return strategies.get(strategy_name, simple_rsi_strategy)


def wrap_strategy_with_execution_intent(strategy_func, strategy_name: str):
    """
    Wrap a strategy function to return ExecutionIntent objects instead of simple signals.

    Args:
        strategy_func: Original strategy function that returns -1, 0, or 1
        strategy_name: Name of the strategy

    Returns:
        Wrapped function that returns ExecutionIntent objects
    """
    def wrapped_strategy(row, params, timestamp=None):
        # Get the original signal - this could be a simple signal or already an ExecutionIntent
        result = strategy_func(row, params)

        # If the result is already an ExecutionIntent (from StrategyAdapter), return it directly
        if hasattr(result, 'is_valid') or (hasattr(result, 'side') and hasattr(result, 'strategy_name')):
            # This is already an ExecutionIntent from a StrategyAdapter, return as-is
            return result

        # If it's a simple signal (-1, 0, 1), convert to ExecutionIntent
        signal = result

        # If no signal, return None
        if signal == 0 or pd.isna(signal):
            return None

        # Create an ExecutionIntent based on the signal
        # This is a simplified approach - in a real implementation, you'd calculate position size
        # and risk parameters based on the strategy's assessment
        import uuid
        from datetime import datetime

        # Get timestamp from row if not provided
        if timestamp is None:
            if hasattr(row, 'name'):
                timestamp = row.name
            else:
                timestamp = datetime.now()

        # Determine side and calculate position size
        side = OrderSide.BUY if signal > 0 else OrderSide.SELL

        # Calculate position size based on risk management
        # This is a simplified approach - in practice, strategies would return more detailed information
        price = row.get('close', 0)
        if price <= 0:
            return None  # Invalid price

        # Use a fixed percentage of capital for position sizing (can be made configurable)
        risk_pct = params.get('risk_per_trade', 0.02)  # 2% risk per trade
        position_size = (params.get('capital', 10000) * risk_pct) / price

        # Calculate stop loss and take profit based on ATR or other methods
        atr = row.get('atr', 0.01 * price)  # Default to 1% if no ATR
        atr_multiplier = params.get('atr_multiplier', 1.5)
        risk_reward_ratio = params.get('risk_reward_ratio', 1.5)

        sl_distance = atr_multiplier * atr
        tp_distance = sl_distance * risk_reward_ratio

        sl_price = None
        tp_price = None

        if signal > 0:  # Buy signal
            sl_price = price - sl_distance
            tp_price = price + tp_distance
        else:  # Sell signal
            sl_price = price + sl_distance
            tp_price = price - tp_distance

        # Create and return the ExecutionIntent
        intent = create_execution_intent(
            side=side,
            size=position_size,
            price=price,
            timestamp=timestamp,
            stop_loss=sl_price,
            take_profit=tp_price,
            strategy_name=strategy_name,
            symbol=params.get('symbol', 'BTCUSDT'),
            intent_id=f"{strategy_name}_{uuid.uuid4().hex[:8]}"
        )

        return intent

    return wrapped_strategy


class BacktestStrategyProvider:
    """Port adapter that yields execution-intent-wrapped strategy functions."""

    def get_strategy(self, strategy_name: str):
        base_strategy = load_sample_strategy(strategy_name)
        return wrap_strategy_with_execution_intent(base_strategy, strategy_name)
