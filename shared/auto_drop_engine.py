"""Complete Auto-Drop System for filtering worthless coins."""

import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from scipy import stats


@dataclass
class Drop1Result:
    passed: bool
    reason: str
    score: float
    avg_volume: float
    volatility: float


class Drop1VolumeVolatility:
    """Checks liquidity & volatility health for low-volume/dormant coins."""

    def __init__(self, min_volume=150_000, min_volatility=0.003):
        self.min_volume = min_volume
        self.min_volatility = min_volatility

    def analyze(self, df: pd.DataFrame) -> Drop1Result:
        if df is None or len(df) < 50:
            return Drop1Result(False, "Not enough data", 0, 0, 0)

        volumes = df['volume'].tail(200)
        prices = df['close'].tail(200)

        avg_volume = volumes.mean()
        volatility = np.std(prices.pct_change())

        passed = avg_volume > self.min_volume and volatility > self.min_volatility

        score = (
            (avg_volume / (self.min_volume + 1)) * 0.6 +
            (volatility / (self.min_volatility + 1e-8)) * 0.4
        )

        return Drop1Result(
            passed=passed,
            reason="OK" if passed else "Low volume/volatility",
            score=float(score),
            avg_volume=float(avg_volume),
            volatility=float(volatility),
        )


@dataclass
class Drop2Result:
    passed: bool
    reason: str
    score: float
    history_days: int


class Drop2HistoricalValidity:
    """Ensures coin has enough historical data + no corrupted gaps."""

    def __init__(self, min_days=120):
        self.min_days = min_days

    def analyze(self, df: pd.DataFrame) -> Drop2Result:
        if df is None or len(df) < 50:
            return Drop2Result(False, "Not enough data", 0, 0)

        # Assuming 1-hour data - adjust based on your timeframe
        history_hours = len(df)
        history_days = history_hours / 24

        has_gaps = df['close'].isna().sum() > 0

        passed = (history_days >= self.min_days) and not has_gaps

        score = (
            min(history_days / self.min_days, 2.0) * 0.7 +
            (0 if has_gaps else 1) * 0.3
        )

        return Drop2Result(
            passed=passed,
            reason="OK" if passed else "Insufficient history or gaps detected",
            score=float(score),
            history_days=int(history_days),
        )


@dataclass
class Drop3Result:
    passed: bool
    reason: str
    spread: float
    micro_score: float


class Drop3Microstructure:
    """Evaluates market microstructure quality."""

    def __init__(self, max_spread=0.004, max_micro_gaps=5):
        self.max_spread = max_spread
        self.max_micro_gaps = max_micro_gaps

    def analyze(self, df: pd.DataFrame) -> Drop3Result:
        if df is None or len(df) < 200:
            return Drop3Result(False, "Not enough data", 0, 0)

        df = df.tail(300)

        spread = float((df['high'] - df['low']).mean() / df['close'].mean())
        # Check for large gaps between open and close
        micro_gaps = int((df['open'] - df['close'].shift(1)).abs().gt(df['close'] * 0.02).sum())

        passed = spread < self.max_spread and micro_gaps < self.max_micro_gaps

        micro_score = (
            (1 - (spread / (self.max_spread + 1e-9))) * 0.7 +
            (1 - (micro_gaps / (self.max_micro_gaps + 1))) * 0.3
        )

        return Drop3Result(
            passed=passed,
            reason="OK" if passed else "Bad microstructure",
            spread=spread,
            micro_score=micro_score,
        )


@dataclass
class Drop4Result:
    passed: bool
    reason: str
    trend_score: float
    noise_score: float
    final_score: float


