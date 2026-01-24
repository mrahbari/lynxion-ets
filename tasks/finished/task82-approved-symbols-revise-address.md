First, Always you must cover the rules and requirements that written in ./tasks/task0-force-to-cover.md

Take a look at ./runner_sync_approved_symbols.py and fix the issues to resolve the missed symbols of bingx. 
I recommend you to review both below and implemented code and fix the issues. after that run the script and get the result.  
Also, the archive config must be moved to ./data/approved-symbols . 

Why you only get 444 symbols:

Because you are only querying USDT-margined perpetuals, which is roughly half of BingX’s futures market.

Nothing is “wrong” with Python — your market coverage is incomplete.
This fixes the root cause of your missing symbols.

---

## ✅ What this script does correctly

✔ Fetches **USDT-margined perpetuals**
✔ Fetches **COIN-margined (inverse) perpetuals**
✔ Filters **PERPETUAL only**
✔ No spot pollution
✔ No Binance fallback corruption
✔ Safe backup + atomic update
✔ You should now see **~800–1000+ symbols**, depending on BingX listings

---

## ✅ FINAL SCRIPT (drop-in replacement)

```python
#!/usr/bin/env python3
"""
BingX Perpetual Futures Symbol Updater
Fetches ALL BingX perpetual futures symbols (USDT + COIN margined)
and updates approved_symbols.json safely.
"""

import os
import json
import requests
import shutil
from datetime import datetime


BINGX_SWAP_ENDPOINTS = [
    # USDT-margined perpetuals
    "https://open-api.bingx.com/openApi/swap/v1/public/contracts",

    # COIN-margined (inverse) perpetuals
    "https://open-api.bingx.com/openApi/swap/v1/public/coin/contracts",
]


def fetch_available_symbols():
    """
    Fetch all BingX perpetual futures symbols (USDT + COIN margined)
    """
    symbols = set()

    for url in BINGX_SWAP_ENDPOINTS:
        try:
            print(f"🔍 Fetching: {url}")
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            payload = response.json()

            if payload.get("code") != 0:
                print(f"⚠️ Non-zero response code from {url}")
                continue

            for contract in payload.get("data", []):
                if not isinstance(contract, dict):
                    continue

                # Defensive filtering
                if contract.get("contractType") == "PERPETUAL":
                    symbol = contract.get("symbol")
                    if symbol:
                        symbols.add(symbol)

            print(f"✅ Collected so far: {len(symbols)} symbols")

        except Exception as e:
            print(f"❌ Failed fetching {url}: {e}")

    return sorted(symbols)


def backup_current_symbols(file_path):
    if os.path.exists(file_path):
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{file_path}.backup_{ts}"
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

        print(f"\n✅ approved_symbols.json updated")
        print(f"📄 Total symbols saved: {len(new_symbols)}")
        return True

    except Exception as e:
        print(f"❌ Update failed: {e}")
        if backup_path and os.path.exists(backup_path):
            shutil.copy2(backup_path, file_path)
            print("♻️ Restored from backup")
        return False


def main():
    print("🚀 Fetching BingX perpetual futures symbols...")

    symbols = fetch_available_symbols()

    if not symbols:
        print("❌ No symbols fetched. Exiting.")
        return 1

    print(f"\n🎯 Total perpetual symbols fetched: {len(symbols)}")

    symbols_file_path = os.path.join(
        os.path.dirname(__file__),
        "application",
        "configs",
        "approved_symbols.json"
    )

    success = update_approved_symbols_file(symbols, symbols_file_path)
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())
```

---

## 📈 What you should expect now

| Market Type | Approx Count   |
| ----------- | -------------- |
| USDT Perps  | ~400–500       |
| COIN Perps  | ~300–500       |
| **TOTAL**   | **~800–1000+** |

(Exact number depends on BingX delistings / new launches.)


My question is , imagine btc hostory is for from 2023-01-01 by now, and if i run the following scrits again, wheter "python runner_historical_data_sync.py now" what will happen for older btc histoiries?  

./runner_historical_data_sync.py, ./runner_history_download.py, ./runner_multitimeframe_update.py,.runner_resync.py


