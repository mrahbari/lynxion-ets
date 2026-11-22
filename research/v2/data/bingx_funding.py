"""Fetch BingX historical funding (public) for given symbols into data/lake/bingx/funding/<SYM>.parquet."""
import json, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import pandas as pd
ROOT = Path(__file__).resolve().parents[3] / "data" / "lake" / "bingx" / "funding"
URL = "https://open-api.bingx.com/openApi/swap/v2/quote/fundingRate?symbol={s}&startTime={a}&endTime={b}&limit=1000"

def get(u):
    for i in range(6):
        try:
            return json.loads(urllib.request.urlopen(u, timeout=30).read())
        except Exception:
            time.sleep(2 * (i + 1))
    raise RuntimeError(u)

def fetch(sym, start_ms, end_ms):
    out = ROOT / f"{sym}.parquet"
    if out.exists():
        return sym, -1
    bx = sym[:-4] + "-USDT"
    rows, b = [], end_ms
    while b > start_ms:
        d = get(URL.format(s=bx, a=start_ms, b=b)).get("data") or []
        time.sleep(0.12)
        if not d:
            break
        rows += d
        t = min(int(x["fundingTime"]) for x in d)
        if t >= b or len(d) < 2:
            break
        b = t - 1
    if not rows:
        return sym, 0
    df = pd.DataFrame(rows)
    df = pd.DataFrame({"calc_time": df.fundingTime.astype("int64"), "funding_rate": df.fundingRate.astype(float),
                       "mark": pd.to_numeric(df.markPrice, errors="coerce")}).drop_duplicates("calc_time").sort_values("calc_time")
    ROOT.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out, index=False)
    return sym, len(df)

if __name__ == "__main__":
    syms = sys.argv[1].split(","); a = int(sys.argv[2]); b = int(sys.argv[3])
    with ThreadPoolExecutor(4) as ex:
        for s, n in ex.map(lambda s: fetch(s, a, b), syms):
            if n == 0: print("EMPTY", s, flush=True)
    print("done", len(syms))
