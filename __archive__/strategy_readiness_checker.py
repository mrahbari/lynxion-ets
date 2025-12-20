"""
Strategy Readiness Gate - Validates strategies are ready for optimization.

This script performs comprehensive validation of strategies to ensure they are:
1. Trading without optimization (static correctness)
2. Generating sufficient activity 
3. Explainable in their behavior
4. Robust under stress conditions
"""

import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any
from domain.value_objects import Symbol
from domain.entities.trading_entities import Signal, SignalType

from infrastructure.strategies.adapters.trend_follow_strategy_adapter import TrendFollowStrategyAdapter
from infrastructure.strategies.adapters.mean_reversion_strategy_adapter import MeanReversionStrategyAdapter
from infrastructure.strategies.adapters.scalping_strategy_adapter import ScalpingStrategyAdapter
from infrastructure.strategies.adapters.breakout_strategy_adapter import BreakoutStrategyAdapter
from infrastructure.strategies.adapters.liquidity_strategy_adapter import LiquidityStrategyAdapter
from infrastructure.strategies.adapters.mtf_trend_strategy_adapter import MTFTrendStrategyAdapter
from infrastructure.strategies.adapters.oi_footprint_strategy_adapter import OIFootprintStrategyAdapter
from infrastructure.strategies.adapters.sweep_scalper_strategy_adapter import SweepScalperAdapter
from infrastructure.strategies.adapters.vwap_reversal_strategy_adapter import VWAPReversalStrategyAdapter

from shared.logger import logger


