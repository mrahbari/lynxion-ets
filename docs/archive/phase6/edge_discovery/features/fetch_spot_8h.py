"""Cache 8h SPOT OHLCV for the universe (for spot-perp basis research, class 1).
Mirrors price_cache.py but for the spot market (BASE/USDT). Free data.

Run from repo root:
    .venv/bin/python3 research/edge_discovery/features/fetch_spot_8h.py
"""
from __future__ import annotations

import csv
import os
import sys
import time

CACHE = os.path.join("data", "research_cache", "8h_spot")
COLS = ["timestamp", "open", "high", "low", "close", "volume"]


def _spot_sym(symbol):
    s = symbol.replace("-", "").upper()
    return f"{s[:-4]}/USDT" if s.endswith("USDT") else f"{s}/USDT"


def _store(symbol):
    s = symbol.replace("/", "").upper()
    return f"{s[:-4]}-USDT" if s.endswith("USDT") else s


def main():
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from universe_loader import load_universe
    symbols = load_universe("sync")
    start_ms = int(time.time() * 1000) - 1095 * 86_400_000

    import ccxt
    ex = ccxt.binance({"enableRateLimit": True, "options": {"defaultType": "spot"}})
    ex.load_markets()
    os.makedirs(CACHE, exist_ok=True)
    ok, err = 0, 0
    for symbol in symbols:
        sym, since, rows = _spot_sym(symbol), start_ms, []
        now = int(time.time() * 1000)
        try:
            while since < now:
                for a in range(5):
                    try:
                        page = ex.fetch_ohlcv(sym, "8h", since=since, limit=1000)
                        break
                    except Exception as e:  # noqa: BLE001
                        if any(k in str(e).lower() for k in ("not found", "invalid symbol", "does not have")):
                            raise
                        time.sleep(0.5 * 2 ** a)
                else:
                    raise RuntimeError("retries")
                if not page:
                    break
                rows += [[int(c[0]) // 1000, c[1], c[2], c[3], c[4], c[5]] for c in page]
                nxt = int(page[-1][0]) + 1
                if nxt <= since:
                    break
                since = nxt
                time.sleep(0.2)
            seen, dd = set(), []
            for r in sorted(rows, key=lambda x: x[0]):
                if r[0] not in seen and r[4] is not None:
                    seen.add(r[0]); dd.append(r)
            with open(os.path.join(CACHE, f"{_store(symbol)}.csv"), "w", newline="") as f:
                w = csv.writer(f); w.writerow(COLS); w.writerows(dd)
            ok += 1
            print(f"  {symbol}: {len(dd)} spot 8h bars", flush=True)
        except Exception as e:  # noqa: BLE001
            err += 1
            print(f"  {symbol}: ERROR {str(e)[:70]}", flush=True)
    print(f"SPOT_CACHE_DONE ok={ok} err={err} -> {CACHE}")


if __name__ == "__main__":
    main()
