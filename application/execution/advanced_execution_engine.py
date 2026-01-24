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
from infrastructure.risk.advanced_sltp_manager import sltp_manager, AdvancedSLTPManager, RegimeType as SlTpRegimeType, PositionSide


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
        Calculate dynamic stop loss and take profit - DEPRECATED: Use Risk Manager instead
        """
        # According to the risk governance rules, SL/TP calculation should only be done by the Risk module
        # This method is deprecated and should not be used in production
        # The actual calculation must be done by the Risk module.

        # Return default values that will be overridden by the risk manager
        # This is just a placeholder to maintain interface compatibility

        # Default values based on direction
        if direction == PositionDirection.LONG:
            # For long positions: SL below entry, TP above entry
            default_sl_distance = entry_price * 0.02  # 2% stop loss
            default_tp_distance = entry_price * 0.03  # 3% take profit
            sl = entry_price - default_sl_distance
            tp = entry_price + default_tp_distance
        else:  # SHORT
            # For short positions: SL above entry, TP below entry
            default_sl_distance = entry_price * 0.02  # 2% stop loss
            default_tp_distance = entry_price * 0.03  # 3% take profit
            sl = entry_price + default_sl_distance
            tp = entry_price - default_tp_distance

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

        # According to risk governance rules, stop loss and take profit should be calculated by the Risk module
        # We'll delegate to the advanced SL/TP manager for proper calculation based on volatility and other factors

        # Convert the regime context to the appropriate format for the SL/TP manager
        sltp_regime = SlTpRegimeType.NORMAL
        if regime_context:
            if 'trending' in regime_context.lower():
                sltp_regime = SlTpRegimeType.BULLISH_TRENDING if 'bullish' in regime_context.lower() else SlTpRegimeType.BEARISH_TRENDING
            elif 'high_volatility' in regime_context.lower():
                sltp_regime = SlTpRegimeType.HIGH_VOLATILITY
            elif 'low_volatility' in regime_context.lower():
                sltp_regime = SlTpRegimeType.LOW_VOLATILITY
            elif 'choppy' in regime_context.lower():
                sltp_regime = SlTpRegimeType.CHOPPY
            elif 'breakout' in regime_context.lower():
                sltp_regime = SlTpRegimeType.BREAKOUT

        # Map PositionDirection to PositionSide for the SL/TP manager
        if direction == PositionDirection.LONG:
            position_side_for_sltp = PositionSide.LONG
        else:  # PositionDirection.SHORT
            position_side_for_sltp = PositionSide.SHORT

        # Use the advanced SL/TP manager to calculate proper levels based on volatility and regime
        sltp_result = sltp_manager.calculate_levels(
            entry_price=entry_price,
            position_side=position_side_for_sltp,
            atr_value=volatility * entry_price,  # Convert volatility percentage to price-based ATR
            regime=sltp_regime,
            volatility=volatility,
            trend_strength=signal_strength
        )

        sl = sltp_result.stop_loss
        tp = sltp_result.take_profit

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