class Drop4SignalQuality:
    """Evaluates signal structure quality and trend consistency."""

    def __init__(self, min_trend_score=0.35, max_noise=0.6):
        self.min_trend_score = min_trend_score
        self.max_noise = max_noise

    def analyze(self, df: pd.DataFrame) -> Drop4Result:
        if df is None or len(df) < 200:
            return Drop4Result(False, "Not enough data", 0, 0, 0)

        prices = df['close'].tail(400)
        returns = prices.pct_change().fillna(0)

        # Calculate trend score using correlation
        trend_score = abs(np.corrcoef(np.arange(len(prices)), prices)[0, 1]) if len(prices) > 1 else 0
        noise = float(np.std(returns) / (abs(np.mean(returns)) + 1e-9)) if np.mean(returns) != 0 else float(np.std(returns))

        passed = (trend_score >= self.min_trend_score) and (noise <= self.max_noise)

        final_score = (
            trend_score * 0.7 +
            (1 - min(noise / self.max_noise, 1)) * 0.3
        )

        return Drop4Result(
            passed=passed,
            reason="OK" if passed else "Unstable signal structure",
            trend_score=trend_score,
            noise_score=noise,
            final_score=final_score,
        )


@dataclass
class ExchangeRiskResult:
    passed: bool
    score: float
    reason: str


class ExchangeRiskModel:
    """Detects exchange-related risks like delisting probability, outages, etc."""

    def __init__(self, risk_threshold=0.35):
        self.risk_threshold = risk_threshold

    def analyze(self, coin_metrics: Dict) -> ExchangeRiskResult:
        # Default values if metrics not provided
        funding_stability = coin_metrics.get("funding_stability", 0.5)
        listing_age_score = coin_metrics.get("listing_age_score", 0.5)
        outage_score = coin_metrics.get("outage_score", 0.5)
        spread_health = coin_metrics.get("spread_health", 0.5)

        score = (
            funding_stability * 0.3 +
            listing_age_score * 0.2 +
            outage_score * 0.2 +
            spread_health * 0.3
        )

        passed = score > self.risk_threshold

        return ExchangeRiskResult(
            passed=passed,
            score=score,
            reason="OK" if passed else "Exchange risk detected"
        )


@dataclass
class MarketPhaseResult:
    phase: str
    volatility: float
    trend_strength: float


class MarketPhaseModel:
    """Detects current market phase and regime."""

    def analyze(self, df: pd.DataFrame) -> MarketPhaseResult:
        prices = df['close'].tail(400)
        returns = prices.pct_change().fillna(0)

        volatility = float(np.std(returns))
        trend_strength = float(abs(np.corrcoef(np.arange(len(prices)), prices)[0, 1]) if len(prices) > 1 else 0)

        if trend_strength > 0.45 and volatility < 0.02:
            phase = "TREND"
        elif volatility > 0.05 and trend_strength < 0.25:
            phase = "HIGH_VOL_CHOP"
        elif volatility < 0.02:
            phase = "LOW_VOL"
        else:
            phase = "CHOP"

        return MarketPhaseResult(
            phase=phase,
            volatility=volatility,
            trend_strength=trend_strength
        )


@dataclass
class BacktestMemoryResult:
    passed: bool
    weighted_score: float
    reason: str


class BacktestMemoryFilter:
    """Evaluates coin based on historical backtest performance."""

    def __init__(self, min_score=0.45):
        self.min_score = min_score

    def analyze(self, history_record: Optional[Dict]) -> BacktestMemoryResult:
        if history_record is None:
            return BacktestMemoryResult(False, 0, "No history")

        win_rate = history_record.get("win_rate", 0.5)
        profit_factor = history_record.get("profit_factor", 1.5)
        avg_trade_quality = history_record.get("avg_trade_quality", 0.5)

        score = (
            win_rate * 0.4 +
            profit_factor * 0.1 +  # Lower weight as profit factor can be volatile
            avg_trade_quality * 0.5
        )

        passed = score >= self.min_score

        return BacktestMemoryResult(
            passed=passed,
            weighted_score=score,
            reason="OK" if passed else "History performance too weak"
        )


