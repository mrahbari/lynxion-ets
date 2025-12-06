"""Use cases for optimization functionality."""

from typing import Dict, Any, Optional
import pandas as pd
from datetime import datetime, timedelta

from application.services.optimization_service_app import OptimizationAppService, AutoRetuneService
from domain.ports.optimization_ports import IDataLoader
from shared.logger import EnhancedLogger


class RunStrategyOptimizationUseCase:
    """Use case for running strategy optimization."""
    
    def __init__(self, 
                 optimization_service: OptimizationAppService,
                 data_loader: IDataLoader):
        self.optimization_service = optimization_service
        self.data_loader = data_loader
        self.logger = EnhancedLogger("RunStrategyOptimizationUseCase")
    
    def execute(self, 
                strategy_name: str, 
                symbol: str, 
                timeframe: str = "1h",
                lookback_period: int = 1000,
                max_evals: int = 100) -> Dict[str, Any]:
        """Execute strategy optimization."""
        try:
            self.logger.info(f"Starting optimization for {strategy_name} on {symbol}")
            
            # Load historical data
            data = self.data_loader.load_historical_data(
                symbol=symbol, 
                timeframe=timeframe, 
                limit=lookback_period
            )
            
            if data.empty:
                self.logger.error(f"No data available for {symbol}")
                return {"error": f"No data available for {symbol}"}
            
            # Prepare parameters for optimization
            params = {
                'symbol': symbol,
                'max_evals': max_evals
            }
            
            # Run optimization
            results = self.optimization_service.optimize_strategy(
                strategy_name=strategy_name,
                data=data,
                parameters=params
            )
            
            self.logger.info(f"Optimization completed for {strategy_name} on {symbol}")
            return results
            
        except Exception as e:
            self.logger.error(f"Error in RunStrategyOptimizationUseCase: {e}")
            return {"error": str(e)}


class CheckAutoRetuneUseCase:
    """Use case for checking if auto-retuning is needed."""
    
    def __init__(self, 
                 auto_retune_service: AutoRetuneService,
                 data_loader: IDataLoader):
        self.auto_retune_service = auto_retune_service
        self.data_loader = data_loader
        self.logger = EnhancedLogger("CheckAutoRetuneUseCase")
    
    def execute(self, 
                strategy_name: str, 
                symbol: str, 
                timeframe: str = "1h",
                lookback_period: int = 500) -> Dict[str, Any]:
        """Execute auto-retune check."""
        try:
            self.logger.info(f"Checking auto-retune for {strategy_name} on {symbol}")
            
            # Load recent data to make performance assessment
            data = self.data_loader.load_historical_data(
                symbol=symbol,
                timeframe=timeframe,
                limit=lookback_period
            )
            
            if data.empty:
                self.logger.error(f"No data available for {symbol}")
                return {"retune_needed": False, "error": f"No data available for {symbol}"}
            
            # For now, we'll just return if retune is needed based on historical data
            # In a real system, you'd have a performance tracking system
            needs_retune = self.auto_retune_service.should_retune(
                strategy_name=strategy_name,
                symbol=symbol,
                current_performance=-0.1  # Placeholder - would come from performance tracker
            )
            
            result = {
                "retune_needed": needs_retune,
                "symbol": symbol,
                "strategy": strategy_name
            }
            
            if needs_retune:
                self.logger.info(f"Auto-retune needed for {strategy_name} on {symbol}")
            else:
                self.logger.info(f"No auto-retune needed for {strategy_name} on {symbol}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error in CheckAutoRetuneUseCase: {e}")
            return {"error": str(e), "retune_needed": False}


class RunAutoRetuneUseCase:
    """Use case for running automatic retuning."""
    
    def __init__(self, 
                 auto_retune_service: AutoRetuneService,
                 data_loader: IDataLoader):
        self.auto_retune_service = auto_retune_service
        self.data_loader = data_loader
        self.logger = EnhancedLogger("RunAutoRetuneUseCase")
    
    def execute(self, 
                strategy_name: str, 
                symbol: str, 
                timeframe: str = "1h",
                lookback_period: int = 1000) -> Dict[str, Any]:
        """Execute auto-retuning."""
        try:
            self.logger.info(f"Running auto-retune for {strategy_name} on {symbol}")
            
            # Load data
            data = self.data_loader.load_historical_data(
                symbol=symbol,
                timeframe=timeframe,
                limit=lookback_period
            )
            
            if data.empty:
                self.logger.error(f"No data available for {symbol}")
                return {"error": f"No data available for {symbol}"}
            
            # Run auto-retuning
            results = self.auto_retune_service.run_auto_retune(
                strategy_name=strategy_name,
                symbol=symbol,
                data=data
            )
            
            self.logger.info(f"Auto-retune completed for {strategy_name} on {symbol}")
            return results
            
        except Exception as e:
            self.logger.error(f"Error in RunAutoRetuneUseCase: {e}")
            return {"error": str(e)}


class FilterTradingAssetsUseCase:
    """Use case for filtering trading assets using Auto-Drop."""
    
    def __init__(self, 
                 data_loader: IDataLoader,
                 optimization_service: OptimizationAppService):
        self.data_loader = data_loader
        self.optimization_service = optimization_service
        # We'll access the autodrop engine from the optimization service
        self.logger = EnhancedLogger("FilterTradingAssetsUseCase")
    
    def execute(self, 
                symbols: list, 
                timeframe: str = "1h",
                lookback_period: int = 500) -> Dict[str, Any]:
        """Filter trading assets based on quality metrics."""
        try:
            self.logger.info(f"Filtering {len(symbols)} assets")
            
            # This would use the auto-drop engine to filter symbols
            # For now, we'll use the autodrop engine that's available
            # in the optimization service
            from shared.auto_drop import AutoDropEngine
            auto_drop = AutoDropEngine()
            
            filtered_symbols = []
            evaluation_details = {}
            
            for symbol in symbols:
                # Load data for the symbol
                data = self.data_loader.load_historical_data(
                    symbol=symbol,
                    timeframe=timeframe,
                    limit=lookback_period
                )
                
                if not data.empty:
                    # Evaluate using auto-drop
                    evaluation = auto_drop.evaluate(data)
                    evaluation_details[symbol] = evaluation
                    
                    if evaluation["status"] == "KEEP":
                        filtered_symbols.append(symbol)
                
            result = {
                "original_count": len(symbols),
                "filtered_count": len(filtered_symbols),
                "kept_symbols": filtered_symbols,
                "evaluation_details": evaluation_details
            }
            
            self.logger.info(f"Asset filtering completed. Kept {len(filtered_symbols)}/{len(symbols)} assets")
            return result
            
        except Exception as e:
            self.logger.error(f"Error in FilterTradingAssetsUseCase: {e}")
            return {"error": str(e)}