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
        atr_sl_multiplier = 2.2
        min_stop_distance_percent = 0.012  # 1.2%
        min_reward_risk_ratio = 1.5
        enable_dynamic_tp = True
        reject_low_rr_setup = True

        if config:
            atr_period = int(config.get('atr_period', 14))
            atr_sl_multiplier = float(config.get('atr_sl_multiplier', 2.2))
            min_stop_distance_percent = float(config.get('min_stop_distance_percent', 1.2)) / 100.0
            min_reward_risk_ratio = float(config.get('min_reward_risk_ratio', 1.5))
            enable_dynamic_tp = bool(config.get('enable_dynamic_tp', True))
            reject_low_rr_setup = bool(config.get('reject_low_rr_setup', True))

        setups = []
        n = len(prices)
        if n < 5:
            return setups

        current_price = prices[-1]
        ts = ExchangeTimestamp(int(datetime.now().timestamp() * 1000))

        # Extract latest open price for candle body analysis
        open_price = current_price
        if data_buffer and len(data_buffer) > 0 and isinstance(data_buffer[-1], dict):
            open_price = float(data_buffer[-1].get('open', current_price))

        # Compute trend momentum alignment over 20 bars
        is_bull_trend = False
        is_bear_trend = False
        if n >= 20:
            sma_short = sum(prices[-10:]) / 10.0
            sma_med = sum(prices[-20:]) / 20.0
            if sma_short > sma_med * 1.002:
                is_bull_trend = True
            elif sma_short < sma_med * 0.998:
                is_bear_trend = True

        # Calculate ATR dynamically for all setup types
        atr = (min_stop_distance_percent / atr_sl_multiplier) * current_price
        if len(prices) >= atr_period + 1 and highs and lows and len(highs) == len(prices) and len(lows) == len(prices):
            tr_list = []
            for i in range(1, len(prices)):
                tr = max(highs[i] - lows[i], 
                         abs(highs[i] - prices[i-1]), 
                         abs(lows[i] - prices[i-1]))
                tr_list.append(tr)
            lookback = min(atr_period, len(tr_list))
            if lookback > 0:
                atr = sum(tr_list[-lookback:]) / lookback

        # Compute VWAP and Standard Deviation over 20 bars if volume available
        vwap = 0.0
        vwap_std = 0.0
        if n >= 10:
            vol_list = []
            if data_buffer and len(data_buffer) >= n:
                vol_list = [float(item.get('volume', 1.0)) for item in data_buffer[-n:]]
            else:
                vol_list = [1.0] * n
            
            total_vol = sum(vol_list[-20:])
            if total_vol > 0:
                typical_prices = [(highs[i] + lows[i] + prices[i]) / 3.0 for i in range(len(prices)-min(20, n), len(prices))]
                vols = vol_list[-len(typical_prices):]
                vwap = sum(typical_prices[i] * vols[i] for i in range(len(vols))) / total_vol
                var = sum(vols[i] * ((typical_prices[i] - vwap) ** 2) for i in range(len(vols))) / total_vol
                vwap_std = (var ** 0.5) if var > 0 else 0.0

        # 1. NGLS Sweep Setup detection (Liquidity Sweeps with Market Structure Confirmation)
        if n >= 21:
            prev_low_20 = min(lows[-21:-1])
            prev_high_20 = max(highs[-21:-1])

            # Bullish sweep: Wicks below 20-bar low and rejects back up with MSS confirmation
            if lows[-1] < prev_low_20 and current_price > prev_low_20:
                # 1. Price action confirmation: Green close OR long lower absorption wick (>= 25% of range)
                candle_range = highs[-1] - lows[-1]
                lower_wick = min(open_price, current_price) - lows[-1]
                is_rejection = (current_price >= open_price) or (candle_range > 0 and (lower_wick / candle_range) >= 0.25)
                
                # 2. Market Structure Shift (MSS) / CHoCH confirmation (close above previous bar midpoint)
                prev_mid = (highs[-2] + lows[-2]) / 2.0
                is_mss = current_price >= prev_mid

                # 3. Avoid buying in strong downward breakdown or bear trend
                is_breakdown = is_bear_trend or (val > 0 and current_price < val * 0.995)

                if is_rejection and is_mss and not is_breakdown:
                    sl_structural = lows[-1] - atr_sl_multiplier * atr
                    sl_limit = current_price * (1.0 - min_stop_distance_percent)
                    sl = max(0.0001, min(sl_structural, sl_limit)) if sl_structural > 0 else sl_limit

                    tp_structural = prev_high_20
                    if enable_dynamic_tp:
                        tp_min = current_price + min_reward_risk_ratio * (current_price - sl)
                        tp = max(tp_structural, tp_min)
                    else:
                        tp = max(tp_structural, current_price + min_reward_risk_ratio * (current_price - sl))

                    # Strict Reward/Risk gating:
                    if not hasattr(self, 'rejected_low_rr_count'):
                        self.rejected_low_rr_count = {}
                    rr_ratio = abs(tp - current_price) / abs(current_price - sl) if abs(current_price - sl) > 0 else 0.0
                    if not reject_low_rr_setup or rr_ratio >= (min_reward_risk_ratio - 1e-6):
                        setups.append(CandidateSetup(
                            symbol=symbol,
                            timestamp=ts,
                            setup_type="NGLS_SWEEP",
                            direction="BUY",
                            trigger_price=Decimal(str(current_price)),
                            stop_loss_level=Decimal(str(sl)),
                            take_profit_level=Decimal(str(tp))
                        ))
                    else:
                        self.rejected_low_rr_count[str(symbol)] = self.rejected_low_rr_count.get(str(symbol), 0) + 1
            # Bearish sweep: Wicks above 20-bar high and rejects back down with MSS confirmation
            elif highs[-1] > prev_high_20 and current_price < prev_high_20:
                # 1. Price action confirmation: Red close OR long upper rejection wick (>= 25% of range)
                candle_range = highs[-1] - lows[-1]
                upper_wick = highs[-1] - max(open_price, current_price)
                is_rejection = (current_price <= open_price) or (candle_range > 0 and (upper_wick / candle_range) >= 0.25)
                
                # 2. Market Structure Shift (MSS) / CHoCH confirmation (close below previous bar midpoint)
                prev_mid = (highs[-2] + lows[-2]) / 2.0
                is_mss = current_price <= prev_mid

                # 3. Avoid shorting in strong upward breakout above VAH or strong bull trend
                is_breakout = is_bull_trend or (vah > 0 and current_price > vah * 1.005)

                if is_rejection and is_mss and not is_breakout:
                    sl_structural = highs[-1] + atr_sl_multiplier * atr
                    sl_limit = current_price * (1.0 + min_stop_distance_percent)
                    sl = max(sl_structural, sl_limit)

                    tp_structural = prev_low_20
                    if enable_dynamic_tp:
                        tp_max = current_price - min_reward_risk_ratio * (sl - current_price)
                        tp = max(0.0, min(tp_structural, tp_max))
                    else:
                        tp = max(0.0, current_price - max(abs(current_price - tp_structural), min_reward_risk_ratio * (sl - current_price)))

                    # Strict Reward/Risk gating:
                    if not hasattr(self, 'rejected_low_rr_count'):
                        self.rejected_low_rr_count = {}
                    rr_ratio = abs(current_price - tp) / abs(sl - current_price) if abs(sl - current_price) > 0 else 0.0
                    if not reject_low_rr_setup or rr_ratio >= (min_reward_risk_ratio - 1e-6):
                        setups.append(CandidateSetup(
                            symbol=symbol,
                            timestamp=ts,
                            setup_type="NGLS_SWEEP",
                            direction="SELL",
                            trigger_price=Decimal(str(current_price)),
                            stop_loss_level=Decimal(str(sl)),
                            take_profit_level=Decimal(str(tp))
                        ))
                    else:
                        self.rejected_low_rr_count[str(symbol)] = self.rejected_low_rr_count.get(str(symbol), 0) + 1

        # 2. NGMR Reversion Setup detection (Value Area & VWAP 2.5σ Extreme Deviation)
        threshold = 0.0015 * current_price  # 0.15% threshold buffer around Value Area boundaries
        is_val_touch = val > 0 and abs(current_price - val) < threshold
        is_vwap_oversold = vwap > 0 and vwap_std > 0 and current_price <= (vwap - 2.5 * vwap_std)
        is_vah_touch = vah > 0 and abs(current_price - vah) < threshold
        is_vwap_overbought = vwap > 0 and vwap_std > 0 and current_price >= (vwap + 2.5 * vwap_std)

        if is_val_touch or is_vwap_oversold or is_vah_touch or is_vwap_overbought:
            candle_range = highs[-1] - lows[-1]
            if is_val_touch or is_vwap_oversold:
                # Buy reversion to POC/VWAP/VAH: Require bounce/rejection and strictly avoid breakdown below VAL in bear trend
                lower_wick = min(open_price, current_price) - lows[-1]
                is_rejection = (current_price >= open_price) or (candle_range > 0 and (lower_wick / candle_range) >= 0.25)
                is_breakdown = is_bear_trend and val > 0 and current_price < val * 0.995

                target_poc = poc if poc > current_price else (vwap if vwap > current_price else (vah if vah > current_price else current_price * 1.01))
                if is_rejection and not is_breakdown and target_poc > current_price:
                    # Hybrid SL: Structural invalidation below VAL/low + Volatility buffer + Min stop distance floor
                    ref_low = min(val, lows[-1]) if val > 0 else lows[-1]
                    sl_structural = ref_low - atr_sl_multiplier * atr
                    sl_limit = current_price * (1.0 - min_stop_distance_percent)
                    sl = min(sl_structural, sl_limit)

                    tp_structural = target_poc
                    if enable_dynamic_tp:
                        tp_min = current_price + min_reward_risk_ratio * (current_price - sl)
                        tp = max(tp_structural, tp_min)
                    else:
                        tp = tp_structural

                    # Strict Reward/Risk gating:
                    if not hasattr(self, 'rejected_low_rr_count'):
                        self.rejected_low_rr_count = {}
                    rr_ratio = abs(tp - current_price) / abs(current_price - sl) if abs(current_price - sl) > 0 else 0.0
                    if not reject_low_rr_setup or rr_ratio >= (min_reward_risk_ratio - 1e-6):
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
            elif is_vah_touch or is_vwap_overbought:
                # Sell reversion to POC/VWAP/VAL: Require rejection from VAH/VWAP+2.5σ and strictly avoid breakout above VAH in bull trend
                upper_wick = highs[-1] - max(open_price, current_price)
                is_rejection = (current_price <= open_price) or (candle_range > 0 and (upper_wick / candle_range) >= 0.25)
                is_breakout = is_bull_trend and vah > 0 and current_price > vah * 1.005

                target_poc = poc if (0 < poc < current_price) else (vwap if (0 < vwap < current_price) else (val if (0 < val < current_price) else current_price * 0.99))
                if is_rejection and not is_breakout and target_poc < current_price:
                    # Hybrid SL: Structural invalidation above VAH/high + Volatility buffer + Min stop distance floor
                    ref_high = max(vah, highs[-1]) if vah > 0 else highs[-1]
                    sl_structural = ref_high + atr_sl_multiplier * atr
                    sl_limit = current_price * (1.0 + min_stop_distance_percent)
                    sl = max(sl_structural, sl_limit)

                    tp_structural = target_poc
                    if enable_dynamic_tp:
                        tp_max = current_price - min_reward_risk_ratio * (sl - current_price)
                        tp = max(0.0, min(tp_structural, tp_max))
                    else:
                        tp = tp_structural

                    # Strict Reward/Risk gating:
                    if not hasattr(self, 'rejected_low_rr_count'):
                        self.rejected_low_rr_count = {}
                    rr_ratio = abs(current_price - tp) / abs(sl - current_price) if abs(sl - current_price) > 0 else 0.0
                    if not reject_low_rr_setup or rr_ratio >= (min_reward_risk_ratio - 1e-6):
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

        # 3. NGTREND_FOLLOW Setup detection (Multi-Timeframe Trend Following with Retest Alignment)
        if vah > 0 and current_price > vah and is_bull_trend:
            # Bullish trend following with momentum confirmation and overextension limit (max +6.0% from VAH)
            is_not_overextended = current_price <= vah * 1.060
            is_momentum_green = current_price >= open_price or (candle_range > 0 and (lower_wick / candle_range) >= 0.20) if 'lower_wick' in locals() else (current_price >= open_price)

            if is_not_overextended and is_momentum_green:
                sl_structural = val if (0 < val < current_price and val >= current_price * 0.90) else (current_price - atr_sl_multiplier * atr)
                sl_limit = current_price * (1.0 - min_stop_distance_percent)
                sl = min(sl_structural, sl_limit)
                tp = current_price + min_reward_risk_ratio * (current_price - sl)
                setups.append(CandidateSetup(
                    symbol=symbol,
                    timestamp=ts,
                    setup_type="NGTREND_FOLLOW",
                    direction="BUY",
                    trigger_price=Decimal(str(current_price)),
                    stop_loss_level=Decimal(str(sl)),
                    take_profit_level=Decimal(str(tp))
                ))
        elif val > 0 and current_price < val and is_bear_trend:
            # Bearish trend following with momentum confirmation and overextension limit (max -6.0% from VAL)
            is_not_overextended = current_price >= val * 0.940
            is_momentum_red = current_price <= open_price or (candle_range > 0 and (upper_wick / candle_range) >= 0.20) if 'upper_wick' in locals() else (current_price <= open_price)

            if is_not_overextended and is_momentum_red:
                sl_structural = vah if (vah > current_price and vah <= current_price * 1.10) else (current_price + atr_sl_multiplier * atr)
                sl_limit = current_price * (1.0 + min_stop_distance_percent)
                sl = max(sl_structural, sl_limit)
                tp = max(0.0, current_price - min_reward_risk_ratio * (sl - current_price))
                setups.append(CandidateSetup(
                    symbol=symbol,
                    timestamp=ts,
                    setup_type="NGTREND_FOLLOW",
                    direction="SELL",
                    trigger_price=Decimal(str(current_price)),
                    stop_loss_level=Decimal(str(sl)),
                    take_profit_level=Decimal(str(tp))
                ))

        # 4. NGBREAKOUT Setup detection (consolidation range compression with volume expansion)
        if n >= 22:
            recent_highs = highs[-11:-1]
            recent_lows = lows[-11:-1]
            recent_range = max(recent_highs) - min(recent_lows) if recent_highs and recent_lows else 0.0

            historical_highs = highs[-21:-1]
            historical_lows = lows[-21:-1]
            historical_range = max(historical_highs) - min(historical_lows) if historical_highs and historical_lows else 0.0

            # Volume surge confirmation if volume is tracked and non-uniform in data_buffer
            has_volume_surge = True
            if 'vol_list' in locals() and len(vol_list) >= 21:
                min_v = min(vol_list[-21:])
                max_v = max(vol_list[-21:])
                if max_v > min_v:
                    avg_prior_vol = sum(vol_list[-21:-1]) / 20.0
                    if avg_prior_vol > 0:
                        has_volume_surge = vol_list[-1] >= avg_prior_vol * 1.05

            compression_ratio = historical_range / recent_range if recent_range > 0 else 0.0
            if compression_ratio > 1.5 and recent_range > 0 and has_volume_surge:
                range_high = max(recent_highs)
                range_low = min(recent_lows)
                breakout_threshold = 0.001

                if current_price > range_high * (1 + breakout_threshold):
                    sl_structural = range_low
                    sl_limit = current_price * (1.0 - min_stop_distance_percent)
                    sl = min(sl_structural, sl_limit)
                    tp = current_price + max(2.0 * atr, min_reward_risk_ratio * (current_price - sl))
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
                    sl_structural = range_high
                    sl_limit = current_price * (1.0 + min_stop_distance_percent)
                    sl = max(sl_structural, sl_limit)
                    tp = max(0.0, current_price - max(2.0 * atr, min_reward_risk_ratio * (sl - current_price)))
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

        # Sanitize SL/TP levels to guarantee validity relative to trigger_price
        from shared.utils import sanitize_sltp_levels
        for s in setups:
            try:
                trig = float(s.trigger_price)
                sl, tp = sanitize_sltp_levels(
                    entry_price=trig,
                    side=s.direction,
                    stop_loss=float(s.stop_loss_level),
                    take_profit=float(s.take_profit_level)
                )
                s.stop_loss_level = Decimal(str(sl))
                s.take_profit_level = Decimal(str(tp))
            except Exception:
                pass

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
