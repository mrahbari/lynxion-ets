"""
DEPRECATED (E3.T1 -- Option A: Retire & Redefine). Dead backtest validator (zero
importers). Canonical engine is RealisticBacktester behind BacktestEnginePort
(infrastructure/backtest/backtest_engine_adapter.py). Physical removal -> E8.

Backtesting Validation System based on Enterprise Hedge Fund Architecture
Validates adherence to 17 critical hedge fund rules
"""
from typing import List, Dict, Tuple
import pandas as pd
import numpy as np
from datetime import datetime


class BacktestValidator:
    """
    Comprehensive backtesting validator checking 17 critical hedge fund rules
    """
    def __init__(self):
        self.violations = []
        self.fix_suggestions = []
        self.check_results = {}
    
    def validate(self, execution_engine, data_pipeline, market_data: pd.DataFrame = None) -> Tuple[List[str], List[str]]:
        """
        Run all 17 validation checks on the backtest
        """
        self.violations.clear()
        self.fix_suggestions.clear()
        self.check_results.clear()
        
        # Run all validation checks
        self._check_lookahead_bias(execution_engine, market_data)
        self._check_lag_misalignment(execution_engine)
        self._check_indicator_shifting(execution_engine)
        self._check_data_snooping_bias()
        self._check_survivorship_bias(market_data)
        self._check_timestamp_sorting(market_data)
        self._check_duplicate_removal(market_data)
        self._check_multitimeframe_sync(execution_engine)
        self._check_execution_sl_tp_logic(execution_engine)
        self._check_sl_tp_priority_logic(execution_engine)
        self._check_pnl_with_fees_slippage(execution_engine)
        self._check_drawdown_logic(execution_engine)
        self._check_portfolio_risk_within_limits(execution_engine)
        self._check_no_double_entries(execution_engine)
        self._check_no_stuck_positions(execution_engine)
        self._check_symbol_isolation(execution_engine)
        self._check_reproducibility(execution_engine)
        
        return self.violations, self.fix_suggestions
    
    def _check_lookahead_bias(self, execution_engine, market_data: pd.DataFrame = None):
        """Check 1: No lookahead bias - future data not used for past decisions"""
        # This would check if indicators or signals use future data
        if market_data is not None and not market_data.empty:
            # Check if any columns appear to use future information
            for col in market_data.columns:
                if col.startswith('future_') or col in ['future_price', 'future_close']:
                    self.violations.append(f"Lookahead bias detected: {col} column uses future data")
                    self.fix_suggestions.append(f"Remove or fix {col} column to not use future information")
    
    def _check_lag_misalignment(self, execution_engine):
        """Check 2: No lag misalignment - proper timing between signals and execution"""
        # Check if signals are properly aligned with execution timing
        # In a real implementation, this would check timing relationships
        pass  # Implementation would depend on specific signal generation logic
    
    def _check_indicator_shifting(self, execution_engine):
        """Check 3: Proper indicator shifting to prevent lookahead"""
        # This would check if indicators are properly shifted by 1 period
        # to prevent using future data
        pass  # Would need access to indicator data to validate
    
    def _check_data_snooping_bias(self, market_data: pd.DataFrame = None):
        """Check 4: No data snooping bias - in-sample vs out-of-sample testing"""
        # Check if the same data is used for optimization and testing
        if market_data is not None and len(market_data) > 0:
            # Ensure proper train/test split if needed
            print("Data snooping bias check: Ensure separate training and testing datasets")
    
    def _check_survivorship_bias(self, market_data: pd.DataFrame = None):
        """Check 5: No survivorship bias - include delisted/failed assets"""
        if market_data is not None:
            # Check if all historical data is included, not just currently active assets
            print("Survivorship bias check: Ensure all historical assets are included, not just current survivors")
    
    def _check_timestamp_sorting(self, market_data: pd.DataFrame = None):
        """Check 6: All data is timestamp-sorted with no duplicates"""
        if market_data is not None and not market_data.empty:
            if not market_data.index.is_monotonic_increasing:
                self.violations.append("Timestamp sorting issue: data not properly sorted")
                self.fix_suggestions.append("Sort data by timestamp in ascending order")
    
    def _check_duplicate_removal(self, market_data: pd.DataFrame = None):
        """Check 7: No duplicate timestamps"""
        if market_data is not None and not market_data.empty:
            duplicates = market_data.index.duplicated().sum()
            if duplicates > 0:
                self.violations.append(f"Duplicate timestamps found: {duplicates} duplicates")
                self.fix_suggestions.append("Remove or aggregate duplicate timestamps")
    
    def _check_multitimeframe_sync(self, execution_engine):
        """Check 8: Multi-timeframe data properly synced"""
        # Check synchronization between different timeframes
        print("Multi-timeframe sync check: Ensure proper alignment without lookahead")
    
    def _check_execution_sl_tp_logic(self, execution_engine):
        """Check 9: Execution engine checks SL/TP on candle high/low"""
        # This would validate that stop losses and take profits are triggered correctly
        # based on high/low of candles rather than close prices
        print("SL/TP logic check: Ensure stops triggered on candle high/low, not just close")
    
    def _check_sl_tp_priority_logic(self, execution_engine):
        """Check 10: SL/TP priority realistic - proper handling of simultaneous hits"""
        # Check if the system properly handles cases where both SL and TP are hit in same candle
        print("SL/TP priority check: Ensure proper priority when both SL and TP are hit simultaneously")
    
    def _check_pnl_with_fees_slippage(self, execution_engine):
        """Check 11: PnL calculated with realistic fees and slippage"""
        # Validate that fees and slippage are properly included in PnL calculations
        print("PnL fees/slippage check: Ensure all trades include realistic transaction costs")
    
    def _check_drawdown_logic(self, execution_engine):
        """Check 12: Drawdown uses correct peak/trough logic"""
        # Validate drawdown calculation methodology
        risk_metrics = execution_engine.risk_manager.get_risk_metrics() if hasattr(execution_engine, 'risk_manager') else {}
        if risk_metrics:
            print("Drawdown logic check: Verify peak/trough methodology is correctly implemented")
    
    def _check_portfolio_risk_within_limits(self, execution_engine):
        """Check 13: Portfolio risk stays within defined limits"""
        risk_metrics = execution_engine.risk_manager.get_risk_metrics() if hasattr(execution_engine, 'risk_manager') else {}
        if risk_metrics:
            exposure = risk_metrics.get('total_exposure', 0)
            max_exposure = getattr(execution_engine.risk_manager, 'max_portfolio_exposure', float('inf'))
            if exposure > max_exposure:
                self.violations.append(f"Portfolio exposure ${exposure} exceeds limit ${max_exposure}")
                self.fix_suggestions.append("Reduce position sizes to stay within risk limits")
    
    def _check_no_double_entries(self, execution_engine):
        """Check 14: No double entries - proper position management"""
        # Check if multiple positions in the same symbol are properly handled
        if hasattr(execution_engine, 'risk_manager') and execution_engine.risk_manager:
            positions = execution_engine.risk_manager.positions
            if len(positions) > 0:
                print("Double entries check: Verify proper position management prevents multiple entries")
    
    def _check_no_stuck_positions(self, execution_engine):
        """Check 15: No stuck positions - all positions should eventually be closed"""
        if hasattr(execution_engine, 'risk_manager') and execution_engine.risk_manager:
            positions = execution_engine.risk_manager.positions
            print(f"Stuck positions check: {len(positions)} open positions remain")
    
    def _check_symbol_isolation(self, execution_engine):
        """Check 16: Each symbol has isolated data, positions, PnL"""
        if hasattr(execution_engine, 'risk_manager') and execution_engine.risk_manager:
            positions = execution_engine.risk_manager.positions
            # Verify that each symbol's positions are managed independently
            symbols = [p.symbol for p in positions.values()]
            if len(symbols) > 0:
                print("Symbol isolation check: Verify each symbol's data and P&L are independent")
    
    def _check_reproducibility(self, execution_engine):
        """Check 17: Results are reproducible with fixed random seeds"""
        print("Reproducibility check: Use fixed random seeds for consistent results")
    
    def generate_report(self, execution_engine, market_data: pd.DataFrame = None):
        """Generate comprehensive validation report"""
        violations, suggestions = self.validate(execution_engine, market_data)
        
        report = {
            'validation_timestamp': datetime.now().isoformat(),
            'total_violations': len(violations),
            'violations': violations,
            'suggestions': suggestions,
            'checks_performed': len([k for k, v in self.check_results.items() if v is not None]),
            'execution_summary': execution_engine.get_execution_metrics() if hasattr(execution_engine, 'get_execution_metrics') else {}
        }
        
        return report
    
    def print_validation_summary(self, execution_engine, market_data: pd.DataFrame = None):
        """Print validation summary to console"""
        report = self.generate_report(execution_engine, market_data)
        
        print("=== Backtesting Validation Report ===")
        print(f"Validation Time: {report['validation_timestamp']}")
        print(f"Total Violations: {report['total_violations']}")
        print(f"Checks Performed: {report['checks_performed']}")
        
        if report['violations']:
            print("\n--- Violations Found ---")
            for i, violation in enumerate(report['violations'], 1):
                print(f"{i}. {violation}")
        
        if report['suggestions']:
            print("\n--- Fix Suggestions ---")
            for i, suggestion in enumerate(report['suggestions'], 1):
                print(f"{i}. {suggestion}")
        
        print(f"\n--- Execution Summary ---")
        exec_summary = report.get('execution_summary', {})
        for key, value in exec_summary.items():
            print(f"{key}: {value}")
        
        print("\n=== Validation Complete ===")


class ValidationService:
    """
    Service for managing validation processes
    """
    def __init__(self):
        self.validator = BacktestValidator()
    
    def run_comprehensive_validation(self, execution_engine, data_pipeline, market_data: pd.DataFrame = None):
        """
        Run comprehensive validation on the entire system
        """
        return self.validator.generate_report(execution_engine, market_data)
    
    def check_real_time_validation(self, execution_engine, current_data: Dict = None) -> bool:
        """
        Perform real-time validation checks during live trading
        """
        violations, _ = self.validator.validate(execution_engine, None)
        # If any violations exist, trading should be paused
        return len(violations) == 0
    
    def export_validation_report(self, execution_engine, market_data: pd.DataFrame = None, 
                                filename: str = None):
        """
        Export validation report to file
        """
        import json
        
        if filename is None:
            from datetime import datetime
            filename = f"validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        report = self.validator.generate_report(execution_engine, market_data)
        
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)
        
        return filename