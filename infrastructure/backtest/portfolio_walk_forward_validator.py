"""
Portfolio Walk-Forward Validation - Advanced validation system for portfolio-level
performance across rolling time windows.
"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from sklearn.metrics import mean_squared_error
import warnings
warnings.filterwarnings('ignore')

from shared.logger import EnhancedLogger


class PortfolioWalkForwardValidator:
    """
    Advanced walk-forward validation system for portfolio-level performance
    across rolling time windows, considering correlation and allocation effects.
    """
    
    def __init__(self, 
                 train_period_days: int = 180,  # 6 months training
                 test_period_days: int = 30,   # 1 month testing
                 step_days: int = 15,          # 15-day steps
                 min_correlation_threshold: float = 0.7,
                 max_drawdown_threshold: float = 0.15,
                 min_sharpe_threshold: float = 0.5):
        
        self.train_period_days = train_period_days
        self.test_period_days = test_period_days
        self.step_days = step_days
        self.min_correlation_threshold = min_correlation_threshold
        self.max_drawdown_threshold = max_drawdown_threshold
        self.min_sharpe_threshold = min_sharpe_threshold
        
        self.logger = EnhancedLogger("PortfolioWalkForwardValidator")
        
        # Storage for validation results
        self.validation_windows = []
        self.portfolio_results = []
        self.correlation_matrices = []
        self.performance_metrics = []
    
    def create_walk_forward_windows(self, 
                                  data_dict: Dict[str, pd.DataFrame]) -> List[Tuple[datetime, datetime, datetime, datetime]]:
        """
        Create walk-forward validation windows based on available data.
        
        Returns:
            List of tuples (train_start, train_end, test_start, test_end)
        """
        if not data_dict:
            return []
        
        # Find the overall date range across all symbols
        all_dates = []
        for df in data_dict.values():
            if not df.empty:
                all_dates.extend(df.index.tolist())
        
        if not all_dates:
            return []
        
        # Convert to datetime and sort
        all_dates = pd.to_datetime(all_dates)
        min_date = all_dates.min()
        max_date = all_dates.max()
        
        # Create windows
        windows = []
        current_start = min_date
        
        while current_start + pd.Timedelta(days=self.train_period_days + self.test_period_days) <= max_date:
            train_start = current_start
            train_end = current_start + pd.Timedelta(days=self.train_period_days)
            test_start = train_end
            test_end = test_start + pd.Timedelta(days=self.test_period_days)
            
            # Ensure test period doesn't exceed available data
            if test_end > max_date:
                test_end = max_date
            
            windows.append((train_start, train_end, test_start, test_end))
            
            # Move to next window
            current_start += pd.Timedelta(days=self.step_days)
        
        self.logger.info(f"Created {len(windows)} walk-forward validation windows")
        
        return windows
    
    def run_portfolio_walk_forward_validation(self, 
                                           data_dict: Dict[str, pd.DataFrame],
                                           strategy_functions: Dict[str, callable],
                                           strategy_params: Dict[str, Dict] = None,
                                           capital_allocator: Any = None) -> Dict[str, Any]:
        """
        Run portfolio-level walk-forward validation.
        """
        if strategy_params is None:
            strategy_params = {}
        
        # Create walk-forward windows
        windows = self.create_walk_forward_windows(data_dict)
        
        if not windows:
            return {"error": "No valid walk-forward windows created"}
        
        # Initialize results storage
        all_results = {
            'windows': [],
            'portfolio_performance': [],
            'correlation_analysis': [],
            'validation_metrics': {},
            'success_rate': 0.0
        }
        
        successful_periods = 0
        
        for i, (train_start, train_end, test_start, test_end) in enumerate(windows):
            self.logger.info(f"Processing window {i+1}/{len(windows)}: {train_start.date()} to {test_end.date()}")
            
            # Split data into training and testing periods
            train_data = {symbol: df[(df.index >= train_start) & (df.index <= train_end)] 
                         for symbol, df in data_dict.items() if not df.empty}
            test_data = {symbol: df[(df.index >= test_start) & (df.index <= test_end)] 
                        for symbol, df in data_dict.items() if not df.empty}
            
            # Skip if insufficient data
            if not train_data or not test_data:
                self.logger.warning(f"Insufficient data for window {i+1}, skipping...")
                continue
            
            # Run training period backtests
            train_results = self._run_period_backtests(train_data, strategy_functions, strategy_params)
            
            # Calculate correlations during training period
            correlation_matrix = self._calculate_correlation_matrix(train_results)
            
            # Determine strategy allocations based on training results
            if capital_allocator:
                # Use provided capital allocator
                strategy_names = list(train_results.keys())
                allocations = capital_allocator.calculate_allocations(
                    strategy_names, 
                    correlation_matrix
                )
            else:
                # Use equal allocations as fallback
                strategy_names = list(train_results.keys())
                equal_allocation = 1.0 / len(strategy_names) if strategy_names else 1.0
                allocations = {name: equal_allocation for name in strategy_names}
            
            # Run testing period backtests
            test_results = self._run_period_backtests(test_data, strategy_functions, strategy_params)
            
            # Calculate portfolio-level performance for this window
            portfolio_metrics = self._calculate_portfolio_metrics(
                test_results, 
                allocations, 
                correlation_matrix
            )
            
            # Validate performance against thresholds
            is_valid = self._validate_portfolio_performance(portfolio_metrics)
            
            if is_valid:
                successful_periods += 1
            
            # Store results for this window
            window_result = {
                'window_id': i,
                'train_period': {
                    'start': train_start.isoformat(),
                    'end': train_end.isoformat()
                },
                'test_period': {
                    'start': test_start.isoformat(),
                    'end': test_end.isoformat()
                },
                'train_results': train_results,
                'test_results': test_results,
                'allocations': allocations,
                'correlation_matrix': correlation_matrix.to_dict() if not correlation_matrix.empty else {},
                'portfolio_metrics': portfolio_metrics,
                'is_valid': is_valid
            }
            
            all_results['windows'].append(window_result)
            all_results['portfolio_performance'].append(portfolio_metrics)
        
        # Calculate overall validation metrics
        all_results['validation_metrics'] = self._calculate_validation_metrics(all_results['portfolio_performance'])
        all_results['success_rate'] = successful_periods / len(windows) if windows else 0.0
        
        self.logger.info(f"Portfolio walk-forward validation completed. Success rate: {all_results['success_rate']:.2%}")
        
        return all_results
    
    def _run_period_backtests(self, 
                            data_dict: Dict[str, pd.DataFrame], 
                            strategy_functions: Dict[str, callable],
                            strategy_params: Dict[str, Dict]) -> Dict[str, Dict[str, Any]]:
        """Run backtests for all strategies on all symbols in the given period."""
        from infrastructure.backtest.realistic_backtester import RealisticBacktester
        from infrastructure.portfolio.comprehensive_portfolio_backtester import load_sample_strategies
        
        results = {}
        
        for strategy_name, strategy_func in strategy_functions.items():
            strategy_results = {}
            
            for symbol, df in data_dict.items():
                if df.empty or len(df) < 10:
                    continue
                
                # Calculate indicators with shifting
                df_with_indicators = self._calculate_indicators_with_shifting(df)
                
                # Fill NaN values
                df_with_indicators = df_with_indicators.fillna(method='ffill').fillna(method='bfill')
                df_with_indicators = df_with_indicators.fillna(0)
                
                if len(df_with_indicators) < 10:
                    continue
                
                # Run backtest
                backtester = RealisticBacktester()
                params = strategy_params.get(strategy_name, {})
                
                try:
                    result = backtester.run_backtest(
                        data=df_with_indicators,
                        strategy_function=strategy_func,
                        strategy_params=params
                    )
                    
                    if 'error' not in result:
                        strategy_results[symbol] = result
                except Exception as e:
                    self.logger.error(f"Backtest error for {strategy_name} on {symbol}: {e}")
            
            if strategy_results:
                results[strategy_name] = strategy_results
        
        return results
    
    def _calculate_indicators_with_shifting(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate technical indicators with proper shifting to prevent lookahead bias."""
        df = df.copy()

        # RSI with shifting
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = (100 - (100 / (1 + rs))).shift(1)  # Shift to prevent lookahead

        # Moving averages with shifting
        df['sma_5'] = df['close'].rolling(window=5).mean().shift(1)
        df['sma_10'] = df['close'].rolling(window=10).mean().shift(1)
        df['sma_20'] = df['close'].rolling(window=20).mean().shift(1)
        df['sma_50'] = df['close'].rolling(window=50).mean().shift(1)

        # Bollinger Bands with shifting
        df['bb_middle'] = df['close'].rolling(window=20).mean().shift(1)
        bb_std = df['close'].rolling(window=20).std().shift(1)
        df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
        df['bb_lower'] = df['bb_middle'] - (bb_std * 2)

        # ATR (Average True Range) with shifting
        high_low = df['high'] - df['low']
        high_close = abs(df['high'] - df['close'].shift(1))  # Use previous close
        low_close = abs(df['low'] - df['close'].shift(1))    # Use previous close
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['atr'] = tr.rolling(window=14).mean().shift(1)

        # Rate of Change (ROC) with shifting
        df['roc_10'] = ((df['close'] - df['close'].shift(11)) / df['close'].shift(11)).shift(1)

        # ADX (Average Directional Index) - for trend strength
        up_move = df['high'] - df['high'].shift(1)
        down_move = df['low'].shift(1) - df['low']
        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)
        plus_di_raw = 100 * (pd.Series(plus_dm).rolling(window=14).mean() / df['atr'])
        minus_di_raw = 100 * (pd.Series(minus_dm).rolling(window=14).mean() / df['atr'])

        # Handle division by zero
        plus_di = plus_di_raw.shift(1)
        minus_di = minus_di_raw.shift(1)

        # Calculate DX with division by zero handling
        di_sum = plus_di + minus_di
        di_diff = abs(plus_di - minus_di)
        dx = np.where(di_sum != 0, 100 * di_diff / di_sum, 0)
        df['adx'] = pd.Series(dx).rolling(window=14).mean().shift(1)

        # Volume indicators with shifting
        df['sma_volume_20'] = df['volume'].rolling(window=20).mean().shift(1)
        df['sma_atr_20'] = df['atr'].rolling(window=20).mean().shift(1)

        # High/Low indicators with shifting
        df['high_5'] = df['high'].rolling(window=5).max().shift(1)
        df['high_20'] = df['high'].rolling(window=20).max().shift(1)
        df['low_5'] = df['low'].rolling(window=5).min().shift(1)
        df['low_20'] = df['low'].rolling(window=20).min().shift(1)

        # VWAP (Volume Weighted Average Price) - simplified version
        # For simplicity, we'll approximate VWAP using typical price weighted by volume
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        df['vwap'] = (typical_price * df['volume']).rolling(window=20).sum().shift(1) / df['volume'].rolling(window=20).sum().shift(1)

        # Bid-Ask Spread approximation (using high-low as proxy)
        df['bid_ask_spread'] = (df['high'] - df['low']) / df['close']

        # Multi-timeframe indicators (simulated)
        # For demonstration purposes, we'll create slower moving averages as "longer timeframe" indicators
        df['sma_20_short'] = df['close'].rolling(window=20).mean().shift(1)  # Shorter timeframe
        df['sma_50_short'] = df['close'].rolling(window=50).mean().shift(1)  # Shorter timeframe
        df['sma_20_long'] = df['close'].rolling(window=20).mean().shift(1)   # Longer timeframe (simulated)
        df['sma_50_long'] = df['close'].rolling(window=50).mean().shift(1)   # Longer timeframe (simulated)

        # Volatility regime indicators
        df['volatility_regime'] = df['atr'].rolling(window=20).mean().shift(1)
        df['volatility_percentile'] = df['atr'].rolling(window=100).rank(pct=True).shift(1)

        # Trend strength indicator
        df['trend_strength'] = abs(df['sma_20'] - df['sma_50']) / df['atr']

        return df
    
    def _calculate_correlation_matrix(self, results: Dict[str, Dict[str, Any]]) -> pd.DataFrame:
        """Calculate correlation matrix between strategy returns."""
        # Extract returns for each strategy-symbol combination
        returns_data = {}

        for strategy_name, strategy_results in results.items():
            for symbol, result in strategy_results.items():
                if 'equity_curve' in result and result['equity_curve']:
                    equity_values = [point['equity'] for point in result['equity_curve']]
                    if len(equity_values) > 1:
                        returns = np.diff(equity_values) / equity_values[:-1]
                        returns_data[f"{strategy_name}_{symbol}"] = returns

        if not returns_data:
            return pd.DataFrame()

        # Find the minimum length among all return series
        min_length = min(len(returns) for returns in returns_data.values()) if returns_data else 0

        # Truncate all return series to the same minimum length to avoid DataFrame creation errors
        for key in returns_data:
            returns_data[key] = returns_data[key][:min_length]

        # Create DataFrame
        returns_df = pd.DataFrame(returns_data)

        # Calculate correlation matrix
        correlation_matrix = returns_df.corr()

        return correlation_matrix
    
    def _calculate_portfolio_metrics(self,
                                   results: Dict[str, Dict[str, Any]],
                                   allocations: Dict[str, float],
                                   correlation_matrix: pd.DataFrame) -> Dict[str, float]:
        """Calculate portfolio-level metrics."""
        # Calculate portfolio equity curve by combining strategy equity curves weighted by allocation
        portfolio_equity_curve = []
        strategy_equity_curves = {}

        # Collect all strategy equity curves
        for strategy_name, strategy_results in results.items():
            if strategy_name in allocations:
                allocation_weight = allocations[strategy_name]

                # Aggregate equity curves from all symbols for this strategy
                strategy_equity_points = {}

                for symbol, result in strategy_results.items():
                    if 'equity_curve' in result and result['equity_curve']:
                        for point in result['equity_curve']:
                            timestamp = point['timestamp']
                            equity = point['equity']

                            if timestamp not in strategy_equity_points:
                                strategy_equity_points[timestamp] = []
                            strategy_equity_points[timestamp].append(equity * allocation_weight)

                # Average the equity values at each timestamp for this strategy
                averaged_equity = {}
                for timestamp, equities in strategy_equity_points.items():
                    averaged_equity[timestamp] = np.mean(equities)

                strategy_equity_curves[strategy_name] = averaged_equity

        # Combine all strategy equity curves into portfolio equity curve
        all_timestamps = set()
        for equity_curve in strategy_equity_curves.values():
            all_timestamps.update(equity_curve.keys())

        all_timestamps = sorted(list(all_timestamps))

        portfolio_values = []
        for timestamp in all_timestamps:
            portfolio_value = 0
            for strategy_name, equity_curve in strategy_equity_curves.items():
                if timestamp in equity_curve:
                    portfolio_value += equity_curve[timestamp]
            portfolio_values.append({'timestamp': timestamp, 'equity': portfolio_value})

        if not portfolio_values:
            return {
                'total_return': 0.0,
                'sharpe_ratio': 0.0,
                'max_drawdown': 0.0,
                'volatility': 0.0,
                'win_rate': 0.0,
                'profit_factor': 1.0,
                'portfolio_equity_curve': []
            }

        # Calculate returns from equity curve
        equity_values = [point['equity'] for point in portfolio_values]
        if len(equity_values) < 2:
            return {
                'total_return': 0.0,
                'sharpe_ratio': 0.0,
                'max_drawdown': 0.0,
                'volatility': 0.0,
                'win_rate': 0.0,
                'profit_factor': 1.0,
                'portfolio_equity_curve': portfolio_values
            }

        # Calculate daily returns
        returns = np.diff(equity_values) / equity_values[:-1]

        # Calculate total return
        total_return = (equity_values[-1] - equity_values[0]) / equity_values[0]

        # Calculate volatility (standard deviation of returns)
        volatility = np.std(returns) * np.sqrt(252)  # Annualized volatility

        # Calculate Sharpe ratio (assuming risk-free rate of 0.02 annually)
        risk_free_rate = 0.02 / 252  # Daily risk-free rate
        excess_returns = returns - risk_free_rate
        if volatility > 0:
            sharpe_ratio = np.mean(excess_returns) / volatility * np.sqrt(252)  # Annualized Sharpe
        else:
            sharpe_ratio = 0.0

        # Calculate max drawdown
        cumulative_returns = np.concatenate([[1.0], equity_values / equity_values[0]])
        running_max = np.maximum.accumulate(cumulative_returns)
        drawdowns = (cumulative_returns - running_max) / running_max
        max_drawdown = float(np.min(drawdowns))

        # Calculate win rate (percentage of positive returns)
        positive_returns = np.sum(returns > 0)
        win_rate = positive_returns / len(returns) if len(returns) > 0 else 0.0

        # Calculate profit factor
        gains = returns[returns > 0]
        losses = returns[returns < 0]
        gross_profit = np.sum(gains) if len(gains) > 0 else 0.0
        gross_loss = abs(np.sum(losses)) if len(losses) > 0 else 0.0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')

        # Calculate drawdown recovery time
        from infrastructure.portfolio.comprehensive_portfolio_backtester import ComprehensivePortfolioBacktester
        drawdown_analyzer = ComprehensivePortfolioBacktester()
        recovery_metrics = drawdown_analyzer.calculate_drawdown_recovery_time(portfolio_values)

        return {
            'total_return': float(total_return),
            'sharpe_ratio': float(sharpe_ratio),
            'max_drawdown': float(max_drawdown),
            'volatility': float(volatility),
            'win_rate': float(win_rate),
            'profit_factor': float(profit_factor),
            'portfolio_equity_curve': portfolio_values,
            'drawdown_recovery_metrics': recovery_metrics
        }
    
    def _validate_portfolio_performance(self, metrics: Dict[str, float]) -> bool:
        """Validate portfolio performance against thresholds."""
        # Check if Sharpe ratio meets minimum threshold
        sharpe_valid = metrics.get('sharpe_ratio', 0) >= self.min_sharpe_threshold
        
        # Check if drawdown is within acceptable limits
        drawdown_valid = abs(metrics.get('max_drawdown', 0)) <= self.max_drawdown_threshold
        
        # Check if return is positive
        return_positive = metrics.get('total_return', 0) >= 0
        
        return sharpe_valid and drawdown_valid and return_positive
    
    def _calculate_validation_metrics(self, portfolio_performance: List[Dict[str, float]]) -> Dict[str, float]:
        """Calculate overall validation metrics."""
        if not portfolio_performance:
            return {}
        
        # Extract metrics
        returns = [p.get('total_return', 0) for p in portfolio_performance]
        sharpes = [p.get('sharpe_ratio', 0) for p in portfolio_performance]
        drawdowns = [p.get('max_drawdown', 0) for p in portfolio_performance]
        win_rates = [p.get('win_rate', 0) for p in portfolio_performance]
        profit_factors = [p.get('profit_factor', 1.0) for p in portfolio_performance]
        
        # Calculate statistics
        metrics = {
            'avg_total_return': float(np.mean(returns)) if returns else 0.0,
            'std_total_return': float(np.std(returns)) if returns else 0.0,
            'avg_sharpe_ratio': float(np.mean(sharpes)) if sharpes else 0.0,
            'std_sharpe_ratio': float(np.std(sharpes)) if sharpes else 0.0,
            'avg_max_drawdown': float(np.mean(drawdowns)) if drawdowns else 0.0,
            'max_max_drawdown': float(np.min(drawdowns)) if drawdowns else 0.0,  # Most negative drawdown
            'avg_win_rate': float(np.mean(win_rates)) if win_rates else 0.0,
            'avg_profit_factor': float(np.mean(profit_factors)) if profit_factors else 0.0,
            'total_periods': len(portfolio_performance),
            'positive_return_periods': sum(1 for r in returns if r > 0),
            'consistency_score': self._calculate_consistency_score(returns)
        }
        
        return metrics
    
    def _calculate_consistency_score(self, returns: List[float]) -> float:
        """Calculate consistency score based on return stability."""
        if len(returns) < 2:
            return 0.0
        
        # Calculate coefficient of variation (lower is more consistent)
        mean_return = np.mean(returns)
        std_return = np.std(returns)
        
        if mean_return == 0:
            return 0.0 if std_return > 0 else 1.0
        
        # Coefficient of variation
        cv = abs(std_return / mean_return)
        
        # Convert to consistency score (0-1 scale, higher is better)
        consistency = max(0, min(1, 1 - cv))
        
        return consistency


def run_portfolio_walk_forward_validation_from_backtest_results(
    backtest_results: Dict[str, Any],
    data_dict: Dict[str, pd.DataFrame],
    strategy_functions: Dict[str, callable],
    strategy_params: Dict[str, Dict] = None
) -> Dict[str, Any]:
    """
    Run portfolio walk-forward validation using backtest results as input.
    """
    logger = EnhancedLogger("PortfolioWFOFromResults")
    
    # Initialize validator
    validator = PortfolioWalkForwardValidator()
    
    # Run portfolio walk-forward validation
    results = validator.run_portfolio_walk_forward_validation(
        data_dict=data_dict,
        strategy_functions=strategy_functions,
        strategy_params=strategy_params
    )
    
    logger.info("Portfolio walk-forward validation completed from backtest results")
    
    return results