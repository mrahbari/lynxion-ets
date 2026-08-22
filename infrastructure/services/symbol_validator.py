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
    """Validates symbols against an approved list and dynamic blacklist configuration."""
    
    def __init__(self, config_path: str = None, blacklist_path: str = None):
        self.logger = EnhancedLogger("SymbolValidator")
        self.approved_symbols: Set[str] = set()
        self.blacklisted_symbols: Set[str] = set()
        
        base_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "application", "configs"
        )
        if config_path is None:
            config_path = os.path.join(base_dir, "approved_symbols.json")
        if blacklist_path is None:
            blacklist_path = os.path.join(base_dir, "blacklisted_symbols.json")
            
        self.blacklist_path = blacklist_path
        self.load_blacklisted_symbols(blacklist_path)
        self.load_approved_symbols(config_path)

    def load_blacklisted_symbols(self, blacklist_path: str):
        """Load blacklisted symbols from dynamic configuration file."""
        try:
            if os.path.exists(blacklist_path):
                with open(blacklist_path, 'r', encoding='utf-8') as f:
                    bl = json.load(f)
                normalized = set()
                for s in bl:
                    s_str = str(s).upper().strip()
                    normalized.add(s_str)
                    normalized.add(s_str.replace("/", "").replace("-", "").replace("_", ""))
                self.blacklisted_symbols = normalized
                self.logger.info(f"Loaded {len(bl)} blacklisted symbols from {blacklist_path}")
            else:
                self.blacklisted_symbols = set()
        except Exception as e:
            self.logger.warning(f"Could not load blacklisted symbols: {e}")
            self.blacklisted_symbols = set()
    
    def load_approved_symbols(self, config_path: str):
        """Load approved symbols from configuration file"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                approved_list = json.load(f)
            
            normalized_symbols = set()
            for symbol_str in approved_list:
                normalized = symbol_str.upper().replace("/", "")
                if normalized not in self.blacklisted_symbols:
                    normalized_symbols.add(normalized)
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
        """Check if a symbol is in the approved list and not blacklisted"""
        symbol_str = symbol.value.upper()
        clean = symbol_str.replace("/", "").replace("-", "").replace("_", "")
        if clean in self.blacklisted_symbols or symbol_str in self.blacklisted_symbols:
            self.logger.warning(f"🚫 SYMBOL BLACKLISTED: {symbol_str} is in blacklist configuration.")
            return False
        
        return (symbol_str in self.approved_symbols or 
                symbol_str.replace("/", "") in self.approved_symbols or
                symbol_str.replace("USDT", "/USDT") in self.approved_symbols)
    
    def get_approved_symbols(self) -> Set[str]:
        """Get the set of approved symbols"""
        return self.approved_symbols.copy()

    def get_blacklisted_symbols(self) -> Set[str]:
        """Get the set of blacklisted symbols"""
        return self.blacklisted_symbols.copy()


# Global instance for easy access
symbol_validator = SymbolValidator()