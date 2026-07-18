"""
Trade Tracker for managing and logging trade closures in the forensic logging system.
"""
from datetime import datetime
from typing import Dict, Optional
import threading
from infrastructure.logging.forensic_logger import forensic_logger


from typing import Dict, Optional, List, Any

class TradeTracker:
    """Tracks active trades and logs their closures."""

    def __init__(self, forensic_logging_enabled: bool = True):
        self.active_trades: Dict[str, Dict] = {}
        self.closed_trades_history: List[Dict] = []
        self.lock = threading.Lock()
        # Whether to emit forensic logs on trade closure. Injected by the
        # composition root from settings.monitoring.forensic_logging_enabled;
        # default True mirrors the settings-schema default for the unwired/test
        # path, so this module no longer imports bootstrap.settings.loaders (E1).
        self.forensic_logging_enabled = forensic_logging_enabled
        
    def register_trade(self, trade_id: str, symbol: str, side: str, price: float, quantity: float, 
                      sl: float, tp: float, timestamp: datetime, setup_type: Optional[str] = None):
        """Register a new trade that has been opened."""
        with self.lock:
            self.active_trades[trade_id] = {
                'symbol': symbol,
                'side': side,
                'entry_price': price,
                'quantity': quantity,
                'stop_loss': sl,
                'take_profit': tp,
                'entry_timestamp': timestamp,
                'setup_type': setup_type,
                'exit_reason': None,
                'exit_price': None,
                'exit_timestamp': None
            }
    
    def close_trade(self, trade_id: str, exit_price: float, exit_reason: str, 
                   exit_timestamp: datetime = None) -> Optional[Dict]:
        """Close a trade and log the closure to forensic logger."""
        if exit_timestamp is None:
            exit_timestamp = datetime.utcnow()
            
        with self.lock:
            if trade_id not in self.active_trades:
                return None
                
            trade = self.active_trades[trade_id]
            
            # Calculate PnL
            entry_price = trade['entry_price']
            quantity = trade['quantity']
            side = trade['side']
            
            if side.upper() == 'BUY' or (hasattr(side, 'name') and side.name == 'BUY'):
                pnl = (exit_price - entry_price) * quantity
            else:  # SELL
                pnl = (entry_price - exit_price) * quantity
            
            # Calculate ROI percentage
            investment = entry_price * quantity
            roi_pct = (pnl / investment) if investment != 0 else 0.0
            
            # Calculate holding time in seconds
            holding_seconds = (exit_timestamp - trade['entry_timestamp']).total_seconds()
            
            # Update trade record
            trade['exit_reason'] = exit_reason
            trade['exit_price'] = exit_price
            trade['exit_timestamp'] = exit_timestamp
            
            # Add to history for performance attribution
            closed_trade = {
                'trade_id': trade_id,
                'symbol': trade['symbol'],
                'side': side,
                'setup_type': trade.get('setup_type') or 'UNKNOWN',
                'entry_price': entry_price,
                'exit_price': exit_price,
                'quantity': quantity,
                'pnl': pnl,
                'roi_pct': roi_pct,
                'entry_timestamp': trade['entry_timestamp'],
                'exit_timestamp': exit_timestamp,
                'holding_seconds': holding_seconds
            }
            self.closed_trades_history.append(closed_trade)
            
            # Log the trade closure to forensic logger only if enabled
            if self.forensic_logging_enabled:
                forensic_logger.log_broker_close(
                    trade_id=trade_id,
                    pnl=pnl,
                    roi_pct=roi_pct,
                    exit_reason=exit_reason,
                    holding_seconds=int(holding_seconds),
                    timestamp=exit_timestamp
                )
            
            # Remove from active trades
            del self.active_trades[trade_id]
            
            return {
                'trade_id': trade_id,
                'pnl': pnl,
                'roi_pct': roi_pct,
                'exit_reason': exit_reason,
                'holding_seconds': int(holding_seconds)
            }

    def get_setup_pnl_attribution(self) -> Dict[str, Dict[str, Any]]:
        """Return PnL attribution summary metrics by setup type."""
        attribution = {}
        with self.lock:
            for trade in self.closed_trades_history:
                setup = trade.get('setup_type') or 'UNKNOWN'
                pnl = trade.get('pnl', 0.0)
                roi = trade.get('roi_pct', 0.0)
                holding = trade.get('holding_seconds', 0.0)
                
                if setup not in attribution:
                    attribution[setup] = {
                        'total_trades': 0,
                        'wins': 0,
                        'realized_pnl': 0.0,
                        'total_return': 0.0,
                        'total_holding_time': 0.0,
                        'max_drawdown_contribution': 0.0
                    }
                
                stats = attribution[setup]
                stats['total_trades'] += 1
                if pnl > 0:
                    stats['wins'] += 1
                stats['realized_pnl'] += pnl
                stats['total_return'] += roi
                stats['total_holding_time'] += holding
                # Drawdown contribution is the single worst (minimum) trade PnL
                if pnl < stats['max_drawdown_contribution']:
                    stats['max_drawdown_contribution'] = pnl
            
            result = {}
            for setup, stats in attribution.items():
                n = stats['total_trades']
                result[setup] = {
                    'setup_type': setup,
                    'total_trades': n,
                    'win_rate': (stats['wins'] / n) if n > 0 else 0.0,
                    'realized_pnl': stats['realized_pnl'],
                    'average_return': (stats['total_return'] / n) if n > 0 else 0.0,
                    'average_holding_time': (stats['total_holding_time'] / n) if n > 0 else 0.0,
                    'max_drawdown_contribution': stats['max_drawdown_contribution']
                }
        return result


# Global trade tracker instance
trade_tracker = TradeTracker()