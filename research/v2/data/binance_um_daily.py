"""Binance USD-M DAILY public archives -> compact research parquet (free data, operator decision 2026-11-25).

Datasets (data.binance.vision publishes these only as daily files):
  * metrics   (from 2020-09): 5-min open interest, top-trader and all-account long/short ratios, taker buy/sell
                volume ratio -> HOURLY: last value per hour for levels/ratios, mean for the taker ratio.
                data/lake/binance_um/metrics_1h/<SYM>.parquet
  * bookDepth (from 2023-01): ~30 s snapshots of order-book notional within +/-1..5 % of price
                -> 5-MINUTE: last snapshot per bucket, notional per level (n_m5..n_m1, n_p1..n_p5).
                data/lake/binance_um/bookdepth_5m/<SYM>.parquet
Timestamps: column `t` = END of the bucket in ms UTC (the time the value is known). Never join on the bucket start.
Incremental and resumable: <SYM>.days.json lists the daily files already folded in. Raw zips are not kept.
Checksums are not fetched (would double ~10^5 requests); each zip is opened and parsed, a broken one fails the day
and is retried on the next run.
Symbols: --symbols, or --top N (largest median daily quote volume 2023-2026 from the 1h lake, non-perpetual and
stablecoins excluded), or --liquid (every symbol with >= 30 days of 30-day median volume >= $10M in the lake).
Usage: cd research/v2 && python data/binance_um_daily.py --dataset metrics --liquid
       cd research/v2 && python data/binance_um_daily.py --dataset bookDepth --top 40
"""
from __future__ import annotations

import argparse
import io
import json
import sys
import zipfile
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from data.binance_um_lake import DL, ROOT, _get, s3_list  # noqa: E402

H, M5 = 3_600_000, 300_000
INNER = 16
OUT = {"metrics": ROOT / "metrics_1h", "bookDepth": ROOT / "bookdepth_5m"}
EXCLUDE = {"USDCUSDT", "BUSDUSDT", "TUSDUSDT", "FDUSDUSDT", "USDPUSDT", "DAIUSDT", "EURUSDT", "XAUTUSDT", "PAXGUSDT"}


def _ms(series: pd.Series) -> pd.Series:
    return (pd.to_datetime(series, utc=True).astype("int64") // 10**6).astype("int64")


def parse_metrics(raw: bytes) -> pd.DataFrame:
    d = pd.read_csv(io.BytesIO(raw))
    d["ts"] = _ms(d["create_time"])
    d["t"] = (d.ts // H + 1) * H                                     # hour END
    g = d.groupby("t")
    out = pd.DataFrame({
        "oi": g["sum_open_interest"].last(), "oi_value": g["sum_open_interest_value"].last(),
        "top_ls_accounts": g["count_toptrader_long_short_ratio"].last(),
        "top_ls_positions": g["sum_toptrader_long_short_ratio"].last(),
        "ls_accounts": g["count_long_short_ratio"].last(),
        "taker_ls_vol": g["sum_taker_long_short_vol_ratio"].mean()})
    return out.reset_index().astype({c: "float32" for c in out.columns})


def parse_bookdepth(raw: bytes) -> pd.DataFrame:
    d = pd.read_csv(io.BytesIO(raw))
    d["ts"] = _ms(d["timestamp"])
    w = d.pivot_table(index="ts", columns="percentage", values="notional", aggfunc="last")
    w.columns = [f"n_{'m' if float(c) < 0 else 'p'}{abs(float(c)):g}".replace(".", "_") for c in w.columns]
    w = w.sort_index()
    w["t"] = (w.index // M5 + 1) * M5                                # 5-min bucket END
    out = w.groupby("t").last().reset_index()
    return out.astype({c: "float32" for c in out.columns if c != "t"})


PARSE = {"metrics": parse_metrics, "bookDepth": parse_bookdepth}


def fetch(sym: str, dataset: str) -> tuple[str, int, int]:
    out_dir = OUT[dataset]
    out_dir.mkdir(parents=True, exist_ok=True)
    pq, meta = out_dir / f"{sym}.parquet", out_dir / f"{sym}.days.json"
    keys = sorted(k for k in s3_list(f"data/futures/um/daily/{dataset}/{sym}/") if k.endswith(".zip"))
    if dataset == "bookDepth":
        keys = [k for k in keys if k[-14:-4] >= "2023-01-01"]
    done = set(json.loads(meta.read_text())) if meta.exists() else set()
    todo = [k for k in keys if k not in done]
    if not todo:
        return sym, 0, 0
    frames, ok, bad = [], [], 0

    def one(k):
        with zipfile.ZipFile(io.BytesIO(_get(DL + k))) as z:
            return k, PARSE[dataset](z.read(z.namelist()[0]))
    with ThreadPoolExecutor(INNER) as ex:          # files of one symbol in parallel (request latency bound)
        futs = [ex.submit(one, k) for k in todo]
        for f in as_completed(futs):
            try:
                k, df = f.result()
                frames.append(df); ok.append(k)
            except Exception:  # noqa: BLE001 - retried next run
                bad += 1
    if frames:
        new = pd.concat(frames, ignore_index=True)
        if pq.exists():
            new = pd.concat([pd.read_parquet(pq), new], ignore_index=True)
        new.drop_duplicates("t", keep="last").sort_values("t").to_parquet(pq, index=False)
        meta.write_text(json.dumps(sorted(done | set(ok))))
    return sym, len(ok), bad


def pick_symbols(a) -> list[str]:
    if a.symbols:
        return a.symbols.split(",")
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from lib import panel as pn
    p = pn.load_daily(start="2020-01-01")
    nps = set(json.load(open(pn.LAKE / "non_perpetual_symbols.json")))
    qv = p["quote_volume"][[c for c in p["quote_volume"].columns if c.endswith("USDT") and c not in nps
                            and c not in EXCLUDE]]
    if a.top:
        return list(qv.loc["2023-01-01":].median().sort_values(ascending=False).index[:a.top])
    adv = qv.rolling(30, min_periods=15).median()
    return sorted(c for c in adv.columns if (adv[c] >= 10e6).sum() >= 30)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", choices=sorted(OUT), required=True)
    ap.add_argument("--symbols", default="")
    ap.add_argument("--top", type=int, default=0)
    ap.add_argument("--liquid", action="store_true")
    ap.add_argument("--workers", type=int, default=12)
    a = ap.parse_args()
    syms = pick_symbols(a)
    print(f"{a.dataset}: {len(syms)} symbols", flush=True)
    tot = bad = n = 0
    with ProcessPoolExecutor(a.workers) as ex:      # processes: CSV parsing is CPU-bound (GIL)
        futs = {ex.submit(fetch, s, a.dataset): s for s in syms}
        for f in as_completed(futs):
            n += 1
            try:
                _, k, b = f.result()
                tot += k; bad += b
            except Exception as e:  # noqa: BLE001
                bad += 1
                print(f"FAIL {futs[f]}: {e}", flush=True)
            if n % 10 == 0:
                print(f"progress {n}/{len(syms)} files={tot} bad={bad}", flush=True)
    print(f"DONE symbols={n} files={tot} bad={bad}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
