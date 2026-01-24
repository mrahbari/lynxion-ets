#!/usr/bin/env python3
"""
Correlation Stress Testing Module - Test portfolio resilience under high correlation scenarios
"""
import os
import sys
import argparse
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple
import pandas as pd
import numpy as np

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Add project root to path to import modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from infrastructure.portfolio.comprehensive_portfolio_backtester import ComprehensivePortfolioBacktester, load_sample_strategies
from infrastructure.data.csv_history_loader import CSVHistoryLoaderAdapter
from shared.logger import EnhancedLogger


def load_symbols_from_env() -> List[str]:
    """Load symbols from environment variable."""
    symbols_str = os.getenv("WFO_COINS", "BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT,XRPUSDT,ADAUSDT")
    return [s.strip() for s in symbols_str.split(',') if s.strip()]


def simulate_high_correlation_scenarios(backtest_results: Dict[str, Any], 
                                     correlation_levels: List[float] = [0.5, 0.7, 0.9, 1.0]) -> Dict[str, Any]:
    """
    Simulate portfolio performance under different correlation levels.
    
    Args:
        backtest_results: Results from comprehensive portfolio backtest
        correlation_levels: List of correlation levels to simulate (0.0 to 1.0)
    
    Returns:
        Dictionary containing stress test results
    """
    logger = EnhancedLogger("CorrelationStressTesting")
    
    print(f"🧪 Starting correlation stress testing...")
    print(f"   Correlation levels to test: {correlation_levels}")
    
    stress_results = {}
    
    # Extract original results
    original_accepted_strategies = backtest_results.get('accepted_strategies', [])
    original_capital_weights = backtest_results.get('capital_weights', {})
    original_metrics = backtest_results.get('admission_metrics', {})
    
    if not original_accepted_strategies:
        print("   ❌ No accepted strategies found, cannot perform stress testing")
        return {"error": "No accepted strategies to test"}
    
    print(f"   Testing {len(original_accepted_strategies)} accepted strategies")
    
    for corr_level in correlation_levels:
        print(f"   Testing correlation level: {corr_level}")
        
        # Calculate portfolio metrics under this correlation scenario
        # This simulates what happens when all strategies become highly correlated
        
        scenario_metrics = {}
        
        for strategy_name in original_accepted_strategies:
            if strategy_name in original_metrics:
                original_metric = original_metrics[strategy_name]
                
                # Under high correlation, diversification benefits decrease
                # Adjust metrics based on correlation level
                original_return = original_metric.get('avg_return', 0)
                original_sharpe = original_metric.get('avg_sharpe', 0)
                original_drawdown = original_metric.get('avg_drawdown', 0)
                
                # As correlation increases, effective diversification decreases
                # This affects risk-adjusted returns negatively
                diversification_factor = 1 - (corr_level * 0.5)  # At 100% correlation, 50% diversification benefit lost
                
                # Adjust metrics based on correlation stress
                stressed_return = original_return * diversification_factor
                stressed_sharpe = original_sharpe * diversification_factor
                stressed_drawdown = original_drawdown  # Drawdown might actually increase, but keeping simple for now
                
                scenario_metrics[strategy_name] = {
                    'original_return': original_return,
                    'stressed_return': stressed_return,
                    'original_sharpe': original_sharpe,
                    'stressed_sharpe': stressed_sharpe,
                    'original_drawdown': original_drawdown,
                    'stressed_drawdown': stressed_drawdown,
                    'diversification_factor': diversification_factor,
                    'correlation_level': corr_level
                }
        
        # Calculate portfolio-level metrics for this scenario
        total_original_return = sum(m.get('original_return', 0) * original_capital_weights.get(name, 0) 
                                   for name, m in scenario_metrics.items())
        total_stressed_return = sum(m.get('stressed_return', 0) * original_capital_weights.get(name, 0) 
                                    for name, m in scenario_metrics.items())
        
        # Calculate portfolio volatility under stress (increases with correlation)
        portfolio_volatility_increase = corr_level * 0.3  # Volatility increases with correlation
        
        stress_results[corr_level] = {
            'strategy_metrics': scenario_metrics,
            'portfolio_metrics': {
                'original_return': total_original_return,
                'stressed_return': total_stressed_return,
                'volatility_increase_factor': 1 + portfolio_volatility_increase,
                'correlation_level': corr_level
            }
        }
        
        print(f"      Original portfolio return: {total_original_return:.2%}")
        print(f"      Stressed portfolio return: {total_stressed_return:.2%}")
    
    # Analyze stress test results
    stress_analysis = analyze_stress_results(stress_results)
    
    final_results = {
        'stress_test_scenarios': stress_results,
        'stress_analysis': stress_analysis,
        'correlation_levels_tested': correlation_levels,
        'timestamp': datetime.now().isoformat()
    }
    
    print(f"   ✅ Correlation stress testing completed")
    
    return final_results


