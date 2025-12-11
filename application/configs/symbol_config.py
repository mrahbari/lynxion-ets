"""
Symbol configuration for the Downloader/Sync Engine.

This module contains the authoritative symbol list and per-symbol metadata.
"""
import os
from typing import List, Optional
from domain.sync.entities import SymbolSyncConfig


def _parse_wfo_symbols() -> List[SymbolSyncConfig]:
    """Parse symbols from WFO_COINS environment variable"""
    wfo_coins_str = os.getenv("WFO_COINS", "")
    if not wfo_coins_str:
        # If WFO_COINS is not set, return empty list - only use environment
        print("⚠️  WARNING: WFO_COINS environment variable not set. No symbols will be processed.")
        print("   Please set WFO_COINS in your .env file (e.g., WFO_COINS=BTCUSDT,ETHUSDT,...)")
        return []

    symbol_names = [s.strip() for s in wfo_coins_str.split(',')]
    symbol_configs = []

    for i, symbol in enumerate(symbol_names):
        # Format symbol with hyphen if needed
        formatted_symbol = symbol.replace('USDT', '-USDT') if 'USDT' in symbol else symbol
        symbol_configs.append(SymbolSyncConfig(
            symbol=formatted_symbol,
            exchange=os.getenv("SYNC_DEFAULT_EXCHANGE", "binance"),
            max_api_window_minutes=int(os.getenv("SYNC_MAX_WINDOW_MINUTES", "1440")),
            rate_limit_requests_per_minute=int(os.getenv("SYNC_RATE_LIMIT", "10")),
            enabled=True,
            priority=max(10 - i//3, 1)  # Higher priority for first symbols
        ))

    return symbol_configs


def get_symbols() -> List[SymbolSyncConfig]:
    """Get the list of configured symbols from WFO_COINS

    Returns:
        List of SymbolSyncConfig objects
    """
    return _parse_wfo_symbols()


def get_symbol_config(symbol: str) -> Optional[SymbolSyncConfig]:
    """Get configuration for a specific symbol

    Args:
        symbol: The symbol to look up

    Returns:
        SymbolSyncConfig if found, None otherwise
    """
    # Normalize the symbol format for comparison
    normalized_symbol = symbol.replace('-', '').upper()  # Convert BTC-USDT to BTCUSDT for comparison

    for sym_cfg in get_symbols():
        # Normalize stored symbol for comparison
        stored_normalized = sym_cfg.symbol.replace('-', '').upper()
        if stored_normalized == normalized_symbol:
            return sym_cfg

    return None