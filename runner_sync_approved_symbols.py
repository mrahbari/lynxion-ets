#!/usr/bin/env python3
"""Approved-symbols sync: the daily tradable universe of the execution venue.

approved_symbols.json is the platform's symbol gate (execution, runtime discovery, data availability).
It used to be every listed BingX contract (866 names, refreshed by hand). Since 2026-11-23 it holds only
symbols liquid enough to trade on the venue the platform executes on.

Venue: UNIVERSE_EXCHANGE, else DEFAULT_BROKER, else "bingx" (any ccxt exchange id: bingx, binance, mexc,
phemex, ...). Moving the platform to another exchange needs no change here; if the new venue cannot be
read, the previous list stays in place.

Rule (pre-registered, not fitted to trades):
  linear USDT-margined perpetual, active, base not a stablecoin,
  >= UNIVERSE_MIN_LISTING_DAYS (30) completed daily candles (listing age),
  median daily quote volume over the last 7 completed days >= UNIVERSE_MIN_MEDIAN_QUOTE_VOLUME_USDT (10 M);
  quote volume = base volume x (high + low + close) / 3.
  Always kept: symbols with an open platform position (data/active_positions_journal.json).
Safety: files are replaced atomically and only when >= MIN_SYMBOLS names pass; any failure keeps the previous
list (exit code 1). The blacklist is a separate file and is not touched.

Outputs: application/configs/approved_symbols.json (SymbolValidator), data/approved-symbols/approved_symbols.json
(CentralizedSymbolManager), data/approved-symbols/universe_report.json (per-symbol audit).
Both readers hot-reload the file, so the running platform picks up the new list without a restart.

Usage: python interface/cli/sync_approved_symbols.py [--dry-run]
Scheduled daily 00:30 UTC by scripts/launchd/com.lynxion.approved-symbols-sync.plist.
"""
from __future__ import annotations

import json
import os
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TARGETS = [ROOT / "application" / "configs" / "approved_symbols.json",
           ROOT / "data" / "approved-symbols" / "approved_symbols.json"]
REPORT = ROOT / "data" / "approved-symbols" / "universe_report.json"
ACTIVE = ROOT / "data" / "active_positions_journal.json"
MIN_SYMBOLS = 20
DAY_MS = 86_400_000
STABLE = {"USDT", "USDC", "USD1", "USDG", "USDD", "USDE", "PYUSD", "RLUSD", "FDUSD", "TUSD", "BUSD", "DAI",
          "PAX", "USDP", "USDS", "GUSD", "LUSD", "FRAX", "EURC", "EURT"}


def settings() -> dict:
    return {"exchange": (os.getenv("UNIVERSE_EXCHANGE") or os.getenv("DEFAULT_BROKER") or "bingx").strip().lower(),
            "min_median_qv": float(os.getenv("UNIVERSE_MIN_MEDIAN_QUOTE_VOLUME_USDT", "10000000")),
            "min_age_days": int(os.getenv("UNIVERSE_MIN_LISTING_DAYS", "30"))}


def norm(market_id: str) -> str:
    return str(market_id).upper().replace("-", "").replace("_", "").replace("/", "")


def active_symbols() -> set[str]:
    try:
        d = json.loads(ACTIVE.read_text())
        return {norm(s) for s in (d.get("active_symbols", []) if isinstance(d, dict) else d)}
    except Exception:  # noqa: BLE001
        return set()


def _retry(fn, *a, **k):
    for i in range(4):
        try:
            return fn(*a, **k)
        except Exception:  # noqa: BLE001
            if i == 3:
                raise
            time.sleep(1 + 2 * i)


def make_exchange(name: str):
    import ccxt
    return getattr(ccxt, name)({"enableRateLimit": True, "options": {"defaultType": "swap"}})


def build(ex=None, now_ms: int | None = None, cfg: dict | None = None) -> tuple[list[str], list[dict]]:
    cfg = cfg or settings()
    ex = ex or make_exchange(cfg["exchange"])
    now_ms = now_ms or int(time.time() * 1000)
    day0 = now_ms // DAY_MS * DAY_MS                       # start of the current, incomplete UTC day
    markets = _retry(ex.load_markets)
    perps = {s: m for s, m in markets.items()
             if m.get("swap") and m.get("linear") and m.get("quote") == "USDT" and m.get("settle") == "USDT"}
    tickers = _retry(ex.fetch_tickers, list(perps))
    rows = []
    for s, m in perps.items():
        qv24 = float((tickers.get(s) or {}).get("quoteVolume") or 0)
        row = {"symbol": norm(m["id"]), "qv_24h": round(qv24), "median_qv_7d": None, "days": None,
               "approved": False, "reason": ""}
        if m.get("active") is False or str(m.get("base", "")).upper() in STABLE:
            row["reason"] = "state"
        elif qv24 < cfg["min_median_qv"] * 0.25:          # pre-filter only, limits candle requests
            row["reason"] = "qv_24h"
        else:
            bars = _retry(ex.fetch_ohlcv, s, "1d", limit=cfg["min_age_days"] + 5)
            done = sorted((b for b in bars if int(b[0]) < day0), key=lambda b: int(b[0]))
            row["days"] = len(done)
            qv = [b[5] * (b[2] + b[3] + b[4]) / 3 for b in done[-7:] if None not in b[2:6]]
            row["median_qv_7d"] = round(statistics.median(qv)) if len(qv) == 7 else None
            if len(done) < cfg["min_age_days"]:
                row["reason"] = "age"
            elif row["median_qv_7d"] is None or row["median_qv_7d"] < cfg["min_median_qv"]:
                row["reason"] = "median_qv_7d"
            else:
                row["approved"], row["reason"] = True, "liquid"
        rows.append(row)
    held = active_symbols()
    for r in rows:
        if not r["approved"] and r["symbol"] in held:
            r["approved"], r["reason"] = True, "open_position"
    return sorted({r["symbol"] for r in rows if r["approved"]}), rows


def _atomic_write(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".tmp.{os.getpid()}")
    tmp.write_text(json.dumps(payload, indent=2))
    os.replace(tmp, path)


def sync(dry_run: bool = False) -> int:
    cfg = settings()
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    try:
        approved, rows = build(cfg=cfg)
    except Exception as exc:  # noqa: BLE001
        print(f"{stamp} approved-symbols sync FAILED on {cfg['exchange']}, previous list kept: {exc}")
        return 1
    if len(approved) < MIN_SYMBOLS:
        print(f"{stamp} only {len(approved)} symbols passed on {cfg['exchange']} (< {MIN_SYMBOLS}); previous list kept")
        return 1
    previous = set()
    try:
        previous = set(json.loads(TARGETS[0].read_text()))
    except Exception:  # noqa: BLE001
        pass
    print(f"{stamp} {cfg['exchange']}: approved {len(approved)} of {len(rows)} USDT perps "
          f"(median 7d quote volume >= {cfg['min_median_qv']:,.0f}, >= {cfg['min_age_days']} d) | "
          f"added {sorted(set(approved) - previous)} removed {len(previous - set(approved))}")
    if dry_run:
        print(", ".join(approved))
        return 0
    for target in TARGETS:
        _atomic_write(target, approved)
    _atomic_write(REPORT, {"built_utc": stamp, **cfg, "approved": len(approved), "rows": rows})
    return 0


def main():
    from interface.cli.sync_approved_symbols import main as cli_main
    return cli_main()


if __name__ == "__main__":
    raise SystemExit(main())
