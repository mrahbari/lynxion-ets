"""Phase 17 — microstructure data-layer fetch (data prep only; no strategy code).

Binance FUTURES (perp) klines carry order-flow fields that plain OHLCV discards:
  field[8] = number of trades, field[9] = taker-buy base volume (aggressor buy side),
  field[10] = taker-buy quote volume. From these we derive CVD / aggressor imbalance /
  trade-structure liquidity proxies — genuinely non-OHLCV, historical, free, funding-aligned.

Stored at data/history/micro/<tf>/<SYM>-USDT.csv with columns:
  timestamp,open,high,low,close,volume,num_trades,taker_buy_base,taker_buy_quote

Usage: python scripts/fetch_microstructure.py <interval> <start_YYYY-MM-DD> SYM1 SYM2 ...
"""
import csv, os, sys, time, datetime, random
import requests
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAPI = "https://fapi.binance.com/fapi/v1/klines"
INTERVAL_MS = {"1m": 60_000, "5m": 300_000, "15m": 900_000, "30m": 1_800_000, "1h": 3_600_000}


def get(symbol, interval, start_ms, end_ms, limit=1500):
    for attempt in range(5):
        try:
            r = requests.get(FAPI, params={"symbol": symbol, "interval": interval,
                             "startTime": start_ms, "endTime": end_ms, "limit": limit}, timeout=20)
            if r.status_code == 200:
                return r.json()
            if r.status_code in (429, 418, 502, 503, 504):
                time.sleep(1.5 * (2 ** attempt) + random.uniform(0, 1)); continue
            sys.stderr.write(f"  http {r.status_code} {r.text[:120]}\n"); return []
        except Exception as e:
            time.sleep(1.5 * (2 ** attempt) + random.uniform(0, 1))
    return []


def main():
    interval = sys.argv[1]
    start = datetime.datetime.strptime(sys.argv[2], "%Y-%m-%d").replace(tzinfo=datetime.timezone.utc)
    syms = sys.argv[3:]
    step = INTERVAL_MS[interval]
    start_ms = int(start.timestamp() * 1000)
    end_ms = int(time.time() * 1000)
    for sym in syms:
        p = os.path.join(REPO, "data", "history", "micro", interval, f"{sym}-USDT.csv")
        os.makedirs(os.path.dirname(p), exist_ok=True)
        rows = {}
        cursor = start_ms; fetched = 0
        while cursor < end_ms:
            kl = get(f"{sym}USDT", interval, cursor, end_ms)
            if not kl:
                break
            for k in kl:
                ts = int(k[0]) // 1000
                rows[ts] = [ts, k[1], k[2], k[3], k[4], k[5], k[8], k[9], k[10]]
            fetched += len(kl)
            nxt = int(kl[-1][0]) + step
            if nxt <= cursor:
                break
            cursor = nxt
            if len(kl) < 1500:
                break
            time.sleep(0.25)
        out = sorted(rows.values(), key=lambda r: r[0])
        with open(p, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["timestamp", "open", "high", "low", "close", "volume",
                        "num_trades", "taker_buy_base", "taker_buy_quote"])
            w.writerows(out)
        span = (f"{datetime.datetime.utcfromtimestamp(out[0][0]).date()}->"
                f"{datetime.datetime.utcfromtimestamp(out[-1][0]).date()}") if out else "-"
        sys.stderr.write(f"{sym} {interval}: +{fetched} total={len(out)} {span}\n")
    sys.stderr.write("done\n")


if __name__ == "__main__":
    main()
