#!/usr/bin/env python3
"""CLI entry point for the Walk-Forward Optimization pipeline (E5 entry-point rewiring).

Relocated from application/walk_forward/main_wfo.py. As the operator-facing
composition root it builds the container via bootstrap.lifecycle.lifespan and
resolves the wired wfo_orchestrator_factory, instead of importing infrastructure
from the application layer. The WFVisualizer it uses is an interface-layer
component (legal here). The reusable WFOOrchestrator stays in application/.
"""

import os
import sys
import argparse
import json

# Ensure project root is importable when invoked as a script.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from interface.reporting.walkforward_report import WFVisualizer
from bootstrap.lifecycle import lifespan
from shared.logger import logger


def create_sample_config():
    """Create a sample configuration for WFO."""
    return {
        "data_path": "./data",
        "results_dir": "./data/results/wfo",
        "train_size": 90,      # 3 months for training
        "test_size": 30,       # 1 month for testing
        "step": 30,            # Move forward by 1 month
        "performance_threshold": 0.1,   # Min Sharpe ratio
        "max_drawdown_threshold": 0.15, # Max 15% drawdown
        "max_evals": 50,       # Hyperopt evaluations per asset
        "risk_config": {
            "initial_capital": 100000,
            "fee_rate": 0.001,
            "slippage_factor": 0.0005,
            "max_risk_per_trade": 0.02
        }
    }


def demo_strategy_function(row, params):
    """A simple demo strategy function for testing."""
    # This is a placeholder - in real usage, this would implement actual strategy logic
    # For example, a simple RSI-based strategy:
    rsi = row.get('rsi', 50)
    rsi_oversold = params.get('rsi_oversold', 30)
    rsi_overbought = params.get('rsi_overbought', 70)

    if rsi < rsi_oversold:
        return 1  # Buy signal
    elif rsi > rsi_overbought:
        return -1  # Sell signal
    else:
        return 0  # No signal


def run_sample_wfo(wfo_factory):
    """Run a sample WFO pipeline with demo data."""
    print("🚀 Starting Walk-Forward Optimization Pipeline Demo")

    # Create sample configuration
    config = create_sample_config()

    # Initialize orchestrator via the composition root
    orchestrator = wfo_factory(config)

    # Define symbols for demo (these should exist in your data folder)
    symbols = ["BTCUSDT", "ETHUSDT"]  # Adjust based on your available data

    # Run the complete pipeline
    results = orchestrator.run_complete_wfo_pipeline(
        symbols=symbols,
        strategy_name="demo_strategy",
        strategy_func=demo_strategy_function
    )

    if 'error' in results:
        print(f"❌ Error in WFO pipeline: {results['error']}")
        return results

    # Display summary results
    summary = results['comprehensive_report']['summary_metrics']
    print("\n📊 WFO Pipeline Results Summary:")
    print(f"   Total Assets Analyzed: {summary['total_assets_analyzed']}")
    print(f"   Total WFO Periods: {summary['total_walk_forward_periods']}")
    print(f"   Average Sharpe Ratio: {summary['average_sharpe_ratio']:.4f}")
    print(f"   Average Total Return: {summary['average_total_return']:.4f}")
    print(f"   Average Max Drawdown: {summary['average_max_drawdown']:.4f}")
    print(f"   Pass Rate: {summary['pass_rate']:.2%}")
    print(f"   Parameter Stability: {summary['parameter_stability_score']:.4f}")
    print(f"   Performance Grade: {results['comprehensive_report']['performance_grade']}")

    # Generate visualizations
    print("\n📈 Generating visualizations...")
    visualizer = WFVisualizer()
    plot_files = visualizer.generate_comprehensive_report(
        results=results['walk_forward_results'],
        symbols=symbols,
        strategy_name="demo_strategy"
    )

    print(f"✅ Generated {len(plot_files)} visualization files:")
    for plot_name, file_path in plot_files.items():
        print(f"   - {plot_name}: {file_path}")

    print(f"\n💾 Results saved to: {config['results_dir']}")
    print("✅ WFO Pipeline completed successfully!")

    return results


def run_wfo_from_args(args, wfo_factory):
    """Run WFO with arguments from command line."""
    print(f"🚀 Starting WFO Pipeline for symbols: {args.symbols}")

    # Load or create config
    if args.config:
        with open(args.config, 'r') as f:
            config = json.load(f)
    else:
        config = create_sample_config()

    # Override config with command line args if provided
    if args.train_size:
        config['train_size'] = args.train_size
    if args.test_size:
        config['test_size'] = args.test_size
    if args.step:
        config['step'] = args.step
    if args.data_path:
        config['data_path'] = args.data_path
    if args.results_dir:
        config['results_dir'] = args.results_dir
    if args.max_evals:
        config['max_evals'] = args.max_evals

    # Initialize orchestrator via the composition root
    orchestrator = wfo_factory(config)

    # Parse symbols (comma-separated)
    symbols = [s.strip() for s in args.symbols.split(',')]

    # Run the pipeline
    results = orchestrator.run_complete_wfo_pipeline(
        symbols=symbols,
        strategy_name=args.strategy_name or "default_strategy",
        strategy_func=demo_strategy_function  # In practice, you would load the actual strategy
    )

    if 'error' in results:
        print(f"❌ Error: {results['error']}")
        return 1

    # Display summary
    summary = results['comprehensive_report']['summary_metrics']
    print("\n📊 Results Summary:")
    print(f"   Assets: {summary['total_assets_analyzed']}")
    print(f"   Periods: {summary['total_walk_forward_periods']}")
    print(f"   Avg Sharpe: {summary['average_sharpe_ratio']:.4f}")
    print(f"   Performance Grade: {results['comprehensive_report']['performance_grade']}")

    # Generate visualizations
    visualizer = WFVisualizer(output_dir=config['results_dir'] + '/plots')
    plot_files = visualizer.generate_comprehensive_report(
        results=results['walk_forward_results'],
        symbols=symbols,
        strategy_name=args.strategy_name or "default_strategy"
    )

    print(f"\n📈 Visualizations saved to: {config['results_dir']}/plots")
    print("✅ Pipeline completed!")

    return 0


def main():
    parser = argparse.ArgumentParser(description="Walk-Forward Optimization Pipeline")
    parser.add_argument("--symbols", required=True, help="Comma-separated list of symbols (e.g., 'BTCUSDT,ETHUSDT')")
    parser.add_argument("--strategy-name", help="Name of the strategy to optimize")
    parser.add_argument("--config", help="Path to configuration JSON file")
    parser.add_argument("--train-size", type=int, help="Training window size")
    parser.add_argument("--test-size", type=int, help="Testing window size")
    parser.add_argument("--step", type=int, help="Step size for sliding window")
    parser.add_argument("--data-path", help="Path to data directory")
    parser.add_argument("--results-dir", help="Path to results directory")
    parser.add_argument("--max-evals", type=int, help="Number of hyperopt evaluations")
    parser.add_argument("--demo", action="store_true", help="Run demonstration pipeline")

    args = parser.parse_args()

    with lifespan() as container:
        wfo_factory = container.resolve("wfo_orchestrator_factory")
        if args.demo:
            run_sample_wfo(wfo_factory)
        else:
            return run_wfo_from_args(args, wfo_factory)


if __name__ == "__main__":
    # For direct execution, you can choose between demo and CLI
    if len(sys.argv) == 1:
        # Run demo if no arguments provided
        with lifespan() as container:
            run_sample_wfo(container.resolve("wfo_orchestrator_factory"))
    else:
        # Otherwise, parse arguments
        exit_code = main()
        sys.exit(exit_code)
