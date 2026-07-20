"""15m Setup Engine for detecting sweeps and value area reversions."""

from typing import List, Optional, Dict, Any
from decimal import Decimal
from datetime import datetime
from domain.value_objects import Symbol, ExchangeTimestamp
from domain.entities.research import CandidateSetup


class SetupEngine:
    """
    15m Setup Engine.
    Identifies NGLS sweeps or NGMR reversions and generates CandidateSetup objects.
    """

    def scan_for_setups(self, symbol: Symbol, prices: List[float], highs: List[float],
                         lows: List[float], val: float, vah: float, poc: float,
                         data_buffer: Optional[List[Dict[str, Any]]] = None,
                         config: Optional[Dict[str, Any]] = None) -> List[CandidateSetup]:
        """
        Scan prices for sweeps and reversions, returning any triggered setup objects.
        """
        # Resolve config parameters (Phase 11 Configurable Model)
        atr_period = 14
        atr_sl_multiplier = 1.5
        min_stop_distance_percent = 0.008  # 0.8%
        min_reward_risk_ratio = 1.5
        enable_dynamic_tp = True
        reject_low_rr_setup = True

        if config:
            atr_period = int(config.get('atr_period', 14))
            atr_sl_multiplier = float(config.get('atr_sl_multiplier', 1.5))
            min_stop_distance_percent = float(config.get('min_stop_distance_percent', 0.8)) / 100.0
            min_reward_risk_ratio = float(config.get('min_reward_risk_ratio', 1.5))
            enable_dynamic_tp = bool(config.get('enable_dynamic_tp', True))
            reject_low_rr_setup = bool(config.get('reject_low_rr_setup', True))

        setups = []
        n = len(prices)
        if n < 5:
            return setups

        current_price = prices[-1]
        ts = ExchangeTimestamp(int(datetime.now().timestamp() * 1000))

        # 1. NGLS Sweep Setup detection
        if n >= 21:
            prev_low_20 = min(lows[-21:-1])
            prev_high_20 = max(highs[-21:-1])

            # Bullish sweep
            if lows[-1] < prev_low_20 and current_price > prev_low_20:
                sl = lows[-1] - 0.001 * current_price
                tp = prev_high_20
                setups.append(CandidateSetup(
                    symbol=symbol,
                    timestamp=ts,
                    setup_type="NGLS_SWEEP",
                    direction="BUY",
                    trigger_price=Decimal(str(current_price)),
                    stop_loss_level=Decimal(str(sl)),
                    take_profit_level=Decimal(str(tp))
                ))
            # Bearish sweep
            elif highs[-1] > prev_high_20 and current_price < prev_high_20:
                sl = highs[-1] + 0.001 * current_price
                tp = prev_low_20
                setups.append(CandidateSetup(
                    symbol=symbol,
                    timestamp=ts,
                    setup_type="NGLS_SWEEP",
                    direction="SELL",
                    trigger_price=Decimal(str(current_price)),
                    stop_loss_level=Decimal(str(sl)),
                    take_profit_level=Decimal(str(tp))
                ))

        # 2. NGMR Reversion Setup detection
        threshold = 0.0005 * current_price  # 0.05% threshold
        if abs(current_price - val) < threshold or abs(current_price - vah) < threshold:
            # Calculate ATR dynamically
            atr = (min_stop_distance_percent / atr_sl_multiplier) * current_price
            if len(prices) >= atr_period + 1:
                tr_list = []
                for i in range(1, len(prices)):
                    tr = max(highs[i] - lows[i], 
                             abs(highs[i] - prices[i-1]), 
                             abs(lows[i] - prices[i-1]))
                    tr_list.append(tr)
                lookback = min(atr_period, len(tr_list))
                if lookback > 0:
                    atr = sum(tr_list[-lookback:]) / lookback

            if abs(current_price - val) < threshold:
                # Buy reversion to POC
                # Hybrid SL/TP (Option C): Structural invalidation + Volatility buffer + Min stop distance floor
                sl_structural = val - atr_sl_multiplier * atr
                sl_limit = current_price * (1.0 - min_stop_distance_percent)
                sl = min(sl_structural, sl_limit)
                
                # Take profit:
                tp_structural = poc
                if enable_dynamic_tp:
                    tp_min = current_price + min_reward_risk_ratio * (current_price - sl)
                    tp = max(tp_structural, tp_min)
                else:
                    tp = tp_structural

                # Reward/Risk checking:
                if not hasattr(self, 'rejected_low_rr_count'):
                    self.rejected_low_rr_count = {}
                rr_ratio = abs(tp - current_price) / abs(current_price - sl) if abs(current_price - sl) > 0 else 0.0
                if not reject_low_rr_setup or rr_ratio >= min_reward_risk_ratio:
                    setups.append(CandidateSetup(
                        symbol=symbol,
                        timestamp=ts,
                        setup_type="NGMR_REVERSION",
                        direction="BUY",
                        trigger_price=Decimal(str(current_price)),
                        stop_loss_level=Decimal(str(sl)),
                        take_profit_level=Decimal(str(tp))
                    ))
                else:
                    self.rejected_low_rr_count[str(symbol)] = self.rejected_low_rr_count.get(str(symbol), 0) + 1
            elif abs(current_price - vah) < threshold:
                # Sell reversion to POC
                # Hybrid SL/TP (Option C): Structural invalidation + Volatility buffer + Min stop distance floor
                sl_structural = vah + atr_sl_multiplier * atr
                sl_limit = current_price * (1.0 + min_stop_distance_percent)
                sl = max(sl_structural, sl_limit)
                
                # Take profit:
                tp_structural = poc
                if enable_dynamic_tp:
                    tp_max = current_price - min_reward_risk_ratio * (sl - current_price)
                    tp = max(0.0, min(tp_structural, tp_max))
                else:
                    tp = tp_structural

                # Reward/Risk checking:
                if not hasattr(self, 'rejected_low_rr_count'):
                    self.rejected_low_rr_count = {}
                rr_ratio = abs(current_price - tp) / abs(sl - current_price) if abs(sl - current_price) > 0 else 0.0
                if not reject_low_rr_setup or rr_ratio >= min_reward_risk_ratio:
                    setups.append(CandidateSetup(
                        symbol=symbol,
                        timestamp=ts,
                        setup_type="NGMR_REVERSION",
                        direction="SELL",
                        trigger_price=Decimal(str(current_price)),
                        stop_loss_level=Decimal(str(sl)),
                        take_profit_level=Decimal(str(tp))
                    ))
                else:
                    self.rejected_low_rr_count[str(symbol)] = self.rejected_low_rr_count.get(str(symbol), 0) + 1

        # 3. NGTREND_FOLLOW Setup detection
        if current_price > vah:
            # Bullish trend following
            sl = val if val > 0 else current_price - 0.01 * current_price
            tp = current_price + 0.01 * current_price
            setups.append(CandidateSetup(
                symbol=symbol,
                timestamp=ts,
                setup_type="NGTREND_FOLLOW",
                direction="BUY",
                trigger_price=Decimal(str(current_price)),
                stop_loss_level=Decimal(str(sl)),
                take_profit_level=Decimal(str(tp))
            ))
        elif current_price < val:
            # Bearish trend following
            sl = vah if vah > 0 else current_price + 0.01 * current_price
            tp = current_price - 0.01 * current_price
            setups.append(CandidateSetup(
                symbol=symbol,
                timestamp=ts,
                setup_type="NGTREND_FOLLOW",
                direction="SELL",
                trigger_price=Decimal(str(current_price)),
                stop_loss_level=Decimal(str(sl)),
                take_profit_level=Decimal(str(tp))
            ))

        # 4. NGBREAKOUT Setup detection (consolidation range compression breakout)
        if n >= 22:
            recent_highs = highs[-11:-1]
            recent_lows = lows[-11:-1]
            recent_range = max(recent_highs) - min(recent_lows) if recent_highs and recent_lows else 0.0

            historical_highs = highs[-21:-1]
            historical_lows = lows[-21:-1]
            historical_range = max(historical_highs) - min(historical_lows) if historical_highs and historical_lows else 0.0

            compression_ratio = historical_range / recent_range if recent_range > 0 else 0.0
            if compression_ratio > 1.5 and recent_range > 0:
                range_high = max(recent_highs)
                range_low = min(recent_lows)
                breakout_threshold = 0.001

                if current_price > range_high * (1 + breakout_threshold):
                    sl = range_low
                    tp = current_price + 0.02 * current_price
                    setups.append(CandidateSetup(
                        symbol=symbol,
                        timestamp=ts,
                        setup_type="NGBREAKOUT",
                        direction="BUY",
                        trigger_price=Decimal(str(current_price)),
                        stop_loss_level=Decimal(str(sl)),
                        take_profit_level=Decimal(str(tp))
                    ))
                elif current_price < range_low * (1 - breakout_threshold):
                    sl = range_high
                    tp = current_price - 0.02 * current_price
                    setups.append(CandidateSetup(
                        symbol=symbol,
                        timestamp=ts,
                        setup_type="NGBREAKOUT",
                        direction="SELL",
                        trigger_price=Decimal(str(current_price)),
                        stop_loss_level=Decimal(str(sl)),
                        take_profit_level=Decimal(str(tp))
                    ))

        # 5. NGDONCHIAN_BREAKOUT Setup detection (prior N-bar channel break under expanding volatility)
        if n >= 125:
            prior_high = max(highs[-21:-1])
            prior_low = min(lows[-21:-1])

            # Calculate True Ranges
            tr_list = []
            for i in range(1, n):
                tr_list.append(max(
                    highs[i] - lows[i],
                    abs(highs[i] - prices[i - 1]),
                    abs(lows[i] - prices[i - 1])
                ))
            
            # ATR over atr_window = 14
            atr = sum(tr_list[-14:]) / 14.0
            
            # Median ATR over atr_med_window = 100
            import numpy as np
            atr_med = float(np.median(tr_list[-100:]))
            expanding = atr_med > 0 and atr > 1.1 * atr_med

            if expanding:
                if current_price > prior_high:
                    sl = prior_low
                    tp = current_price + 0.02 * current_price
                    setups.append(CandidateSetup(
                        symbol=symbol,
                        timestamp=ts,
                        setup_type="NGDONCHIAN_BREAKOUT",
                        direction="BUY",
                        trigger_price=Decimal(str(current_price)),
                        stop_loss_level=Decimal(str(sl)),
                        take_profit_level=Decimal(str(tp))
                    ))
                elif current_price < prior_low:
                    sl = prior_high
                    tp = current_price - 0.02 * current_price
                    setups.append(CandidateSetup(
                        symbol=symbol,
                        timestamp=ts,
                        setup_type="NGDONCHIAN_BREAKOUT",
                        direction="SELL",
                        trigger_price=Decimal(str(current_price)),
                        stop_loss_level=Decimal(str(sl)),
                        take_profit_level=Decimal(str(tp))
                    ))

        # 6. NGVOLATILITY_BREAKOUT Setup detection (ATR expansion breakout)
        if n >= 35:
            atr_val = self._calculate_atr(highs, lows, prices, period=14)
            if atr_val > 0:
                prior_high = max(highs[-21:-1])
                prior_low = min(lows[-21:-1])

                up_break = current_price - prior_high
                dn_break = prior_low - current_price
                
                if up_break > 1.5 * atr_val:
                    sl = prior_low
                    tp = current_price + 0.02 * current_price
                    setups.append(CandidateSetup(
                        symbol=symbol,
                        timestamp=ts,
                        setup_type="NGVOLATILITY_BREAKOUT",
                        direction="BUY",
                        trigger_price=Decimal(str(current_price)),
                        stop_loss_level=Decimal(str(sl)),
                        take_profit_level=Decimal(str(tp))
                    ))
                elif dn_break > 1.5 * atr_val:
                    sl = prior_high
                    tp = current_price - 0.02 * current_price
                    setups.append(CandidateSetup(
                        symbol=symbol,
                        timestamp=ts,
                        setup_type="NGVOLATILITY_BREAKOUT",
                        direction="SELL",
                        trigger_price=Decimal(str(current_price)),
                        stop_loss_level=Decimal(str(sl)),
                        take_profit_level=Decimal(str(tp))
                    ))

        # 7. NGOI_SETUP Setup detection (Open Interest divergence with Volume/RSI fallback)
        if n >= 25 and data_buffer is not None:
            closes = prices
            current_volume = float(data_buffer[-1].get('volume', 0.0))
            volumes = [float(item.get('volume', 0.0)) for item in data_buffer]
            avg_volume = sum(volumes[-20:]) / 20.0 if len(volumes) >= 20 else sum(volumes) / len(volumes)
            volume_spike = current_volume > avg_volume * 1.5 if avg_volume > 0 else False

            momentum_period = min(5, len(closes) - 1)
            price_momentum = (current_price - closes[-momentum_period - 1]) / closes[-momentum_period - 1] if momentum_period > 0 else 0.0

            # Check for real Open Interest
            oi_list = [float(item.get("open_interest", item.get("oi", 0.0))) for item in data_buffer]
            has_real_oi = any(val > 0.0 for val in oi_list)

            if has_real_oi:
                # Genuine OI hypothesis: OI change over last 5 bars
                oi_change = (oi_list[-1] - oi_list[-5]) / oi_list[-5] if len(oi_list) >= 5 and oi_list[-5] > 0 else 0.0
                # Rising price + falling OI = BUY (Short Squeeze)
                # Falling price + falling OI = SELL (Long Liquidation)
                if price_momentum > 0 and oi_change < -0.02:
                    sl = current_price - 0.01 * current_price
                    tp = current_price + 0.02 * current_price
                    setups.append(CandidateSetup(
                        symbol=symbol,
                        timestamp=ts,
                        setup_type="NGOI_SETUP",
                        direction="BUY",
                        trigger_price=Decimal(str(current_price)),
                        stop_loss_level=Decimal(str(sl)),
                        take_profit_level=Decimal(str(tp))
                    ))
                elif price_momentum < 0 and oi_change < -0.02:
                    sl = current_price + 0.01 * current_price
                    tp = current_price - 0.02 * current_price
                    setups.append(CandidateSetup(
                        symbol=symbol,
                        timestamp=ts,
                        setup_type="NGOI_SETUP",
                        direction="SELL",
                        trigger_price=Decimal(str(current_price)),
                        stop_loss_level=Decimal(str(sl)),
                        take_profit_level=Decimal(str(tp))
                    ))
            else:
                # Incomplete / proxy fallback (Volume Spike + RSI)
                computed_rsi = self._calculate_rsi(closes, 14)
                
                is_buy = False
                is_sell = False

                if volume_spike and price_momentum > 0 and (not computed_rsi or computed_rsi < 75):
                    is_buy = True
                elif volume_spike and price_momentum < 0 and (not computed_rsi or computed_rsi > 25):
                    is_sell = True
                elif volume_spike and computed_rsi and computed_rsi < 30 and price_momentum > 0:
                    is_buy = True
                elif volume_spike and computed_rsi and computed_rsi > 70 and price_momentum < 0:
                    is_sell = True

                if is_buy:
                    sl = current_price - 0.01 * current_price
                    tp = current_price + 0.02 * current_price
                    setups.append(CandidateSetup(
                        symbol=symbol,
                        timestamp=ts,
                        setup_type="NGOI_SETUP",
                        direction="BUY",
                        trigger_price=Decimal(str(current_price)),
                        stop_loss_level=Decimal(str(sl)),
                        take_profit_level=Decimal(str(tp))
                    ))
                elif is_sell:
                    sl = current_price + 0.01 * current_price
                    tp = current_price - 0.02 * current_price
                    setups.append(CandidateSetup(
                        symbol=symbol,
                        timestamp=ts,
                        setup_type="NGOI_SETUP",
                        direction="SELL",
                        trigger_price=Decimal(str(current_price)),
                        stop_loss_level=Decimal(str(sl)),
                        take_profit_level=Decimal(str(tp))
                    ))

        return setups

    def _calculate_atr(self, highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> float:
        n = len(closes)
        if n < period + 1:
            return 0.0
        tr_list = []
        for i in range(1, n):
            h_l = highs[i] - lows[i]
            h_pc = abs(highs[i] - closes[i - 1])
            l_pc = abs(lows[i] - closes[i - 1])
            tr_list.append(max(h_l, h_pc, l_pc))
        
        return sum(tr_list[-period:]) / period

    def _calculate_rsi(self, prices: List[float], period: int = 14) -> Optional[float]:
        if len(prices) < period + 1:
            return None
        import numpy as np
        deltas = np.diff(np.asarray(prices, dtype=float))
        gains = np.clip(deltas, 0, None)[-period:]
        losses = (-np.clip(deltas, None, 0))[-period:]
        avg_loss = float(losses.mean())
        if avg_loss == 0:
            return 100.0
        rs = float(gains.mean()) / avg_loss
        return float(100 - (100 / (1 + rs)))
