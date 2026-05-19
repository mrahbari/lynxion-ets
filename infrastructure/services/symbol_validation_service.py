"""
Symbol Validation and Filtering Module for Market Opportunity Watcher
Handles validation and filtering of symbols before processing
"""
import re
from typing import List
from domain.value_objects import Symbol
from shared.logger import EnhancedLogger
from utils.symbol_validator import symbol_validator
from application.configs.configs import Configs


class SymbolValidationService:
    """Service class for validating and filtering symbols before processing."""
    
    def __init__(self, logger: EnhancedLogger = None):
        self.logger = logger or EnhancedLogger("SymbolValidationService")
    
    def filter_stablecoin_pairs(self, symbols):
        """Filter out stablecoin-stablecoin pairs from the symbol list."""
        # Check if filtering is enabled
        filter_stablecoin_pairs = Configs.data.filter_out_stablecoin_pairs if Configs.data and hasattr(Configs.data, 'filter_out_stablecoin_pairs') else True

        if not filter_stablecoin_pairs:
            return symbols

        # Get allowed stablecoins from configs
        allowed_stablecoins_raw = Configs.data.allowed_stablecoins if Configs.data and Configs.data.allowed_stablecoins else 'USDT,BUSD,USDC,DAI,PAX,TUSD,USDD,FDUSD'

        # Handle both string and list formats
        if isinstance(allowed_stablecoins_raw, list):
            allowed_stablecoins = [s.strip().upper() for s in allowed_stablecoins_raw if s.strip()]
        else:
            allowed_stablecoins = [s.strip().upper() for s in allowed_stablecoins_raw.split(',')]

        filtered_symbols = []
        for symbol in symbols:
            symbol_str = symbol.value if hasattr(symbol, 'value') else str(symbol)
            symbol_upper = symbol_str.upper()

            # Parse symbol to extract base and quote currencies
            base_currency = ""
            quote_currency = ""

            # Try to identify quote currency by looking for known stablecoins at the end
            # Sort stablecoins by length descending to match longer ones first (to avoid partial matches)
            sorted_stables = sorted(allowed_stablecoins, key=len, reverse=True)
            for stable in sorted_stables:
                stable_upper = stable.upper()
                if symbol_upper.endswith(stable_upper):
                    base_part = symbol_upper[:-len(stable_upper)]
                    if base_part:  # Make sure there's a base currency part
                        base_currency = symbol_str[:-len(stable)]  # Keep original case for logging
                        quote_currency = stable
                        break

            # If we couldn't identify by ending, try to split by common separators
            if not base_currency and not quote_currency:
                if '-' in symbol_str:
                    parts = symbol_str.split('-')
                    if len(parts) == 2:
                        base_currency, quote_currency = parts[0], parts[1]
                elif '/' in symbol_str:
                    parts = symbol_str.split('/')
                    if len(parts) == 2:
                        base_currency, quote_currency = parts[0], parts[1]

            # Check if both base and quote are stablecoins (stablecoin-stablecoin pair)
            if base_currency and quote_currency:
                base_upper = base_currency.upper()
                quote_upper = quote_currency.upper()

                # If both are stablecoins and different, it's a stablecoin pair to filter out
                if base_upper in allowed_stablecoins and quote_upper in allowed_stablecoins and base_upper != quote_upper:
                    self.logger.info(f"🪙 STABLECOIN FILTER: Skipping {symbol_str} (base: {base_currency}, quote: {quote_currency})")
                    continue  # Skip this symbol

                # Also check for same currency pair (e.g., USDCUSDC)
                if base_upper == quote_upper:
                    self.logger.info(f"🪙 STABLECOIN FILTER: Skipping {symbol_str} (same currency)")
                    continue  # Skip this symbol

            # Check using regex pattern if provided - improved to catch more stablecoin pairs
            excluded_pattern = Configs.data.excluded_symbols_pattern if Configs.data and Configs.data.excluded_symbols_pattern else r'(?:USDT|USDC|BUSD|DAI|PAX|TUSD|USDD|FDUSD)(?:USDT|USDC|BUSD|DAI|PAX|TUSD|USDD|FDUSD)|BTC/BTC|ETH/ETH'
            if re.search(excluded_pattern, symbol_upper):
                self.logger.info(f"🚫 PATTERN FILTER: Skipping {symbol_str} (matches exclusion pattern)")
                continue  # Skip this symbol

            # If we reach here, the symbol passed all filters
            filtered_symbols.append(symbol)

        # Log the filtering results
        original_count = len(symbols)
        filtered_count = len(filtered_symbols)
        if original_count != filtered_count:
            self.logger.info(f"📊 SYMBOL FILTERING: {original_count} -> {filtered_count} symbols after stablecoin filtering")

        return filtered_symbols

    def validate_symbol_data_availability(self, symbols):
        """Validate that symbols have data available on exchanges before processing."""
        validated_symbols = []

        # Check if data validation is enabled
        validate_data_availability = Configs.data.validate_symbol_data_availability if Configs.data and hasattr(Configs.data, 'validate_symbol_data_availability') else True

        if not validate_data_availability:
            # Still apply approved symbol validation even if data availability validation is disabled
            for symbol in symbols:
                symbol_str = symbol.value if hasattr(symbol, 'value') else str(symbol)
                if symbol_validator.is_symbol_approved(symbol):
                    validated_symbols.append(symbol)
                else:
                    self.logger.info(f"❌ SYMBOL REJECTED: {symbol_str} is not in approved symbols list. Skipping...")
            return validated_symbols

        self.logger.info(f"🔍 Validating data availability and approved status for {len(symbols)} symbols...")

        for symbol in symbols:
            symbol_str = symbol.value if hasattr(symbol, 'value') else str(symbol)

            # First check if symbol is in approved list
            if not symbol_validator.is_symbol_approved(symbol):
                self.logger.info(f"❌ SYMBOL REJECTED: {symbol_str} is not in approved symbols list. Skipping...")
                continue

            try:
                # Check if the symbol is available in the market data repository
                if hasattr(self, 'market_data_repo') and self.market_data_repo and hasattr(self.market_data_repo, 'is_symbol_available'):
                    is_available = self.market_data_repo.is_symbol_available(symbol_str)

                    if is_available:
                        validated_symbols.append(symbol)
                        self.logger.debug(f"✅ Data available for {symbol_str}")
                    else:
                        self.logger.warning(f"⚠️ Data not available for {symbol_str}, skipping...")
                else:
                    # If no market data repo is available, try to validate using broker service
                    if hasattr(self, 'broker_service') and self.broker_service:
                        available_symbols = self.broker_service.get_available_symbols()

                        if symbol_str in available_symbols:
                            validated_symbols.append(symbol)
                            self.logger.debug(f"✅ Symbol available on broker: {symbol_str}")
                        else:
                            self.logger.warning(f"⚠️ Symbol not available on broker: {symbol_str}, skipping...")
                    else:
                        # If no validation method is available, assume symbol is valid
                        validated_symbols.append(symbol)
                        self.logger.warning(f"⚠️ No validation method available for {symbol_str}, assuming valid...")

            except Exception as e:
                self.logger.warning(f"⚠️ Error validating data for {symbol_str}: {e}, skipping...")
                continue

        original_count = len(symbols)
        validated_count = len(validated_symbols)

        if original_count != validated_count:
            self.logger.info(f"📊 DATA AVAILABILITY & APPROVAL VALIDATION: {original_count} -> {validated_count} symbols after validation")

        return validated_symbols