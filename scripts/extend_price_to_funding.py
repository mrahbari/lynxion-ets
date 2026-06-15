"""Data prep only: extend BTC/ETH/SOL 1h price back to the funding-history start (~2023-06)
so the Phase-14 funding analysis can cover the full ~3-year funding window instead of ~1yr.

Paginated Binance public klines (1000/call) via the existing BinanceClient. Prepends the
older bars to the existing data/history/raw/1h/<SYM>-USDT.csv. No strategy code touched.
"""
import csv, os, sys, time
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
import logging; logging.disable(logging.WARNING)
from infrastructure.data.binance_client import BinanceClient

SYMS = ["BTC", "ETH", "SOL"]
INTERVAL = "1h"
STEP_MS = 3600 * 1000
START_MS = 1686614400 * 1000   # 2023-06-13, funding history start


def existing(sym):
    p = os.path.join(REPO, "data", "history", "raw", INTERVAL, f"{sym}-USDT.csv")
    rows = {}
    if os.path.exists(p):
        with open(p) as f:
            for r in csv.DictReader(f):
                rows[int(r["timestamp"])] = r
    return p, rows


def main():
    c = BinanceClient()
    for sym in SYMS:
        p, rows = existing(sym)
        cur_min = min(rows) if rows else None
        target_end = (cur_min * 1000) if cur_min else int(time.time() * 1000)
        cursor = START_MS
        fetched = 0
        while cursor < target_end:
            kl = c.get_klines(f"{sym}USDT", INTERVAL, cursor, target_end, limit=1000)
            if not kl:
                break
            for k in kl:
                ts = int(k[0]) // 1000  # open time (s)
                rows[ts] = {"timestamp": ts, "open": k[1], "high": k[2],
                            "low": k[3], "close": k[4], "volume": k[5]}
            fetched += len(kl)
            last_open = int(kl[-1][0])
            nxt = last_open + STEP_MS
            if nxt <= cursor:
                break
            cursor = nxt
            if len(kl) < 1000 and cursor >= target_end:
                break
            time.sleep(0.4)
        out = sorted(rows.values(), key=lambda r: int(r["timestamp"]))
        with open(p, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["timestamp", "open", "high", "low", "close", "volume"])
            for r in out:
                w.writerow([r["timestamp"], r["open"], r["high"], r["low"], r["close"], r["volume"]])
        print(f"{sym}: +{fetched} fetched, total={len(out)} rows -> {p}", file=sys.stderr)
    print("done", file=sys.stderr)


if __name__ == "__main__":
    main()
