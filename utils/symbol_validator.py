"""
Symbol Validator Module
Provides functionality to validate symbols against approved list
"""
import json
import os
from typing import Set, List
from domain.value_objects import Symbol
from shared.logger import EnhancedLogger


class SymbolValidator:
    """Validates symbols against an approved list"""
    
    def __init__(self, config_path: str = None):
        self.logger = EnhancedLogger("SymbolValidator")
        self.approved_symbols: Set[str] = set()
        
        if config_path is None:
            # Default to the approved symbols config
            # The file is located at application/configs/approved_symbols.json from project root
            # This file is in /utils/symbol_validator.py, so we go up 2 levels to project root
            config_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),  # Go up 2 levels to project root
                "application", "configs", "approved_symbols.json"
            )
        
        self.load_approved_symbols(config_path)
    
    def load_approved_symbols(self, config_path: str):
        """Load approved symbols from configuration file"""
        try:
            with open(config_path, 'r') as f:
                approved_list = json.load(f)
            
            # Normalize symbols to uppercase and handle different formats
            normalized_symbols = set()
            for symbol_str in approved_list:
                # Convert to uppercase and handle both formats (e.g., "BTC/USDT" and "BTCUSDT")
                normalized = symbol_str.upper().replace("/", "")
                normalized_symbols.add(normalized)
                
                # Also add the slash format for compatibility
                slash_format = symbol_str.upper()
                normalized_symbols.add(slash_format)
            
            self.approved_symbols = normalized_symbols
            self.logger.info(f"Loaded {len(self.approved_symbols)} approved symbols from {config_path}")
            
        except FileNotFoundError:
            self.logger.error(f"Approved symbols configuration file not found: {config_path}")
            raise
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in approved symbols configuration: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Error loading approved symbols: {e}")
            raise
    
    def is_symbol_approved(self, symbol: Symbol) -> bool:
        """Check if a symbol is in the approved list"""
        symbol_str = symbol.value.upper()
        
        # Check both formats: with and without slash
        # e.g., "BTCUSDT" and "BTC/USDT"
        return (symbol_str in self.approved_symbols or 
                symbol_str.replace("/", "") in self.approved_symbols or
                symbol_str.replace("USDT", "/USDT") in self.approved_symbols)
    
    def get_approved_symbols(self) -> Set[str]:
        """Get the set of approved symbols"""
        return self.approved_symbols.copy()


# Global instance for easy access
symbol_validator = SymbolValidator()