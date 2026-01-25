"""
Symbol configuration for the Downloader/Sync Engine.

This module contains the authoritative symbol list and per-symbol metadata.
"""
import json
from typing import List, Optional
from pathlib import Path
from domain.sync.entities import SymbolSyncConfig
from application.configs.configs import Configs


def _parse_wfo_symbols() -> List[SymbolSyncConfig]:
    """Parse symbols from multiple sources: WFO_COINS environment variable, sync_symbols.json file, or default list"""

    # First, try to read from sync_symbols.json file if it exists (for better organization)
    coins_json_path = Path(Configs.data.coins_config_path if Configs.data and hasattr(Configs.data, 'coins_config_path') else "./application/configs/sync_symbols.json")
    if coins_json_path.exists():
        try:
            with open(coins_json_path, 'r') as f:
                coins_data = json.load(f)
                # Try to read from the main 'symbols' array first
                symbol_names = coins_data.get("symbols", [])
                # If that doesn't exist, try to consolidate from categories
                if not symbol_names and "categories" in coins_data:
                    for category_coins in coins_data["categories"].values():
                        symbol_names.extend(category_coins)
        except Exception as e:
            print(f"⚠️  WARNING: Could not load sync_symbols.json from {coins_json_path}: {e}")
            symbol_names = []
    else:
        # If sync_symbols.json doesn't exist, try the WFO_COINS environment variable
        wfo_coins_str = Configs.wfo.wfo_coins if Configs.wfo and Configs.wfo.wfo_coins else ""
        if not wfo_coins_str:
            # If neither sync_symbols.json nor WFO_COINS is set, try common default
            print("⚠️  WARNING: WFO_COINS environment variable not set and sync_symbols.json not found. No symbols will be "
                  "processed.")
            print("   Please set WFO_COINS in your .env file or create ./application/configs/sync_symbols.json")
            print("   Example sync_symbols.json format: {\"symbols\": [\"BTCUSDT\", \"ETHUSDT\", \"ZECUSDT\"]}")
            return []

        symbol_names = [s.strip() for s in wfo_coins_str.split(',')]

    if not symbol_names:
        print("⚠️  WARNING: No symbols found in WFO_COINS or sync_symbols.json. No symbols will be processed.")
        return []

    symbol_configs = []

    for i, symbol in enumerate(symbol_names):
        # Format symbol with hyphen if needed
        formatted_symbol = symbol.replace('USDT', '-USDT') if 'USDT' in symbol else symbol
        symbol_configs.append(SymbolSyncConfig(
            symbol=formatted_symbol,
            exchange=Configs.data.sync_default_exchange if Configs.data and hasattr(Configs.data, 'sync_default_exchange') else "binance",
            max_api_window_minutes=Configs.data.sync_max_window_minutes if Configs.data and hasattr(Configs.data, 'sync_max_window_minutes') else 1440,
            rate_limit_requests_per_minute=Configs.data.sync_rate_limit if Configs.data and hasattr(Configs.data, 'sync_rate_limit') else 10,
            enabled=True,
            priority=max(10 - i // 3, 1)  # Higher priority for first symbols
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
