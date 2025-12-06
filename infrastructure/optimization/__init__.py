"""Infrastructure implementations for optimization services."""

import pandas as pd
from typing import Dict, Any, Optional
import os
from pathlib import Path

from domain.ports.optimization_ports import IDataLoader, IMetricCalculator
from shared.logger import EnhancedLogger


class FileDataLoader(IDataLoader):
    """File-based data loader implementation."""
    
    def __init__(self, data_dir: str = "data/market"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.logger = EnhancedLogger("FileDataLoader")
    
    def load_historical_data(self, symbol: str, timeframe: str, 
                           limit: int) -> pd.DataFrame:
        """Load historical market data from CSV files."""
        # Normalize symbol name (replace / with _ for file names)
        normalized_symbol = symbol.replace('/', '_').replace(':', '_')
        file_path = self.data_dir / f"{normalized_symbol}_{timeframe}.csv"
        
        if not file_path.exists():
            self.logger.warning(f"Data file not found: {file_path}")
            # Return empty DataFrame with required columns
            return pd.DataFrame(columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        try:
            df = pd.read_csv(file_path)
            # Ensure required columns exist
            required_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
            for col in required_cols:
                if col not in df.columns:
                    # Create column with default values
                    if col == 'timestamp':
                        df['timestamp'] = pd.date_range(start='2023-01-01', periods=len(df), freq='1h')
                    else:
                        df[col] = 0.0
            
            # Convert timestamp to datetime if needed
            if not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
                df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # Take only the last 'limit' rows
            if limit > 0 and len(df) > limit:
                df = df.tail(limit).reset_index(drop=True)
            
            self.logger.info(f"Loaded {len(df)} rows for {symbol} from {file_path}")
            return df
            
        except Exception as e:
            self.logger.error(f"Error loading data from {file_path}: {e}")
            return pd.DataFrame(columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    
    def cache_exists(self, symbol: str, timeframe: str) -> bool:
        """Check if cached data exists."""
        normalized_symbol = symbol.replace('/', '_').replace(':', '_')
        file_path = self.data_dir / f"{normalized_symbol}_{timeframe}.csv"
        return file_path.exists()


class BacktestMetricCalculator(IMetricCalculator):
    """Calculate backtest metrics."""
    
    def __init__(self):
        self.logger = EnhancedLogger("BacktestMetricCalculator")
    
    def calculate_sharpe_ratio(self, returns: pd.Series) -> float:
        """Calculate Sharpe ratio."""
        if len(returns) == 0 or returns.std() == 0:
            return 0.0
        
        return (returns.mean() / returns.std()) * (252 ** 0.5)  # Annualized
    
    def calculate_max_drawdown(self, equity_curve: pd.Series) -> float:
        """Calculate maximum drawdown."""
        if len(equity_curve) == 0:
            return 0.0
        
        running_max = equity_curve.expanding().max()
        drawdown = (equity_curve - running_max) / running_max
        return drawdown.min()
    
    def calculate_win_rate(self, trades: pd.DataFrame) -> float:
        """Calculate win rate."""
        if len(trades) == 0:
            return 0.0
        
        # Assuming there's a 'pnl' column in trades
        if 'pnl' not in trades.columns:
            return 0.0
        
        positive_trades = len(trades[trades['pnl'] > 0])
        total_trades = len(trades)
        
        return positive_trades / total_trades if total_trades > 0 else 0.0


class OptimizationRepository:
    """Repository for optimization results and parameters."""
    
    def __init__(self, storage_dir: str = "data/optimization_storage"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.logger = EnhancedLogger("OptimizationRepository")
    
    def save_optimization_results(self, strategy_name: str, symbol: str, 
                                 results: Dict[str, Any]) -> bool:
        """Save optimization results to storage."""
        try:
            file_path = self.storage_dir / f"{strategy_name}_{symbol}_results.json"
            import json
            with open(file_path, 'w') as f:
                json.dump(results, f, indent=4, default=str)
            
            self.logger.info(f"Saved optimization results for {strategy_name} on {symbol}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving optimization results: {e}")
            return False
    
    def load_optimization_results(self, strategy_name: str, symbol: str) -> Optional[Dict[str, Any]]:
        """Load optimization results from storage."""
        file_path = self.storage_dir / f"{strategy_name}_{symbol}_results.json"
        
        if not file_path.exists():
            return None
        
        try:
            import json
            with open(file_path, 'r') as f:
                results = json.load(f)
            
            self.logger.info(f"Loaded optimization results for {strategy_name} on {symbol}")
            return results
            
        except Exception as e:
            self.logger.error(f"Error loading optimization results: {e}")
            return None
    
    def save_best_parameters(self, strategy_name: str, symbol: str, 
                           parameters: Dict[str, Any]) -> bool:
        """Save best parameters to storage."""
        try:
            file_path = self.storage_dir / f"{strategy_name}_{symbol}_best_params.json"
            import json
            with open(file_path, 'w') as f:
                json.dump(parameters, f, indent=4, default=str)
            
            self.logger.info(f"Saved best parameters for {strategy_name} on {symbol}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving best parameters: {e}")
            return False
    
    def load_best_parameters(self, strategy_name: str, symbol: str) -> Optional[Dict[str, Any]]:
        """Load best parameters from storage."""
        file_path = self.storage_dir / f"{strategy_name}_{symbol}_best_params.json"
        
        if not file_path.exists():
            return None
        
        try:
            import json
            with open(file_path, 'r') as f:
                params = json.load(f)
            
            self.logger.info(f"Loaded best parameters for {strategy_name} on {symbol}")
            return params
            
        except Exception as e:
            self.logger.error(f"Error loading best parameters: {e}")
            return None