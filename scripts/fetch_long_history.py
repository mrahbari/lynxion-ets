"""Data prep only (Phase 15): acquire the LONGEST available Binance history for the target
symbols at a given timeframe, merging into data/history/raw/<tf>/<SYM>-USDT.csv.

Paginated Binance public klines (1000/call, the API returns from listing date if start is
earlier). No strategy code touched. Usage:
  python scripts/fetch_long_history.py <interval> <start_YYYY-MM-DD> SYM1 SYM2 ...
"""
import csv, os, sys, time, datetime
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
import logging; logging.disable(logging.WARNING)
from infrastructure.data.binance_client import BinanceClient

INTERVAL_MS = {"1m": 60_000, "5m": 300_000, "15m": 900_000, "30m": 1_800_000, "1h": 3_600_000}


def main():
    interval = sys.argv[1]
    start = datetime.datetime.strptime(sys.argv[2], "%Y-%m-%d").replace(tzinfo=datetime.timezone.utc)
    syms = sys.argv[3:]
    step = INTERVAL_MS[interval]
    start_ms = int(start.timestamp() * 1000)
    end_ms = int(time.time() * 1000)
    c = BinanceClient()
    for sym in syms:
        p = os.path.join(REPO, "data", "history", "raw", interval, f"{sym}-USDT.csv")
        rows = {}
        if os.path.exists(p):
            with open(p) as f:
                for r in csv.DictReader(f):
                    rows[int(r["timestamp"])] = r
        cursor = start_ms
        fetched = 0
        while cursor < end_ms:
            kl = c.get_klines(f"{sym}USDT", interval, cursor, end_ms, limit=1000)
            if not kl:
                break
            for k in kl:
                ts = int(k[0]) // 1000
                rows[ts] = {"timestamp": ts, "open": k[1], "high": k[2],
                            "low": k[3], "close": k[4], "volume": k[5]}
            fetched += len(kl)
            nxt = int(kl[-1][0]) + step
            if nxt <= cursor:
                break
            cursor = nxt
            if len(kl) < 1000:
                break
            time.sleep(0.3)
        out = sorted(rows.values(), key=lambda r: int(r["timestamp"]))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["timestamp", "open", "high", "low", "close", "volume"])
            for r in out:
                w.writerow([r["timestamp"], r["open"], r["high"], r["low"], r["close"], r["volume"]])
        import datetime as _d
        span = "-"
        if out:
            span = f"{_d.datetime.utcfromtimestamp(int(out[0]['timestamp'])).date()}->{_d.datetime.utcfromtimestamp(int(out[-1]['timestamp'])).date()}"
        print(f"{sym} {interval}: +{fetched} fetched, total={len(out)} {span}", file=sys.stderr)
    print("done", file=sys.stderr)


if __name__ == "__main__":
    main()
