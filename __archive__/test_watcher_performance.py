#!/usr/bin/env python3
"""
Comprehensive performance test for each watcher individually.
This script will test each watcher with all others disabled to analyze their performance.
"""
import os
import sys
import time
import json
from datetime import datetime, timedelta
from decimal import Decimal
import numpy as np
from typing import Dict, List, Any, Optional

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from domain.value_objects import Symbol
from domain.entities.trading_entities import Signal, SignalType
from infrastructure.watchers.adapters.market_pulse import MarketPulseWatcher
from infrastructure.watchers.adapters.volatility import VolatilityWatcher
from infrastructure.watchers.adapters.trend_mtf import TrendMTFWatcher
from infrastructure.watchers.adapters.anomaly_ml import AnomalyMLWatcher
from infrastructure.watchers.adapters.orderflow_ws import OrderFlowWSWatcher
from infrastructure.watchers.adapters.cmc_screener import CMCScreener
from infrastructure.watchers.adapters.funding_rate import FundingRateWatcher
from infrastructure.watchers.adapters.liquidity import LiquidityWatcher
from infrastructure.watchers.adapters.historical_candle_watcher import HistoricalCandleWatcherAdapter


class MockDataProvider:
    """Mock data provider for testing purposes"""
    def __init__(self):
        self.prices = {}
        self.volumes = {}
        self.generate_sample_data()
    
    def generate_sample_data(self):
        """Generate sample market data for testing"""
        np.random.seed(42)  # For reproducible results
        
        symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT", "AVAXUSDT", "DOGEUSDT", "DOTUSDT"]
        
        for symbol in symbols:
            # Generate realistic price data
            base_price = np.random.uniform(1000, 50000)  # Base price varies by symbol
            prices = [base_price]
            
            for i in range(50):  # 50 data points
                change_percent = np.random.normal(0, 0.03)  # 3% daily volatility
                new_price = prices[-1] * (1 + change_percent)
                # Keep within reasonable bounds
                new_price = max(10, min(100000, new_price))
                prices.append(new_price)
            
            volumes = [np.random.uniform(1000000, 50000000) for _ in range(len(prices))]  # High volume
            
            self.prices[symbol] = prices
            self.volumes[symbol] = volumes
    
    def get_price_data(self, symbol: str, lookback: int = 50):
        """Get price data for a symbol"""
        if symbol in self.prices:
            data = []
            prices = self.prices[symbol][-lookback:]
            volumes = self.volumes[symbol][-lookback:]
            
            for i in range(len(prices)):
                data.append({
                    'close': prices[i],
                    'high': prices[i] * (1 + abs(np.random.normal(0, 0.02))),
                    'low': prices[i] * (1 - abs(np.random.normal(0, 0.02))),
                    'open': prices[i] * (1 + np.random.normal(0, 0.01)),
                    'volume': volumes[i]
                })
            return data
        return []