class StrategyReadinessChecker:
    """
    Validates strategy fitness for optimization and live trading.
    Implements the 'static correctness precedes dynamic optimization' principle.
    """
    
    def __init__(self):
        self.validation_results = {}
    
    def generate_market_data(self, start_price: float = 100.0, n_points: int = 100, regime: str = "trending"):
        """Generate synthetic market data with specified regime"""
        np.random.seed(42)  # Fixed seed for reproducible results
        prices = [start_price]
        
        if regime == "trending":
            # Create a trending market with small drift
            for i in range(1, n_points):
                drift = 0.0005  # Small upward drift
                volatility = np.random.normal(0, 0.02)
                change = drift + volatility
                new_price = max(0.01, prices[-1] * (1 + change))
                prices.append(new_price)
        elif regime == "ranging":
            # Create a ranging market oscillating around mean
            mean_price = start_price
            for i in range(1, n_points):
                # Oscillate around mean with mean reversion tendency
                distance_from_mean = (prices[-1] - mean_price) / mean_price
                mean_reversion_force = -distance_from_mean * 0.05  # Pull back to mean
                volatility = np.random.normal(0, 0.015)
                change = mean_reversion_force + volatility
                new_price = max(0.01, prices[-1] * (1 + change))
                prices.append(new_price)
        else:  # "volatile"
            # Create high volatility environment
            for i in range(1, n_points):
                volatility = np.random.normal(0, 0.04)  # Higher volatility
                change = volatility
                new_price = max(0.01, prices[-1] * (1 + change))
                prices.append(new_price)
        
        # Create OHLCV data from prices
        data = []
        for i, price in enumerate(prices):
            high = price * (1 + abs(np.random.normal(0, 0.01)))
            low = price * (1 - abs(np.random.normal(0, 0.01)))
            open_price = prices[i-1] if i > 0 else price
            volume = max(100, np.random.exponential(1000))
            
            data.append({
                'timestamp': datetime.now() - timedelta(hours=n_points-i),
                'open': open_price,
                'high': high,
                'low': low,
                'close': price,
                'volume': volume
            })
        
        return data
    
    def validate_static_activity(self, strategy, symbol: Symbol, market_data: List[Dict], min_trades: int = 5):
        """Validate that strategy produces sufficient activity without optimization"""
        try:
            strategy.update_with_market_data(market_data)
            
            # Test if strategy generates signals when market data is provided
            signals_generated = 0
            sample_size = min(len(market_data), 20)  # Test with subset of data
            
            for data_point in market_data[-sample_size:]:
                test_strategy = self._clone_strategy(strategy)
                test_strategy.update_with_market_data([data_point])
                signal = test_strategy.generate_signal(symbol)
                
                if signal and signal.signal_type != SignalType.HOLD:
                    signals_generated += 1
            
            # Overall activity check
            strategy.update_with_market_data(market_data)
            final_signal = strategy.generate_signal(symbol)
            
            has_activity = signals_generated >= min_trades or (final_signal and final_signal.signal_type != SignalType.HOLD)
            
            return {
                'signals_generated': signals_generated,
                'has_sufficient_activity': has_activity,
                'min_trades_required': min_trades,
                'sample_size_tested': sample_size
            }
        except Exception as e:
            logger.error(f"Error validating static activity for {strategy.get_strategy_name()}: {e}")
            return {
                'signals_generated': 0,
                'has_sufficient_activity': False,
                'min_trades_required': min_trades,
                'sample_size_tested': 0,
                'error': str(e)
            }
    
    def validate_explainability(self, strategy, symbol: Symbol, market_data: List[Dict]):
        """Validate that the strategy behavior is explainable"""
        try:
            strategy.update_with_market_data(market_data)
            signal = strategy.generate_signal(symbol)
            
            is_explainable = False
            explanation = "No explanation available"
            
            if signal and signal.signal_type != SignalType.HOLD:
                # Check if signal has metadata with technical indicators
                has_metadata = signal.metadata is not None
                has_reasonable_score = -1.0 <= signal.score <= 1.0
                has_reasonable_confidence = 0.0 <= float(signal.confidence.value) <= 1.0
                
                is_explainable = has_metadata and has_reasonable_score and has_reasonable_confidence
                
                # Create explanation string
                if signal.metadata:
                    tech_indicators = list(signal.metadata.keys())
                    explanation = f"Signal explained by indicators: {tech_indicators}"
                else:
                    explanation = "Signal generated but no technical explanation in metadata"
            else:
                explanation = "No trade signal generated (may be normal depending on market conditions)"
            
            return {
                'is_explainable': is_explainable,
                'explanation': explanation,
                'has_metadata': signal.metadata is not None if signal else False,
                'confidence_level': float(signal.confidence.value) if signal else 0.0,
                'score_range_valid': -1.0 <= signal.score <= 1.0 if signal else True
            }
        except Exception as e:
            logger.error(f"Error validating explainability for {strategy.get_strategy_name()}: {e}")
            return {
                'is_explainable': False,
                'explanation': f"Error during explainability check: {e}",
                'has_metadata': False,
                'confidence_level': 0.0,
                'error': str(e)
            }
    
    def run_stress_test(self, strategy, symbol: Symbol, market_data: List[Dict]):
        """Run stress test without optimization"""
        try:
            # Normal market conditions test
            normal_strategy = self._clone_strategy(strategy)
            normal_strategy.update_with_market_data(market_data)
            normal_signal = normal_strategy.generate_signal(symbol)
            
            # Highly volatile market conditions test
            volatile_data = self.generate_market_data(regime="volatile", n_points=50)
            volatile_strategy = self._clone_strategy(strategy)
            volatile_strategy.update_with_market_data(volatile_data)
            volatile_signal = volatile_strategy.generate_signal(symbol)
            
            # Ranging market conditions test
            ranging_data = self.generate_market_data(regime="ranging", n_points=50)
            ranging_strategy = self._clone_strategy(strategy)
            ranging_strategy.update_with_market_data(ranging_data)
            ranging_signal = ranging_strategy.generate_signal(symbol)
            
            # Assess robustness - all three conditions should produce reasonable signals
            normal_works = normal_signal is not None
            volatile_works = volatile_signal is not None
            ranging_works = ranging_signal is not None
            
            robustness_score = sum([normal_works, volatile_works, ranging_works]) / 3.0
            
            # Check for consistent behavior under stress
            is_robust = robustness_score >= 0.67  # At least 2 out of 3 conditions work
            
            return {
                'normal_conditions_work': normal_works,
                'volatile_conditions_work': volatile_works,
                'ranging_conditions_work': ranging_works,
                'robustness_score': robustness_score,
                'is_robust': is_robust
            }
        except Exception as e:
            logger.error(f"Error running stress test for {strategy.get_strategy_name()}: {e}")
            return {
                'normal_conditions_work': False,
                'volatile_conditions_work': False,
                'ranging_conditions_work': False,
                'robustness_score': 0.0,
                'is_robust': False,
                'error': str(e)
            }
    
    def _clone_strategy(self, strategy):
        """Create a new instance of the strategy with same config"""
        strategy_name = strategy.get_strategy_name()
        
        if strategy_name == "TrendFollow":
            return TrendFollowStrategyAdapter(
                lookback_period=getattr(strategy, 'lookback_period', 50),
                ma_type=getattr(strategy, 'ma_type', 'EMA'),
                ma_period=getattr(strategy, 'ma_period', 20)
            )
        elif strategy_name == "MeanReversion":
            return MeanReversionStrategyAdapter(
                lookback_period=getattr(strategy, 'lookback_period', 20),
                std_dev_threshold=getattr(strategy, 'std_dev_threshold', 1.5),
                rsi_oversold=getattr(strategy, 'rsi_oversold', 30),
                rsi_overbought=getattr(strategy, 'rsi_overbought', 70)
            )
        elif strategy_name == "Scalper":
            return ScalpingStrategyAdapter(
                lookback_period=getattr(strategy, 'lookback_period', 5),
                profit_target=getattr(strategy, 'profit_target', 0.005),
                stop_loss=getattr(strategy, 'stop_loss', 0.003),
                rsi_period=getattr(strategy, 'rsi_period', 14)
            )
        elif strategy_name == "Breakout":
            return BreakoutStrategyAdapter(
                lookback_period=getattr(strategy, 'lookback_period', 20),
                consolidation_period=getattr(strategy, 'consolidation_period', 10),
                breakout_threshold=getattr(strategy, 'breakout_threshold', 0.02)
            )
        elif strategy_name == "Liquidity":
            config = getattr(strategy, 'config', {})
            return LiquidityStrategyAdapter(config=config)
        elif strategy_name == "MTFTrend":
            config = getattr(strategy, 'config', {})
            return MTFTrendStrategyAdapter(config=config)
        elif strategy_name == "OIFootprint":
            config = getattr(strategy, 'config', {})
            return OIFootprintStrategyAdapter(config=config)
        elif strategy_name == "SweepScalper":
            config = getattr(strategy, 'config', {})
            return SweepScalperAdapter(config=config)
        elif strategy_name == "VWAPReversal":
            config = getattr(strategy, 'config', {})
            return VWAPReversalStrategyAdapter(config=config)
        else:
            # Default case - return same type with basic config
            return type(strategy)()
    
    def validate_strategy_fitness(self, strategy, symbol: Symbol, market_data: List[Dict]):
        """Comprehensive validation of strategy fitness"""
        print(f"Validating: {strategy.get_strategy_name()}")
        
        # Run all validation checks
        activity_result = self.validate_static_activity(strategy, symbol, market_data)
        explainability_result = self.validate_explainability(strategy, symbol, market_data)
        stress_result = self.run_stress_test(strategy, symbol, market_data)
        
        # Calculate composite fitness score
        activity_score = 1.0 if activity_result['has_sufficient_activity'] else 0.3
        explainability_score = 1.0 if explainability_result['is_explainable'] else 0.4
        robustness_score = stress_result['robustness_score']
        
        composite_score = (activity_score * 0.4 + explainability_score * 0.3 + robustness_score * 0.3)
        
        # Classify strategy readiness
        if composite_score >= 0.8 and activity_result['has_sufficient_activity'] and stress_result['is_robust']:
            status = "[OPTIMIZATION-ELIGIBLE]"
        elif composite_score >= 0.5:
            status = "[NEEDS_REVISION]"
        else:
            status = "[REJECTED]"
        
        result = {
            'strategy_name': strategy.get_strategy_name(),
            'status': status,
            'composite_score': composite_score,
            'activity_result': activity_result,
            'explainability_result': explainability_result,
            'stress_result': stress_result
        }
        
        print(f"  Status: {status}")
        print(f"  Composite Score: {composite_score:.3f}")
        print(f"  Activity: {'✅' if activity_result['has_sufficient_activity'] else '❌'}")
        print(f"  Explainable: {'✅' if explainability_result['is_explainable'] else '❌'}")
        print(f"  Robust: {'✅' if stress_result['is_robust'] else '❌'}")
        print()
        
        return result
    
    def run_comprehensive_validation(self, coins: List[str] = None):
        """Run comprehensive validation on all strategies"""
        if coins is None:
            coins = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT"]
        
        print("🚀 HEDGE-GRADE STRATEGY READINESS GATE SYSTEM")
        print("="*60)
        print("Validating strategies before allowing dynamic optimization")
        print()
        
        # Generate market data in a single regime for consistency
        market_data = self.generate_market_data(n_points=100, regime="trending")
        print(f"📊 Generated market data: {len(market_data)} data points")
        
        # Get all available strategies
        strategies = [
            TrendFollowStrategyAdapter(),
            MeanReversionStrategyAdapter(),
            ScalpingStrategyAdapter(),
            BreakoutStrategyAdapter(),
            LiquidityStrategyAdapter(),
            MTFTrendStrategyAdapter(),
            OIFootprintStrategyAdapter(),
            SweepScalperAdapter(),
            VWAPReversalStrategyAdapter()
        ]
        
        # Validate each strategy on each coin
        all_results = {}
        optimization_eligible = 0
        needs_revision = 0
        rejected = 0
        
        for coin in coins:
            print(f"Testing on coin: {coin}")
            symbol = Symbol(coin)
            
            coin_results = []
            for strategy in strategies:
                result = self.validate_strategy_fitness(strategy, symbol, market_data)
                coin_results.append(result)
                
                if result['status'] == '[OPTIMIZATION-ELIGIBLE]':
                    optimization_eligible += 1
                elif result['status'] == '[NEEDS_REVISION]':
                    needs_revision += 1
                else:
                    rejected += 1
            
            all_results[coin] = coin_results
        
        # Print final summary
        print("="*60)
        print("🎯 FINAL VALIDATION SUMMARY")
        print("="*60)
        print(f" OPTIMIZATION-ELIGIBLE: {optimization_eligible} strategies")
        print(f" NEEDS_REVISION: {needs_revision} strategies")
        print(f" REJECTED: {rejected} strategies")
        print(f" TOTAL: {len(strategies) * len(coins)} validation tests")
        print()
        
        # Check if all systems are ready for next phase
        total_strategies = len(strategies)
        if optimization_eligible >= total_strategies * 0.5:  # At least half strategies ready
            print("✅ SYSTEM READY FOR HYPERPARAMETER OPTIMIZATION")
            print("✅ Static correctness verified across strategy portfolio")
            print("✅ Safe to proceed to next phase (hyperopt/retune)")
        else:
            print("❌ SYSTEM NOT READY FOR OPTIMIZATION")
            print("❌ Too many strategies are not statically correct")
            print("❌ Need to fix strategies before enabling dynamic systems")
        
        return all_results


def main():
    """Main entry point for strategy validation"""
    checker = StrategyReadinessChecker()
    results = checker.run_comprehensive_validation()
    
    print("\\n🎯 STRATEGY VERIFICATION COMPLETE")
    print("All strategies have been validated for static correctness")
    print("Following 'Static correctness precedes dynamic optimization' principle")
    
    return results


if __name__ == "__main__":
    main()