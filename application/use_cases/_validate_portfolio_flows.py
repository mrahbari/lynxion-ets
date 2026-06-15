"""E5.T5 split: validate_portfolio validation-flow methods (mixin). Behavior-preserving;
methods moved verbatim, composed via inheritance. No trade surface."""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

import pandas as pd
import numpy as np

from shared.logger import EnhancedLogger
from shared.mock_data_guard import mock_data_allowed
from application.use_cases._validate_portfolio_support import (
    PortfolioBacktestRequest, ComprehensiveValidationRequest, ExtendedHorizonRequest, generate_mock_data,
)


class _ValidatePortfolioFlowsMixin:
    """run_portfolio_backtest / run_comprehensive_validation / run_extended_horizon."""

    def run_portfolio_backtest(self, request: PortfolioBacktestRequest) -> Dict[str, Any]:
        """Run the comprehensive portfolio backtest process."""
        symbols = request.symbols
        strategy_functions = request.strategy_functions
        strategy_params = request.strategy_params
        start_date = request.start_date
        end_date = request.end_date
        initial_capital = request.initial_capital
        fee_rate = request.fee_rate
        slippage_factor = request.slippage_factor
        min_success_rate = request.min_success_rate

        logger = EnhancedLogger("ComprehensivePortfolioBacktestRunner")

        print(f"🔄 Starting comprehensive portfolio backtest...")
        print(f"   Symbols: {symbols}")
        print(f"   Strategies: {list(strategy_functions.keys())}")
        print(f"   Date Range: {start_date.date()} to {end_date.date()}")
        print(f"   Initial Capital: ${initial_capital:,.2f}")
        print(f"   Fee Rate: {fee_rate:.3%}")
        print(f"   Slippage Factor: {slippage_factor:.3%}")
        print(f"   Min Success Rate: {min_success_rate:.1%}")
        print(f"   Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        start_time = datetime.now()

        # Initialize comprehensive portfolio backtester
        backtester = self._build_backtester(initial_capital, fee_rate, slippage_factor)

        try:
            # Run comprehensive backtest
            results = backtester.run_comprehensive_backtest(
                symbols=symbols,
                strategy_functions=strategy_functions,
                strategy_params=strategy_params,
                start_date=start_date,
                end_date=end_date,
                min_success_rate=min_success_rate
            )

            if 'error' not in results:
                print(f"   ✅ Comprehensive backtest completed successfully")

                # Print summary
                summary = results['summary']
                print(f"\n📊 PORTFOLIO BACKTEST SUMMARY")
                print(f"   Total Strategies: {summary['total_strategies']}")
                print(f"   Accepted Strategies: {summary['accepted_strategies_count']}")
                print(f"   Rejected Strategies: {summary['rejected_strategies_count']}")
                print(f"   Total Symbols: {summary['total_symbols']}")
                print(f"   Data Available: {summary['data_symbols_count']}")

                # Print strategy rankings
                print(f"\n🏆 STRATEGY RANKINGS (by Return)")
                for i, ranking in enumerate(results['strategy_rankings'][:10], 1):  # Top 10
                    status = "✅" if ranking['acceptance_status'] == 'accepted' else "❌"
                    print(f"   {i}. {ranking['strategy']:<20} "
                          f"Return: {ranking['avg_return']:.2%}, "
                          f"Sharpe: {ranking['avg_sharpe']:.2f}, "
                          f"Status: {status}")

                # Print accepted strategies with weights
                print(f"\n💰 ACCEPTED STRATEGIES WITH CAPITAL ALLOCATION")
                for strategy_name in results['accepted_strategies']:
                    weight = results['capital_weights'].get(strategy_name, 0)
                    metrics = results['admission_metrics'][strategy_name]
                    print(f"   • {strategy_name:<20} "
                          f"Weight: {weight:.2%}, "
                          f"Return: {metrics['avg_return']:.2%}, "
                          f"Sharpe: {metrics['avg_sharpe']:.2f}")

            else:
                print(f"   ❌ Comprehensive backtest failed: {results['error']}")

        except Exception as e:
            print(f"   ❌ Error during comprehensive portfolio backtest: {e}")
            import traceback
            traceback.print_exc()
            results = {"error": str(e)}

        # Add end time and duration
        end_time = datetime.now()
        results['end_time'] = end_time.isoformat()
        results['duration_seconds'] = (end_time - start_time).total_seconds()

        # Print final summary
        print(f"\n⏱️  PROCESSING TIME: {results['duration_seconds']:.2f}s")

        return results

    # ------------------------------------------------------------------
    # Comprehensive hedge-fund validation (runner_comprehensive_validation)
    # ------------------------------------------------------------------
    def run_comprehensive_validation(self, request: ComprehensiveValidationRequest) -> Dict[str, Any]:
        """Run the complete hedge fund validation pipeline."""
        symbols = request.symbols
        strategy_functions = request.strategy_functions
        strategy_params = request.strategy_params
        start_date = request.start_date
        end_date = request.end_date
        initial_capital = request.initial_capital
        fee_rate = request.fee_rate
        slippage_factor = request.slippage_factor
        min_success_rate = request.min_success_rate

        logger = EnhancedLogger("ComprehensiveHedgeFundValidation")

        print(f"🚀 Starting comprehensive hedge fund validation pipeline...")
        print(f"   Symbols: {symbols}")
        print(f"   Strategies: {list(strategy_functions.keys())}")
        print(f"   Date Range: {start_date.date()} to {end_date.date()}")
        print(f"   Initial Capital: ${initial_capital:,.2f}")
        print(f"   Fee Rate: {fee_rate:.3%}")
        print(f"   Slippage Factor: {slippage_factor:.3%}")
        print(f"   Min Success Rate: {min_success_rate:.1%}")
        print(f"   Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        start_time = datetime.now()

        # Initialize comprehensive portfolio backtester
        backtester = self._build_backtester(initial_capital, fee_rate, slippage_factor)

        # Load data for all symbols
        data_loader = self._get_csv_loader()
        data_dict = {}

        # E-P5.2 T3: the mock-data decision is no longer derived from settings/
        # profile (which made dev runs silently fabricate data). It is gated by
        # the explicit unit-test-only guard, so any wired validation run leaves
        # this False and missing/insufficient data raises below.
        use_mock_data = mock_data_allowed()

        for symbol in symbols:
            try:
                df = data_loader.load(symbol=symbol)

                if df.empty:
                    if use_mock_data:
                        logger.warning(f"No real data found for {symbol}, generating mock data")
                        # Generate mock data for testing
                        df = generate_mock_data(symbol, days=(end_date - start_date).days)
                    else:
                        logger.error(f"No real data found for {symbol}, and mock data is forbidden in production validation.")
                        raise RuntimeError(f"Real data not found for {symbol}, and mock data is forbidden in production validation.")
                else:
                    # Convert timestamp column to datetime if it exists
                    if 'timestamp' in df.columns:
                        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
                        # Filter data by date range using the timestamp column
                        df = df[(df['timestamp'] >= start_date) & (df['timestamp'] <= end_date)]
                        # Set timestamp as index for compatibility with the rest of the system
                        df = df.set_index('timestamp')
                    else:
                        # If no timestamp column, try to use index as datetime
                        df.index = pd.to_datetime(df.index)
                        df = df[(df.index >= start_date) & (df.index <= end_date)]

                if len(df) < 10:
                    if use_mock_data:
                        logger.warning(f"Insufficient data for {symbol} (only {len(df)} rows), generating mock data")
                        df = generate_mock_data(symbol, days=(end_date - start_date).days)
                    else:
                        logger.error(f"Insufficient data for {symbol} (only {len(df)} rows), and mock data is forbidden in production validation.")
                        raise RuntimeError(f"Insufficient real data for {symbol}, and mock data is forbidden in production validation.")

                data_dict[symbol] = df
                logger.info(f"Using data for {symbol} ({len(df)} rows)")

            except Exception as e:
                if use_mock_data:
                    logger.warning(f"Error loading data for {symbol}: {e}, generating mock data")
                    # Generate mock data as fallback
                    df = generate_mock_data(symbol, days=(end_date - start_date).days)
                    data_dict[symbol] = df
                    logger.info(f"Generated mock data for {symbol} ({len(df)} rows)")
                else:
                    logger.error(f"Error loading data for {symbol}: {e}, and mock data is forbidden in production validation.")
                    raise RuntimeError(f"Error loading data for {symbol}: {e}, and mock data is forbidden in production validation.")

        if not data_dict:
            logger.error("No data loaded for any symbols")
            return {"error": "No data available for validation"}

        print(f"   ✅ Loaded/Generated data for {len(data_dict)} symbols")

        # IMPLEMENT HARD DATA INTEGRITY VALIDATION GATE: Block backtesting if data quality is poor
        print(f"\n🔒 DATA INTEGRITY CHECK: Validating data quality before backtesting...")
        integrity_checker = self._get_integrity_checker()

        # Validate data quality for all symbols
        validation_results = integrity_checker.validate_multiple_symbols(
            data_dict,
            symbols,
            start_date,
            end_date,
            timeframe="1d",  # Assuming daily data based on the context
            max_missing_ratio=0.05  # Maximum 5% missing data allowed
        )

        # Check if any symbol failed validation
        failed_symbols = [symbol for symbol, is_valid in validation_results.items() if not is_valid]
        if failed_symbols:
            logger.error(f"Data integrity validation failed for symbols: {failed_symbols}")
            print(f"   ❌ Data integrity validation failed for {len(failed_symbols)} symbols: {failed_symbols}")
            print(f"   🚫 BLOCKING backtest execution due to poor data quality")
            raise RuntimeError(f"Data integrity validation failed for symbols: {failed_symbols}. Backtest blocked due to poor data quality.")

        print(f"   ✅ All {len(symbols)} symbols passed data integrity validation")
        print(f"   📊 Data quality check completed - Ready for backtesting")

        # Phase 1: Run comprehensive portfolio backtest
        print(f"\n🔍 PHASE 1: Running comprehensive portfolio backtest...")
        portfolio_backtest_results = backtester.run_comprehensive_backtest(
            symbols=list(data_dict.keys()),
            strategy_functions=strategy_functions,
            strategy_params=strategy_params,
            start_date=start_date,
            end_date=end_date,
            min_success_rate=min_success_rate
        )

        if 'error' in portfolio_backtest_results:
            print(f"   ❌ Portfolio backtest failed: {portfolio_backtest_results['error']}")
            return portfolio_backtest_results

        print(f"   ✅ Portfolio backtest completed")
        print(f"      Total Strategies: {portfolio_backtest_results['summary']['total_strategies']}")
        print(f"      Accepted Strategies: {portfolio_backtest_results['summary']['accepted_strategies_count']}")
        print(f"      Data Symbols: {portfolio_backtest_results['summary']['data_symbols_count']}")

        # Phase 2: Create capital allocator
        print(f"\n💰 PHASE 2: Creating capital allocator...")
        capital_allocator = self._capital_allocator_factory(
            portfolio_backtest_results,
            total_capital=initial_capital
        )

        if capital_allocator:
            allocations = capital_allocator.calculate_allocations(
                strategy_names=portfolio_backtest_results['accepted_strategies'],
                correlation_matrix=pd.DataFrame(portfolio_backtest_results['correlation_matrix']) if portfolio_backtest_results['correlation_matrix'] else None
            )
            print(f"   ✅ Created capital allocator with {len(allocations)} strategy allocations")

            # Print top allocations
            sorted_allocations = sorted(allocations.items(), key=lambda x: x[1], reverse=True)
            print(f"      Top 5 Allocations:")
            for i, (strategy, alloc) in enumerate(sorted_allocations[:5]):
                print(f"        {i+1}. {strategy}: ${alloc:,.2f} ({alloc/initial_capital:.2%})")
        else:
            print(f"   ⚠️  Failed to create capital allocator")
            allocations = {}

        # Phase 3: Run Monte Carlo risk simulation
        print(f"\n🎲 PHASE 3: Running Monte Carlo risk simulation...")
        monte_carlo_results = self._monte_carlo_analyzer(portfolio_backtest_results)

        if 'error' not in monte_carlo_results:
            print(f"   ✅ Monte Carlo simulation completed")
            # Check the structure of the results
            risk_metrics = {}
            if 'combined_analysis' in monte_carlo_results:
                if 'monte_carlo_results' in monte_carlo_results['combined_analysis']:
                    risk_metrics = monte_carlo_results['combined_analysis']['monte_carlo_results'].get('risk_metrics', {})
                elif 'risk_metrics' in monte_carlo_results['combined_analysis']:
                    risk_metrics = monte_carlo_results['combined_analysis']['risk_metrics']
            elif 'risk_metrics' in monte_carlo_results:
                risk_metrics = monte_carlo_results['risk_metrics']

            print(f"      Probability of Ruin: {risk_metrics.get('probability_of_ruin', 0):.2%}")
            print(f"      Worst Case Drawdown: {risk_metrics.get('worst_case_drawdown', 0):.2%}")
            print(f"      Value at Risk: {risk_metrics.get('value_at_risk', 0):.2%}")
        else:
            print(f"   ⚠️  Monte Carlo simulation failed: {monte_carlo_results['error']}")
            monte_carlo_results = {}

        # Phase 4: Create strategy kill-switch engine
        print(f"\n⚡ PHASE 4: Creating strategy kill-switch engine...")
        kill_switch_engine = self._kill_switch_factory(portfolio_backtest_results)

        if kill_switch_engine:
            print(f"   ✅ Created kill-switch engine with {len(kill_switch_engine.strategy_states)} strategies")

            # Get health report
            health_report = kill_switch_engine.get_strategy_health_report()
            active_strategies = kill_switch_engine.get_active_strategies()
            disabled_strategies = kill_switch_engine.get_disabled_strategies()

            print(f"      Active Strategies: {len(active_strategies)}")
            print(f"      Disabled Strategies: {len(disabled_strategies)}")

            # Print recommendations
            recommendations = kill_switch_engine.get_kill_switch_recommendations()
            if recommendations:
                print(f"      Recommendations: {len(recommendations)}")
                for rec in recommendations[:3]:  # Show first 3
                    print(f"        - {rec['strategy']}: {rec['action']} ({rec['reason'][:50]}...)")
        else:
            print(f"   ⚠️  Failed to create kill-switch engine")
            kill_switch_engine = None

        # Phase 5: Run portfolio walk-forward validation
        print(f"\n📊 PHASE 5: Running portfolio walk-forward validation...")
        walk_forward_results = self._portfolio_walk_forward_validator(
            portfolio_backtest_results,
            data_dict,
            strategy_functions,
            strategy_params
        )

        if 'error' not in walk_forward_results:
            print(f"   ✅ Walk-forward validation completed")
            wf_metrics = walk_forward_results.get('validation_metrics', {})
            success_rate = walk_forward_results.get('success_rate', 0)
            print(f"      Success Rate: {success_rate:.2%}")
            print(f"      Avg Return: {wf_metrics.get('avg_total_return', 0):.2%}")
            print(f"      Avg Sharpe: {wf_metrics.get('avg_sharpe_ratio', 0):.3f}")
        else:
            print(f"   ⚠️  Walk-forward validation failed: {walk_forward_results['error']}")
            walk_forward_results = {}

        # Compile final results
        final_results = {
            'pipeline_start_time': start_time.isoformat(),
            'pipeline_end_time': datetime.now().isoformat(),
            'duration_seconds': (datetime.now() - start_time).total_seconds(),
            'portfolio_backtest_results': portfolio_backtest_results,
            'capital_allocation_results': {
                'allocations': allocations,
                'allocator_summary': capital_allocator.get_allocation_summary() if capital_allocator else {}
            } if capital_allocator else {},
            'monte_carlo_results': monte_carlo_results,
            'kill_switch_results': {
                'health_report': health_report if kill_switch_engine else {},
                'active_strategies': active_strategies if kill_switch_engine else [],
                'disabled_strategies': disabled_strategies if kill_switch_engine else [],
                'recommendations': recommendations if kill_switch_engine else []
            } if kill_switch_engine else {},
            'walk_forward_results': walk_forward_results,
            'validation_summary': {
                'total_strategies': portfolio_backtest_results['summary']['total_strategies'],
                'accepted_strategies': portfolio_backtest_results['summary']['accepted_strategies_count'],
                'data_symbols': portfolio_backtest_results['summary']['data_symbols_count'],
                'monte_carlo_success': 'error' not in monte_carlo_results,
                'walk_forward_success': 'error' not in walk_forward_results,
                'capital_allocator_created': capital_allocator is not None,
                'kill_switch_created': kill_switch_engine is not None
            }
        }

        # Print final summary
        print(f"\n🏆 COMPREHENSIVE VALIDATION SUMMARY")
        print(f"   Pipeline Duration: {final_results['duration_seconds']:.2f}s")
        print(f"   Total Strategies: {final_results['validation_summary']['total_strategies']}")
        print(f"   Accepted Strategies: {final_results['validation_summary']['accepted_strategies']}")
        print(f"   Data Symbols: {final_results['validation_summary']['data_symbols']}")
        print(f"   Monte Carlo Success: {'✅' if final_results['validation_summary']['monte_carlo_success'] else '❌'}")
        print(f"   Walk-Forward Success: {'✅' if final_results['validation_summary']['walk_forward_success'] else '❌'}")
        print(f"   Capital Allocator: {'✅' if final_results['validation_summary']['capital_allocator_created'] else '❌'}")
        print(f"   Kill Switch: {'✅' if final_results['validation_summary']['kill_switch_created'] else '❌'}")

        # Print top performing strategies
        if 'strategy_rankings' in portfolio_backtest_results:
            top_strategies = portfolio_backtest_results['strategy_rankings'][:5]
            print(f"\n🥇 TOP 5 PERFORMING STRATEGIES:")
            for i, strategy in enumerate(top_strategies, 1):
                status = "✅" if strategy['acceptance_status'] == 'accepted' else "❌"
                print(f"   {i}. {strategy['strategy']:<20} "
                      f"Return: {strategy['avg_return']:.2%}, "
                      f"Sharpe: {strategy['avg_sharpe']:.3f}, "
                      f"Status: {status}")

        return final_results

    # ------------------------------------------------------------------
    # Extended horizon validation (runner_extended_horizon_validation)
    # ------------------------------------------------------------------
    def run_extended_horizon(self, request: ExtendedHorizonRequest) -> Dict[str, Any]:
        """Run extended horizon validation across multiple time periods."""
        horizons = request.horizons
        symbols = request.symbols
        strategy_functions = request.strategy_functions
        strategy_params = request.strategy_params
        initial_capital = request.initial_capital
        fee_rate = request.fee_rate
        slippage_factor = request.slippage_factor
        min_success_rate = request.min_success_rate

        logger = EnhancedLogger("ExtendedHorizonValidation")

        print(f"🚀 Starting extended horizon validation...")
        print(f"   Horizons: {horizons} days")
        print(f"   Symbols: {symbols}")
        print(f"   Strategies: {list(strategy_functions.keys())}")
        print(f"   Initial Capital: ${initial_capital:,.2f}")
        print(f"   Fee Rate: {fee_rate:.3%}")
        print(f"   Slippage Factor: {slippage_factor:.3%}")
        print(f"   Min Success Rate: {min_success_rate:.1%}")
        print(f"   Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        start_time = datetime.now()

        # Initialize comprehensive portfolio backtester
        backtester = self._build_backtester(initial_capital, fee_rate, slippage_factor)

        # Results storage for each horizon
        horizon_results = {}

        for horizon in horizons:
            print(f"\n🔍 HORIZON {horizon} DAYS:")
            print(f"   Calculating date range...")

            # Calculate date range for this horizon
            end_date = datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999)
            start_date = end_date - timedelta(days=horizon)

            print(f"   Date Range: {start_date.date()} to {end_date.date()}")

            # E-P5.2 T3: mock-data decision gated by the explicit unit-test-only
            # guard, not settings/profile. False in any wired validation run.
            use_mock_data = mock_data_allowed()

            # Load data for all symbols
            data_loader = self._get_csv_loader()
            data_dict = {}

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
                        # Check if timestamp column exists (returned by CSV loader)
                        if 'timestamp' in df.columns:
                            # Convert timestamp column to datetime if it exists
                            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s', utc=True)

                            # Convert start_date and end_date to timezone-aware if they aren't already
                            from datetime import timezone
                            if start_date.tzinfo is None:
                                start_date = start_date.replace(tzinfo=timezone.utc)
                            if end_date.tzinfo is None:
                                end_date = end_date.replace(tzinfo=timezone.utc)


                            # Filter data by date range using the timestamp column
                            df = df[(df['timestamp'] >= start_date) & (df['timestamp'] <= end_date)]
                            # Set timestamp as index for compatibility with the rest of the system
                            df = df.set_index('timestamp')
                        else:
                            # If no timestamp column, try to use index as datetime
                            df.index = pd.to_datetime(df.index)

                            # Convert start_date and end_date to timezone-aware if they aren't already
                            from datetime import timezone
                            if start_date.tzinfo is None:
                                start_date = start_date.replace(tzinfo=timezone.utc)
                            if end_date.tzinfo is None:
                                end_date = end_date.replace(tzinfo=timezone.utc)


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
                    logger.info(f"Using data for {symbol} ({len(df)} rows) for {horizon}-day horizon")

                except Exception as e:
                    if use_mock_data:
                        logger.warning(f"Error loading data for {symbol}: {e}, generating mock data")
                        # Generate mock data as fallback
                        df = backtester.generate_mock_data(symbol, start_date, end_date)
                        data_dict[symbol] = df
                        logger.info(f"Generated mock data for {symbol} ({len(df)} rows) for {horizon}-day horizon")
                    else:
                        logger.error(f"Error loading data for {symbol}: {e}, and mock data is forbidden in production validation.")
                        raise RuntimeError(f"Error loading data for {symbol}: {e}, and mock data is forbidden in production validation.")

            if not data_dict:
                logger.error(f"No data loaded for any symbols in {horizon}-day horizon")
                horizon_results[horizon] = {"error": f"No data available for {horizon}-day horizon validation"}
                continue

            print(f"   ✅ Loaded/Generated data for {len(data_dict)} symbols")

            # Run comprehensive portfolio backtest for this horizon
            print(f"   Running comprehensive portfolio backtest...")
            portfolio_backtest_results = backtester.run_comprehensive_backtest(
                symbols=list(data_dict.keys()),
                strategy_functions=strategy_functions,
                strategy_params=strategy_params,
                start_date=start_date,
                end_date=end_date,
                min_success_rate=min_success_rate
            )

            if 'error' in portfolio_backtest_results:
                print(f"   ❌ Portfolio backtest failed: {portfolio_backtest_results['error']}")
                horizon_results[horizon] = portfolio_backtest_results
                continue

            print(f"   ✅ Portfolio backtest completed")
            print(f"      Total Strategies: {portfolio_backtest_results['summary']['total_strategies']}")
            print(f"      Accepted Strategies: {portfolio_backtest_results['summary']['accepted_strategies_count']}")
            print(f"      Data Symbols: {portfolio_backtest_results['summary']['data_symbols_count']}")

            # Create capital allocator
            print(f"   Creating capital allocator...")
            capital_allocator = self._capital_allocator_factory(
                portfolio_backtest_results,
                total_capital=initial_capital
            )

            if capital_allocator:
                allocations = capital_allocator.calculate_allocations(
                    strategy_names=portfolio_backtest_results['accepted_strategies'],
                    correlation_matrix=pd.DataFrame(portfolio_backtest_results['correlation_matrix']) if portfolio_backtest_results['correlation_matrix'] else None
                )
                print(f"   ✅ Created capital allocator with {len(allocations)} strategy allocations")
            else:
                print(f"   ⚠️  Failed to create capital allocator")
                allocations = {}

            # Run Monte Carlo risk simulation
            print(f"   Running Monte Carlo risk simulation...")
            monte_carlo_results = self._monte_carlo_analyzer(portfolio_backtest_results)

            if 'error' not in monte_carlo_results:
                print(f"   ✅ Monte Carlo simulation completed")
            else:
                print(f"   ⚠️  Monte Carlo simulation failed: {monte_carlo_results['error']}")
                monte_carlo_results = {}

            # Create strategy kill-switch engine
            print(f"   Creating strategy kill-switch engine...")
            kill_switch_engine = self._kill_switch_factory(portfolio_backtest_results)

            if kill_switch_engine:
                print(f"   ✅ Created kill-switch engine with {len(kill_switch_engine.strategy_states)} strategies")
            else:
                print(f"   ⚠️  Failed to create kill-switch engine")
                kill_switch_engine = None

            # Run portfolio walk-forward validation
            print(f"   Running portfolio walk-forward validation...")
            walk_forward_results = self._portfolio_walk_forward_validator(
                portfolio_backtest_results,
                data_dict,
                strategy_functions,
                strategy_params
            )

            if 'error' not in walk_forward_results:
                print(f"   ✅ Walk-forward validation completed")
            else:
                print(f"   ⚠️  Walk-forward validation failed: {walk_forward_results['error']}")
                walk_forward_results = {}

            # Store results for this horizon
            horizon_results[horizon] = {
                'portfolio_backtest_results': portfolio_backtest_results,
                'capital_allocation_results': {
                    'allocations': allocations,
                    'allocator_summary': capital_allocator.get_allocation_summary() if capital_allocator else {}
                } if capital_allocator else {},
                'monte_carlo_results': monte_carlo_results,
                'kill_switch_results': {
                    'health_report': kill_switch_engine.get_strategy_health_report() if kill_switch_engine else {},
                    'active_strategies': kill_switch_engine.get_active_strategies() if kill_switch_engine else [],
                    'disabled_strategies': kill_switch_engine.get_disabled_strategies() if kill_switch_engine else [],
                    'recommendations': kill_switch_engine.get_kill_switch_recommendations() if kill_switch_engine else []
                } if kill_switch_engine else {},
                'walk_forward_results': walk_forward_results,
                'date_range': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat(),
                    'days': horizon
                }
            }

            # Print top performing strategies for this horizon
            if 'strategy_rankings' in portfolio_backtest_results:
                top_strategies = portfolio_backtest_results['strategy_rankings'][:5]
                print(f"   🥇 TOP 5 PERFORMING STRATEGIES FOR {horizon}D HORIZON:")
                for i, strategy in enumerate(top_strategies, 1):
                    status = "✅" if strategy['acceptance_status'] == 'accepted' else "❌"
                    print(f"      {i}. {strategy['strategy']:<20} "
                          f"Return: {strategy['avg_return']:.2%}, "
                          f"Sharpe: {strategy['avg_sharpe']:.3f}, "
                          f"Status: {status}")

        # Compile final results
        final_results = {
            'pipeline_start_time': start_time.isoformat(),
            'pipeline_end_time': datetime.now().isoformat(),
            'duration_seconds': (datetime.now() - start_time).total_seconds(),
            'horizon_results': horizon_results,
            'horizons_tested': horizons,
            'symbols': symbols,
            'strategy_functions': list(strategy_functions.keys()),
            'summary': {
                'total_horizons': len(horizons),
                'successful_horizons': len([h for h, r in horizon_results.items() if 'error' not in r]),
                'failed_horizons': len([h for h, r in horizon_results.items() if 'error' in r])
            }
        }

        # Print final summary
        print(f"\n🏆 EXTENDED HORIZON VALIDATION SUMMARY")
        print(f"   Pipeline Duration: {final_results['duration_seconds']:.2f}s")
        print(f"   Total Horizons: {final_results['summary']['total_horizons']}")
        print(f"   Successful Horizons: {final_results['summary']['successful_horizons']}")
        print(f"   Failed Horizons: {final_results['summary']['failed_horizons']}")

        # Print performance decay analysis
        print(f"\n📉 PERFORMANCE DECAY ANALYSIS")
        for horizon in sorted(horizons):
            if horizon in horizon_results and 'error' not in horizon_results[horizon]:
                results = horizon_results[horizon]['portfolio_backtest_results']
                avg_return = np.mean([s['avg_return'] for s in results['strategy_rankings'] if s['acceptance_status'] == 'accepted']) if results['strategy_rankings'] else 0
                avg_sharpe = np.mean([s['avg_sharpe'] for s in results['strategy_rankings'] if s['acceptance_status'] == 'accepted']) if results['strategy_rankings'] else 0
                accepted_count = results['summary']['accepted_strategies_count']

                print(f"   {horizon}D: Return={avg_return:.2%}, Sharpe={avg_sharpe:.3f}, Accepted={accepted_count}")

        return final_results
