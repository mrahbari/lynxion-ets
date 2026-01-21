"""
Advanced Risk-Aware Execution Engine based on Enterprise Hedge Fund Architecture
"""
import pandas as pd
from typing import Dict, List, Tuple, Optional
from datetime import datetime
from decimal import Decimal
import numpy as np

from application.risk_management.enterprise_risk_manager import EnterpriseRiskManager, PositionDirection
from application.position_sizing.enterprise_position_sizing import PositionSizingService
from infrastructure.market_regime.regime_detector import RegimeType


class AdvancedExecutionEngine:
    """
    Advanced execution engine with integrated risk management
    """
    def __init__(self,
                 risk_manager: EnterpriseRiskManager,
                 position_sizing_service: PositionSizingService,
                 fees_per_trade: float = 0.1,
                 slippage_tolerance: float = 0.001):

        self.risk_manager = risk_manager
        self.position_sizing_service = position_sizing_service
        self.fees_per_trade = fees_per_trade
        self.slippage_tolerance = slippage_tolerance

        # Track execution results
        self.trade_log: List[Dict] = []
        self.execution_reports: Dict[str, List] = {}

    def calculate_stop_loss_take_profit(self, entry_price: float, direction: PositionDirection,
                                      signal_strength: float = 1.0, volatility: float = 1.0,
                                      regime_context: str = None, strategy_name: str = None) -> Tuple[float, float]:
        """
        Calculate dynamic stop loss and take profit based on signal strength, volatility, regime, and strategy
        """
        # Use ATR-like measure for stop loss calculation
        atr_factor = volatility * 1.5  # 1.5x volatility for stop loss

        # Adjust stop loss and take profit based on regime
        if regime_context:
            if regime_context in [RegimeType.HIGH_VOLATILITY.value, RegimeType.CHOPPY.value]:
                # In high volatility/choppy regimes, use wider stops
                atr_factor *= 1.5
            elif regime_context in [RegimeType.TRENDING_UP.value, RegimeType.TRENDING_DOWN.value]:
                # In trending regimes, use tighter stops for better risk management
                atr_factor *= 0.8

        # Adjust based on strategy-specific requirements
        if strategy_name:
            if 'breakout' in strategy_name.lower():
                # For breakout strategies, use wider stops to avoid noise exits
                atr_factor *= 1.3
            elif 'mean_reversion' in strategy_name.lower():
                # For mean reversion, use tighter stops as reversals can be sharp
                atr_factor *= 0.9

        # Calculate stop loss distance based on direction
        if direction == PositionDirection.LONG:
            sl_distance = atr_factor * signal_strength
            sl = entry_price - sl_distance
            # Take profit is typically 2-3x the risk distance, adjusted for regime
            tp_distance = atr_factor * signal_strength * 2.0
            if regime_context in [RegimeType.TRENDING_UP.value, RegimeType.TRENDING_DOWN.value]:
                # In trending markets, allow for bigger targets
                tp_distance *= 1.2
            tp = entry_price + tp_distance
        else:  # SHORT
            sl_distance = atr_factor * signal_strength
            sl = entry_price + sl_distance
            tp_distance = atr_factor * signal_strength * 2.0
            if regime_context in [RegimeType.TRENDING_UP.value, RegimeType.TRENDING_DOWN.value]:
                # In trending markets, allow for bigger targets
                tp_distance *= 1.2
            tp = entry_price - tp_distance

        # Ensure SL and TP are valid
        if direction == PositionDirection.LONG:
            sl = min(sl, entry_price * 0.95)  # Stop loss shouldn't be above entry for long
            tp = max(tp, entry_price * 1.05)  # Take profit shouldn't be below entry for long
        else:
            sl = max(sl, entry_price * 1.05)  # Stop loss shouldn't be below entry for short
            tp = min(tp, entry_price * 0.95)  # Take profit shouldn't be above entry for short

        return sl, tp

    def execute_entry(self, symbol: str, entry_price: float, direction: PositionDirection,
                     signal_strength: float = 1.0, volatility: float = 1.0,
                     position_size_model: str = 'fixed_risk',
                     portfolio_equity: float = 100000, risk_per_trade: float = 0.01,
                     prevent_same_direction: bool = True,
                     regime_context: str = None, strategy_name: str = None,
                     signal_expectancy: float = 0.0, regime_accuracy: float = 1.0,
                     fusion_confidence: float = 0.5, correlation_exposure: float = 0.0,
                     current_drawdown: float = 0.0) -> bool:
        """
        Execute a position entry with full risk management
        """
        # Check if trading is allowed based on risk limits
        if not self.risk_manager.is_trading_allowed():
            print(f"Execution blocked: Risk limits exceeded")
            return False

        # Check if duplicate same-direction trade prevention is enabled
        if prevent_same_direction and hasattr(self.risk_manager, 'has_active_position_in_direction'):
            if self.risk_manager.has_active_position_in_direction(symbol, direction):
                print(f"Execution blocked: Already have an active {direction.value} position for {symbol}")
                return False

        # Calculate stop loss and take profit with regime and strategy considerations
        sl, tp = self.calculate_stop_loss_take_profit(entry_price, direction, signal_strength,
                                                     volatility, regime_context, strategy_name)

        # Calculate correlation penalty
        portfolio_symbols = list(self.risk_manager.positions.keys())
        correlation_penalty = self.risk_manager.calculate_correlation_penalty(symbol, portfolio_symbols)

        # Calculate drawdown factor
        drawdown_factor = self.risk_manager.calculate_drawdown_factor()

        # Calculate position size using the specified model with all new parameters
        size = self.position_sizing_service.compute_size(
            model_name=position_size_model,
            entry_price=entry_price,
            stop_loss=sl,
            portfolio_equity=portfolio_equity,
            risk_per_trade=risk_per_trade,
            volatility=volatility,
            signal_expectancy=signal_expectancy,
            regime_accuracy=regime_accuracy,
            fusion_confidence=fusion_confidence,
            correlation_exposure=correlation_exposure,
            current_drawdown=current_drawdown
        )

        # Attempt to enter the position with regime context
        success = self.risk_manager.enter_position(
            symbol=symbol,
            entry_price=entry_price,
            size=size,
            direction=direction,
            stop_loss=sl,
            take_profit=tp,
            regime_context=regime_context
        )

        if success:
            # Log the trade
            self.trade_log.append({
                'timestamp': datetime.now(),
                'symbol': symbol,
                'action': 'ENTRY',
                'direction': direction.value,
                'entry_price': entry_price,
                'size': size,
                'stop_loss': sl,
                'take_profit': tp,
                'signal_strength': signal_strength,
                'volatility': volatility,
                'regime_context': regime_context,
                'strategy_name': strategy_name,
                'signal_expectancy': signal_expectancy,
                'regime_accuracy': regime_accuracy,
                'fusion_confidence': fusion_confidence,
                'correlation_exposure': correlation_exposure,
                'current_drawdown': current_drawdown
            })

            print(f"Position entered: {symbol} {direction.value} at {entry_price}, size: {size:.2f}, "
                  f"regime: {regime_context}, strategy: {strategy_name}")

        return success

    def process_candle(self, symbol: str, candle_high: float, candle_low: float, 
                      candle_close: float) -> float:
        """
        Process a candle and check for SL/TP exits
        Returns PnL from any exits
        """
        # Check if this symbol has an open position
        exit_price, exit_type = self.risk_manager.check_stop_loss_take_profit(symbol, candle_high, candle_low)
        
        total_pnl = 0.0
        if exit_price and exit_type:
            # Exit the position
            pnl = self.risk_manager.exit_position(symbol, exit_price, exit_type)
            total_pnl += pnl
            
            # Log the exit
            position = self._get_recent_position(symbol)
            if position:
                self.trade_log.append({
                    'timestamp': datetime.now(),
                    'symbol': symbol,
                    'action': 'EXIT',
                    'direction': position.direction.value,
                    'exit_price': exit_price,
                    'exit_type': exit_type,
                    'size': position.size,
                    'entry_price': position.entry_price,
                    'pnl': pnl,
                    'candle_high': candle_high,
                    'candle_low': candle_low
                })
                
                print(f"Position exited: {symbol} {exit_type} at {exit_price}, PnL: {pnl:.2f}")
        
        return total_pnl

    def _get_recent_position(self, symbol: str):
        """
        Get the most recent position for a symbol (helper method)
        """
        # This is a simplified helper - in a real implementation, 
        # you might want to keep more detailed position tracking
        from application.risk_management.enterprise_risk_manager import Position
        # In this case, we're using the position from risk manager directly
        return self.risk_manager.positions.get(symbol)

    def process_signal(self, symbol: str, signal_direction: PositionDirection, signal_confidence: float,
                      market_data: Dict[str, float], position_size_model: str = 'fixed_risk',
                      prevent_same_direction: bool = True) -> bool:
        """
        Process a trading signal and execute if conditions are met
        """
        if 'price' not in market_data:
            print(f"Cannot process signal: missing price data for {symbol}")
            return False

        current_price = market_data['price']
        volatility = market_data.get('volatility', 1.0)  # Default to 1.0 if not provided
        portfolio_equity = market_data.get('portfolio_equity', self.risk_manager.starting_equity)
        risk_per_trade = market_data.get('risk_per_trade', self.risk_manager.max_risk_per_trade)

        # Execute entry with duplicate prevention
        return self.execute_entry(
            symbol=symbol,
            entry_price=current_price,
            direction=signal_direction,
            signal_strength=signal_confidence,
            volatility=volatility,
            position_size_model=position_size_model,
            portfolio_equity=portfolio_equity,
            risk_per_trade=risk_per_trade,
            prevent_same_direction=prevent_same_direction
        )

    def get_execution_metrics(self) -> Dict[str, any]:
        """
        Get execution performance metrics
        """
        total_trades = len([t for t in self.trade_log if t['action'] == 'EXIT'])
        winning_trades = len([t for t in self.trade_log if t['action'] == 'EXIT' and t['pnl'] > 0])
        losing_trades = len([t for t in self.trade_log if t['action'] == 'EXIT' and t['pnl'] < 0])
        
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        # Calculate total PnL
        total_pnl = sum(t['pnl'] for t in self.trade_log if t['action'] == 'EXIT')
        
        return {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'avg_win': np.mean([t['pnl'] for t in self.trade_log if t['action'] == 'EXIT' and t['pnl'] > 0]) if winning_trades > 0 else 0,
            'avg_loss': np.mean([t['pnl'] for t in self.trade_log if t['action'] == 'EXIT' and t['pnl'] < 0]) if losing_trades > 0 else 0,
            'risk_metrics': self.risk_manager.get_risk_metrics()
        }

    def export_trade_log(self, filename: str = None) -> str:
        """
        Export trade log to file
        """
        import json
        from datetime import datetime
        
        if filename is None:
            filename = f"trade_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        export_data = {
            'timestamp': datetime.now().isoformat(),
            'trade_log': self.trade_log,
            'execution_metrics': self.get_execution_metrics()
        }
        
        with open(filename, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)
        
        return filename