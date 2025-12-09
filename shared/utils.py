import time
import hashlib
import hmac
import json
from typing import Any, Dict, Optional
from datetime import datetime, timezone


def generate_client_order_id(strategy_name: str, symbol: str) -> str:
    """Generate a unique client order ID"""
    timestamp = str(int(time.time() * 1000))
    message = f"{strategy_name}_{symbol}_{timestamp}"
    return hashlib.md5(message.encode()).hexdigest()


def calculate_position_size(balance: float, risk_per_trade: float, entry_price: float, stop_loss: float) -> float:
    """Calculate position size based on risk management"""
    risk_amount = balance * risk_per_trade
    price_distance = abs(entry_price - stop_loss) if stop_loss != 0 else entry_price * 0.02  # default 2%
    position_size = risk_amount / price_distance
    return position_size


def normalize_symbol(symbol: str) -> str:
    """Normalize symbol format"""
    return symbol.upper().replace('/', '').replace('_', '')


def now_utc() -> datetime:
    """Get current time in UTC"""
    return datetime.now(timezone.utc)


def timestamp_to_datetime(timestamp: float) -> datetime:
    """Convert timestamp to datetime object"""
    return datetime.fromtimestamp(timestamp, tz=timezone.utc)


def calculate_pnl(entry_price: float, current_price: float, quantity: float, is_long: bool = True) -> float:
    """Calculate profit and loss"""
    if is_long:
        return (current_price - entry_price) * quantity
    else:
        return (entry_price - current_price) * quantity


def calculate_percentage_change(old_value: float, new_value: float) -> float:
    """Calculate percentage change between two values"""
    if old_value == 0:
        return 0.0
    return (new_value - old_value) / old_value * 100


def sign_message(message: str, secret: str) -> str:
    """Sign a message using HMAC SHA256"""
    return hmac.new(
        secret.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()


def json_dumps(data: Any) -> str:
    """Safely serialize to JSON"""
    return json.dumps(data, default=str)


def json_loads(json_str: str) -> Any:
    """Safely deserialize from JSON"""
    return json.loads(json_str)