class CoinQualityFilter:
    """Main filter for detecting worthless coins based on multiple metrics."""

    def __init__(self,
                 min_volume=100000,
                 max_spread=0.003,
                 min_liquidity_score=0.35,
                 wash_trading_threshold=0.65,
                 pump_dump_detector=True,
                 filter_config: Dict[str, Any] = None):
        # Use filter_config if provided, otherwise use individual parameters
        if filter_config:
            self.min_volume = filter_config.get('min_volume', min_volume)
            self.max_spread = filter_config.get('max_spread', max_spread)
            self.min_liquidity_score = filter_config.get('min_liquidity_score', min_liquidity_score)
            self.wash_trading_threshold = filter_config.get('wash_trading_threshold', wash_trading_threshold)
            self.pump_dump_detector = filter_config.get('pump_dump_detector', pump_dump_detector)
        else:
            self.min_volume = min_volume
            self.max_spread = max_spread
            self.min_liquidity_score = min_liquidity_score
            self.wash_trading_threshold = wash_trading_threshold
            self.pump_dump_detector = pump_dump_detector

    def is_worthless(self, coin_data: dict) -> bool:
        """Check if coin should be dropped based on metrics."""
        # Check volume
        if coin_data.get("vol", 0) < self.min_volume:
            return True

        # Check spread
        if coin_data.get("spread", 0) > self.max_spread:
            return True

        # Check liquidity (if available)
        if coin_data.get("liquidity", 1.0) < self.min_liquidity_score:
            return True

        # Check wash trading score
        if coin_data.get("wash_score", 0) > self.wash_trading_threshold:
            return True

        # Check pump/dump flag
        if self.pump_dump_detector and coin_data.get("pump_dump_flag", False):
            return True

        return False

    def get_optimizable_params(self) -> Dict[str, Any]:
        """Get the current filter parameters that can be optimized."""
        return {
            'min_volume': self.min_volume,
            'max_spread': self.max_spread,
            'min_liquidity_score': self.min_liquidity_score,
            'wash_trading_threshold': self.wash_trading_threshold,
            'pump_dump_detector': self.pump_dump_detector
        }

    def update_from_params(self, params: Dict[str, Any]):
        """Update filter parameters from optimization results."""
        self.min_volume = params.get('min_volume', self.min_volume)
        self.max_spread = params.get('max_spread', self.max_spread)
        self.min_liquidity_score = params.get('min_liquidity_score', self.min_liquidity_score)
        self.wash_trading_threshold = params.get('wash_trading_threshold', self.wash_trading_threshold)
        self.pump_dump_detector = params.get('pump_dump_detector', self.pump_dump_detector)

    def filter_list(self, all_coins: dict) -> List[str]:
        """Return list of allowed coins only."""
        return [
            symbol for symbol, data in all_coins.items()
            if not self.is_worthless(data)
        ]


class AutoDropEngine:
    """Main Auto-Drop engine that coordinates all DROP modules."""

    def __init__(self):
        self.drop1 = Drop1VolumeVolatility()
        self.drop2 = Drop2HistoricalValidity()
        self.drop3 = Drop3Microstructure()
        self.drop4 = Drop4SignalQuality()
        self.exchange_risk = ExchangeRiskModel()
        self.market_phase = MarketPhaseModel()
        self.btf_memory = BacktestMemoryFilter()

    def evaluate(self, df: pd.DataFrame, coin_metrics: Optional[Dict] = None, 
                 history: Optional[Dict] = None) -> Dict[str, any]:
        """Perform complete evaluation of a coin."""
        results = {}

        # Run all drop checks
        r1 = self.drop1.analyze(df)
        results["drop1"] = r1

        r2 = self.drop2.analyze(df)
        results["drop2"] = r2

        r3 = self.drop3.analyze(df)
        results["drop3"] = r3

        r4 = self.drop4.analyze(df)
        results["drop4"] = r4

        # Default coin metrics if not provided
        default_metrics = {
            "funding_stability": 0.5,
            "listing_age_score": 0.5,
            "outage_score": 0.5,
            "spread_health": 0.5
        }
        coin_metrics = coin_metrics or default_metrics
        r_exchange = self.exchange_risk.analyze(coin_metrics)
        results["exchange"] = r_exchange

        r_phase = self.market_phase.analyze(df)
        results["market_phase"] = r_phase

        r_memory = self.btf_memory.analyze(history)
        results["backtest_memory"] = r_memory

        # Final decision: coin is kept only if ALL checks pass
        final_pass = (
            r1.passed and
            r2.passed and
            r3.passed and
            r4.passed and
            r_exchange.passed and
            r_memory.passed
        )

        return {
            "status": "KEEP" if final_pass else "DROP",
            "details": results
        }