"""
Unified Symbol Format & Conversion Helper for all Broker / Exchange Integrations.
"""
from typing import Dict, List, Optional, Tuple, Any
import re


class SymbolFormatHelper:
    """Centralized helper for standardizing, validating, and converting symbols per target broker."""

    QUOTE_CURRENCIES = [
        'USDT', 'USD', 'USDC', 'BTC', 'ETH', 'BNB', 'BUSD', 'DAI', 'TUSD', 'PAX',
        'USDD', 'FDUSD', 'TERRA', 'FRAX', 'LUSD', 'FEI', 'ALUSD', 'GUSD', 'HUSD',
        'EUR', 'GBP', 'JPY', 'TRY', 'RUB', 'ZAR', 'UAH', 'NGN', 'BRL', 'AUD',
        'CAD', 'CHF', 'CNY', 'HKD', 'IDR', 'INR', 'KRW', 'SGD', 'THB', 'VND'
    ]

    @classmethod
    def normalize_symbol(cls, symbol: Any) -> str:
        """Normalize symbol to standard uppercase string without separators (e.g. 'BTCUSDT')."""
        s = getattr(symbol, 'value', None) or str(symbol or "")
        return s.upper().replace('-', '').replace('/', '').replace('_', '').replace(' ', '').strip()

    @classmethod
    def split_base_quote(cls, symbol: Any) -> Tuple[str, str]:
        """Extract (base, quote) tuple from any symbol representation."""
        norm = cls.normalize_symbol(symbol)
        # Check known quote currencies sorted by length descending
        for qc in sorted(cls.QUOTE_CURRENCIES, key=len, reverse=True):
            if norm.endswith(qc):
                base = norm[:-len(qc)]
                if len(base) >= 1:
                    return base, qc
        return norm, "USDT"

    @classmethod
    def format_symbol_for_exchange(cls, symbol: Any, exchange_name: str) -> str:
        """Format symbol according to the specific broker / exchange API specifications.

        - BingX perpetual: 'BTC-USDT'
        - Binance / CCXT:  'BTC/USDT'
        - MEXC contract:   'BTC_USDT'
        - Phemex contract: 'BTC/USDT'
        - Standard default:'BTCUSDT'
        """
        ex = str(exchange_name or "").lower().strip()
        base, quote = cls.split_base_quote(symbol)

        if not base:
            return cls.normalize_symbol(symbol)

        if ex in ('bingx', 'bingx_swap', 'bingx_futures'):
            return f"{base}-{quote}"
        elif ex in ('binance', 'phemex', 'bybit', 'okx', 'ccxt'):
            return f"{base}/{quote}"
        elif ex in ('mexc', 'mexc_futures'):
            return f"{base}_{quote}"
        else:
            return f"{base}{quote}"

    @classmethod
    def format_order_symbol(cls, symbol: Any, exchange_name: str) -> str:
        """Alias for formatting before order placement."""
        return cls.format_symbol_for_exchange(symbol, exchange_name)

    @classmethod
    def parse_symbol_from_exchange(cls, symbol: Any, exchange_name: Optional[str] = None) -> str:
        """Parse symbol from exchange format back to standard normalized format (e.g. 'BTCUSDT')."""
        return cls.normalize_symbol(symbol)

    @classmethod
    def is_valid_symbol_format(cls, symbol: Any) -> bool:
        """Validate if symbol has proper format and recognizable quote currency."""
        norm = cls.normalize_symbol(symbol)
        if len(norm) < 4 or not re.match(r'^[A-Za-z0-9]+$', norm):
            return False
        base, quote = cls.split_base_quote(norm)
        return len(base) >= 1 and quote in cls.QUOTE_CURRENCIES