"""
Trade Tracker for managing and logging trade closures in the forensic logging system.
"""
from datetime import datetime
from typing import Dict, Optional
import threading
import os
from infrastructure.logging.forensic_logger import forensic_logger


class TradeTracker:
    """Tracks active trades and logs their closures."""

    def __init__(self):
        self.active_trades: Dict[str, Dict] = {}
        self.lock = threading.Lock()
        # Check if forensic logging is enabled
        self.forensic_logging_enabled = os.getenv('FORENSIC_LOGGING_ENABLED', 'true').lower() == 'true'
        
    def register_trade(self, trade_id: str, symbol: str, side: str, price: float, quantity: float, 
                      sl: float, tp: float, timestamp: datetime):
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


# Global trade tracker instance
trade_tracker = TradeTracker()