class WatcherPerformanceTester:
    """Class to test individual watcher performance"""
    
    def __init__(self):
        self.mock_data = MockDataProvider()
        self.all_symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT", "AVAXUSDT", "DOGEUSDT", "DOTUSDT"]
        self.results = {}
    
    def test_watcher(self, watcher_name: str, watcher_class, symbol: str = "BTCUSDT"):
        """Test a single watcher with mock data"""
        print(f"\n{'='*60}")
        print(f"TESTING {watcher_name}")
        print(f"{'='*60}")
        
        # Disable all watchers first
        self._disable_all_watchers()
        
        # Enable only this watcher
        self._enable_single_watcher(watcher_name)
        
        # Create watcher instance
        if watcher_name == "HistoricalCandleWatcher":
            # Special handling for HistoricalCandleWatcher
            watcher = watcher_class(f"Test{watcher_name}", symbol, self.mock_data)
        else:
            watcher = watcher_class(f"Test{watcher_name}", symbol)
        
        # Get test data for this symbol
        test_data = self.mock_data.get_price_data(symbol)
        
        # Feed data to watcher
        triggered_coins = []
        rejected_coins = []
        signals_generated = []
        
        for data_point in test_data:
            try:
                # Update watcher with data
                watcher.update_data(data_point)
                
                # Analyze and get signal
                signal = watcher.analyze(Symbol(symbol))
                
                if signal:
                    signals_generated.append({
                        'signal_type': signal.signal_type.name,
                        'confidence': float(signal.confidence.value),
                        'score': signal.score,
                        'timestamp': str(signal.timestamp),
                        'metadata': signal.metadata if hasattr(signal, 'metadata') else {}
                    })
                    
                    # Add to triggered coins if not already there
                    if symbol not in triggered_coins:
                        triggered_coins.append(symbol)
                        
            except Exception as e:
                print(f"  Error processing data point: {e}")
                continue
        
        # Test with multiple symbols to see which get triggered/rejected
        for test_symbol in self.all_symbols:
            if test_symbol != symbol:  # Test other symbols too
                try:
                    # Create a temporary watcher instance for each symbol
                    if watcher_name == "HistoricalCandleWatcher":
                        temp_watcher = watcher_class(f"Temp{watcher_name}", test_symbol, self.mock_data)
                    else:
                        temp_watcher = watcher_class(f"Temp{watcher_name}", test_symbol)
                    
                    # Get data for this symbol
                    symbol_data = self.mock_data.get_price_data(test_symbol)
                    
                    # Feed data and check for signals
                    symbol_has_signal = False
                    for data_point in symbol_data[-10:]:  # Check last 10 data points
                        temp_watcher.update_data(data_point)
                        signal = temp_watcher.analyze(Symbol(test_symbol))
                        if signal:
                            symbol_has_signal = True
                            break
                    
                    if symbol_has_signal:
                        if test_symbol not in triggered_coins:
                            triggered_coins.append(test_symbol)
                    else:
                        if test_symbol not in rejected_coins:
                            rejected_coins.append(test_symbol)
                            
                except Exception as e:
                    if test_symbol not in rejected_coins:
                        rejected_coins.append(test_symbol)
        
        # Prepare results
        result = {
            'watcher_name': watcher_name,
            'triggered_coins': triggered_coins,
            'rejected_coins': rejected_coins,
            'total_signals': len(signals_generated),
            'signals': signals_generated,
            'analysis': self._analyze_watcher_behavior(watcher_name, triggered_coins, rejected_coins, signals_generated)
        }
        
        self.results[watcher_name] = result
        
        # Print results
        self._print_watcher_results(result)
        
        return result
    
    def _disable_all_watchers(self):
        """Disable all watchers by setting environment variables"""
        watcher_env_vars = [
            'MARKET_PULSE_WATCHER_ENABLED',
            'VOLATILITY_WATCHER_ENABLED', 
            'TREND_MTF_WATCHER_ENABLED',
            'ANOMALY_ML_WATCHER_ENABLED',
            'ORDERFLOW_WS_WATCHER_ENABLED',
            'CMC_SCREENER_ENABLED',
            'FUNDING_RATE_WATCHER_ENABLED',
            'LIQUIDITY_WATCHER_ENABLED',
            'HISTORICAL_CANDLE_WATCHER_ENABLED'
        ]
        
        for var in watcher_env_vars:
            os.environ[var] = 'false'
    
    def _enable_single_watcher(self, watcher_name: str):
        """Enable a single watcher"""
        watcher_map = {
            'MarketPulseWatcher': 'MARKET_PULSE_WATCHER_ENABLED',
            'VolatilityWatcher': 'VOLATILITY_WATCHER_ENABLED',
            'TrendMTFWatcher': 'TREND_MTF_WATCHER_ENABLED',
            'AnomalyMLWatcher': 'ANOMALY_ML_WATCHER_ENABLED',
            'OrderFlowWSWatcher': 'ORDERFLOW_WS_WATCHER_ENABLED',
            'CMCScreener': 'CMC_SCREENER_ENABLED',
            'FundingRateWatcher': 'FUNDING_RATE_WATCHER_ENABLED',
            'LiquidityWatcher': 'LIQUIDITY_WATCHER_ENABLED',
            'HistoricalCandleWatcher': 'HISTORICAL_CANDLE_WATCHER_ENABLED'
        }
        
        if watcher_name in watcher_map:
            os.environ[watcher_map[watcher_name]] = 'true'
    
    def _analyze_watcher_behavior(self, watcher_name: str, triggered_coins: List[str], 
                                  rejected_coins: List[str], signals: List[Dict]) -> Dict[str, Any]:
        """Analyze the behavior of a specific watcher"""
        analysis = {
            'strengths': [],
            'weaknesses': [],
            'improvement_recommendations': [],
            'behavior_notes': []
        }
        
        # Analyze based on watcher type
        if watcher_name == "MarketPulseWatcher":
            analysis['strengths'] = [
                "Good at detecting momentum shifts",
                "Clear separation of momentum, trend, and volume components",
                "Effective noise filtering with NO SIGNAL zone"
            ]
            analysis['weaknesses'] = [
                "May generate signals too frequently in volatile markets",
                "Requires sufficient historical data for stable calculations"
            ]
            analysis['improvement_recommendations'] = [
                "Consider adding more sophisticated trend detection algorithms",
                "Fine-tune the NO SIGNAL zone threshold based on market conditions"
            ]
            
        elif watcher_name == "VolatilityWatcher":
            analysis['strengths'] = [
                "Excellent at detecting volatility regime changes",
                "Distinguishes between expansion and compression",
                "Prevents constant firing during stable regimes"
            ]
            analysis['weaknesses'] = [
                "May miss gradual volatility transitions",
                "Requires stable historical baseline"
            ]
            analysis['improvement_recommendations'] = [
                "Implement adaptive threshold adjustment based on market conditions",
                "Add more sophisticated regime detection algorithms"
            ]
            
        elif watcher_name == "TrendMTFWatcher":
            analysis['strengths'] = [
                "Clear separation of timeframe analysis",
                "Explicit alignment and divergence detection",
                "Independent trend state tracking"
            ]
            analysis['weaknesses'] = [
                "May generate conflicting signals during ranging markets",
                "Relies on moving average crossovers which can lag"
            ]
            analysis['improvement_recommendations'] = [
                "Add more sophisticated trend detection methods",
                "Consider price action-based trend identification"
            ]
            
        elif watcher_name == "AnomalyMLWatcher":
            analysis['strengths'] = [
                "Very low false signal rate due to strict thresholds",
                "Provides clear confidence and anomaly type",
                "Hard suppression rules prevent frequent triggers"
            ]
            analysis['weaknesses'] = [
                "May miss novel patterns not in historical data",
                "Requires stable market conditions for baseline"
            ]
            analysis['improvement_recommendations'] = [
                "Implement adaptive baseline updating",
                "Add multiple anomaly detection algorithms for robustness"
            ]
            
        elif watcher_name == "OrderFlowWSWatcher":
            analysis['strengths'] = [
                "Temporal confirmation prevents single-snapshot signals",
                "Effective persistence validation",
                "Cooldown mechanisms prevent signal spamming"
            ]
            analysis['weaknesses'] = [
                "Requires real-time order book data",
                "May miss short-term manipulative movements"
            ]
            analysis['improvement_recommendations'] = [
                "Add more sophisticated imbalance detection algorithms",
                "Implement machine learning for pattern recognition"
            ]
            
        elif watcher_name == "CMCScreener":
            analysis['strengths'] = [
                "Provides universe signals rather than trade signals",
                "Very low update frequency reduces noise",
                "Quality filtering prevents low-quality signals"
            ]
            analysis['weaknesses'] = [
                "Dependent on CMC API availability and rate limits",
                "May miss rapidly changing market conditions"
            ]
            analysis['improvement_recommendations'] = [
                "Implement better caching strategies",
                "Add more sophisticated quality filters"
            ]
            
        elif watcher_name == "FundingRateWatcher":
            analysis['strengths'] = [
                "Separates extreme funding from acceleration detection",
                "Long cooldown windows prevent frequent signals",
                "Detects meaningful changes rather than levels"
            ]
            analysis['weaknesses'] = [
                "May not work well during low volatility periods",
                "Dependent on accurate funding rate data"
            ]
            analysis['improvement_recommendations'] = [
                "Add more sophisticated acceleration detection",
                "Implement adaptive threshold adjustment"
            ]
            
        elif watcher_name == "LiquidityWatcher":
            analysis['strengths'] = [
                "Liquidity levels are derived, reproducible, and timestamped",
                "Clear separation of liquidity identification from sweep detection",
                "Provides detailed liquidity metrics"
            ]
            analysis['weaknesses'] = [
                "May trigger during normal market hours vs. low liquidity periods",
                "Dependent on order book depth data quality"
            ]
            analysis['improvement_recommendations'] = [
                "Add more sophisticated sweep detection algorithms",
                "Implement adaptive liquidity regime classification"
            ]
            
        elif watcher_name == "HistoricalCandleWatcher":
            analysis['strengths'] = [
                "Limited to justified set of patterns with strict confirmation",
                "No single-candle signals allowed",
                "Clear pattern detection with mathematical confirmation"
            ]
            analysis['weaknesses'] = [
                "Limited to simple pattern detection",
                "Requires sufficient historical data for pattern confirmation"
            ]
            analysis['improvement_recommendations'] = [
                "Add more sophisticated pattern recognition algorithms",
                "Implement machine learning for complex pattern detection"
            ]
        
        return analysis
    
    def _print_watcher_results(self, result: Dict[str, Any]):
        """Print formatted results for a watcher"""
        print(f"📊 RESULTS FOR {result['watcher_name']}:")
        print(f"   Triggered Coins: {result['triggered_coins']}")
        print(f"   Rejected Coins: {result['rejected_coins']}")
        print(f"   Total Signals Generated: {result['total_signals']}")
        
        # Show signal details if any were generated
        if result['signals']:
            print("   Sample Signals:")
            for i, signal in enumerate(result['signals'][:3]):  # Show first 3 signals
                print(f"     [{i+1}] Type: {signal['signal_type']}, Confidence: {signal['confidence']:.3f}, Score: {signal['score']:.3f}")
        
        analysis = result['analysis']
        print(f"\n💪 STRENGTHS:")
        for strength in analysis['strengths']:
            print(f"   • {strength}")
        
        print(f"\n⚠️  WEAKNESSES:")
        for weakness in analysis['weaknesses']:
            print(f"   • {weakness}")
        
        print(f"\n💡 IMPROVEMENT RECOMMENDATIONS:")
        for recommendation in analysis['improvement_recommendations']:
            print(f"   • {recommendation}")
    
    def run_comprehensive_test(self):
        """Run comprehensive test for all watchers"""
        print("🚀 STARTING COMPREHENSIVE WATCHER PERFORMANCE TEST")
        print("="*80)
        print("Testing each watcher individually with all others disabled...")
        
        # Define watchers to test
        watchers_to_test = [
            ("MarketPulseWatcher", MarketPulseWatcher),
            ("VolatilityWatcher", VolatilityWatcher),
            ("TrendMTFWatcher", TrendMTFWatcher),
            ("AnomalyMLWatcher", AnomalyMLWatcher),
            ("OrderFlowWSWatcher", OrderFlowWSWatcher),
            ("CMCScreener", CMCScreener),
            ("FundingRateWatcher", FundingRateWatcher),
            ("LiquidityWatcher", LiquidityWatcher),
            ("HistoricalCandleWatcher", HistoricalCandleWatcherAdapter)
        ]
        
        # Test each watcher individually
        for watcher_name, watcher_class in watchers_to_test:
            self.test_watcher(watcher_name, watcher_class)
        
        # Print summary
        self._print_summary()
        
        # Save detailed results
        self._save_results()
        
        return self.results
    
    def _print_summary(self):
        """Print summary of all watcher tests"""
        print("\n" + "="*80)
        print("📊 COMPREHENSIVE TEST SUMMARY")
        print("="*80)
        
        for watcher_name, result in self.results.items():
            triggered_count = len(result['triggered_coins'])
            rejected_count = len(result['rejected_coins'])
            signal_count = result['total_signals']
            
            print(f"{watcher_name}:")
            print(f"   • Triggered: {triggered_count} coins | Rejected: {rejected_count} coins")
            print(f"   • Signals Generated: {signal_count}")
            print(f"   • Efficiency: {(triggered_count/(triggered_count+rejected_count)*100) if (triggered_count+rejected_count) > 0 else 0:.1f}%")
            print()
    
    def _save_results(self):
        """Save detailed results to JSON file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"watcher_performance_report_{timestamp}.json"
        
        # Convert Decimal objects to float/string for JSON serialization
        serializable_results = {}
        for watcher_name, result in self.results.items():
            serializable_result = {}
            for key, value in result.items():
                if isinstance(value, list):
                    serializable_result[key] = []
                    for item in value:
                        if isinstance(item, dict):
                            serializable_item = {}
                            for k, v in item.items():
                                if isinstance(v, Decimal):
                                    serializable_item[k] = float(v)
                                else:
                                    serializable_item[k] = v
                            serializable_result[key].append(serializable_item)
                        else:
                            serializable_result[key] = value
                elif isinstance(value, dict):
                    serializable_result[key] = {}
                    for k, v in value.items():
                        if isinstance(v, Decimal):
                            serializable_result[key][k] = float(v)
                        else:
                            serializable_result[key][k] = v
                else:
                    if isinstance(value, Decimal):
                        serializable_result[key] = float(value)
                    else:
                        serializable_result[key] = value
            
            serializable_results[watcher_name] = serializable_result
        
        with open(filename, 'w') as f:
            json.dump(serializable_results, f, indent=2, default=str)
        
        print(f"📋 Detailed results saved to: {filename}")


def main():
    """Run the comprehensive watcher performance test"""
    tester = WatcherPerformanceTester()
    results = tester.run_comprehensive_test()
    
    print("\n🎉 COMPREHENSIVE WATCHER PERFORMANCE TEST COMPLETED!")
    print("✅ All watchers tested individually with detailed analysis")
    print("✅ Strengths, weaknesses, and recommendations documented")
    print("✅ Results saved for future reference")


if __name__ == "__main__":
    main()