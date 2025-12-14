#!/usr/bin/env python3
"""
Walk-Forward Runner - Execute walk-forward optimization and analysis.

This script runs comprehensive walk-forward analysis for trading strategies with 
training/testing windows, parameter optimization, and performance validation.
"""
import os
import sys
import argparse
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Add project root to path to import modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from application.walk_forward.wfo_orchestrator import WFOOrchestrator
from application.walk_forward.sliding_window_splitter import SlidingWindowSplitter
from application.walk_forward.hyperopt_adapter import MultiAssetHyperoptAdapter
from application.walk_forward.cross_validation_engine import CrossValidationEngine
from shared.logger import EnhancedLogger


def load_symbols_from_env() -> List[str]:
    """Load symbols from environment variable."""
    symbols_str = os.getenv("WFO_COINS", "BTCUSDT,ETHUSDT")
    return [s.strip() for s in symbols_str.split(',') if s.strip()]


def run_walkforward_process(symbols: List[str], 
                           strategy_name: str,
                           train_size: int = 90,
                           test_size: int = 30,
                           step_size: int = 30,
                           max_evals: int = 50,
                           cv_splits: int = 5) -> Dict[str, Any]:
    """Run the walk-forward process for specified symbols and strategy."""
    logger = EnhancedLogger(f"WFO_Runner_{strategy_name}")
    
    print(f"🔄 Starting walk-forward optimization process for strategy: {strategy_name}")
    print(f"   Symbols: {symbols}")
    print(f"   Training Window: {train_size} days")
    print(f"   Testing Window: {test_size} days")
    print(f"   Sliding Step: {step_size} days")
    print(f"   Max Evaluations: {max_evals}")
    print(f"   CV Splits: {cv_splits}")
    print(f"   Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    start_time = datetime.now()
    
    # Configuration for WFO
    wfo_config = {
        'train_size': train_size,
        'test_size': test_size,
        'step': step_size,
        'max_evals': max_evals,
        'results_dir': './data/results/wfo',
        'risk_config': {
            'initial_capital': float(os.getenv('INITIAL_CAPITAL', '100000')),
            'fee_rate': float(os.getenv('FEE_RATE', '0.001')),
            'slippage_factor': float(os.getenv('SLIPPAGE_FACTOR', '0.0005'))
        },
        'cv_n_splits': cv_splits,
        'cv_min_train_size': train_size // 2,
        'cv_test_size': test_size
    }
    
    # Initialize WFO orchestrator
    orchestrator = WFOOrchestrator(config=wfo_config)
    
    results = {
        'strategy_name': strategy_name,
        'symbols': symbols,
        'wfo_config': wfo_config,
        'process_start_time': start_time.isoformat(),
        'wfo_results': None,
        'status': 'started',
        'error': None
    }
    
    try:
        print(f"\n🔍 Running complete WFO pipeline for {len(symbols)} symbols...")
        
        # Run the complete WFO pipeline
        wfo_results = orchestrator.run_complete_wfo_pipeline(
            symbols=symbols,
            strategy_name=strategy_name
        )
        
        if 'error' not in wfo_results:
            results['wfo_results'] = wfo_results
            results['status'] = 'completed'
            print(f"   ✅ WFO pipeline completed successfully")
            
            # Extract key metrics for summary
            if 'comprehensive_report' in wfo_results:
                report = wfo_results['comprehensive_report']
                summary_metrics = report.get('summary_metrics', {})
                
                print(f"   📊 Key Metrics:")
                print(f"      Avg Sharpe Ratio: {summary_metrics.get('average_sharpe_ratio', 0):.3f}")
                print(f"      Avg Total Return: {summary_metrics.get('average_total_return', 0):.2%}")
                print(f"      Avg Max Drawdown: {summary_metrics.get('average_max_drawdown', 0):.2%}")
                print(f"      Pass Rate: {summary_metrics.get('pass_rate', 0):.1%}")
                print(f"      Parameter Stability: {summary_metrics.get('parameter_stability_score', 0):.3f}")
        else:
            results['status'] = 'failed'
            results['error'] = wfo_results.get('error', 'Unknown error')
            print(f"   ❌ WFO pipeline failed: {wfo_results.get('error', 'Unknown error')}")
                
    except Exception as e:
        print(f"   ❌ Error during WFO process: {e}")
        results['status'] = 'failed'
        results['error'] = str(e)
    
    # Add end time and duration
    end_time = datetime.now()
    results['process_end_time'] = end_time.isoformat()
    results['duration_seconds'] = (end_time - start_time).total_seconds()
    
    # Print summary
    print(f"\n📊 WALK-FORWARD ANALYSIS SUMMARY")
    print(f"   Strategy: {strategy_name}")
    print(f"   Symbols: {symbols}")
    print(f"   Status: {results['status']}")
    print(f"   Duration: {results['duration_seconds']:.2f}s")
    
    if results['status'] == 'completed' and results['wfo_results']:
        wfo_res = results['wfo_results']
        print(f"   Data Validation: {'✅' if wfo_res.get('data_validation', {}).get('all_symbols_valid', False) else '❌'}")
        print(f"   Cross-Validation Runs: {len(wfo_res.get('cross_validation_results', {}))}")
        print(f"   Assets Optimized: {len(wfo_res.get('multi_asset_optimization', {}))}")
        print(f"   WFO Periods Analyzed: {wfo_res.get('walk_forward_results', {}).get('total_periods', 0)}")
    
    return results


def validate_walkforward_results(results: Dict[str, Any]) -> Dict[str, Any]:
    """Validate the results of the walk-forward process."""
    print(f"\n✅ Validating walk-forward results...")
    
    validation_results = {
        'valid': False,
        'issues': [],
        'validation_details': {}
    }
    
    if results['status'] == 'completed' and results['wfo_results']:
        # Basic validation checks
        wfo_results = results['wfo_results']
        
        # Check if comprehensive report exists
        if 'comprehensive_report' not in wfo_results:
            validation_results['issues'].append("No comprehensive report generated")
        else:
            report = wfo_results['comprehensive_report']
            summary_metrics = report.get('summary_metrics', {})
            
            # Validate key metrics are reasonable
            avg_sharpe = summary_metrics.get('average_sharpe_ratio', 0)
            if abs(avg_sharpe) > 3:  # Unusually high Sharpe ratio
                validation_results['issues'].append(f"Unusually high average Sharpe ratio: {avg_sharpe}")
            
            avg_return = summary_metrics.get('average_total_return', 0)
            if abs(avg_return) > 10:  # 1000% return seems unreasonable
                validation_results['issues'].append(f"Unreasonable average return: {avg_return:.2%}")
            
            avg_drawdown = summary_metrics.get('average_max_drawdown', 0)
            if avg_drawdown > 0:  # Drawdown should be negative
                validation_results['issues'].append(f"Positive average drawdown value: {avg_drawdown:.2%}")
            
            pass_rate = summary_metrics.get('pass_rate', 0)
            if pass_rate < 0 or pass_rate > 1:  # Pass rate should be 0-1
                validation_results['issues'].append(f"Invalid pass rate: {pass_rate:.2%}")
            
            param_stability = summary_metrics.get('parameter_stability_score', 0)
            if param_stability < 0 or param_stability > 1:  # Parameter stability should be 0-1
                validation_results['issues'].append(f"Invalid parameter stability: {param_stability}")
        
        # Validate that all expected components are present
        expected_components = [
            'data_validation', 
            'cross_validation_results', 
            'multi_asset_optimization', 
            'walk_forward_results'
        ]
        
        for component in expected_components:
            if component not in wfo_results:
                validation_results['issues'].append(f"Missing expected component: {component}")
        
        validation_results['valid'] = len(validation_results['issues']) == 0
    else:
        validation_results['issues'].append("WFO process did not complete successfully")
        validation_results['valid'] = False
    
    print(f"   Valid: {validation_results['valid']}")
    if validation_results['issues']:
        print(f"   Issues: {validation_results['issues']}")
    
    return validation_results


def main():
    """Main entry point for the walk-forward runner."""
    parser = argparse.ArgumentParser(
        description='Run walk-forward optimization and analysis for trading strategies',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --strategy crypto_breakout --symbols BTCUSDT ETHUSDT
  %(prog)s --strategy rsi_strategy --train 60 --test 20 --step 20 --evals 25
  %(prog)s --strategy ma_crossover_strategy --all --train 120 --test 30 --cv-splits 3
        """
    )

    parser.add_argument('--strategy', type=str, 
                       default='crypto_breakout',
                       help='Strategy name to use for WFO (default: crypto_breakout)')

    parser.add_argument('--symbols', nargs='+', type=str,
                       help='Specific symbols to analyze (default: from WFO_COINS env var)')

    parser.add_argument('--train', type=int, default=90,
                       help='Training window size in days (default: 90)')

    parser.add_argument('--test', type=int, default=30,
                       help='Testing window size in days (default: 30)')

    parser.add_argument('--step', type=int, default=30,
                       help='Sliding step size in days (default: 30)')

    parser.add_argument('--evals', type=int, default=50,
                       help='Maximum hyperopt evaluations per asset (default: 50)')

    parser.add_argument('--cv-splits', type=int, default=5,
                       help='Number of cross-validation splits (default: 5)')

    parser.add_argument('--output', type=str,
                       help='Output file to save results (JSON format)')

    parser.add_argument('--validate', action='store_true',
                       help='Validate results after WFO')

    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose output')

    args = parser.parse_args()

    # Get symbols
    if args.symbols:
        symbols = args.symbols
    else:
        symbols = load_symbols_from_env()
    
    print(f"🚀 Walk-Forward Runner Started")
    print(f"   Strategy: {args.strategy}")
    print(f"   Symbols: {symbols}")
    print(f"   WFO Config: {args.train}/{args.test}/{args.step} (train/test/step)")
    print(f"   Max evals: {args.evals}")
    print(f"   CV splits: {args.cv_splits}")

    try:
        # Run WFO process
        results = run_walkforward_process(
            symbols=symbols,
            strategy_name=args.strategy,
            train_size=args.train,
            test_size=args.test,
            step_size=args.step,
            max_evals=args.evals,
            cv_splits=args.cv_splits
        )

        # Validate results if requested
        if args.validate:
            validation_results = validate_walkforward_results(results)
            results['validation'] = validation_results

        # Save results if output file specified
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            print(f"\n💾 Results saved to {args.output}")

        # Exit with appropriate code based on status
        if results['status'] == 'failed':
            print(f"\n❌ WFO process failed")
            return 1
        else:
            print(f"\n🎉 WFO process completed successfully!")
            return 0

    except KeyboardInterrupt:
        print(f"\n⚠️  Process interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Walk-forward process failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())