#!/usr/bin/env python3
"""
RunWalkforwardUseCase - application-layer orchestration for walk-forward
optimization and analysis.

Orchestration moved here from runner_walkforward.py (E2.T4). The WFO orchestrator
is constructed via an injected factory supplied by the composition root, so this
use case never instantiates infrastructure classes directly.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from shared.logger import EnhancedLogger


@dataclass
class WalkforwardRequest:
    symbols: List[str]
    strategy_name: str = "crypto_breakout"
    train_size: int = 90
    test_size: int = 30
    step_size: int = 30
    max_evals: int = 50
    cv_splits: int = 5


class RunWalkforwardUseCase:
    """Run the walk-forward optimization pipeline using container-injected ports."""

    def __init__(self, settings, wfo_orchestrator_factory: Optional[Callable[[Dict[str, Any]], Any]] = None) -> None:
        # Settings injected by the composition root (E1.T5); read off self._settings
        # instead of importing bootstrap.settings.loaders.
        self._settings = settings
        self._wfo_orchestrator_factory = wfo_orchestrator_factory

    def execute(self, request: WalkforwardRequest) -> Dict[str, Any]:
        return self._run_walkforward_process(
            symbols=request.symbols,
            strategy_name=request.strategy_name,
            train_size=request.train_size,
            test_size=request.test_size,
            step_size=request.step_size,
            max_evals=request.max_evals,
            cv_splits=request.cv_splits,
        )

    def _run_walkforward_process(self, symbols: List[str],
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
                'initial_capital': self._settings.backtest.initial_capital if self._settings.backtest and hasattr(self._settings.backtest, 'initial_capital') else 100000.0,
                'fee_rate': self._settings.execution.fee_rate if self._settings.execution and hasattr(self._settings.execution, 'fee_rate') else 0.001,
                'slippage_factor': self._settings.execution.slippage_factor if self._settings.execution and hasattr(self._settings.execution, 'slippage_factor') else 0.0005
            },
            'cv_n_splits': cv_splits,
            'cv_min_train_size': train_size // 2,
            'cv_test_size': test_size
        }

        # Initialize WFO orchestrator via injected composition-root factory
        if self._wfo_orchestrator_factory is None:
            from application.walk_forward.wfo_orchestrator import WFOOrchestrator
            orchestrator = WFOOrchestrator(config=wfo_config)
        else:
            orchestrator = self._wfo_orchestrator_factory(wfo_config)

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

    def validate_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
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
