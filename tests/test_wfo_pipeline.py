#!/usr/bin/env python3
"""Test script to validate the complete Walk-Forward Optimization pipeline."""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Add the project root to the path so imports work
sys.path.append(str(Path(__file__).parent))

from application.walk_forward.wfo_orchestrator import WFOOrchestrator
from application.walk_forward.sliding_window_splitter import SlidingWindowSplitter
from infrastructure.data.csv_history_loader import CSVHistoryLoaderAdapter as CSVHistoryLoader
from application.walk_forward.hyperopt_adapter import MultiAssetHyperoptAdapter
from application.walk_forward.visualizer import WFVisualizer
from infrastructure.backtest.adapters.walk_forward import WalkForwardAnalyzer
from infrastructure.backtest.realistic_backtester import RealisticBacktester


def create_sample_data(symbols: list, days: int = 365) -> dict:
    """Create sample data for testing purposes."""
    print(f"📊 Creating sample data for {symbols} with {days} days...")

    data = {}

    for symbol in symbols:
        # Create date range
        dates = pd.date_range(end=datetime.now(), periods=days, freq='D')

        # Create price series with some random walk characteristics
        prices = 100 + np.cumsum(np.random.randn(days) * 0.5)

        # Create OHLCV data
        df = pd.DataFrame({
            'timestamp': dates,
            'open': prices * (1 + np.random.randn(days) * 0.005),
            'high': prices * (1 + abs(np.random.randn(days)) * 0.01),
            'low': prices * (1 - abs(np.random.randn(days)) * 0.01),
            'close': prices,
            'volume': np.abs(np.random.randn(days)) * 1000000
        })

        # Ensure OHLC relationships make sense
        df['high'] = df[['open', 'close', 'high']].max(axis=1)
        df['low'] = df[['open', 'close', 'low']].min(axis=1)

        df = df.set_index('timestamp').sort_index()
        data[symbol] = df

        print(f"   Generated {len(df)} rows for {symbol}")

    return data


def test_sliding_window_splitter():
    """Test the sliding window splitter functionality."""
    print("\n🧪 Testing Sliding Window Splitter...")

    # Create sample data
    sample_data = create_sample_data(['BTCUSDT'], days=200)['BTCUSDT']

    # Create splitter
    splitter = SlidingWindowSplitter(train_size=60, test_size=20, step=10)

    # Split the data
    windows = splitter.split(sample_data)

    print(f"   Generated {len(windows)} windows")

    if len(windows) > 0:
        first_window = windows[0]
        print(f"   First window - Train: {len(first_window.train_data)} rows, Test: {len(first_window.test_data)} rows")
        print(f"   First window - Train: {first_window.train_start} to {first_window.train_end}")
        print(f"   First window - Test: {first_window.test_start} to {first_window.test_end}")
        print("   ✅ Sliding Window Splitter test passed")
        return True
    else:
        print("   ❌ Sliding Window Splitter test failed - no windows generated")
        return False


def test_data_loader():
    """Test the data loader functionality."""
    print("\n🧪 Testing Data Loader...")

    # Create temporary data directory in appropriate location and sample files
    temp_data_dir = Path('./data/temp_test_data')
    temp_data_dir.mkdir(parents=True, exist_ok=True)

    # Create a sample CSV file
    sample_data = create_sample_data(['BTCUSDT'], days=100)
    sample_df = sample_data['BTCUSDT']

    # Create symbol directory
    (temp_data_dir / 'BTCUSDT').mkdir(exist_ok=True)
    sample_df.to_csv(temp_data_dir / 'BTCUSDT' / '1d.csv')

    try:
        # Test the loader
        loader = CSVHistoryLoader(str(temp_data_dir))
        df = loader.load('BTCUSDT')

        print(f"   Loaded {len(df)} rows for BTCUSDT")
        print(f"   Columns: {list(df.columns)}")
        print("   ✅ Data Loader test passed")

        # Clean up
        import shutil
        shutil.rmtree(temp_data_dir.parent)

        return True
    except Exception as e:
        print(f"   ❌ Data Loader test failed: {e}")

        # Clean up
        import shutil
        shutil.rmtree(temp_data_dir.parent, ignore_errors=True)

        return False


