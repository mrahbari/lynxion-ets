"""
Unified Symbol Configuration - Single source of truth for all symbol-related configurations.

This module provides a unified interface for managing symbols across all downloaders
and prevents duplicate symbol registration in multiple places.
"""
import os
import json
from typing import List, Dict, Any, Optional
from pathlib import Path
from application.symbol_management.centralized_symbol_manager import symbol_manager


class UnifiedSymbolConfig:
    """
    Unified symbol configuration that coordinates between environment variables,
    configuration files, and runtime validation.
    """
    
    def __init__(self):
        self.manager = symbol_manager
    
    def get_symbols_for_downloader(self) -> List[str]:
        """
        Get symbols for the downloaders following the unified approach.
        This ensures all downloaders use the same symbol list.
        """
        return self.manager.get_unified_symbols()
    
    def get_symbols_for_backtesting(self) -> List[str]:
        """
        Get symbols for backtesting - same as downloaders to ensure consistency.
        """
        return self.manager.get_unified_symbols()
    
    def get_symbols_for_live_trading(self) -> List[str]:
        """
        Get symbols for live trading - same as downloaders to ensure consistency.
        """
        return self.manager.get_unified_symbols()
    
    def validate_symbol(self, symbol: str) -> bool:
        """
        Validate a symbol against the unified approved list.
        """
        return self.manager.is_symbol_approved(symbol)
    
    def format_symbol_for_storage(self, symbol: str) -> str:
        """
        Format symbol for storage path following the required format.
        """
        return self.manager.get_formatted_symbol_for_storage(symbol)
    
    def format_symbol_for_exchange(self, symbol: str) -> str:
        """
        Format symbol for exchange API.
        """
        return self.manager.get_formatted_symbol_for_exchange(symbol)
    
    def get_symbol_metadata(self, symbol: str) -> Dict[str, Any]:
        """
        Get metadata for a specific symbol.
        """
        # This could be extended to include additional metadata
        return {
            "symbol": symbol,
            "is_approved": self.validate_symbol(symbol),
            "storage_format": self.format_symbol_for_storage(symbol),
            "exchange_format": self.format_symbol_for_exchange(symbol)
        }
    
    def get_all_categories(self) -> Dict[str, List[str]]:
        """
        Get all symbol categories for organizational purposes.
        """
        # This could be expanded to include category information
        unified_symbols = self.get_symbols_for_downloader()
        return {
            "all_symbols": unified_symbols,
            "count": len(unified_symbols)
        }


# Global instance for easy access
unified_config = UnifiedSymbolConfig()


def get_symbols_for_all_purposes() -> List[str]:
    """Get symbols for all purposes (downloaders, backtesting, live trading)."""
    return unified_config.get_symbols_for_downloader()


def is_valid_symbol(symbol: str) -> bool:
    """Validate a symbol against the unified approved list."""
    return unified_config.validate_symbol(symbol)


def format_symbol_for_data_storage(symbol: str) -> str:
    """Format symbol for data storage path."""
    return unified_config.format_symbol_for_storage(symbol)


def format_symbol_for_api(symbol: str) -> str:
    """Format symbol for API calls."""
    return unified_config.format_symbol_for_exchange(symbol)


def get_symbol_metadata(symbol: str) -> Dict[str, Any]:
    """Get metadata for a specific symbol."""
    return unified_config.get_symbol_metadata(symbol)