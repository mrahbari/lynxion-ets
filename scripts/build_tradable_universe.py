"""Daily BingX tradable universe -> approved_symbols.json (the platform's execution / discovery / data gate).

Why (2026-11-23): runtime discovery picks symbols by CMC / Binance activity; half of the 61 discovered names
traded < 5 M USDT/day on BingX (stops fill with gap slippage, e.g. PROMUSDT -1.5 R) and 5 were not listed
on BingX at all. The approved list itself was a static 866-name file. The gate now follows BingX liquidity.

Rule (pre-registered, not fitted to trades):
  BingX USDT-M perpetual, status 1 and API open/close enabled, listed >= 30 days,
  median daily quote volume over the last 7 COMPLETED days >= MIN_MEDIAN_QV (default 10 M USDT;
  quote volume = base volume x (high + low + close) / 3), stablecoin bases excluded.
  Always kept: symbols with an open platform position (data/active_positions_journal.json), so a
  de-listing from the gate can never block managing an open trade.
Safety: the files are replaced atomically and only when the build yields >= MIN_SYMBOLS names; any failure
leaves the previous list in place (exit code 1). Blacklist is unchanged (separate file).

Writes application/configs/approved_symbols.json (SymbolValidator: execution, discovery, data availability)
and data/approved-symbols/approved_symbols.json (CentralizedSymbolManager: historical data), plus
data/approved-symbols/universe_report.json (per-symbol numbers, for audit).

Usage: python scripts/build_tradable_universe.py [--dry-run]
Scheduled daily by ~/Library/LaunchAgents/com.lynxion.tradable-universe.plist.
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API = "https://open-api.bingx.com"
TARGETS = [ROOT / "application" / "configs" / "approved_symbols.json",
           ROOT / "data" / "approved-symbols" / "approved_symbols.json"]
REPORT = ROOT / "data" / "approved-symbols" / "universe_report.json"
ACTIVE = ROOT / "data" / "active_positions_journal.json"
MIN_MEDIAN_QV = float(os.getenv("UNIVERSE_MIN_MEDIAN_QUOTE_VOLUME_USDT", "10000000"))
MIN_AGE_DAYS = int(os.getenv("UNIVERSE_MIN_LISTING_DAYS", "30"))
MIN_SYMBOLS = 20
PREFILTER_QV = MIN_MEDIAN_QV * 0.25        # 24h ticker pre-filter, only to limit kline requests
STABLE = {"USDT", "USDC", "USD1", "USDG", "USDD", "USDE", "PYUSD", "RLUSD", "FDUSD", "TUSD", "BUSD", "DAI",
          "PAX", "USDP", "USDS", "GUSD", "LUSD", "FRAX", "EURC", "EURT"}


def _get(path: str):
    for i in range(4):
        try:
            with urllib.request.urlopen(API + path, timeout=20) as r:
                d = json.loads(r.read())
            if d.get("code") == 0:
                return d["data"]
        except Exception:  # noqa: BLE001
            pass
        time.sleep(1 + 2 * i)
    raise RuntimeError(f"BingX request failed: {path}")


def active_symbols() -> set[str]:
    try:
        d = json.loads(ACTIVE.read_text())
        syms = d.get("active_symbols", []) if isinstance(d, dict) else d
        return {str(s).upper().replace("-", "").replace("/", "") for s in syms}
    except Exception:  # noqa: BLE001
        return set()


def build(now_ms: int | None = None) -> tuple[list[str], list[dict]]:
    now_ms = now_ms or int(time.time() * 1000)
    day0 = now_ms // 86_400_000 * 86_400_000          # start of the current (incomplete) UTC day
    contracts = {c["symbol"]: c for c in _get("/openApi/swap/v2/quote/contracts")}
    tickers = {t["symbol"]: float(t.get("quoteVolume") or 0) for t in _get("/openApi/swap/v2/quote/ticker")}
    rows = []
    for sym, c in contracts.items():
        base = c.get("asset") or sym.split("-")[0]
        ok_state = (str(c.get("status")) == "1" and str(c.get("apiStateOpen")).lower() == "true"
                    and str(c.get("apiStateClose")).lower() == "true" and sym.endswith("-USDT")
                    and base.upper() not in STABLE)
        age_days = (now_ms - int(c.get("launchTime") or now_ms)) / 86_400_000
        row = {"symbol": sym.replace("-", ""), "age_days": round(age_days, 1), "qv_24h": tickers.get(sym, 0.0),
               "median_qv_7d": None, "approved": False, "reason": ""}
        if not ok_state:
            row["reason"] = "state"
        elif age_days < MIN_AGE_DAYS:
            row["reason"] = "age"
        elif row["qv_24h"] < PREFILTER_QV:
            row["reason"] = "qv_24h"
        else:
            k = _get(f"/openApi/swap/v3/quote/klines?symbol={sym}&interval=1d&limit=9")
            done = sorted((b for b in k if int(b["time"]) < day0), key=lambda b: int(b["time"]))[-7:]  # API is newest-first
            qv = [float(b["volume"]) * (float(b["high"]) + float(b["low"]) + float(b["close"])) / 3 for b in done]
            row["median_qv_7d"] = round(statistics.median(qv), 0) if len(qv) == 7 else None
            if row["median_qv_7d"] is None:
                row["reason"] = "history"
            elif row["median_qv_7d"] < MIN_MEDIAN_QV:
                row["reason"] = "median_qv_7d"
            else:
                row["approved"], row["reason"] = True, "liquid"
            time.sleep(0.05)
        rows.append(row)
    held = active_symbols()
    for r in rows:
        if not r["approved"] and r["symbol"] in held:
            r["approved"], r["reason"] = True, "open_position"
    return sorted(r["symbol"] for r in rows if r["approved"]), rows


def _atomic_write(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".tmp.{os.getpid()}")
    tmp.write_text(json.dumps(payload, indent=2))
    os.replace(tmp, path)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    try:
        approved, rows = build()
    except Exception as exc:  # noqa: BLE001
        print(f"{stamp} universe build FAILED, previous list kept: {exc}", file=sys.stderr)
        return 1
    if len(approved) < MIN_SYMBOLS:
        print(f"{stamp} only {len(approved)} symbols passed (< {MIN_SYMBOLS}); previous list kept", file=sys.stderr)
        return 1
    print(f"{stamp} approved {len(approved)} of {len(rows)} BingX contracts "
          f"(median 7d quote volume >= {MIN_MEDIAN_QV:,.0f}, age >= {MIN_AGE_DAYS} d)")
    if args.dry_run:
        print(", ".join(approved))
        return 0
    for target in TARGETS:
        _atomic_write(target, approved)
    _atomic_write(REPORT, {"built_utc": stamp, "min_median_qv": MIN_MEDIAN_QV, "min_age_days": MIN_AGE_DAYS,
                           "approved": len(approved), "rows": rows})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
