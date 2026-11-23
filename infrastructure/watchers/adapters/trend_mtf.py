from .base_watcher import BaseWatcher
from domain.entities import MarketObservation
from domain.value_objects import Symbol, Percentage
from shared.logger import logger
import numpy as np
from decimal import Decimal
from infrastructure.logging.forensic_logger import forensic_logger
from infrastructure.messaging.clock import LiveClock
from shared.config_helper import cfg_get, cfg_get_bool, cfg_get_int, cfg_get_float, cfg_get_list, cfg_get_str


class TrendMTFWatcher(BaseWatcher):
    """Multi-Timeframe Trend Watcher - analyzes trends across multiple timeframes, returns raw market observations

    Modes:
      * "mtf" — real multi-timeframe: closed 1m bars (payload ``candle`` with ``timestamp``) are
        downsampled into closed 15m / 1h / 4h bars; each timeframe's trend is the t-statistic of a
        log-price regression over its last ``MTF_LOOKBACK`` closed bars. trend_positive/negative only
        when all three timeframes agree with |t| >= ``MTF_T_MIN``; otherwise trend_neutral. No
        observation until every timeframe has enough closed bars (no partial higher-TF bars used).
      * "legacy" — the original 5/15/30-sample regression on whatever cadence is fed (kept for the
        frozen research studies that feed close-only payloads).
      * "auto" (default) — "mtf" as soon as a timestamped candle arrives, "legacy" for close-only feeds.
    """

    MTF_TIMEFRAMES = (900, 3600, 14400)   # 15m, 1h, 4h in seconds
    MTF_LOOKBACK = 20
    MTF_T_MIN = 2.0

    def __init__(self, name: str, symbol: str, broker_service=None, target_broker=None, short_period: int = 5, medium_period: int = 15, long_period: int = 30, watcher_config=None, clock=None, forensic_sink=None, mode: str = "auto"):
        # Convert symbol string to Symbol object if needed
        symbol_obj = Symbol(symbol) if isinstance(symbol, str) else symbol
        super().__init__(name, symbol_obj)

        # Store broker service and other parameters separately
        self.broker_service = broker_service
        self.target_broker = target_broker
        self.clock = clock if clock is not None else LiveClock()
        self.forensic_sink = forensic_sink if forensic_sink is not None else forensic_logger

        # Configuration injected via constructor (E1.T4); falls back to the
        # typed settings aggregate (same values as the legacy Configs.watcher).
        self.enabled = cfg_get_bool(watcher_config, 'trend_mtf_watcher_enabled', True)

        # Only set logger if enabled, otherwise use mock logger
        if self.enabled:
            self.logger = logger
        else:
            # Create a mock logger that doesn't log anything when disabled
            class MockLogger:
                def debug(self, msg): pass
                def info(self, msg): pass
                def warning(self, msg): pass
                def error(self, msg): pass
            self.logger = MockLogger()

        self.short_period = short_period
        self.medium_period = medium_period
        self.long_period = long_period

        # Stores for different timeframes - each with independent state
        self.short_trend_state = {'direction': 0, 'strength': 0, 'timestamp': None}
        self.medium_trend_state = {'direction': 0, 'strength': 0, 'timestamp': None}
        self.long_trend_state = {'direction': 0, 'strength': 0, 'timestamp': None}

        self.price_history = []

        # Trend thresholds
        self.trend_threshold = 0.005  # 0.5% threshold for trend significance

        self.mode = mode
        self._mtf_active = mode == "mtf"
        # per timeframe: closed higher-TF closes, current bucket id, last 1m close, bucket closed flag
        self._htf = {tf: {'closes': [], 'bucket': None, 'last': None, 'closed': True}
                     for tf in self.MTF_TIMEFRAMES}

    def update_data(self, data: dict):
        """Update with new market data"""
        if not self.enabled:
            return

        if 'close' in data:
            self.price_history.append(data['close'])
            if len(self.price_history) > self.long_period * 3:  # Keep more data for longer periods
                self.price_history.pop(0)

        if self.mode != "legacy":
            candle = data.get('candle') if isinstance(data.get('candle'), dict) else None
            opened = self._epoch(candle.get('timestamp')) if candle else None
            if opened is not None and candle.get('close') is not None:
                self._mtf_active = True
                closed_at = self._epoch(candle.get('close_time'))
                self._update_htf(opened, closed_at if closed_at is not None else opened + 60,
                                 float(candle['close']))

    @staticmethod
    def _epoch(value):
        if value is None:
            return None
        if hasattr(value, 'timestamp'):
            return int(round(value.timestamp()))
        try:
            v = float(value)
        except (TypeError, ValueError):
            return None
        return int(v / 1000) if v > 1e11 else int(v)

    def _update_htf(self, opened: int, closed_at: int, close: float) -> None:
        """Downsample one closed 1m bar into the higher timeframes (closed HTF bars only)."""
        keep = self.MTF_LOOKBACK * 3
        for tf, st in self._htf.items():
            bucket = opened // tf
            if st['bucket'] is not None and bucket < st['bucket']:
                continue  # out-of-order bar
            if st['bucket'] is not None and bucket != st['bucket'] and not st['closed']:
                st['closes'].append(st['last'])  # bucket ended without its boundary bar (gap)
            st['bucket'], st['last'] = bucket, close
            st['closed'] = closed_at % tf == 0
            if st['closed']:
                st['closes'].append(close)
            if len(st['closes']) > keep:
                del st['closes'][:-keep]

    @staticmethod
    def _trend_t(closes) -> tuple:
        """(normalized slope per bar, t-statistic) of a log-price regression."""
        y = np.log(np.asarray(closes, dtype=float))
        n = len(y)
        x = np.arange(n, dtype=float)
        xm = x - x.mean()
        sxx = float(np.sum(xm * xm))
        slope = float(np.sum(xm * (y - y.mean())) / sxx)
        resid = y - (y.mean() + slope * xm)
        se = float(np.sqrt(np.sum(resid * resid) / (n - 2) / sxx)) if n > 2 else 0.0
        if se <= 0:
            return slope, 0.0
        return slope, slope / se

    def _analyze_mtf(self, symbol: Symbol):
        n = self.MTF_LOOKBACK
        if any(len(st['closes']) < n for st in self._htf.values()):
            return None
        trends = [self._trend_t(self._htf[tf]['closes'][-n:]) for tf in self.MTF_TIMEFRAMES]
        dirs = [0 if abs(t) < self.MTF_T_MIN else (1 if t > 0 else -1) for _, t in trends]
        now = self.clock.now()
        for state, (slope, t) in zip(('short_trend_state', 'medium_trend_state', 'long_trend_state'), trends):
            setattr(self, state, {'direction': slope, 'strength': abs(t), 'timestamp': now})
        min_abs_t = min(abs(t) for _, t in trends)
        if all(d == 1 for d in dirs):
            observation_type, value = 'trend_positive', min(1.0, min_abs_t / 10.0)
        elif all(d == -1 for d in dirs):
            observation_type, value = 'trend_negative', -min(1.0, min_abs_t / 10.0)
        else:
            observation_type, value = 'trend_neutral', 0.0
        aligned = observation_type != 'trend_neutral'
        confidence = min(0.95, 0.55 + 0.05 * (min_abs_t - self.MTF_T_MIN)) if aligned else 0.3
        observation = MarketObservation(
            symbol=symbol,
            observation_type=observation_type,
            observation_value=value,
            confidence=Percentage(Decimal(str(round(confidence, 6)))),
            timestamp=self.clock.now(),
            metadata={
                'mode': 'mtf',
                'timeframes': {f'{tf // 60}m': {'slope': s, 't_stat': t, 'direction': d}
                               for tf, (s, t), d in zip(self.MTF_TIMEFRAMES, trends, dirs)},
                'trend_source': self.name,
                'price_history_length': len(self.price_history),
            },
        )
        self.forensic_sink.log_watcher_observation(
            watcher=self.name,
            symbol=symbol.value,
            exchange=getattr(self, 'target_broker', 'BINANCE'),
            observation_type=observation_type,
            value=value,
            confidence=float(confidence),
            timestamp=observation.timestamp,
        )
        return observation

    def _analyze_impl(self, symbol: Symbol) -> MarketObservation:
        """Analyze multi-timeframe trends and return a raw market observation (no strategy selection)"""
        if not self.enabled:
            return None

        if self._mtf_active:
            return self._analyze_mtf(symbol)

        if len(self.price_history) < 2:  # Require only 2 data points to start generating observations
            return None

        # Calculate trends for each timeframe
        short_trend = self.calculate_trend(self.price_history[-self.short_period:])
        medium_trend = self.calculate_trend(self.price_history[-self.medium_period:])
        long_trend = self.calculate_trend(self.price_history[-self.long_period:])

        # Update trend states
        self.short_trend_state = {'direction': short_trend[0], 'strength': short_trend[1], 'timestamp': self.clock.now()}
        self.medium_trend_state = {'direction': medium_trend[0], 'strength': medium_trend[1], 'timestamp': self.clock.now()}
        self.long_trend_state = {'direction': long_trend[0], 'strength': long_trend[1], 'timestamp': self.clock.now()}

        # Calculate overall trend score (combination of all timeframes)
        overall_trend_score = self.calculate_overall_trend_score(short_trend, medium_trend, long_trend)

        # Determine observation type based on trend alignment
        # Calculate confidence based on trend alignment and strength
        trend_alignment = self.calculate_trend_alignment(short_trend, medium_trend, long_trend)
        trend_strength = max(abs(short_trend[1]), abs(medium_trend[1]), abs(long_trend[1]))

        # Lowered threshold for trend detection
        lowered_threshold = 0.001  # Much lower threshold to detect trends faster

        # Base confidence on alignment and strength, with higher confidence for clearer signals
        if abs(overall_trend_score) < lowered_threshold:
            observation_type = 'trend_neutral'
            observation_value = 0.0
            # For neutral trends, confidence is based on alignment (how consistent the neutral state is across timeframes)
            confidence = min(0.6, trend_alignment * 0.6)  # Lowered neutral confidence
        elif overall_trend_score > 0:
            observation_type = 'trend_positive'  # Bullish trend
            observation_value = abs(overall_trend_score)
            # For positive trends, confidence is based on both alignment and strength
            confidence = min(0.95, (trend_alignment * 0.5 + trend_strength * 0.3))  # Lowered minimum confidence
        else:
            observation_type = 'trend_negative'  # Bearish trend
            observation_value = -abs(overall_trend_score)
            # For negative trends, confidence is based on both alignment and strength
            confidence = min(0.95, (trend_alignment * 0.5 + trend_strength * 0.3))  # Lowered minimum confidence

        # Convert confidence to Percentage object for domain compatibility
        confidence_percentage = Percentage(Decimal(str(confidence)))

        # Create and return a MarketObservation instead of a Signal
        observation = MarketObservation(
            symbol=symbol,
            observation_type=observation_type,
            observation_value=observation_value,
            confidence=confidence_percentage,
            timestamp=self.clock.now(),
            metadata={
                'short_trend': {
                    'direction': short_trend[0],
                    'strength': short_trend[1]
                },
                'medium_trend': {
                    'direction': medium_trend[0],
                    'strength': medium_trend[1]
                },
                'long_trend': {
                    'direction': long_trend[0],
                    'strength': long_trend[1]
                },
                'overall_trend_score': overall_trend_score,
                'trend_alignment': self.calculate_trend_alignment(short_trend, medium_trend, long_trend),
                'trend_source': self.name,
                'price_history_length': len(self.price_history)
            }
        )

        # Log the watcher observation to forensic log
        self.forensic_sink.log_watcher_observation(
            watcher=self.name,
            symbol=symbol.value,
            exchange=getattr(self, 'target_broker', 'BINANCE'),  # Use target broker if available, otherwise default
            observation_type=observation_type,
            value=observation_value,
            confidence=float(confidence),
            timestamp=observation.timestamp
        )

        return observation

    def analyze(self, symbol: Symbol) -> MarketObservation:
        """Analyze market conditions and return a raw market observation"""
        return self._analyze_impl(symbol)

    def calculate_trend(self, prices):
        """Calculate trend direction and strength using linear regression"""
        if len(prices) < 2:
            return (0, 0)  # No trend if not enough data

        # Convert to numpy array
        prices = np.array(prices)
        x = np.arange(len(prices))

        # Calculate linear regression
        if len(x) > 1:
            slope = (len(x) * np.sum(x * prices) - np.sum(x) * np.sum(prices)) / \
                    (len(x) * np.sum(x * x) - (np.sum(x)) ** 2)

            # Calculate average price for normalization
            avg_price = np.mean(prices)
            if avg_price != 0:
                normalized_slope = slope / avg_price
            else:
                normalized_slope = 0

            # Calculate trend strength (R-squared or similar measure)
            if len(prices) > 2:
                # Calculate R-squared as a measure of trend strength
                y_pred = slope * x + (np.mean(prices) - slope * np.mean(x))
                ss_res = np.sum((prices - y_pred) ** 2)
                ss_tot = np.sum((prices - np.mean(prices)) ** 2)
                if ss_tot != 0:
                    r_squared = 1 - (ss_res / ss_tot)
                    trend_strength = r_squared * abs(normalized_slope)
                else:
                    trend_strength = abs(normalized_slope)
            else:
                trend_strength = abs(normalized_slope)

            return (normalized_slope, min(1.0, trend_strength))
        else:
            return (0, 0)

    def calculate_overall_trend_score(self, short_trend, medium_trend, long_trend):
        """Calculate an overall trend score combining all timeframes"""
        # Weight different timeframes (longer timeframes might be more reliable)
        short_weight = 0.2
        medium_weight = 0.3
        long_weight = 0.5

        overall_score = (short_trend[0] * short_weight + 
                        medium_trend[0] * medium_weight + 
                        long_trend[0] * long_weight)

        return overall_score

    def calculate_trend_alignment(self, short_trend, medium_trend, long_trend):
        """Calculate how aligned the trends are across timeframes"""
        directions = [short_trend[0], medium_trend[0], long_trend[0]]
        
        # Count how many timeframes have the same direction
        positive_count = sum(1 for d in directions if d > 0)
        negative_count = sum(1 for d in directions if d < 0)
        
        # Alignment score (0-1, where 1 is perfect alignment)
        if positive_count == 3 or negative_count == 3:
            alignment = 1.0
        elif positive_count == 0 or negative_count == 0:
            alignment = 0.0
        else:
            # Partial alignment
            alignment = max(positive_count, negative_count) / 3.0

        return alignment
