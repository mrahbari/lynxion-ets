"""Pin the existing full-data optimization leak before any economic WFO run."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd


class TrainOnlyWFOGateTests(unittest.TestCase):
    def test_optimizer_must_not_receive_unpartitioned_symbol_history(self):
        with tempfile.TemporaryDirectory() as directory, patch(
            'shared.log_paths.logs_dir', return_value=Path(directory)
        ), patch('shared.log_paths.log_path', return_value=str(Path(directory) / 'system.log')):
            from application.walk_forward.wfo_orchestrator import WFOOrchestrator

            with patch('application.walk_forward.wfo_orchestrator.CSVHistoryLoader'), patch(
                'application.walk_forward.wfo_orchestrator.MultiAssetHyperoptAdapter'
            ) as hyperopt_class, patch(
                'application.walk_forward.wfo_orchestrator.CrossValidationEngine'
            ), patch('application.walk_forward.wfo_orchestrator.WalkForwardAnalyzer') as analyzer_class:
                orchestrator = WFOOrchestrator({'results_dir': directory})
                bars = pd.DataFrame({'close': [1.0, 2.0, 3.0]}, index=pd.date_range(
                    '2026-01-01', periods=3, freq='D', tz='UTC'))
                orchestrator._load_data = lambda _symbols: {'BTCUSDT': bars}
                orchestrator._validate_data_for_wfo = lambda _data: {'all_symbols_valid': True}
                orchestrator._get_parameter_space = lambda _name: {}
                orchestrator._run_cross_validation = lambda *_args: {}
                orchestrator._generate_comprehensive_report = lambda *_args: {}
                orchestrator._save_results = lambda *_args: None
                hyperopt_class.return_value.optimize.return_value = {
                    'BTCUSDT': {'window': 2}}
                def run_one_window(**kwargs):
                    self.assertTrue(kwargs['optimizer_with_symbol'])
                    kwargs['strategy_optimizer'](bars.iloc[:2], symbol='BTCUSDT')
                    return {}
                analyzer_class.return_value.run_walk_forward_analysis.side_effect = run_one_window

                orchestrator.run_complete_wfo_pipeline(
                    ['BTCUSDT'], 'trend_following', strategy_func=lambda row, params: 0
                )
                # A valid OOS pipeline may optimize only on the window the
                # analyzer supplies; the third row must never reach Hyperopt.
                calls = hyperopt_class.return_value.optimize.call_args_list
                self.assertEqual(len(calls), 1)
                optimized_data = calls[0].kwargs['multi_asset_data']
                self.assertEqual(list(optimized_data), ['BTCUSDT'])
                pd.testing.assert_frame_equal(optimized_data['BTCUSDT'], bars.iloc[:2])

    def test_each_window_optimizes_only_its_own_training_slice(self):
        with tempfile.TemporaryDirectory() as directory, patch(
            'shared.log_paths.logs_dir', return_value=Path(directory)
        ), patch('shared.log_paths.log_path', return_value=str(Path(directory) / 'system.log')):
            from application.walk_forward.wfo_orchestrator import WFOOrchestrator

            with patch('application.walk_forward.wfo_orchestrator.CSVHistoryLoader'), patch(
                'application.walk_forward.wfo_orchestrator.MultiAssetHyperoptAdapter'
            ) as hyperopt_class, patch(
                'application.walk_forward.wfo_orchestrator.CrossValidationEngine'
            ), patch('application.walk_forward.wfo_orchestrator.WalkForwardAnalyzer') as analyzer_class:
                orchestrator = WFOOrchestrator({'results_dir': directory})
                bars = pd.DataFrame({'close': [1.0, 2.0, 3.0, 4.0]}, index=pd.date_range(
                    '2026-01-01', periods=4, freq='D', tz='UTC'))
                orchestrator._load_data = lambda _symbols: {'BTCUSDT': bars}
                orchestrator._validate_data_for_wfo = lambda _data: {'all_symbols_valid': True}
                orchestrator._get_parameter_space = lambda _name: {}
                orchestrator._run_cross_validation = lambda data, *_args: {
                    key: {'rows': len(value)} for key, value in data.items()}
                orchestrator._generate_comprehensive_report = lambda *_args: {}
                orchestrator._save_results = lambda *_args: None
                def fake_optimize(**kwargs):
                    key = next(iter(kwargs['multi_asset_data']))
                    return {key: {'rows': len(kwargs['multi_asset_data'][key])}}
                hyperopt_class.return_value.optimize.side_effect = fake_optimize
                def run_two_windows(**kwargs):
                    first = kwargs['strategy_optimizer'](bars.iloc[:2], symbol='BTCUSDT')
                    second = kwargs['strategy_optimizer'](bars.iloc[:3], symbol='BTCUSDT')
                    return {'selected': [first, second]}
                analyzer_class.return_value.run_walk_forward_analysis.side_effect = run_two_windows

                result = orchestrator.run_complete_wfo_pipeline(
                    ['BTCUSDT'], 'trend_following', strategy_func=lambda row, params: 0)
                self.assertEqual(result['walk_forward_results']['selected'],
                                 [{'rows': 2}, {'rows': 3}])
                self.assertEqual(result['cross_validation_results'], {
                    'train_window_1': {'rows': 2}, 'train_window_2': {'rows': 3}})
                self.assertEqual(len(hyperopt_class.return_value.optimize.call_args_list), 2)
                for call, expected in zip(hyperopt_class.return_value.optimize.call_args_list,
                                          [bars.iloc[:2], bars.iloc[:3]]):
                    pd.testing.assert_frame_equal(next(iter(call.kwargs['multi_asset_data'].values())),
                                                  expected)

    def test_actual_analyzer_supplies_real_asset_and_training_slice_to_optimizer(self):
        from application.walk_forward.wfo_orchestrator import WFOOrchestrator
        from application.walk_forward.sliding_window_splitter import SlidingWindowSplitter
        with tempfile.TemporaryDirectory() as directory:
            orchestrator = WFOOrchestrator({
                'results_dir': directory, 'data_path': directory,
                'train_size': 2, 'test_size': 1, 'step': 1,
            })
            index = pd.date_range('2026-01-01', periods=6 * 24 + 1, freq='h', tz='UTC')
            frames = {s: pd.DataFrame({'close': [offset + i for i in range(len(index))]}, index=index)
                      for s, offset in (('ETHUSDT', 100), ('SOLUSDT', 200))}
            orchestrator._load_data = lambda _: frames
            orchestrator._validate_data_for_wfo = lambda _: {'all_symbols_valid': True}
            orchestrator._get_parameter_space = lambda _: {}
            cv_inputs, optimization_inputs = [], []
            def cv(data, *_args):
                cv_inputs.append(data)
                return {next(iter(data)): {'synthetic': True}}
            def optimize(**kwargs):
                data = kwargs['multi_asset_data']
                optimization_inputs.append(data)
                return {next(iter(data)): {'window': 2}}
            orchestrator._run_cross_validation = cv
            orchestrator.hyperopt_adapter.optimize = optimize
            # Fixed synthetic metrics: never run strategy economics or real Hyperopt.
            orchestrator.wfo_analyzer._test_on_out_of_sample = lambda *_: {
                'sharpe_ratio': 1, 'max_drawdown': 0, 'total_return': 0,
                'win_rate': 0, 'profit_factor': 1}
            orchestrator._generate_comprehensive_report = lambda *_: {}
            orchestrator._save_results = lambda *_: None
            result = orchestrator.run_complete_wfo_pipeline(
                list(frames), 'synthetic', lambda row, params: 0)
            splitter = SlidingWindowSplitter(2, 1, 1, size_unit='days')
            expected = [(s, window.train_data) for s, data in frames.items()
                        for window in splitter.split(data)]
            self.assertGreater(len(expected), 2)
            self.assertEqual(len(optimization_inputs), len(expected))
            self.assertEqual(len(cv_inputs), len(expected))
            for actuals in (cv_inputs, optimization_inputs):
                for actual, (symbol, frame) in zip(actuals, expected):
                    self.assertEqual(list(actual), [symbol])
                    pd.testing.assert_frame_equal(actual[symbol], frame)
                    self.assertLess(len(actual[symbol]), len(frames[symbol]))
            self.assertEqual(result['walk_forward_results']['total_assets_analyzed'], 2)


if __name__ == '__main__':
    unittest.main()
