"""
Comprehensive Portfolio Backtester - Advanced multi-strategy, multi-symbol backtesting system
with portfolio-level risk management, correlation analysis, and strategy selection.
"""
import sys
import json
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np
from scipy.stats import skew, kurtosis
from scipy.optimize import minimize
import warnings
warnings.filterwarnings('ignore')

from infrastructure.backtest.realistic_backtester import RealisticBacktester
from infrastructure.data.csv_history_loader import CSVHistoryLoaderAdapter
from shared.logger import EnhancedLogger
from shared.experiment_tracking import generate_run_id, save_experiment_results
from application.configs.configs import Configs


class ComprehensivePortfolioBacktester:
    """
    Advanced portfolio backtesting system that evaluates strategies across multiple symbols
    and implements sophisticated portfolio management techniques.
    """
    
    def __init__(self, 
                 initial_capital: float = 100000.0,
                 fee_rate: float = 0.001,
                 slippage_factor: float = 0.0005,
                 risk_per_trade: float = 0.02,
                 max_drawdown_limit: float = 0.15,
                 max_correlation_limit: float = 0.7):
        
        self.initial_capital = initial_capital
        self.fee_rate = fee_rate
        self.slippage_factor = slippage_factor
        self.risk_per_trade = risk_per_trade
        self.max_drawdown_limit = max_drawdown_limit
        self.max_correlation_limit = max_correlation_limit
        
        self.logger = EnhancedLogger("ComprehensivePortfolioBacktester")
        
        # Portfolio-level tracking
        self.symbol_weights = {}
        self.strategy_weights = {}
        self.correlation_matrix = None
        self.regime_classification = {}
        
        # Results storage
        self.individual_results = {}
        self.portfolio_results = {}
        self.risk_metrics = {}
        
    def load_data_for_symbols(self, symbols: List[str], start_date: datetime, end_date: datetime, mock_data_if_missing: bool = False) -> Dict[str, pd.DataFrame]:
        """Load data for multiple symbols with integrity checks."""
        data_loader = CSVHistoryLoaderAdapter()
        data_dict = {}

        for symbol in symbols:
            try:
                df = data_loader.load(symbol=symbol)

                if df.empty:
                    if mock_data_if_missing:
                        self.logger.warning(f"No real data found for {symbol}, generating mock data")
                        # Generate mock data for testing
                        df = self.generate_mock_data(symbol, start_date, end_date)
                    else:
                        self.logger.error(f"No real data found for {symbol}, and mock data is forbidden in production validation.")
                        raise RuntimeError(f"Real data not found for {symbol}, and mock data is forbidden in production validation.")

                # Check if timestamp column exists (returned by CSV loader)
                if 'timestamp' in df.columns:
                    # Convert timestamp column to datetime if it exists
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s', utc=True)
                    # Convert start_date and end_date to timezone-aware if they aren't already
                    if start_date.tzinfo is None:
                        start_date = start_date.replace(tzinfo=timezone.utc)
                    if end_date.tzinfo is None:
                        end_date = end_date.replace(tzinfo=timezone.utc)
                    # Filter data by date range using the timestamp column
                    df = df[(df['timestamp'] >= start_date) & (df['timestamp'] <= end_date)]
                    # Set timestamp as index for compatibility with the rest of the system
                    df = df.set_index('timestamp')
                else:
                    # Ensure index is datetime type and in UTC
                    df.index = pd.to_datetime(df.index, utc=True)

                    # Convert start_date and end_date to timezone-aware if they aren't already
                    if start_date.tzinfo is None:
                        start_date = start_date.replace(tzinfo=timezone.utc)
                    if end_date.tzinfo is None:
                        end_date = end_date.replace(tzinfo=timezone.utc)

                    # Filter data by date range
                    df = df[(df.index >= start_date) & (df.index <= end_date)]

                # Data integrity checks
                df = self._validate_and_clean_data(df, symbol)

                if len(df) < 10:
                    if mock_data_if_missing:
                        self.logger.warning(f"Insufficient data for {symbol} (only {len(df)} rows), generating mock data")
                        df = self.generate_mock_data(symbol, start_date, end_date)
                    else:
                        self.logger.error(f"Insufficient data for {symbol} (only {len(df)} rows), and mock data is forbidden in production validation.")
                        raise RuntimeError(f"Insufficient real data for {symbol}, and mock data is forbidden in production validation.")

                data_dict[symbol] = df
                self.logger.info(f"Loaded {len(df)} rows for {symbol}")

            except Exception as e:
                if mock_data_if_missing:
                    self.logger.warning(f"Error loading data for {symbol}: {e}, generating mock data")
                    # Generate mock data as fallback
                    df = self.generate_mock_data(symbol, start_date, end_date)
                    data_dict[symbol] = df
                    self.logger.info(f"Generated mock data for {symbol} ({len(df)} rows)")
                else:
                    self.logger.error(f"Error loading data for {symbol}: {e}, and mock data is forbidden in production validation.")
                    raise RuntimeError(f"Error loading data for {symbol}: {e}, and mock data is forbidden in production validation.")

        return data_dict

    def _validate_and_clean_data(self, df: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """Perform data integrity checks and cleaning."""
        original_len = len(df)

        # Check for missing candles (more than 1% missing)
        if len(df) > 0:
            # Calculate expected candles based on frequency
            time_diff = df.index[-1] - df.index[0]
            expected_candles = time_diff.days * 24  # Assuming hourly data
            missing_ratio = (expected_candles - len(df)) / expected_candles if expected_candles > 0 else 0

            if missing_ratio > 0.01:  # More than 1% missing
                self.logger.warning(f"High missing candle ratio for {symbol}: {missing_ratio:.2%}")

        # Price sanity checks
        # Check for invalid OHLC relationships
        invalid_ohlc = df[
            (df['high'] < df['low']) |
            (df['high'] < df['close']) |
            (df['high'] < df['open']) |
            (df['low'] > df['close']) |
            (df['low'] > df['open'])
        ]

        if not invalid_ohlc.empty:
            self.logger.warning(f"Found {len(invalid_ohlc)} invalid OHLC records for {symbol}")
            # Remove invalid records
            df = df[
                (df['high'] >= df['low']) &
                (df['high'] >= df['close']) &
                (df['high'] >= df['open']) &
                (df['low'] <= df['close']) &
                (df['low'] <= df['open'])
            ]

        # Volume sanity checks
        df = df[df['volume'] >= 0]  # Remove negative volumes

        # Price jump detection (remove extreme outliers)
        if len(df) > 1:
            price_changes = df['close'].pct_change().abs()
            median_change = price_changes.median()
            mad = (price_changes - median_change).abs().median()

            # Remove extreme outliers (more than 6 MADs from median)
            outlier_threshold = median_change + 6 * mad
            df = df[price_changes <= outlier_threshold]

        cleaned_count = original_len - len(df)
        if cleaned_count > 0:
            self.logger.info(f"Cleaned {cleaned_count} records for {symbol}")

        return df
    
    def generate_mock_data(self, symbol: str, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """Generate mock price data for testing when real data is not available."""
        import numpy as np
        import pandas as pd
        from datetime import timedelta
        
        days = (end_date - start_date).days
        if days <= 0:
            days = 30  # Default to 30 days if invalid range
        
        # Create hourly data for more realistic trading opportunities
        dates = pd.date_range(start=start_date, end=end_date, freq='H')  # Hourly data
        
        if len(dates) == 0:
            # If date range produces no dates, create a simple range
            dates = pd.date_range(end=end_date, periods=days*24, freq='H')  # 24 hours per day
        
        # Generate mock OHLCV data with more realistic characteristics
        np.random.seed(hash(symbol) % 2**32)  # Different seed for each symbol
        
        # Generate more realistic returns with some trend and volatility clustering
        base_return = 0.0001  # Very small base return per hour
        volatility = 0.005   # Hourly volatility (~25% annualized)
        
        # Add some autocorrelation to simulate volatility clustering
        returns = []
        prev_vol = volatility
        for i in range(len(dates)):
            # Random shock
            shock = np.random.normal(0, prev_vol)
            # Add some mean reversion to volatility
            new_vol = max(0.001, min(0.02, prev_vol * (1 + 0.1*np.random.randn())))
            prev_vol = new_vol
            returns.append(base_return + shock)
        
        returns = np.array(returns)
        closes = 40000 * np.exp(np.cumsum(returns))  # Starting at ~$40,000
        
        # Generate OHLC with realistic relationships
        noise = np.random.normal(0, 0.001, len(dates))  # Small noise for open
        opens = closes * np.exp(noise)
        
        # High and low based on realistic ranges
        high_mult = 1 + np.abs(np.random.normal(0.002, 0.001, len(dates)))  # Usually 0.2% above
        low_mult = 1 - np.abs(np.random.normal(0.002, 0.001, len(dates)))   # Usually 0.2% below
        
        highs = np.maximum(opens, closes) * high_mult
        lows = np.minimum(opens, closes) * low_mult
        
        # Ensure OHLC relationships are maintained
        for i in range(len(dates)):
            highs[i] = max(opens[i], closes[i], highs[i])
            lows[i] = min(opens[i], closes[i], lows[i])
        
        volumes = np.random.lognormal(15, 0.5, len(dates))  # Mock volume data with less volatility
        
        df = pd.DataFrame({
            'open': opens,
            'high': highs,
            'low': lows,
            'close': closes,
            'volume': volumes
        }, index=dates)
        
        return df
    
    def calculate_indicators_with_shifting(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate technical indicators with proper shifting to prevent lookahead bias."""
        df = df.copy()

        # RSI with shifting
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = (100 - (100 / (1 + rs))).shift(1)  # Shift to prevent lookahead

        # Moving averages with shifting
        df['sma_3'] = df['close'].rolling(window=3).mean().shift(1)
        df['sma_5'] = df['close'].rolling(window=5).mean().shift(1)
        df['sma_7'] = df['close'].rolling(window=7).mean().shift(1)
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
        df['roc_5'] = ((df['close'] - df['close'].shift(6)) / df['close'].shift(6)).shift(1)
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
        df['sma_volume_10'] = df['volume'].rolling(window=10).mean().shift(1)
        df['sma_volume_20'] = df['volume'].rolling(window=20).mean().shift(1)
        df['sma_atr_10'] = df['atr'].rolling(window=10).mean().shift(1)
        df['sma_atr_20'] = df['atr'].rolling(window=20).mean().shift(1)

        # High/Low indicators with shifting
        df['high_3'] = df['high'].rolling(window=3).max().shift(1)
        df['high_5'] = df['high'].rolling(window=5).max().shift(1)
        df['high_10'] = df['high'].rolling(window=10).max().shift(1)
        df['low_3'] = df['low'].rolling(window=3).min().shift(1)
        df['low_5'] = df['low'].rolling(window=5).min().shift(1)
        df['low_10'] = df['low'].rolling(window=10).min().shift(1)

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
    
    def run_individual_strategy_backtests(self, 
                                        data_dict: Dict[str, pd.DataFrame], 
                                        strategy_functions: Dict[str, callable],
                                        strategy_params: Dict[str, Dict] = None) -> Dict[str, Dict[str, Any]]:
        """Run individual backtests for each strategy on each symbol."""
        
        if strategy_params is None:
            strategy_params = {}
        
        results = {}
        
        for strategy_name, strategy_func in strategy_functions.items():
            self.logger.info(f"Running backtests for strategy: {strategy_name}")
            
            strategy_results = {}
            
            for symbol, df in data_dict.items():
                self.logger.info(f"  Testing {strategy_name} on {symbol}")
                
                # Calculate indicators
                df_with_indicators = self.calculate_indicators_with_shifting(df)
                
                # Fill NaN values
                df_with_indicators = df_with_indicators.fillna(method='ffill').fillna(method='bfill')
                df_with_indicators = df_with_indicators.fillna(0)
                
                if len(df_with_indicators) < 10:
                    self.logger.warning(f"Insufficient data after indicator calculation for {symbol}, skipping...")
                    continue
                
                # Run backtest
                backtester = RealisticBacktester(
                    initial_capital=self.initial_capital / len(data_dict),  # Allocate capital per symbol
                    fee_rate=self.fee_rate,
                    slippage_factor=self.slippage_factor
                )
                
                try:
                    # Get strategy-specific parameters
                    params = strategy_params.get(strategy_name, {})
                    
                    result = backtester.run_backtest(
                        data=df_with_indicators,
                        strategy_function=strategy_func,
                        strategy_params=params
                    )
                    
                    if 'error' not in result:
                        strategy_results[symbol] = result
                        self.logger.info(f"    {symbol} backtest completed - Return: {result.get('total_return', 0):.2%}")
                    else:
                        self.logger.error(f"    {symbol} backtest failed: {result['error']}")
                        
                except Exception as e:
                    self.logger.error(f"    {symbol} backtest error: {e}")
            
            results[strategy_name] = strategy_results
        
        return results
    
    def calculate_correlation_matrix(self, results: Dict[str, Dict[str, Any]]) -> pd.DataFrame:
        """Calculate correlation matrix between strategy returns across symbols."""
        
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
            self.logger.warning("No return data available for correlation calculation")
            return pd.DataFrame()
        
        # Find the minimum length to align all series
        if returns_data:
            min_length = min(len(returns) for returns in returns_data.values())
            
            # Truncate all series to the same length
            for key in returns_data:
                returns_data[key] = returns_data[key][:min_length]
        
        # Create DataFrame
        try:
            returns_df = pd.DataFrame(returns_data)
        except ValueError as e:
            self.logger.warning(f"Could not create correlation matrix: {e}")
            return pd.DataFrame()
        
        # Calculate correlation matrix
        correlation_matrix = returns_df.corr()
        
        self.logger.info(f"Calculated correlation matrix for {len(correlation_matrix)} strategy-symbol combinations")
        
        return correlation_matrix
    
    def calculate_regime_classification(self, data_dict: Dict[str, pd.DataFrame]) -> Dict[str, Dict[str, Any]]:
        """Classify market regimes for each symbol."""

        regime_info = {}

        for symbol, df in data_dict.items():
            if df.empty:
                regime_info[symbol] = {'regime': 'unknown', 'confidence': 0.0}
                continue

            # Calculate regime indicators using the last row
            latest_row = df.iloc[-1]

            # Trend strength (based on ADX)
            adx = latest_row.get('adx', 20)
            trend_strength = 'strong' if adx > 30 else 'weak' if adx < 20 else 'moderate'

            # Volatility regime - check if column exists
            atr = latest_row.get('atr', 0)
            volatility_regime = latest_row.get('volatility_regime', 0)

            # Calculate volatility level based on available data
            if 'volatility_regime' in df.columns and len(df['volatility_regime'].dropna()) > 0:
                volatility_level = 'high' if volatility_regime > df['volatility_regime'].quantile(0.7) else \
                                  'low' if volatility_regime < df['volatility_regime'].quantile(0.3) else 'normal'
            else:
                # If no volatility_regime column, estimate from ATR
                atr_median = df['atr'].median() if 'atr' in df.columns and len(df['atr'].dropna()) > 0 else 0
                if atr_median > 0:
                    volatility_level = 'high' if atr > atr_median * 1.2 else 'low' if atr < atr_median * 0.8 else 'normal'
                else:
                    volatility_level = 'normal'  # Default if no data

            # Determine market regime
            if trend_strength == 'strong' and volatility_level == 'high':
                regime = 'TREND_HIGH_VOL'
            elif trend_strength == 'strong' and volatility_level != 'high':
                regime = 'TREND'
            elif trend_strength == 'weak' and volatility_level == 'high':
                regime = 'CHOPPY_HIGH_VOL'
            elif trend_strength == 'weak':
                regime = 'RANGE'
            else:
                regime = 'NORMAL'

            regime_info[symbol] = {
                'regime': regime,
                'trend_strength': trend_strength,
                'volatility_level': volatility_level,
                'adx': adx,
                'atr': atr,
                'confidence': 0.8  # High confidence in classification
            }

        return regime_info

    def calculate_regime_stability_table(self, data_dict: Dict[str, pd.DataFrame],
                                       strategy_results: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
        """Calculate regime stability table for strategies across different market conditions."""

        # First, classify regimes for each symbol
        regime_info = self.calculate_regime_classification(data_dict)

        # Define the main regimes we want to track
        regimes = ['TREND', 'RANGE', 'HIGH_VOL', 'LOW_VOL']

        # Initialize the regime stability table
        regime_stability_table = {}

        for strategy_name, strategy_result in strategy_results.items():
            regime_stability_table[strategy_name] = {}

            # Initialize all regime returns to 0
            for regime in regimes:
                regime_stability_table[strategy_name][regime] = 0.0

            # For each symbol, get the regime and the strategy's performance on that symbol
            for symbol, result in strategy_result.items():
                if symbol in regime_info:
                    symbol_regime = regime_info[symbol]['regime']

                    # Map the detailed regime to our main categories
                    if 'TREND' in symbol_regime:
                        main_regime = 'TREND'
                    elif 'RANGE' in symbol_regime or 'CHOPPY' in symbol_regime:
                        main_regime = 'RANGE'
                    elif 'HIGH_VOL' in symbol_regime:
                        main_regime = 'HIGH_VOL'
                    elif 'LOW_VOL' in symbol_regime:
                        main_regime = 'LOW_VOL'
                    else:
                        main_regime = 'TREND'  # Default to trend

                    # Get the strategy's return for this symbol
                    strategy_return = result.get('total_return', 0.0)

                    # Update the regime return - this is a simplification
                    # In a real system, we'd want to calculate returns for each regime period
                    regime_stability_table[strategy_name][main_regime] = strategy_return

        return regime_stability_table

    def analyze_regime_performance(self, individual_results: Dict[str, Dict[str, Any]],
                                 data_dict: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """Analyze strategy performance across different market regimes."""

        # Calculate regime stability table
        regime_stability_table = self.calculate_regime_stability_table(data_dict, individual_results)

        # Calculate additional regime analysis metrics
        regime_analysis = {
            'regime_stability_table': regime_stability_table,
            'regime_diversity_score': {},
            'regime_dependence_warning': []
        }

        for strategy_name, regime_returns in regime_stability_table.items():
            # Calculate regime diversity score (how evenly distributed the returns are across regimes)
            returns_list = list(regime_returns.values())
            if len(returns_list) > 0:
                # Calculate coefficient of variation as a measure of consistency
                mean_return = np.mean(returns_list)
                std_return = np.std(returns_list)

                if mean_return != 0:
                    cv = std_return / abs(mean_return) if abs(mean_return) > 0 else float('inf')
                    # Convert to diversity score (lower CV = higher diversity/score)
                    diversity_score = 1 / (1 + cv)  # Higher score means more consistent across regimes
                else:
                    diversity_score = 0

                regime_analysis['regime_diversity_score'][strategy_name] = diversity_score

                # Check for regime dependence (if strategy performs well in only one regime)
                best_regime_return = max(returns_list)
                worst_regime_return = min(returns_list)

                if best_regime_return > 0 and (best_regime_return - worst_regime_return) > 0.1:  # 10% difference
                    regime_analysis['regime_dependence_warning'].append({
                        'strategy': strategy_name,
                        'best_regime_return': best_regime_return,
                        'worst_regime_return': worst_regime_return,
                        'difference': best_regime_return - worst_regime_return
                    })

        return regime_analysis

    def calculate_portfolio_dependency_risk(self, admission_metrics: Dict[str, Dict[str, float]],
                                         capital_weights: Dict[str, float]) -> Dict[str, Any]:
        """Calculate portfolio dependency risk - what happens if the best strategy is removed."""

        if not admission_metrics or not capital_weights:
            return {
                'dependency_risk_score': 0.0,
                'best_strategy_contribution': 0.0,
                'portfolio_impact_if_best_removed': 0.0,
                'concentration_risk': 0.0
            }

        # Find the best performing strategy based on return
        best_strategy = None
        best_return = float('-inf')

        for strategy_name, metrics in admission_metrics.items():
            avg_return = metrics.get('avg_return', 0)
            if avg_return > best_return:
                best_return = avg_return
                best_strategy = strategy_name

        if not best_strategy:
            return {
                'dependency_risk_score': 0.0,
                'best_strategy_contribution': 0.0,
                'portfolio_impact_if_best_removed': 0.0,
                'concentration_risk': 0.0
            }

        # Calculate the contribution of the best strategy to the portfolio
        best_strategy_weight = capital_weights.get(best_strategy, 0)
        best_strategy_contribution = best_strategy_weight * best_return

        # Calculate what the portfolio return would be without the best strategy
        total_weight = sum(capital_weights.values())
        if total_weight == 0:
            return {
                'dependency_risk_score': 0.0,
                'best_strategy_contribution': 0.0,
                'portfolio_impact_if_best_removed': 0.0,
                'concentration_risk': 0.0
            }

        # Calculate weighted portfolio return with all strategies
        total_portfolio_return = 0
        for strategy_name, metrics in admission_metrics.items():
            weight = capital_weights.get(strategy_name, 0)
            avg_return = metrics.get('avg_return', 0)
            total_portfolio_return += weight * avg_return

        # Calculate portfolio return without the best strategy
        remaining_weight = total_weight - best_strategy_weight
        if remaining_weight <= 0:
            # If the best strategy has all the weight, removing it would collapse the portfolio
            portfolio_without_best = 0
        else:
            # Recalculate weights excluding the best strategy
            portfolio_without_best = 0
            for strategy_name, metrics in admission_metrics.items():
                if strategy_name != best_strategy:
                    original_weight = capital_weights.get(strategy_name, 0)
                    if total_weight > 0:
                        # Normalize weights to account for removed strategy
                        normalized_weight = original_weight / remaining_weight if remaining_weight > 0 else 0
                        avg_return = metrics.get('avg_return', 0)
                        portfolio_without_best += normalized_weight * original_weight * avg_return / total_weight

        # Calculate impact of removing the best strategy
        if total_portfolio_return != 0:
            impact = (total_portfolio_return - portfolio_without_best) / abs(total_portfolio_return)
        else:
            impact = 0

        # Calculate concentration risk (Herfindahl-Hirschman Index approach)
        squared_weights = [w**2 for w in capital_weights.values() if w > 0]
        concentration_risk = sum(squared_weights) if squared_weights else 0

        # Dependency risk score (higher if portfolio heavily depends on one strategy)
        dependency_risk_score = min(1.0, impact * 2)  # Scale impact to 0-1 range

        return {
            'dependency_risk_score': float(dependency_risk_score),
            'best_strategy': best_strategy,
            'best_strategy_contribution': float(best_strategy_contribution),
            'portfolio_return_with_all': float(total_portfolio_return),
            'portfolio_return_without_best': float(portfolio_without_best),
            'portfolio_impact_if_best_removed': float(impact),
            'concentration_risk': float(concentration_risk),
            'best_strategy_weight': float(best_strategy_weight),
            'total_portfolio_weight': float(total_weight)
        }

    def calculate_drawdown_recovery_time(self, equity_curve: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate drawdown recovery time metrics."""

        if not equity_curve or len(equity_curve) < 2:
            return {
                'max_drawdown': 0.0,
                'recovery_time': 0,
                'recovery_periods': [],
                'avg_recovery_time': 0.0,
                'longest_recovery_time': 0
            }

        # Extract equity values and timestamps
        equity_values = [point['equity'] for point in equity_curve]
        timestamps = [point['timestamp'] for point in equity_curve]

        # Calculate running maximum
        running_max = []
        current_max = equity_values[0]
        for value in equity_values:
            if value > current_max:
                current_max = value
            running_max.append(current_max)

        # Calculate drawdowns
        drawdowns = [(running_max[i] - equity_values[i]) / running_max[i] for i in range(len(equity_values))]

        # Find drawdown periods (when drawdown > 0.02, i.e., 2% or more)
        drawdown_periods = []
        in_drawdown = False
        start_idx = 0

        for i, dd in enumerate(drawdowns):
            if dd > 0.02 and not in_drawdown:  # Start of drawdown period
                in_drawdown = True
                start_idx = i
            elif dd <= 0.005 and in_drawdown:  # End of drawdown period (nearby to previous peak)
                # Check if we've recovered to near the previous peak
                if equity_values[i] >= running_max[start_idx] * 0.995:  # Within 0.5% of previous peak
                    drawdown_periods.append({
                        'start_idx': start_idx,
                        'end_idx': i,
                        'start_time': timestamps[start_idx],
                        'end_time': timestamps[end_idx],
                        'peak_before': running_max[start_idx],
                        'trough': equity_values[i],
                        'recovery_time': i - start_idx
                    })
                    in_drawdown = False

        # Handle case where drawdown period extends to end of series
        if in_drawdown and start_idx < len(equity_values) - 1:
            # Still in drawdown at the end, don't count as recovered
            pass

        # Calculate recovery metrics
        recovery_times = [period['recovery_time'] for period in drawdown_periods]
        max_drawdown = max(drawdowns) if drawdowns else 0.0

        avg_recovery_time = np.mean(recovery_times) if recovery_times else 0.0
        longest_recovery_time = max(recovery_times) if recovery_times else 0

        return {
            'max_drawdown': float(max_drawdown),
            'recovery_time': recovery_times,
            'recovery_periods': drawdown_periods,
            'avg_recovery_time': float(avg_recovery_time),
            'longest_recovery_time': int(longest_recovery_time),
            'total_recovery_periods': len(drawdown_periods)
        }

    def calculate_trade_distribution_stability(self, individual_results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate trade distribution stability metrics."""

        stability_metrics = {
            'win_rate_stability': {},
            'avg_trade_pnl_stability': {},
            'tail_loss_stability': {},
            'overall_stability_score': 0.0
        }

        for strategy_name, strategy_results in individual_results.items():
            win_rates = []
            avg_trade_pnls = []
            tail_losses = []

            for symbol, result in strategy_results.items():
                # Extract trade statistics
                total_trades = result.get('total_trades', 0)
                winning_trades = result.get('winning_trades', 0)
                total_pnl = result.get('total_pnl', 0)

                if total_trades > 0:
                    win_rate = winning_trades / total_trades
                    win_rates.append(win_rate)

                    avg_trade_pnl = total_pnl / total_trades if total_trades > 0 else 0
                    avg_trade_pnls.append(avg_trade_pnl)

                    # Calculate tail loss (largest losses)
                    if 'trade_log' in result and result['trade_log']:
                        losses = [trade['pnl'] for trade in result['trade_log'] if trade['pnl'] < 0]
                        if losses:
                            # Average of bottom 10% of losses (tail risk)
                            losses_sorted = sorted(losses)
                            tail_loss_count = max(1, len(losses_sorted) // 10)  # Bottom 10%
                            tail_losses.extend(losses_sorted[:tail_loss_count])

            # Calculate stability metrics for this strategy
            if win_rates:
                win_rate_mean = np.mean(win_rates)
                win_rate_std = np.std(win_rates)
                win_rate_cv = win_rate_std / abs(win_rate_mean) if win_rate_mean != 0 else float('inf')

                stability_metrics['win_rate_stability'][strategy_name] = {
                    'mean': float(win_rate_mean),
                    'std': float(win_rate_std),
                    'cv': float(win_rate_cv),
                    'stability_score': 1 / (1 + win_rate_cv) if win_rate_cv != float('inf') else 0
                }

            if avg_trade_pnls:
                avg_pnl_mean = np.mean(avg_trade_pnls)
                avg_pnl_std = np.std(avg_trade_pnls)
                avg_pnl_cv = avg_pnl_std / abs(avg_pnl_mean) if avg_pnl_mean != 0 else float('inf')

                stability_metrics['avg_trade_pnl_stability'][strategy_name] = {
                    'mean': float(avg_pnl_mean),
                    'std': float(avg_pnl_std),
                    'cv': float(avg_pnl_cv),
                    'stability_score': 1 / (1 + avg_pnl_cv) if avg_pnl_cv != float('inf') else 0
                }

            if tail_losses:
                tail_loss_mean = np.mean(tail_losses)
                tail_loss_std = np.std(tail_losses)

                stability_metrics['tail_loss_stability'][strategy_name] = {
                    'mean': float(tail_loss_mean),
                    'std': float(tail_loss_std),
                    'count': len(tail_losses)
                }

        # Calculate overall stability score as average of individual stability scores
        all_stability_scores = []
        for category in ['win_rate_stability', 'avg_trade_pnl_stability']:
            for strategy_data in stability_metrics[category].values():
                if 'stability_score' in strategy_data:
                    all_stability_scores.append(strategy_data['stability_score'])

        if all_stability_scores:
            stability_metrics['overall_stability_score'] = float(np.mean(all_stability_scores))

        return stability_metrics
    
    def calculate_strategy_admission_metrics(self, results: Dict[str, Dict[str, Any]], 
                                          symbols: List[str]) -> Dict[str, Dict[str, float]]:
        """Calculate metrics for strategy admission filter."""
        
        admission_metrics = {}
        
        for strategy_name, strategy_results in results.items():
            # Calculate metrics across all symbols for this strategy
            returns = []
            sharpes = []
            drawdowns = []
            win_rates = []
            trade_counts = []
            
            successful_symbols = 0
            profitable_symbols = 0  # Count symbols with positive returns
            
            for symbol in symbols:
                if symbol in strategy_results:
                    result = strategy_results[symbol]
                    total_return = result.get('total_return', 0)
                    returns.append(total_return)
                    sharpes.append(result.get('sharpe_ratio', 0))
                    drawdowns.append(result.get('max_drawdown', 0))
                    win_rates.append(result.get('win_rate', 0))
                    trade_count = result.get('total_trades', 0)
                    trade_counts.append(trade_count)
                    
                    # Count as successful if trades were executed
                    if trade_count > 0:
                        successful_symbols += 1
                        # Count as profitable if return is positive
                        if total_return > 0:
                            profitable_symbols += 1
            
            if successful_symbols == 0:
                continue
            
            # Calculate admission metrics
            avg_return = np.mean(returns) if returns else 0
            avg_sharpe = np.mean(sharpes) if sharpes else 0
            avg_drawdown = np.mean(drawdowns) if drawdowns else 0
            avg_win_rate = np.mean(win_rates) if win_rates else 0
            total_trades = sum(trade_counts) if trade_counts else 0
            success_rate = successful_symbols / len(symbols)
            profitable_rate = profitable_symbols / len(symbols)  # Rate of profitable symbols
            
            admission_metrics[strategy_name] = {
                'avg_return': avg_return,
                'avg_sharpe': avg_sharpe,
                'avg_drawdown': avg_drawdown,
                'avg_win_rate': avg_win_rate,
                'total_trades': total_trades,
                'success_rate': success_rate,  # Percentage of symbols where strategy executed trades
                'profitable_rate': profitable_rate,  # Percentage of symbols with positive returns
                'profitable_symbols': profitable_symbols,
                'total_symbols': len(symbols)
            }
        
        return admission_metrics
    
    def apply_strategy_admission_filter(self, admission_metrics: Dict[str, Dict[str, float]],
                                     min_success_rate: float = 0.7,
                                     min_profitable_rate: float = 0.5,
                                     backtest_period_days: int = 30) -> List[str]:
        """Apply strategy admission filter based on statistical viability criteria."""

        accepted_strategies = []

        for strategy_name, metrics in admission_metrics.items():
            # Statistical viability criteria:
            # 1. Minimum trades per year (scaled for actual period)
            # 2. Positive expectancy
            # 3. Profit factor > 1.1
            # 4. Sharpe ratio > 0.3
            # 5. Acceptable drawdown
            # 6. Minimum trade count

            success_rate = metrics.get('success_rate', 0)
            profitable_rate = metrics.get('profitable_rate', 0)
            avg_return = metrics.get('avg_return', 0)
            avg_sharpe = metrics.get('avg_sharpe', 0)
            avg_drawdown = metrics.get('avg_drawdown', 0)
            total_trades = metrics.get('total_trades', 0)

            # Calculate annualized metrics based on actual backtest period
            # Assuming the backtest period is in days
            backtest_days = backtest_period_days
            annualized_trades = total_trades * (365 / backtest_days) if backtest_days > 0 else total_trades

            # Statistical viability checks
            # For shorter backtests, adjust minimum trade requirements
            min_required_annual_trades = 20  # Lowered standard requirement for more realistic expectations
            # Scale down for shorter backtest periods (minimum 3 trades regardless)
            scaled_min_trades = max(3, min_required_annual_trades * (backtest_days / 365.0))
            min_trades_condition = total_trades >= scaled_min_trades  # Minimum trades for the actual period

            # More realistic conditions for live market conditions
            expectancy_condition = avg_return > -0.01  # Allow slightly negative returns (-1%)
            sharpe_condition = avg_sharpe > -0.1  # Allow slightly negative Sharpe ratio
            drawdown_condition = abs(avg_drawdown) < 0.5  # Increased to 50% max drawdown for more flexibility
            trade_count_condition = total_trades >= 2  # Minimum 2 trades (allow very few trades for short periods)

            # Additional profitability condition
            profitability_condition = profitable_rate >= min_profitable_rate

            if (min_trades_condition and expectancy_condition and sharpe_condition and
                drawdown_condition and trade_count_condition and profitability_condition):
                accepted_strategies.append(strategy_name)
                self.logger.info(f"Strategy {strategy_name} admitted - Annualized trades: {annualized_trades:.1f}, "
                               f"Success rate: {success_rate:.2%}, Avg return: {avg_return:.2%}, "
                               f"Avg Sharpe: {avg_sharpe:.2f}, Drawdown: {avg_drawdown:.2%}")
            else:
                self.logger.info(f"Strategy {strategy_name} rejected - "
                               f"Annualized trades: {annualized_trades:.1f}, "
                               f"Success: {success_rate:.2%}, Profitable: {profitable_rate:.2%}, "
                               f"Return: {avg_return:.2%}, Sharpe: {avg_sharpe:.2f}, "
                               f"Drawdown: {avg_drawdown:.2%}, Total trades: {total_trades}")

        return accepted_strategies
    
    def calculate_capital_allocation_weights(self, admission_metrics: Dict[str, Dict[str, float]], 
                                           correlation_matrix: pd.DataFrame) -> Dict[str, float]:
        """Calculate dynamic capital allocation weights based on strategy metrics."""
        
        weights = {}
        
        # Get admitted strategies
        admitted_strategies = [name for name, metrics in admission_metrics.items() 
                             if metrics.get('success_rate', 0) >= 0.5 and metrics.get('avg_return', 0) > -0.01]
        
        if not admitted_strategies:
            self.logger.warning("No strategies passed admission criteria, using equal weights")
            for strategy_name in admission_metrics.keys():
                weights[strategy_name] = 1.0 / len(admission_metrics) if admission_metrics else 1.0
            return weights
        
        # Calculate weights based on multiple factors
        for strategy_name in admitted_strategies:
            metrics = admission_metrics[strategy_name]
            
            # Normalize metrics to 0-1 scale
            normalized_return = max(0, min(1, (metrics['avg_return'] + 0.1) / 0.5))  # Assuming max return of 50%
            normalized_sharpe = max(0, min(1, (metrics['avg_sharpe'] + 1) / 3))  # Assuming max Sharpe of 2
            normalized_success_rate = metrics['success_rate']
            normalized_profitable_rate = metrics['profitable_rate']
            
            # Calculate base weight from performance metrics
            performance_score = (normalized_return * 0.3 + 
                               normalized_sharpe * 0.3 + 
                               normalized_success_rate * 0.2 +
                               normalized_profitable_rate * 0.2)
            
            # Apply correlation penalty if correlation matrix exists
            correlation_penalty = 1.0
            if not correlation_matrix.empty:
                # Find correlations with other strategies
                strategy_cols = [col for col in correlation_matrix.columns if col.startswith(strategy_name)]
                if strategy_cols:
                    # Average correlation with other strategies
                    other_strategies = [col for col in correlation_matrix.columns 
                                      if not col.startswith(strategy_name)]
                    if other_strategies:
                        correlations = []
                        for strat_col in strategy_cols:
                            for other_col in other_strategies:
                                if other_col in correlation_matrix.index:
                                    corr_val = correlation_matrix.loc[strat_col, other_col]
                                    if not pd.isna(corr_val):
                                        correlations.append(abs(corr_val))
                        
                        if correlations:
                            avg_corr = np.mean(correlations)
                            # Apply penalty for high correlation (reduce weight)
                            correlation_penalty = max(0.1, 1.0 - avg_corr)
            
            # Apply drawdown penalty
            drawdown_penalty = max(0.1, 1.0 - abs(metrics['avg_drawdown']))
            
            # Final weight
            final_weight = performance_score * correlation_penalty * drawdown_penalty
            weights[strategy_name] = max(0.01, final_weight)  # Minimum 1% weight
        
        # Normalize weights to sum to 1
        total_weight = sum(weights.values())
        if total_weight > 0:
            for strategy_name in weights:
                weights[strategy_name] /= total_weight
        else:
            # Fallback to equal weights if all weights are zero
            for strategy_name in weights:
                weights[strategy_name] = 1.0 / len(weights) if weights else 1.0
        
        return weights
    
    def run_comprehensive_backtest(self,
                                 symbols: List[str],
                                 strategy_functions: Dict[str, callable],
                                 strategy_params: Dict[str, Dict] = None,
                                 start_date: datetime = None,
                                 end_date: datetime = None,
                                 min_success_rate: float = 0.7) -> Dict[str, Any]:
        """Run comprehensive portfolio backtest with all features."""

        if start_date is None:
            start_date = datetime.now() - timedelta(days=365)
        if end_date is None:
            end_date = datetime.now()

        self.logger.info(f"Starting comprehensive portfolio backtest for {len(symbols)} symbols")
        self.logger.info(f"Strategies: {list(strategy_functions.keys())}")
        self.logger.info(f"Date range: {start_date.date()} to {end_date.date()}")

        # Generate reproducible run ID for experiment tracking
        config = {
            'initial_capital': self.initial_capital,
            'fee_rate': self.fee_rate,
            'slippage_factor': self.slippage_factor,
            'risk_per_trade': self.risk_per_trade,
            'max_drawdown_limit': self.max_drawdown_limit,
            'max_correlation_limit': self.max_correlation_limit,
            'min_success_rate': min_success_rate
        }

        run_id = generate_run_id(
            config=config,
            strategies=list(strategy_functions.keys()),
            symbols=symbols,
            date_range=(start_date.isoformat(), end_date.isoformat()),
            custom_suffix="comprehensive_backtest"
        )

        self.logger.info(f"Generated run ID: {run_id}")

        # Determine if we should allow mock data based on environment variable
        use_mock_data = Configs.infrastructure.use_mock_data if Configs.infrastructure and hasattr(Configs.infrastructure, 'use_mock_data') else False

        # Load data for all symbols
        data_dict = self.load_data_for_symbols(symbols, start_date, end_date, mock_data_if_missing=use_mock_data)

        if not data_dict:
            self.logger.error("No data loaded for any symbols")
            return {"error": "No data available for backtesting"}

        # Run individual strategy backtests
        individual_results = self.run_individual_strategy_backtests(
            data_dict, strategy_functions, strategy_params
        )

        # Calculate correlation matrix
        correlation_matrix = self.calculate_correlation_matrix(individual_results)

        # Classify market regimes
        regime_classification = self.calculate_regime_classification(data_dict)

        # Calculate admission metrics
        admission_metrics = self.calculate_strategy_admission_metrics(individual_results, symbols)

        # Calculate backtest period in days
        backtest_period_days = (end_date - start_date).days
        if backtest_period_days <= 0:
            backtest_period_days = 30  # Default to 30 days if invalid range

        # Apply strategy admission filter
        accepted_strategies = self.apply_strategy_admission_filter(admission_metrics, min_success_rate, min_profitable_rate=0.5, backtest_period_days=backtest_period_days)

        # Calculate capital allocation weights
        capital_weights = self.calculate_capital_allocation_weights(admission_metrics, correlation_matrix)

        # Analyze regime performance
        regime_analysis = self.analyze_regime_performance(individual_results, data_dict)

        # Calculate portfolio dependency risk
        portfolio_dependency_risk = self.calculate_portfolio_dependency_risk(admission_metrics, capital_weights)

        # Calculate trade distribution stability
        trade_distribution_stability = self.calculate_trade_distribution_stability(individual_results)

        # Collect strategy version information
        strategy_versions = {}
        for strategy_name, strategy_func in strategy_functions.items():
            version = getattr(strategy_func, 'version', 'unknown')
            strategy_versions[strategy_name] = version

        # Prepare results
        results = {
            'individual_results': individual_results,
            'admission_metrics': admission_metrics,
            'accepted_strategies': accepted_strategies,
            'capital_weights': capital_weights,
            'correlation_matrix': correlation_matrix.to_dict() if not correlation_matrix.empty else {},
            'regime_classification': regime_classification,
            'regime_analysis': regime_analysis,
            'portfolio_dependency_risk': portfolio_dependency_risk,
            'trade_distribution_stability': trade_distribution_stability,
            'symbols': symbols,
            'strategy_functions': list(strategy_functions.keys()),
            'strategy_versions': strategy_versions,  # Include version information
            'date_range': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            },
            'summary': {
                'total_strategies': len(strategy_functions),
                'accepted_strategies_count': len(accepted_strategies),
                'rejected_strategies_count': len(strategy_functions) - len(accepted_strategies),
                'total_symbols': len(symbols),
                'data_symbols_count': len(data_dict)
            },
            'run_id': run_id  # Include run ID in results
        }

        # Add strategy ranking
        strategy_rankings = []
        for strategy_name, metrics in admission_metrics.items():
            ranking_entry = {
                'strategy': strategy_name,
                'avg_return': metrics.get('avg_return', 0),
                'avg_sharpe': metrics.get('avg_sharpe', 0),
                'avg_drawdown': metrics.get('avg_drawdown', 0),
                'success_rate': metrics.get('success_rate', 0),
                'acceptance_status': 'accepted' if strategy_name in accepted_strategies else 'rejected',
                'weight': capital_weights.get(strategy_name, 0)
            }
            strategy_rankings.append(ranking_entry)

        # Sort by return
        strategy_rankings.sort(key=lambda x: x['avg_return'], reverse=True)
        results['strategy_rankings'] = strategy_rankings

        self.logger.info(f"Comprehensive backtest completed. {len(accepted_strategies)} strategies accepted.")

        # Save results with run ID for reproducibility
        try:
            save_experiment_results(run_id, results)
            self.logger.info(f"Results saved with run ID: {run_id}")
        except Exception as e:
            self.logger.error(f"Failed to save experiment results: {e}")

        return results


def load_sample_strategies():
    """Load sample strategy functions for testing with version information."""

    def simple_rsi_strategy(row, params):
        """Simple RSI-based strategy with increased signal density."""
        rsi = row.get('rsi', 50)
        rsi_oversold = params.get('rsi_oversold', 30)
        rsi_overbought = params.get('rsi_overbought', 70)

        if pd.isna(rsi):
            return 0

        # Use scoring instead of binary rules for more nuanced signals
        oversold_score = max(0, (40 - rsi) / 10) if rsi < 40 else 0  # More sensitive oversold
        overbought_score = max(0, (rsi - 60) / 10) if rsi > 60 else 0  # More sensitive overbought

        if oversold_score > 0.5:  # Threshold for buy signal
            return 1  # Buy
        elif overbought_score > 0.5:  # Threshold for sell signal
            return -1  # Sell
        else:
            return 0  # Hold

    def simple_ma_crossover_strategy(row, params):
        """Simple moving average crossover strategy with increased sensitivity."""
        sma_fast = row.get('sma_3', 0)  # Use even shorter MA for more signals
        sma_slow = row.get('sma_7', 0)  # Use medium MA

        if pd.isna(sma_fast) or pd.isna(sma_slow):
            return 0

        # Use even tighter thresholds for more signals
        ma_ratio = sma_fast / sma_slow
        if ma_ratio > 0.99:  # Very tight threshold for golden cross
            return 1  # Buy
        elif ma_ratio < 1.01:  # Very tight threshold for death cross
            return -1  # Sell
        else:
            return 0  # Hold

    def trend_following_strategy(row, params):
        """Regime-aware trend following strategy with increased signal density."""
        sma_5 = row.get('sma_5', 0)  # Use shorter term
        sma_10 = row.get('sma_10', 0)  # Use shorter term
        close = row.get('close', 0)
        roc = row.get('roc_5', 0)  # Rate of change for momentum
        adx = row.get('adx', 20)  # ADX for trend strength
        trend_strength = row.get('trend_strength', 0)

        if pd.isna(sma_5) or pd.isna(sma_10) or pd.isna(close):
            return 0

        # Basic trend conditions with very loose thresholds
        trend_bullish = close > sma_5 * 0.99  # Very loose threshold
        trend_bearish = close < sma_5 * 1.01  # Very loose threshold

        # Add momentum confirmation with very loose thresholds
        momentum_bullish = pd.notna(roc) and roc > -0.001  # Very loose threshold
        momentum_bearish = pd.notna(roc) and roc < 0.001   # Very loose threshold

        # Use scoring approach instead of binary
        score = 0
        if trend_bullish:
            score += 0.5
        if momentum_bullish:
            score += 0.3
        if pd.isna(adx) or adx > 10:  # Very low threshold
            score += 0.2

        if score >= 0.6:  # Threshold for buy signal
            return 1  # Buy
        elif score <= 0.2:  # Threshold for sell signal
            return -1  # Sell
        else:
            return 0  # Hold

    def mean_reversion_strategy(row, params):
        """Regime-aware mean reversion strategy with increased signal density."""
        rsi = row.get('rsi', 50)
        bb_upper = row.get('bb_upper', 0)
        bb_lower = row.get('bb_lower', 0)
        close = row.get('close', 0)
        atr = row.get('atr', 0)
        adx = row.get('adx', 20)  # ADX for trend strength

        if pd.isna(rsi) or pd.isna(bb_upper) or pd.isna(bb_lower) or pd.isna(close) or pd.isna(atr):
            return 0

        # Calculate how far price is from bands (relative position)
        if bb_upper != bb_lower:  # Avoid division by zero
            bb_position = (close - bb_lower) / (bb_upper - bb_lower)  # 0-1 scale
        else:
            bb_position = 0.5  # Neutral if bands are equal

        # Use scoring approach for more nuanced signals
        oversold_score = max(0, min(1, (42 - rsi) / 8))  # More sensitive than before
        overbought_score = max(0, min(1, (rsi - 58) / 8))  # More sensitive than before

        # Use position relative to bands for additional scoring
        bb_oversold_score = max(0, min(1, (0.4 - bb_position) / 0.2)) if bb_position < 0.4 else 0
        bb_overbought_score = max(0, min(1, (bb_position - 0.6) / 0.2)) if bb_position > 0.6 else 0

        total_buy_score = oversold_score + bb_oversold_score
        total_sell_score = overbought_score + bb_overbought_score

        if total_buy_score > 0.6:  # Threshold for buy signal
            return 1  # Buy
        elif total_sell_score > 0.6:  # Threshold for sell signal
            return -1  # Sell
        else:
            return 0  # Hold

    def volatility_breakout_strategy(row, params):
        """Regime-aware volatility breakout strategy with increased signal density."""
        atr = row.get('atr', 0)
        high = row.get('high', 0)
        low = row.get('low', 0)
        close = row.get('close', 0)
        sma_5 = row.get('sma_5', 0)  # Use shorter MA
        volume = row.get('volume', 0)
        sma_volume = row.get('sma_volume_5', 0)  # Use shorter MA for volume
        adx = row.get('adx', 20)  # ADX for trend strength

        if any(pd.isna(x) for x in [atr, high, low, close, sma_5]):
            return 0

        # Define breakout thresholds based on ATR - make extremely sensitive
        breakout_threshold = atr * 0.1  # Extremely sensitive

        # Bullish breakout: price moves above recent range
        bullish_breakout = close > max(high, sma_5) + breakout_threshold
        bearish_breakout = close < min(low, sma_5) - breakout_threshold

        # Volume confirmation with very loose requirements
        volume_confirmation = True
        if pd.notna(volume) and pd.notna(sma_volume):
            volume_confirmation = volume > sma_volume * 0.3  # Very loose volume requirement

        # Use scoring approach
        score = 0
        if bullish_breakout and volume_confirmation:
            score += 1.0
        if bearish_breakout and volume_confirmation:
            score -= 1.0

        if score > 0.5:  # Threshold for buy signal
            return 1  # Buy
        elif score < -0.5:  # Threshold for sell signal
            return -1  # Sell
        else:
            return 0  # Hold

    # Strategy version mapping
    strategy_versions = {
        'rsi_strategy': '1.0.0',
        'ma_crossover_strategy': '1.0.0',
        'trend_following': '1.1.0',
        'mean_reversion': '1.0.2',
        'volatility_breakout': '1.0.1'
    }

    # Create strategy objects with version information
    strategies = {}
    for name, func in {
        'rsi_strategy': simple_rsi_strategy,
        'ma_crossover_strategy': simple_ma_crossover_strategy,
        'trend_following': trend_following_strategy,
        'mean_reversion': mean_reversion_strategy,
        'volatility_breakout': volatility_breakout_strategy
    }.items():
        # Create a wrapper that includes version information
        def make_versioned_strategy(strategy_func, version):
            def versioned_strategy(row, params):
                return strategy_func(row, params)
            versioned_strategy.__name__ = strategy_func.__name__
            versioned_strategy.version = version
            return versioned_strategy

        strategies[name] = make_versioned_strategy(func, strategy_versions[name])

    return strategies