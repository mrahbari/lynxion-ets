"""Phase 18 — cross-venue 1m fetch (data prep only; no strategy code).

Pulls 1-minute klines for the same symbols from multiple venues onto a common UTC minute grid,
to test cross-exchange and lead-lag microstructure. Venues use binance-style kline payloads
(MEXC spot v3 mirrors Binance): row = [openTimeMs, O,H,L,C,V, ...].

Stored at data/history/xvenue/<venue>/<SYM>-USDT.csv: timestamp,close,volume
Usage: python scripts/fetch_xvenue.py <interval> <days> SYM1 SYM2 ...
"""
import csv, os, sys, time, random
import requests
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INTERVAL_MS = {"1m": 60_000, "5m": 300_000}

VENUES = {
    "binance_fut":  ("https://fapi.binance.com/fapi/v1/klines", 1500),
    "binance_spot": ("https://api.binance.com/api/v3/klines", 1000),
    "mexc_spot":    ("https://api.mexc.com/api/v3/klines", 500),  # MEXC caps 1m klines at 500/call
}


def get(url, symbol, interval, start_ms, end_ms, limit):
    for attempt in range(5):
        try:
            r = requests.get(url, params={"symbol": symbol, "interval": interval,
                             "startTime": start_ms, "endTime": end_ms, "limit": limit}, timeout=20)
            if r.status_code == 200:
                j = r.json()
                return j if isinstance(j, list) else []
            if r.status_code in (429, 418, 500, 502, 503, 504):
                time.sleep(1.2 * (2 ** attempt) + random.uniform(0, 1)); continue
            sys.stderr.write(f"  {symbol} http {r.status_code} {r.text[:100]}\n"); return []
        except Exception:
            time.sleep(1.2 * (2 ** attempt) + random.uniform(0, 1))
    return []


def main():
    interval = sys.argv[1]; days = int(sys.argv[2]); syms = sys.argv[3:]
    step = INTERVAL_MS[interval]
    end_ms = int(time.time() * 1000)
    start_ms = end_ms - days * 86400 * 1000
    for venue, (url, lim) in VENUES.items():
        for sym in syms:
            p = os.path.join(REPO, "data", "history", "xvenue", venue, f"{sym}-USDT.csv")
            os.makedirs(os.path.dirname(p), exist_ok=True)
            # skip already-complete files (resume after an interrupted run)
            if os.path.exists(p):
                with open(p) as _f:
                    nlines = sum(1 for _ in _f) - 1
                if nlines >= int(days * 1440 * 0.95):
                    sys.stderr.write(f"{venue}/{sym}: skip (have {nlines})\n"); continue
            rows = {}; cursor = start_ms; fetched = 0
            while cursor < end_ms:
                kl = get(url, f"{sym}USDT", interval, cursor, end_ms, lim)
                if not kl:
                    break
                for k in kl:
                    ts = int(k[0]) // 1000
                    rows[ts] = [ts, k[4], k[5]]
                fetched += len(kl)
                nxt = int(kl[-1][0]) + step
                if nxt <= cursor:
                    break
                cursor = nxt
                if len(kl) < lim:
                    break
                time.sleep(0.2)
            out = sorted(rows.values(), key=lambda r: r[0])
            with open(p, "w", newline="") as f:
                w = csv.writer(f); w.writerow(["timestamp", "close", "volume"]); w.writerows(out)
            sys.stderr.write(f"{venue}/{sym}: {len(out)} rows\n")
    sys.stderr.write("done\n")


if __name__ == "__main__":
    main()
