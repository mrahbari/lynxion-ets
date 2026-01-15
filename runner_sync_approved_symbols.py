#!/usr/bin/env python3
"""
Symbol Updater Utility
Fetches the latest available symbols from BingX and updates the approved_symbols.json file
"""
import os
import json
import requests
import shutil
from datetime import datetime
from pathlib import Path


def fetch_available_symbols():
    """Fetch available symbols from exchange APIs with multiple fallbacks"""
    # Try BingX API first (public endpoint that might not require auth)
    try:
        print("Trying BingX API...")
        # Try the public exchange info endpoint
        exchange_info_url = "https://open-api.bingx.com/openApi/swap/v1/public/contracts"
        response = requests.get(exchange_info_url, timeout=30)

        if response.status_code == 200:
            data = response.json()
            if 'code' in data and data['code'] == 0 and 'data' in data:
                symbols = []
                for contract in data['data']:
                    if isinstance(contract, dict) and 'symbol' in contract:
                        symbols.append(contract['symbol'])
                if symbols:
                    return sorted(list(set(symbols)))

        # If the contracts endpoint doesn't work, try spot markets
        spot_info_url = "https://open-api.bingx.com/openApi/spot/v1/public/time"
        response = requests.get(spot_info_url, timeout=30)
        if response.status_code == 200:
            # If the time endpoint works, try the exchange info endpoint for spot
            exchange_info_url = "https://open-api.bingx.com/openApi/spot/v1/public/exchangeInfo"
            response = requests.get(exchange_info_url, timeout=30)
            if response.status_code == 200:
                data = response.json()
                if 'code' in data and data['code'] == 0 and 'data' in data and 'symbols' in data['data']:
                    symbols = []
                    for symbol_info in data['data']['symbols']:
                        if symbol_info.get('status') == 'TRADING':
                            symbol = symbol_info['symbol']
                            symbols.append(symbol)
                    if symbols:
                        return sorted(list(set(symbols)))
    except Exception as e:
        print(f"BingX API failed: {e}")

    # Fallback to Binance API (more reliable public endpoint)
    try:
        print("BingX API failed, trying Binance API...")
        binance_url = "https://api.binance.com/api/v3/exchangeInfo"
        response = requests.get(binance_url, timeout=30)
        response.raise_for_status()

        data = response.json()
        if 'symbols' in data:
            symbols = []
            for symbol_info in data['symbols']:
                if symbol_info.get('status') == 'TRADING':
                    symbol = symbol_info['symbol']
                    # Only include USDT pairs which are commonly available on multiple exchanges
                    if symbol.endswith('USDT'):
                        symbols.append(symbol)
            if symbols:
                print(f"Got {len(symbols)} symbols from Binance")
                return sorted(list(set(symbols)))
    except Exception as e:
        print(f"Binance API also failed: {e}")

    # If both APIs fail, return the current approved symbols as a fallback
    print("Both APIs failed, using current approved symbols as fallback")
    current_symbols_path = os.path.join(
        os.path.dirname(__file__),
        "application", "configs", "approved_symbols.json"
    )

    if os.path.exists(current_symbols_path):
        try:
            with open(current_symbols_path, 'r') as f:
                current_symbols = json.load(f)
            print(f"Using {len(current_symbols)} existing approved symbols as fallback")
            return current_symbols
        except Exception as e:
            print(f"Could not load existing symbols file: {e}")

    # If all else fails, return an empty list
    print("All methods failed, returning empty list")
    return []


def backup_current_symbols(file_path):
    """Create a backup of the current symbols file"""
    if os.path.exists(file_path):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{file_path}.backup_{timestamp}"
        shutil.copy2(file_path, backup_path)
        print(f"Backed up current symbols to: {backup_path}")
        return backup_path
    return None


def update_approved_symbols_file(symbols, file_path):
    """Update the approved symbols file with new symbols"""
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # Backup current file
        backup_path = backup_current_symbols(file_path)
        
        # Read existing symbols if file exists
        existing_symbols = set()
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                existing_data = json.load(f)
                existing_symbols = set(existing_data)
        
        # Convert new symbols to set
        new_symbols_set = set(symbols)
        
        # Find added and removed symbols
        added_symbols = new_symbols_set - existing_symbols
        removed_symbols = existing_symbols - new_symbols_set
        
        print(f"\nSymbol Update Summary:")
        print(f"- Previously approved: {len(existing_symbols)} symbols")
        print(f"- Newly fetched: {len(new_symbols_set)} symbols")
        print(f"- Added: {len(added_symbols)} symbols")
        print(f"- Removed: {len(removed_symbols)} symbols")
        
        if added_symbols:
            print(f"\nAdded symbols (first 10): {list(added_symbols)[:10]}")
        if removed_symbols:
            print(f"\nRemoved symbols (first 10): {list(removed_symbols)[:10]}")
        
        # Save updated symbols
        with open(file_path, 'w') as f:
            json.dump(sorted(list(new_symbols_set)), f, indent=2)
        
        print(f"\n✅ Updated approved symbols file: {file_path}")
        print(f"   Total symbols in file: {len(new_symbols_set)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error updating symbols file: {e}")
        # Restore backup if update failed
        if 'backup_path' in locals() and backup_path and os.path.exists(backup_path):
            print(f"Restoring from backup...")
            shutil.copy2(backup_path, file_path)
            print(f"Restored from backup: {backup_path}")
        return False


def main():
    """Main function to run the symbol updater"""
    print("🔍 Fetching latest symbols from exchange APIs...")

    # Fetch symbols from exchange APIs with fallbacks
    symbols = fetch_available_symbols()

    if not symbols:
        print("❌ Could not fetch symbols from any source. Exiting.")
        return 1

    print(f"✅ Fetched {len(symbols)} symbols from exchange")

    # Define the path to the approved symbols file
    symbols_file_path = os.path.join(
        os.path.dirname(__file__),
        "application", "configs", "approved_symbols.json"
    )

    # Update the symbols file
    success = update_approved_symbols_file(symbols, symbols_file_path)

    if success:
        print(f"\n🎉 Symbol update completed successfully!")
        print(f"📄 Updated file: {symbols_file_path}")
    else:
        print(f"\n💥 Symbol update failed!")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())