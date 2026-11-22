"""Binance USD-M full-universe data lake builder (Lynxion research v2).

Downloads public monthly archives from data.binance.vision for EVERY USDT-M
perpetual ever listed (including delisted symbols -> no survivorship bias):

  * klines 1h               -> data/lake/binance_um/klines_1h/<SYM>.parquet
  * fundingRate             -> data/lake/binance_um/funding/<SYM>.parquet
  * premiumIndexKlines 1h   -> data/lake/binance_um/premium_1h/<SYM>.parquet

Every downloaded zip is verified against its published .CHECKSUM (SHA-256).
A manifest (one JSON line per file) is written to data/lake/binance_um/manifest.jsonl.
Re-running is idempotent: symbols whose parquet already covers all listed months are skipped.

Timestamps: kline `open_time` is ms UTC of bar OPEN. A bar is only known at
open_time + 1h. Downstream code must respect that (see research/v2/lib/panel.py).
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import sys
import time
import urllib.parse
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd

S3 = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
DL = "https://data.binance.vision/"
ROOT = Path(__file__).resolve().parents[3] / "data" / "lake" / "binance_um"

KLINE_COLS = ["open_time", "open", "high", "low", "close", "volume", "close_time",
              "quote_volume", "count", "taker_buy_volume", "taker_buy_quote_volume", "ignore"]

DATASETS = {
    "klines_1h": ("data/futures/um/monthly/klines/{s}/1h/", "kline"),
    "premium_1h": ("data/futures/um/monthly/premiumIndexKlines/{s}/1h/", "kline"),
    "funding": ("data/futures/um/monthly/fundingRate/{s}/", "funding"),
}


def _get(url: str, retries: int = 5) -> bytes:
    for i in range(retries):
        try:
            url = urllib.parse.quote(url, safe=':/?&=.-_%')
            with urllib.request.urlopen(url, timeout=60) as r:
                return r.read()
        except Exception:  # noqa: BLE001 - network retry
            if i == retries - 1:
                raise
            time.sleep(1.5 * (i + 1))
    raise RuntimeError("unreachable")


def s3_list(prefix: str) -> list[str]:
    out, marker = [], ""
    while True:
        url = f"{S3}?delimiter=/&prefix={prefix}" + (f"&marker={marker}" if marker else "")
        x = _get(url).decode()
        out += re.findall(r"<Prefix>([^<]+)</Prefix>", x)[1:]
        out += re.findall(r"<Key>([^<]+)</Key>", x)
        if "<IsTruncated>true" in x:
            marker = re.findall(r"<NextMarker>([^<]+)</NextMarker>", x)[0]
        else:
            return out


def list_symbols() -> list[str]:
    syms = [p.rstrip("/").split("/")[-1] for p in s3_list("data/futures/um/monthly/klines/")]
    return sorted(s for s in syms if s.endswith("USDT"))


def _parse_csv(raw: bytes, kind: str) -> pd.DataFrame:
    first = raw.split(b"\n", 1)[0]
    has_header = not first[:1].isdigit()
    if kind == "kline":
        df = pd.read_csv(io.BytesIO(raw), header=0 if has_header else None)
        df = df.iloc[:, :12]
        df.columns = KLINE_COLS
        df = df.drop(columns=["ignore"])
        for c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        df["open_time"] = df["open_time"].astype("int64")
        # some archives use microseconds; normalize to ms
        big = df["open_time"] > 10**14
        df.loc[big, "open_time"] //= 1000
        df["close_time"] = df["close_time"].astype("int64")
        df.loc[df["close_time"] > 10**14, "close_time"] //= 1000
        return df
    df = pd.read_csv(io.BytesIO(raw), header=0 if has_header else None).iloc[:, :3]
    df.columns = ["calc_time", "funding_interval_hours", "funding_rate"]
    df["calc_time"] = pd.to_numeric(df["calc_time"]).astype("int64")
    df["funding_rate"] = pd.to_numeric(df["funding_rate"], errors="coerce")
    return df[["calc_time", "funding_interval_hours", "funding_rate"]]


def fetch_symbol(sym: str, dataset: str, manifest_lines: list) -> tuple[str, str, int]:
    prefix, kind = DATASETS[dataset]
    out = ROOT / dataset / f"{sym}.parquet"
    keys = [k for k in s3_list(prefix.format(s=sym)) if k.endswith(".zip")]
    if not keys:
        return sym, dataset, 0
    if out.exists():
        meta = out.with_suffix(".months.json")
        if meta.exists() and set(json.loads(meta.read_text())) >= set(keys):
            return sym, dataset, -1
    frames = []
    for k in keys:
        blob = _get(DL + k)
        sha = hashlib.sha256(blob).hexdigest()
        try:
            expected = _get(DL + k + ".CHECKSUM").decode().split()[0]
        except Exception:  # noqa: BLE001
            expected = None
        if expected and expected != sha:
            raise ValueError(f"checksum mismatch {k}")
        with zipfile.ZipFile(io.BytesIO(blob)) as z:
            raw = z.read(z.namelist()[0])
        frames.append(_parse_csv(raw, kind))
        manifest_lines.append({"key": k, "sha256": sha, "checksum_ok": expected == sha if expected else None,
                               "bytes": len(blob)})
    df = pd.concat(frames, ignore_index=True)
    tcol = "open_time" if kind == "kline" else "calc_time"
    df = df.drop_duplicates(tcol).sort_values(tcol).reset_index(drop=True)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out, index=False)
    out.with_suffix(".months.json").write_text(json.dumps(sorted(keys)))
    return sym, dataset, len(df)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--datasets", default="klines_1h,funding,premium_1h")
    ap.add_argument("--symbols", default="")
    ap.add_argument("--workers", type=int, default=12)
    a = ap.parse_args()
    ROOT.mkdir(parents=True, exist_ok=True)
    syms = a.symbols.split(",") if a.symbols else list_symbols()
    (ROOT / "symbols.json").write_text(json.dumps(syms))
    print(f"{len(syms)} symbols", flush=True)
    jobs = [(s, d) for d in a.datasets.split(",") for s in syms]
    manifest: list = []
    done = fail = 0
    with ThreadPoolExecutor(a.workers) as ex:
        futs = {ex.submit(fetch_symbol, s, d, manifest): (s, d) for s, d in jobs}
        for f in as_completed(futs):
            s, d = futs[f]
            try:
                f.result()
                done += 1
            except Exception as e:  # noqa: BLE001
                fail += 1
                print(f"FAIL {d} {s}: {e}", flush=True)
            if (done + fail) % 100 == 0:
                print(f"progress {done + fail}/{len(jobs)} fail={fail}", flush=True)
                with open(ROOT / "manifest.jsonl", "a") as fh:
                    while manifest:
                        fh.write(json.dumps(manifest.pop()) + "\n")
    with open(ROOT / "manifest.jsonl", "a") as fh:
        for m in manifest:
            fh.write(json.dumps(m) + "\n")
    print(f"DONE ok={done} fail={fail}", flush=True)
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
