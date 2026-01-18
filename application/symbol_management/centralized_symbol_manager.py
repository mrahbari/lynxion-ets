"""
Centralized Symbol Manager - Single source of truth for approved symbols.

This module provides a unified interface for managing symbols across all downloaders
and prevents duplicate symbol registration in multiple places.
"""
import json
import os
from typing import List, Set, Dict, Optional
from pathlib import Path
from domain.value_objects import Symbol
from shared.logger import EnhancedLogger


class CentralizedSymbolManager:
    """
    Centralized symbol manager that serves as the single source of truth for approved symbols.
    Coordinates between environment variables, configuration files, and runtime validation.
    """
    
    def __init__(self,
                 approved_symbols_path: str = None,
                 sync_symbols_path: str = None):
        self.logger = EnhancedLogger("CentralizedSymbolManager")

        # Set up paths
        if approved_symbols_path is None:
            # Use the archive location as the primary source of truth
            approved_symbols_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),  # Go up to project root/
                "data", "approved-symbols", "approved_symbols.json"
            )
        
        if sync_symbols_path is None:
            sync_symbols_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),  # Go up to application/
                "configs", "sync_symbols.json"
            )
        
        self.approved_symbols_path = approved_symbols_path
        self.sync_symbols_path = sync_symbols_path
        
        # Load symbols
        self.approved_symbols = self._load_approved_symbols()
        self.sync_symbols = self._load_sync_symbols()

        # Create unified symbol list
        self.unified_symbols = self._create_unified_symbol_list()

        self.logger.info(f"Initialized CentralizedSymbolManager with {len(self.unified_symbols)} symbols")
    
    def _load_approved_symbols(self) -> Set[str]:
        """Load approved symbols from the approved_symbols.json file."""
        try:
            with open(self.approved_symbols_path, 'r') as f:
                approved_list = json.load(f)
            
            # Normalize symbols to uppercase and handle different formats
            normalized_symbols = set()
            for symbol_str in approved_list:
                # Convert to uppercase and handle both formats (e.g., "BTC/USDT" and "BTCUSDT")
                normalized = symbol_str.upper().replace("/", "").replace("-", "")
                normalized_symbols.add(normalized)
                
                # Also add the hyphen format for compatibility (e.g., BTC-USDT)
                hyphen_format = symbol_str.upper().replace("/", "-")
                if "-" in hyphen_format:
                    normalized_symbols.add(hyphen_format)
                
                # Also add the slash format for compatibility
                slash_format = symbol_str.upper()
                normalized_symbols.add(slash_format)
            
            self.logger.info(f"Loaded {len(normalized_symbols)} approved symbols from {self.approved_symbols_path}")
            return normalized_symbols
            
        except FileNotFoundError:
            self.logger.error(f"Approved symbols configuration file not found: {self.approved_symbols_path}")
            return set()
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in approved symbols configuration: {e}")
            return set()
        except Exception as e:
            self.logger.error(f"Error loading approved symbols: {e}")
            return set()
    
    def _load_sync_symbols(self) -> List[str]:
        """Load sync symbols from the sync_symbols.json file."""
        try:
            with open(self.sync_symbols_path, 'r') as f:
                sync_data = json.load(f)
            
            # Get symbols from the main 'symbols' array first
            symbol_names = sync_data.get("symbols", [])
            
            # If that doesn't exist, try to consolidate from categories
            if not symbol_names and "categories" in sync_data:
                for category_coins in sync_data["categories"].values():
                    symbol_names.extend(category_coins)
            
            # Normalize symbols
            normalized_symbols = []
            for symbol in symbol_names:
                normalized = symbol.upper().replace("/", "").replace("-", "")
                normalized_symbols.append(normalized)
            
            self.logger.info(f"Loaded {len(normalized_symbols)} sync symbols from {self.sync_symbols_path}")
            return normalized_symbols
            
        except FileNotFoundError:
            self.logger.warning(f"Sync symbols configuration file not found: {self.sync_symbols_path}")
            return []
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in sync symbols configuration: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Error loading sync symbols: {e}")
            return []
    
    def _create_unified_symbol_list(self) -> List[str]:
        """Create a unified list of symbols from all sources."""
        # Get symbols from environment variable (WFO_COINS)
        wfo_coins_str = os.getenv("WFO_COINS", "")
        env_symbols = []
        if wfo_coins_str:
            env_symbols = [s.strip().upper().replace("/", "").replace("-", "")
                          for s in wfo_coins_str.split(',') if s.strip()]

        # Combine all sources: environment and sync config (approved symbols are filtered later)
        all_symbols = set(env_symbols + self.sync_symbols)

        # Filter to only include symbols that are in the approved list
        unified = []
        for symbol in all_symbols:
            if self.is_symbol_approved(symbol):
                if symbol not in unified:  # Avoid duplicates
                    unified.append(symbol)

        self.logger.info(f"Created unified symbol list with {len(unified)} symbols")
        return unified
    
    def get_unified_symbols(self) -> List[str]:
        """Get the unified list of approved symbols."""
        return self.unified_symbols.copy()
    
    def get_approved_symbols(self) -> Set[str]:
        """Get the set of approved symbols."""
        return self.approved_symbols.copy()
    
    def get_sync_symbols(self) -> List[str]:
        """Get the list of sync symbols."""
        return self.sync_symbols.copy()
    
    def is_symbol_approved(self, symbol: str) -> bool:
        """Check if a symbol is in the approved list."""
        symbol_upper = symbol.upper()
        
        # Check various formats: with and without separators
        formats_to_check = [
            symbol_upper,
            symbol_upper.replace("/", ""),
            symbol_upper.replace("-", ""),
            symbol_upper.replace("USDT", "/USDT"),
            symbol_upper.replace("USDT", "-USDT"),
        ]
        
        for fmt in formats_to_check:
            if fmt in self.approved_symbols:
                return True
        
        return False
    
    def is_symbol_in_sync_list(self, symbol: str) -> bool:
        """Check if a symbol is in the sync list."""
        symbol_upper = symbol.upper().replace("/", "").replace("-", "")
        return symbol_upper in [s.replace("/", "").replace("-", "") for s in self.sync_symbols]
    
    def is_symbol_in_unified_list(self, symbol: str) -> bool:
        """Check if a symbol is in the unified list."""
        symbol_upper = symbol.upper().replace("/", "").replace("-", "")
        return symbol_upper in [s.replace("/", "").replace("-", "") for s in self.unified_symbols]
    
    def get_formatted_symbol_for_storage(self, symbol: str) -> str:
        """
        Format symbol for storage path following the required format.
        
        Converts symbols to the format: SOL-USDT.csv
        """
        symbol_upper = symbol.upper()
        
        # Convert to hyphen format if it contains USDT, etc.
        if "USDT" in symbol_upper:
            # Convert BTCUSDT to BTC-USDT format
            base = symbol_upper.replace("USDT", "")
            return f"{base}-USDT"
        elif "/" in symbol_upper:
            # Convert BTC/USDT to BTC-USDT format
            return symbol_upper.replace("/", "-")
        else:
            # If no known format, return as is
            return symbol_upper
    
    def get_formatted_symbol_for_exchange(self, symbol: str) -> str:
        """
        Format symbol for exchange API (e.g., BTC-USDT to BTCUSDT).
        """
        return symbol.replace('-', '').replace('/', '')


# Global instance for easy access
symbol_manager = CentralizedSymbolManager()


def get_unified_symbols() -> List[str]:
    """Get the unified list of approved symbols."""
    return symbol_manager.get_unified_symbols()


def is_symbol_approved(symbol: str) -> bool:
    """Check if a symbol is approved."""
    return symbol_manager.is_symbol_approved(symbol)


def get_formatted_symbol_for_storage(symbol: str) -> str:
    """Format symbol for storage path."""
    return symbol_manager.get_formatted_symbol_for_storage(symbol)


def get_formatted_symbol_for_exchange(symbol: str) -> str:
    """Format symbol for exchange API."""
    return symbol_manager.get_formatted_symbol_for_exchange(symbol)


def get_approved_symbols() -> Set[str]:
    """Get the set of approved symbols."""
    return symbol_manager.get_approved_symbols()


def is_symbol_in_unified_list(symbol: str) -> bool:
    """Check if a symbol is in the unified list."""
    return symbol_manager.is_symbol_in_unified_list(symbol)