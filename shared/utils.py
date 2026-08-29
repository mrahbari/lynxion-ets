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
    """Calculate position size based on risk management - DEPRECATED: Use Risk Manager instead"""
    # According to the risk governance rules, position sizing should only be done by the Risk module
    # This function is deprecated and should not be used in production
    # The actual calculation must be done by the Risk module.

    # Return a default value that will be overridden by the risk manager
    # This is just a placeholder to maintain interface compatibility
    return 0.0


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


def format_price_for_api(price: float, max_total_digits: int = 9) -> str:
    """
    Format price according to API requirements:
    - Total digits (integer + decimal) must not exceed max_total_digits
    - For prices >= $1: max 5 decimal places
    - For prices < $1: max 8 decimal places
    - No trailing zeros unless necessary to maintain precision
    """
    if price is None:
        return None

    # Determine max decimal places based on price value
    if abs(price) >= 1:
        max_decimal_places = 5
    else:
        max_decimal_places = 8

    # Start with the appropriate precision based on price range
    initial_format = f"{price:.{max_decimal_places}f}"

    # Check if the formatted price exceeds the total digit limit
    clean_initial = initial_format.replace('.', '').lstrip('-')
    if len(clean_initial) <= max_total_digits:
        # If it fits within the limit, apply trailing zero removal
        if '.' in initial_format:
            result = initial_format.rstrip('0').rstrip('.')
        else:
            result = initial_format
        return result

    # If it exceeds the limit, we need to reduce precision
    # First, determine how many integer digits we have
    if '.' in initial_format:
        integer_part, _ = initial_format.split('.')
    else:
        integer_part = initial_format

    integer_digits = len(integer_part.lstrip('-'))

    # If even the integer part exceeds the limit, return a rounded integer
    if integer_digits >= max_total_digits:
        # Round to fit within the digit limit
        digits_to_reduce = integer_digits - max_total_digits + 1  # +1 to ensure we're under limit
        factor = 10 ** digits_to_reduce
        rounded_value = round(price / factor) * factor
        result = f"{int(rounded_value):.0f}"
        # Double check we're within limits, if not reduce further
        while len(result.lstrip('-')) > max_total_digits:
            factor *= 10
            rounded_value = round(price / factor) * factor
            result = f"{int(rounded_value):.0f}"
        return result

    # If integer part is within limits but total exceeds limits, reduce decimal places
    available_decimal_digits = max_total_digits - integer_digits
    if available_decimal_digits < 0:
        available_decimal_digits = 0

    # Format with the available decimal places
    result = f"{price:.{available_decimal_digits}f}"

    # Remove trailing zeros after decimal point, but keep the decimal point if there were decimals
    if '.' in result:
        result = result.rstrip('0').rstrip('.')

    return result


def sanitize_sltp_levels(
    entry_price: float,
    side: Any,  # 'BUY'/'SELL', OrderSide, or SignalType
    stop_loss: Optional[float] = None,
    take_profit: Optional[float] = None,
    default_sl_pct: float = 0.02,
    default_tp_pct: float = 0.035,
    min_sl_pct: float = 0.012,
    max_sl_pct: float = 0.030,
    max_tp_pct: float = 0.055
) -> tuple:
    """
    Centralized, robust utility for sanitizing and validating Stop Loss and Take Profit levels.
    Guarantees mathematically valid SL/TP relative to entry_price with realistic caps for perpetual leverage trading.

    Returns:
        tuple: (sanitized_stop_loss, sanitized_take_profit)
    """
    entry = float(entry_price) if entry_price else 0.0
    if entry <= 0:
        return 0.0, 0.0

    side_str = side.name if hasattr(side, 'name') else (side.value if hasattr(side, 'value') else str(side))
    is_buy = side_str.upper() in ('BUY', 'LONG')

    sl = float(stop_loss) if stop_loss is not None else 0.0
    tp = float(take_profit) if take_profit is not None else 0.0

    if is_buy:
        # BUY: Stop loss must be below entry, clamped between min_sl_pct and max_sl_pct
        if sl >= entry or sl <= 0:
            sl = entry * (1.0 - default_sl_pct)
        else:
            sl_dist_pct = (entry - sl) / entry
            if sl_dist_pct < min_sl_pct:
                sl = entry * (1.0 - min_sl_pct)
            elif sl_dist_pct > max_sl_pct:
                sl = entry * (1.0 - max_sl_pct)

        # BUY: Take profit must be above entry, at least 1.5x SL distance, capped at max_tp_pct
        sl_dist = entry - sl
        min_tp_dist = max(entry * default_tp_pct, 1.5 * sl_dist)
        if tp <= entry or tp <= 0:
            tp = entry + min(min_tp_dist, entry * max_tp_pct)
        else:
            tp_dist_pct = (tp - entry) / entry
            if tp_dist_pct > max_tp_pct:
                tp = entry * (1.0 + max_tp_pct)
            elif (tp - entry) < (1.5 * sl_dist):
                tp = entry + min(1.5 * sl_dist, entry * max_tp_pct)
    else:
        # SELL: Stop loss must be above entry, clamped between min_sl_pct and max_sl_pct
        if sl <= entry or sl <= 0:
            sl = entry * (1.0 + default_sl_pct)
        else:
            sl_dist_pct = (sl - entry) / entry
            if sl_dist_pct < min_sl_pct:
                sl = entry * (1.0 + min_sl_pct)
            elif sl_dist_pct > max_sl_pct:
                sl = entry * (1.0 + max_sl_pct)

        # SELL: Take profit must be below entry, at least 1.5x SL distance, capped at max_tp_pct
        sl_dist = sl - entry
        min_tp_dist = max(entry * default_tp_pct, 1.5 * sl_dist)
        if tp >= entry or tp <= 0:
            tp = max(0.0001, entry - min(min_tp_dist, entry * max_tp_pct))
        else:
            tp_dist_pct = (entry - tp) / entry
            if tp_dist_pct > max_tp_pct:
                tp = max(0.0001, entry * (1.0 - max_tp_pct))
            elif (entry - tp) < (1.5 * sl_dist):
                tp = max(0.0001, entry - min(1.5 * sl_dist, entry * max_tp_pct))

    precision = 5 if entry >= 1.0 else 8
    return round(sl, precision), round(tp, precision)