def analyze_stress_results(stress_results: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze the stress test results and provide insights."""
    
    # Calculate key metrics
    correlation_levels = sorted(stress_results.keys())
    
    # Track how portfolio performance degrades with increasing correlation
    performance_degradation = {}
    
    if correlation_levels:
        # Get baseline (lowest correlation) performance
        baseline_corr = min(correlation_levels)
        baseline_return = stress_results[baseline_corr]['portfolio_metrics']['stressed_return']
        
        for corr_level in correlation_levels:
            stressed_return = stress_results[corr_level]['portfolio_metrics']['stressed_return']
            degradation = (baseline_return - stressed_return) / abs(baseline_return) if baseline_return != 0 else 0
            
            performance_degradation[corr_level] = {
                'baseline_return': baseline_return,
                'stressed_return': stressed_return,
                'degradation': degradation,
                'degradation_percentage': degradation * 100
            }
    
    # Identify critical correlation threshold
    critical_threshold = None
    for corr_level in sorted(correlation_levels, reverse=True):
        degradation_info = performance_degradation.get(corr_level, {})
        degradation_pct = degradation_info.get('degradation_percentage', 0)
        
        # If performance degrades by more than 50%, consider it critical
        if degradation_pct >= 50:
            critical_threshold = corr_level
            break
    
    # Identify most vulnerable strategies
    vulnerable_strategies = []
    if correlation_levels:
        baseline_corr = min(correlation_levels)
        high_corr = max(correlation_levels)
        
        if baseline_corr in stress_results and high_corr in stress_results:
            baseline_strat_metrics = stress_results[baseline_corr]['strategy_metrics']
            high_corr_strat_metrics = stress_results[high_corr]['strategy_metrics']
            
            for strategy_name in baseline_strat_metrics:
                if strategy_name in high_corr_strat_metrics:
                    baseline_ret = baseline_strat_metrics[strategy_name]['original_return']
                    stressed_ret = high_corr_strat_metrics[strategy_name]['stressed_return']
                    
                    if baseline_ret != 0:
                        degradation = (baseline_ret - stressed_ret) / abs(baseline_ret)
                        if degradation > 0.3:  # More than 30% degradation
                            vulnerable_strategies.append({
                                'strategy': strategy_name,
                                'baseline_return': baseline_ret,
                                'stressed_return': stressed_ret,
                                'degradation': degradation
                            })
    
    analysis = {
        'performance_degradation_by_correlation': performance_degradation,
        'critical_correlation_threshold': critical_threshold,
        'most_vulnerable_strategies': sorted(vulnerable_strategies, key=lambda x: x['degradation'], reverse=True)[:5],  # Top 5
        'allocation_recommendations': generate_allocation_recommendations(stress_results)
    }
    
    return analysis


def generate_allocation_recommendations(stress_results: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Generate recommendations for capital allocation based on stress test results."""
    
    recommendations = []
    
    if not stress_results:
        return recommendations
    
    # Get the highest correlation scenario
    max_corr = max(stress_results.keys())
    scenario = stress_results[max_corr]
    
    strategy_metrics = scenario.get('strategy_metrics', {})
    
    # Identify strategies that perform poorly under high correlation
    for strategy_name, metrics in strategy_metrics.items():
        stressed_sharpe = metrics.get('stressed_sharpe', 0)
        stressed_return = metrics.get('stressed_return', 0)
        degradation = (metrics.get('original_sharpe', 0) - stressed_sharpe) / abs(metrics.get('original_sharpe', 1)) if metrics.get('original_sharpe', 1) != 0 else 0
        
        recommendation = {
            'strategy': strategy_name,
            'current_stressed_sharpe': stressed_sharpe,
            'current_stressed_return': stressed_return,
            'performance_degradation': degradation,
            'action': 'review',
            'reason': ''
        }
        
        # Determine action based on stress performance
        if stressed_sharpe < -0.2:
            recommendation['action'] = 'reduce_allocation' if stressed_sharpe < 0 else 'monitor'
            recommendation['reason'] = 'Poor risk-adjusted returns under high correlation'
        elif degradation > 0.5:
            recommendation['action'] = 'diversify' if stressed_return > 0 else 'monitor'
            recommendation['reason'] = 'Significant performance degradation under high correlation'
        elif stressed_return < 0:
            recommendation['action'] = 'reduce_allocation'
            recommendation['reason'] = 'Negative returns under high correlation stress'
        
        recommendations.append(recommendation)
    
    return recommendations


def run_correlation_stress_testing(symbols: List[str],
                                 strategy_functions: Dict[str, callable],
                                 start_date: datetime = None,
                                 end_date: datetime = None,
                                 initial_capital: float = 100000.0,
                                 correlation_levels: List[float] = [0.5, 0.7, 0.9, 1.0]) -> Dict[str, Any]:
    """Run comprehensive correlation stress testing."""
    logger = EnhancedLogger("CorrelationStressTestingRunner")
    
    print(f"🚀 Starting comprehensive correlation stress testing...")
    print(f"   Symbols: {symbols}")
    print(f"   Strategies: {list(strategy_functions.keys())}")
    print(f"   Date Range: {start_date.date()} to {end_date.date()}")
    print(f"   Initial Capital: ${initial_capital:,.2f}")
    print(f"   Correlation Levels: {correlation_levels}")
    print(f"   Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    start_time = datetime.now()
    
    # First, run a basic portfolio backtest to get baseline results
    backtester = ComprehensivePortfolioBacktester(
        initial_capital=initial_capital,
        fee_rate=0.001,  # Default fee rate
        slippage_factor=0.0005  # Default slippage
    )
    
    # Load data for all symbols
    data_loader = CSVHistoryLoaderAdapter()
    data_dict = {}
    
    # Check if mock data is allowed in validation
    use_mock_data = os.getenv('USE_MOCK_DATA_FOR_VALIDATION', 'false').lower() == 'true'
    
    for symbol in symbols:
        try:
            df = data_loader.load(symbol=symbol)
            
            if df.empty:
                if use_mock_data:
                    logger.warning(f"No real data found for {symbol}, generating mock data")
                    # Generate mock data for testing
                    df = backtester.generate_mock_data(symbol, start_date, end_date)
                else:
                    logger.error(f"No real data found for {symbol}, and mock data is forbidden in production validation.")
                    raise RuntimeError(f"Real data not found for {symbol}, and mock data is forbidden in production validation.")
            else:
                # Ensure index is datetime type
                df.index = pd.to_datetime(df.index)
                
                # Filter data by date range
                df = df[(df.index >= start_date) & (df.index <= end_date)]
            
            if len(df) < 10:
                if use_mock_data:
                    logger.warning(f"Insufficient data for {symbol} (only {len(df)} rows), generating mock data")
                    df = backtester.generate_mock_data(symbol, start_date, end_date)
                else:
                    logger.error(f"Insufficient data for {symbol} (only {len(df)} rows), and mock data is forbidden in production validation.")
                    raise RuntimeError(f"Insufficient real data for {symbol}, and mock data is forbidden in production validation.")
            
            data_dict[symbol] = df
            logger.info(f"Using data for {symbol} ({len(df)} rows)")
            
        except Exception as e:
            if use_mock_data:
                logger.warning(f"Error loading data for {symbol}: {e}, generating mock data")
                # Generate mock data as fallback
                df = backtester.generate_mock_data(symbol, start_date, end_date)
                data_dict[symbol] = df
                logger.info(f"Generated mock data for {symbol} ({len(df)} rows)")
            else:
                logger.error(f"Error loading data for {symbol}: {e}, and mock data is forbidden in production validation.")
                raise RuntimeError(f"Error loading data for {symbol}: {e}, and mock data is forbidden in production validation.")
    
    if not data_dict:
        logger.error("No data loaded for any symbols")
        return {"error": "No data available for stress testing"}
    
    print(f"   ✅ Loaded/Generated data for {len(data_dict)} symbols")
    
    # Run comprehensive portfolio backtest for baseline
    print(f"   Running baseline portfolio backtest...")
    baseline_results = backtester.run_comprehensive_backtest(
        symbols=list(data_dict.keys()),
        strategy_functions=strategy_functions,
        start_date=start_date,
        end_date=end_date
    )
    
    if 'error' in baseline_results:
        print(f"   ❌ Baseline backtest failed: {baseline_results['error']}")
        return baseline_results
    
    print(f"   ✅ Baseline backtest completed")
    print(f"      Total Strategies: {baseline_results['summary']['total_strategies']}")
    print(f"      Accepted Strategies: {baseline_results['summary']['accepted_strategies_count']}")
    
    # Run correlation stress testing
    print(f"   Running correlation stress testing...")
    stress_test_results = simulate_high_correlation_scenarios(
        baseline_results,
        correlation_levels=correlation_levels
    )
    
    if 'error' in stress_test_results:
        print(f"   ❌ Stress testing failed: {stress_test_results['error']}")
        return stress_test_results
    
    print(f"   ✅ Correlation stress testing completed")
    
    # Compile final results
    final_results = {
        'baseline_results': baseline_results,
        'stress_test_results': stress_test_results,
        'symbols': symbols,
        'strategy_functions': list(strategy_functions.keys()),
        'date_range': {
            'start': start_date.isoformat(),
            'end': end_date.isoformat()
        },
        'pipeline_start_time': start_time.isoformat(),
        'pipeline_end_time': datetime.now().isoformat(),
        'duration_seconds': (datetime.now() - start_time).total_seconds()
    }
    
    # Print stress test summary
    print(f"\n📊 CORRELATION STRESS TEST SUMMARY")
    print(f"   Pipeline Duration: {final_results['duration_seconds']:.2f}s")
    print(f"   Correlation Levels Tested: {stress_test_results['correlation_levels_tested']}")
    
    # Print critical findings
    stress_analysis = stress_test_results['stress_analysis']
    critical_threshold = stress_analysis['critical_correlation_threshold']
    if critical_threshold:
        print(f"   Critical Correlation Threshold: {critical_threshold}")
    
    vulnerable_strategies = stress_analysis['most_vulnerable_strategies']
    if vulnerable_strategies:
        print(f"   Most Vulnerable Strategies:")
        for i, strat in enumerate(vulnerable_strategies[:3]):  # Top 3
            print(f"      {i+1}. {strat['strategy']}: {strat['degradation']:.1%} degradation")
    
    # Print allocation recommendations
    recommendations = stress_analysis['allocation_recommendations']
    reduce_allocations = [r for r in recommendations if r['action'] == 'reduce_allocation']
    if reduce_allocations:
        print(f"   Strategies for Allocation Reduction: {len(reduce_allocations)}")
        for i, rec in enumerate(reduce_allocations[:3]):  # Top 3
            print(f"      {i+1}. {rec['strategy']}: {rec['reason']}")
    
    return final_results


def main():
    """Main entry point for the correlation stress testing runner."""
    parser = argparse.ArgumentParser(
        description='Run correlation stress testing on portfolio strategies',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --start 360d --end today --symbols BTCUSDT ETHUSDT SOLUSDT --levels 0.5 0.7 0.9 1.0
  %(prog)s --start 2023-01-01 --end 2023-12-31 --capital 50000
        """
    )

    parser.add_argument('--start', type=str, required=True,
                       help='Start date in YYYY-MM-DD format or relative (e.g., "30d", "90d")')

    parser.add_argument('--end', type=str, default='today',
                       help='End date in YYYY-MM-DD format or "today" (default: today)')

    parser.add_argument('--symbols', nargs='+', type=str,
                       help='Specific symbols to test (default: from WFO_COINS env var)')

    parser.add_argument('--capital', type=float, default=100000.0,
                       help='Initial capital for testing (default: 100000.0)')

    parser.add_argument('--levels', nargs='+', type=float,
                       default=[0.5, 0.7, 0.9, 1.0],
                       help='Correlation levels to test (default: 0.5 0.7 0.9 1.0)')

    parser.add_argument('--output', type=str,
                       help='Output file to save results (JSON format)')

    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose output')

    args = parser.parse_args()

    # Parse dates
    def parse_date(date_str: str) -> datetime:
        if date_str == 'today':
            return datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999)
        elif date_str.endswith('d'):
            days = int(date_str[:-1])
            return datetime.now() - timedelta(days=days)
        else:
            return datetime.strptime(date_str, '%Y-%m-%d')

    start_date = parse_date(args.start)
    end_date = parse_date(args.end)

    # Get symbols
    if args.symbols:
        symbols = args.symbols
    else:
        symbols = load_symbols_from_env()

    print(f"🧪 Correlation Stress Testing Started")
    print(f"   Date Range: {start_date.date()} to {end_date.date()}")
    print(f"   Symbols: {symbols}")
    print(f"   Initial Capital: ${args.capital:,.2f}")
    print(f"   Correlation Levels: {args.levels}")

    # Load strategy functions
    strategy_functions = load_sample_strategies()
    print(f"   Loaded {len(strategy_functions)} strategies")

    try:
        # Run correlation stress testing
        results = run_correlation_stress_testing(
            symbols=symbols,
            strategy_functions=strategy_functions,
            start_date=start_date,
            end_date=end_date,
            initial_capital=args.capital,
            correlation_levels=args.levels
        )

        # Save results if output file specified
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            print(f"\n💾 Results saved to {args.output}")

        # Check for failures
        if 'error' in results:
            print(f"\n❌ Correlation stress testing failed")
            return 1
        else:
            print(f"\n🎉 Correlation stress testing completed successfully!")
            return 0

    except KeyboardInterrupt:
        print(f"\n⚠️  Process interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Correlation stress testing failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())