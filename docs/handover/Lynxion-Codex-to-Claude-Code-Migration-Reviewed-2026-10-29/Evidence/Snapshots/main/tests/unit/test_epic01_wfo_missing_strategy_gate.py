"""A WFO run cannot silently substitute a zero-signal strategy."""

import tempfile
from pathlib import Path
from unittest.mock import patch


def test_missing_strategy_fails_before_loading_or_optimizing():
    with tempfile.TemporaryDirectory() as directory, patch(
        'shared.log_paths.logs_dir', return_value=Path(directory)
    ), patch('shared.log_paths.log_path', return_value=str(Path(directory) / 'system.log')):
        from application.walk_forward.wfo_orchestrator import WFOOrchestrator

        with patch('application.walk_forward.wfo_orchestrator.CSVHistoryLoader'), patch(
            'application.walk_forward.wfo_orchestrator.MultiAssetHyperoptAdapter'
        ) as hyperopt_class, patch(
            'application.walk_forward.wfo_orchestrator.CrossValidationEngine'
        ), patch('application.walk_forward.wfo_orchestrator.WalkForwardAnalyzer'):
            orchestrator = WFOOrchestrator({'results_dir': directory})
            with patch.object(orchestrator, '_load_data') as load_data:
                result = orchestrator.run_complete_wfo_pipeline(['BTCUSDT'], 'trend_following')
            assert result['error'] == 'Strategy function is required for WFO'
            load_data.assert_not_called()
            hyperopt_class.return_value.optimize.assert_not_called()
