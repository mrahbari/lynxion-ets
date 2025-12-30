"""
Symbol format helper for consistent symbol formatting across all exchanges.
"""
from typing import Dict, List, Optional
import re


class SymbolFormatHelper:
    """Helper class for consistent symbol formatting across exchanges."""

    @staticmethod
    def format_symbol_for_exchange(symbol: str, exchange_name: str) -> str:
        """
        Format symbol according to exchange requirements.
        
        Args:
            symbol: Symbol in various formats (e.g., BTCUSDT, BTC-USDT, BTC/USDT)
            exchange_name: Name of the exchange (binance, bingx, mexc, phemex)
            
        Returns:
            Formatted symbol string
        """
        # Normalize the input symbol by removing any existing separators
        normalized_symbol = symbol.replace('-', '').replace('/', '').replace('_', '')

        # Define exchange-specific formats
        slash_format_exchanges = ['binance', 'bingx', 'mexc', 'phemex']

        if exchange_name.lower() in slash_format_exchanges:
            # These exchanges expect the format like BTC/USDT
            # Extract base and quote currency by looking for common quote currencies at the end
            quote_currencies = [
                'USDT', 'USD', 'BTC', 'ETH', 'BNB', 'BUSD', 'USDC', 'DAI', 'TUSD', 'PAX', 
                'USDD', 'FDUSD', 'TERRA', 'FRAX', 'LUSD', 'FEI', 'ALUSD', 'GUSD', 'HUSD',
                'EUR', 'GBP', 'JPY', 'TRY', 'RUB', 'ZAR', 'UAH', 'NGN', 'BRL', 'AUD', 
                'CAD', 'CHF', 'CNY', 'HKD', 'IDR', 'INR', 'KRW', 'SGD', 'THB', 'VND'
            ]

            # Look for quote currency at the end of the symbol first (most common case)
            for qc in quote_currencies:
                if normalized_symbol.upper().endswith(qc.upper()):
                    base = normalized_symbol[:-len(qc)]
                    quote = qc
                    return f"{base}/{quote}"

            # If not found at the end, return the normalized symbol as is
            return normalized_symbol
        else:
            # Default to no separator format for other exchanges
            return normalized_symbol

    @staticmethod
    def parse_symbol_from_exchange(symbol: str, exchange_name: str) -> str:
        """
        Parse symbol from exchange format back to standard format.
        
        Args:
            symbol: Symbol in exchange format (e.g., BTC/USDT, BTC-USDT)
            exchange_name: Name of the exchange
            
        Returns:
            Standard symbol format (e.g., BTCUSDT)
        """
        # Remove separators and return standard format
        return symbol.replace('-', '').replace('/', '').replace('_', '')

    @staticmethod
    def normalize_symbol(symbol: str) -> str:
        """
        Normalize symbol to standard format (e.g., BTCUSDT).
        
        Args:
            symbol: Symbol in any format
            
        Returns:
            Normalized symbol in standard format
        """
        return symbol.replace('-', '').replace('/', '').replace('_', '')

    @staticmethod
    def is_valid_symbol_format(symbol: str) -> bool:
        """
        Check if symbol has a valid format.
        
        Args:
            symbol: Symbol to validate
            
        Returns:
            True if valid, False otherwise
        """
        # Basic validation: should have at least 6 characters (e.g., BTCUSDT)
        # and start with letters followed by letters/numbers
        if len(symbol) < 6:
            return False
        
        # Should contain only letters and numbers
        if not re.match(r'^[A-Za-z0-9]+$', symbol):
            return False
            
        # Should end with common quote currencies
        quote_currencies = [
            'USDT', 'USD', 'BTC', 'ETH', 'BNB', 'BUSD', 'USDC', 'DAI', 'TUSD', 'PAX',
            'USDD', 'FDUSD', 'TERRA', 'FRAX', 'LUSD', 'FEI', 'ALUSD', 'GUSD', 'HUSD',
            'EUR', 'GBP', 'JPY', 'TRY', 'RUB', 'ZAR', 'UAH', 'NGN', 'BRL', 'AUD',
            'CAD', 'CHF', 'CNY', 'HKD', 'IDR', 'INR', 'KRW', 'SGD', 'THB', 'VND'
        ]
        
        for quote in quote_currencies:
            if symbol.upper().endswith(quote.upper()):
                base = symbol[:-len(quote)]
                if len(base) >= 1:  # Base currency should be at least 1 character
                    return True
        
        return False