"""Research-layer coarse-OHLCV fetcher/cache (8h bars) for the funding-reversion
re-test. The production OHLCV downloader is 1m-only (millions of rows at multi-
year scale); for a multi-day-horizon funding study we only need bars at the
funding cadence (8h), so this fetches 8h klines directly via ccxt and caches them
under data/research_cache/8h/. Research data only — kept out of the production
data-sync path; production 1m ingestion is unchanged.

Run from repo root:
    .venv/bin/python3 research/edge_discovery/features/price_cache.py --scope sync --start 1095d
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
import time

CACHE = os.path.join("data", "research_cache", "8h")
COLS = ["timestamp", "open", "high", "low", "close", "volume"]


def _sym(symbol: str) -> str:
    if "/" in symbol:
        return symbol
    s = symbol.replace("-", "").upper()
    base = s[:-4] if s.endswith("USDT") else s
    return f"{base}/USDT:USDT"


def _store(symbol: str) -> str:
    s = symbol.replace("/", "").replace(":USDT", "").upper()
    return f"{s[:-4]}-USDT" if s.endswith("USDT") else s


def fetch_8h(ex, symbol: str, start_ms: int) -> int:
    sym, since, rows = _sym(symbol), start_ms, []
    now_ms = int(time.time() * 1000)
    while since < now_ms:
        for attempt in range(5):
            try:
                page = ex.fetch_ohlcv(sym, "8h", since=since, limit=1000)
                break
            except Exception as e:  # noqa: BLE001
                if any(k in str(e).lower() for k in ("not found", "invalid symbol")):
                    raise
                time.sleep(0.5 * 2 ** attempt)
        else:
            raise RuntimeError("retries exhausted")
        if not page:
            break
        for c in page:
            rows.append([int(c[0]) // 1000, c[1], c[2], c[3], c[4], c[5]])
        nxt = int(page[-1][0]) + 1
        if nxt <= since:
            break
        since = nxt
        time.sleep(0.2)
    os.makedirs(CACHE, exist_ok=True)
    seen, dedup = set(), []
    for r in sorted(rows, key=lambda x: x[0]):
        if r[0] not in seen and r[4] is not None:
            seen.add(r[0]); dedup.append(r)
    with open(os.path.join(CACHE, f"{_store(symbol)}.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(COLS); w.writerows(dedup)
    return len(dedup)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Cache 8h OHLCV for the funding re-test")
    ap.add_argument("--symbols", nargs="+")
    ap.add_argument("--scope", default="sync", choices=["sync", "approved"])
    ap.add_argument("--start", default="1095d")
    ap.add_argument("--exchange", default="binance")
    args = ap.parse_args(argv)

    if args.symbols:
        symbols = [s.upper() for s in args.symbols]
    else:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from universe_loader import load_universe
        symbols = load_universe(args.scope)
    start_ms = int(time.time() * 1000) - int(args.start[:-1]) * 86_400_000

    import ccxt
    ex = ccxt.binance({"enableRateLimit": True, "options": {"defaultType": "future"}})
    ex.load_markets()
    ok, errors = 0, []
    for s in symbols:
        try:
            n = fetch_8h(ex, s, start_ms)
            ok += 1
            print(f"  {s}: {n} 8h bars", flush=True)
        except Exception as e:  # noqa: BLE001
            errors.append((s, str(e)[:80]))
            print(f"  {s}: ERROR {str(e)[:80]}", flush=True)
    print(f"PRICE_CACHE_DONE ok={ok} errors={len(errors)} -> {CACHE}")


if __name__ == "__main__":
    main()
