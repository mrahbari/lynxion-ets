#!/usr/bin/env python3
"""
BingX Perpetual Futures Symbol Updater
Fetches BingX perpetual futures symbols (USDT-margined only)
and updates approved_symbols.json safely.
Note: COIN-margined futures endpoint not available in current BingX API.
"""

import os
import json
import requests
import shutil
from datetime import datetime


BINGX_SWAP_ENDPOINTS = [
    # USDT-margined perpetuals (v2 endpoint) - WORKING
    "https://open-api.bingx.com/openApi/swap/v2/quote/contracts",

    # NOTE: COIN-margined (inverse) perpetuals endpoint appears to not exist in BingX API
    # Tried: https://open-api.bingx.com/openApi/swap/v2/quote/coin/contracts (not exist)
    # Tried: https://open-api.bingx.com/openApi/swap/v1/public/coin/contracts (not exist)
    # Current BingX API only appears to provide USDT-margined futures via the v2 endpoint
]


def fetch_available_symbols():
    """
    Fetch all BingX perpetual futures symbols (USDT-margined)
    NOTE: COIN-margined futures endpoint not available in current BingX API
    """
    symbols = set()

    for url in BINGX_SWAP_ENDPOINTS:
        try:
            print(f"🔍 Fetching: {url}")
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            payload = response.json()

            if payload.get("code") != 0:
                print(f"⚠️ Non-zero response code from {url}: {payload.get('msg', 'Unknown error')}")
                # Skip this endpoint if it's not available
                if "not exist" in payload.get('msg', ''):
                    print(f"   📝 Endpoint not available - skipping")
                    continue
                continue

            for contract in payload.get("data", []):
                if not isinstance(contract, dict):
                    continue

                # status == 1 means tradable (from working code in task70)
                if contract.get("status") == 1:
                    raw_symbol = contract.get("symbol")
                    if raw_symbol:
                        # Convert BTC-USDT -> BTCUSDT
                        symbol = raw_symbol.replace('-', '')
                        symbols.add(symbol)

            print(f"✅ Collected so far: {len(symbols)} symbols")

        except Exception as e:
            print(f"❌ Failed fetching {url}: {e}")
            # Continue to next endpoint if current one fails

    return sorted(symbols)


def backup_current_symbols(file_path):
    if os.path.exists(file_path):
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        # Create backup in the archive directory
        filename = os.path.basename(file_path)
        archive_dir = os.path.join(os.path.dirname(__file__), "data", "approved-symbols")
        os.makedirs(archive_dir, exist_ok=True)
        backup_path = os.path.join(archive_dir, f"{filename}.backup_{ts}")
        shutil.copy2(file_path, backup_path)
        print(f"📦 Backup created: {backup_path}")
        return backup_path
    return None


def update_approved_symbols_file(symbols, file_path):
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        backup_path = backup_current_symbols(file_path)

        existing_symbols = set()
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                existing_symbols = set(json.load(f))

        new_symbols = set(symbols)

        added = new_symbols - existing_symbols
        removed = existing_symbols - new_symbols

        print("\n📊 Symbol Update Summary")
        print(f"Previously approved : {len(existing_symbols)}")
        print(f"Newly fetched       : {len(new_symbols)}")
        print(f"Added               : {len(added)}")
        print(f"Removed             : {len(removed)}")

        if added:
            print(f"➕ Added (sample): {list(added)[:10]}")
        if removed:
            print(f"➖ Removed (sample): {list(removed)[:10]}")

        with open(file_path, "w") as f:
            json.dump(sorted(new_symbols), f, indent=2)

        print(f"\n✅ Main config updated: {file_path}")
        print(f"📄 Total symbols saved: {len(new_symbols)}")

        # Also save to archive location
        archive_file_path = os.path.join(
            os.path.dirname(__file__),
            "data", "approved-symbols", "approved_symbols.json"
        )
        os.makedirs(os.path.dirname(archive_file_path), exist_ok=True)

        with open(archive_file_path, "w") as f:
            json.dump(sorted(new_symbols), f, indent=2)

        print(f"📦 Archive updated: {archive_file_path}")

        return True

    except Exception as e:
        print(f"❌ Update failed: {e}")
        if backup_path and os.path.exists(backup_path):
            shutil.copy2(backup_path, file_path)
            print("♻️ Restored from backup")
        return False


def main():
    """Backward-compatible entry point.

    E2.T3: process I/O now lives in :mod:`interface.cli.sync_approved_symbols`.
    This job has no domain ports to inject, so there is no container wiring;
    the shim simply delegates. The fetch/update helpers above are consumed by
    the CLI.
    """
    from interface.cli.sync_approved_symbols import main as cli_main
    return cli_main()


if __name__ == "__main__":
    exit(main())