def test_hyperopt_adapter():
    """Test the hyperopt adapter functionality."""
    print("\n🧪 Testing Hyperopt Adapter...")

    try:
        # Create sample data
        sample_data = create_sample_data(['BTCUSDT'], days=150)

        # Create a simple parameter space for testing
        from hyperopt import hp
        test_space = {
            'param1': hp.uniform('param1', 0, 1),
            'param2': hp.quniform('param2', 1, 10, 1)
        }

        # Create adapter
        adapter = MultiAssetHyperoptAdapter(
            backtester_class=RealisticBacktester,
            risk_engine=None
        )

        # Define a simple test objective function
        def test_objective(data, params):
            # Simple objective function that returns a score based on parameters
            # This would normally run a backtest
            return -abs(params['param1'] - 0.5)  # Maximize around 0.5

        # Optimize (with a small number of evals for testing)
        result = adapter.optimize(
            multi_asset_data=sample_data,
            parameter_space=test_space,
            max_evals=3  # Small number for quick testing
        )

        if result:
            print(f"   Optimization result: {result}")
            print("   ✅ Hyperopt Adapter test passed")
            return True
        else:
            print("   ❌ Hyperopt Adapter test failed - no results returned")
            return False

    except Exception as e:
        print(f"   ❌ Hyperopt Adapter test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_walk_forward_analyzer():
    """Test the Walk-Forward Analyzer functionality."""
    print("\n🧪 Testing Walk-Forward Analyzer...")

    try:
        # Create sample data
        sample_data = create_sample_data(['BTCUSDT'], days=300)

        # Create analyzer
        analyzer = WalkForwardAnalyzer({
            'train_size': 60,
            'test_size': 20,
            'step': 20
        })

        # Define a simple strategy optimizer function
        def simple_strategy_optimizer(data):
            # Return some dummy parameters
            return {'param1': 0.5, 'param2': 5}

        # Run analysis (with small subset for quick test)
        subset_data = sample_data['BTCUSDT'].iloc[:120]  # Use subset for faster test
        result = analyzer.run_walk_forward_analysis(
            data={'BTCUSDT': subset_data},  # Analyzer expects dict format
            strategy_optimizer=simple_strategy_optimizer
        )

        if result and 'total_periods' in result:
            print(f"   Generated {result['total_periods']} WFO periods")
            print(f"   Average Sharpe: {result.get('avg_sharpe_ratio', 'N/A')}")
            print("   ✅ Walk-Forward Analyzer test passed")
            return True
        else:
            print(f"   ❌ Walk-Forward Analyzer test failed - invalid results: {result}")
            return False

    except Exception as e:
        print(f"   ❌ Walk-Forward Analyzer test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_visualizer():
    """Test the visualizer functionality."""
    print("\n🧪 Testing Visualizer...")

    try:
        # Create sample results that match expected format
        sample_results = {
            'total_periods': 5,
            'avg_sharpe_ratio': 0.8,
            'avg_total_return': 0.15,
            'pass_rate': 0.8,
            'parameter_stability': 0.7,
            'out_of_sample_results': [
                {
                    'total_return': 0.05,
                    'sharpe_ratio': 0.6,
                    'max_drawdown': -0.05,
                    'total_trades': 20,
                    'win_rate': 0.6,
                    'profit_factor': 1.8,
                    'equity_curve': [
                        {'timestamp': '2023-01-01', 'equity': 1000},
                        {'timestamp': '2023-01-02', 'equity': 1010},
                        {'timestamp': '2023-01-03', 'equity': 1015}
                    ]
                }
            ] * 5,  # Repeat for 5 periods
            'optimized_parameters_history': [
                {'param1': 0.5, 'param2': 5},
                {'param1': 0.6, 'param2': 6},
                {'param1': 0.4, 'param2': 4},
                {'param1': 0.55, 'param2': 5.5},
                {'param1': 0.45, 'param2': 4.5}
            ]
        }

        # Create visualizer
        visualizer = WFVisualizer('./results/temp_plots')
        plot_files = visualizer.generate_comprehensive_report(
            results=sample_results,
            symbols=['BTCUSDT'],
            strategy_name='test_strategy'
        )

        print(f"   Generated {len(plot_files)} plot files")
        print("   ✅ Visualizer test passed")

        # Clean up temp files
        import shutil
        shutil.rmtree('./results/temp_plots', ignore_errors=True)

        return True

    except Exception as e:
        print(f"   ❌ Visualizer test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_complete_pipeline():
    """Test the complete pipeline end-to-end."""
    print("\n🧪 Testing Complete WFO Pipeline...")

    try:
        # Create sample config
        config = {
            'data_path': './data/temp_test_data',
            'results_dir': './results/temp_wfo_results',
            'train_size': 30,
            'test_size': 10,
            'step': 10,
            'performance_threshold': 0.05,
            'max_drawdown_threshold': 0.1,
            'max_evals': 3,  # Small number for testing
            'risk_config': {
                'initial_capital': 10000,
                'fee_rate': 0.001
            }
        }

        # Create temporary data directory and sample files
        temp_data_dir = Path(config['data_path'])
        temp_data_dir.mkdir(parents=True, exist_ok=True)

        # Create sample data files
        sample_data = create_sample_data(['BTCUSDT', 'ETHUSDT'], days=120)
        for symbol, df in sample_data.items():
            (temp_data_dir / symbol).mkdir(exist_ok=True)
            df_with_timestamp = df.reset_index()
            df_with_timestamp.to_csv(temp_data_dir / symbol / '1d.csv', index=False)

        # Create orchestrator
        orchestrator = WFOOrchestrator(config)

        # Define a simple demo strategy function
        def demo_strategy_function(row, params):
            # Simple strategy that returns random signals for testing
            import random
            return random.choice([-1, 0, 1])  # -1: sell, 0: hold, 1: buy

        # Run the pipeline
        results = orchestrator.run_complete_wfo_pipeline(
            symbols=['BTCUSDT', 'ETHUSDT'],
            strategy_name='demo_strategy',
            strategy_func=demo_strategy_function
        )

        success = 'error' not in results
        if success:
            print("   ✅ Complete Pipeline test passed")
        else:
            print(f"   ❌ Complete Pipeline test failed: {results.get('error', 'Unknown error')}")

        # Clean up
        import shutil
        shutil.rmtree(temp_data_dir, ignore_errors=True)
        shutil.rmtree(Path(config['results_dir']), ignore_errors=True)

        return success

    except Exception as e:
        print(f"   ❌ Complete Pipeline test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("🧪 Starting Walk-Forward Optimization Pipeline Tests...\n")

    tests = [
        ("Sliding Window Splitter", test_sliding_window_splitter),
        ("Data Loader", test_data_loader),
        ("Hyperopt Adapter", test_hyperopt_adapter),
        ("Walk-Forward Analyzer", test_walk_forward_analyzer),
        ("Visualizer", test_visualizer),
        ("Complete Pipeline", test_complete_pipeline)
    ]

    results = []
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"   ❌ {test_name} test crashed: {e}")
            results.append((test_name, False))

    # Print summary
    print(f"\n📊 Test Summary:")
    passed = sum(1 for _, success in results if success)
    total = len(results)

    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"   {status} - {test_name}")

    print(f"\nOverall: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All WFO pipeline tests passed! The system is working correctly.")
        return 0
    else:
        print("⚠️ Some WFO pipeline tests failed. Please check the output above.")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)