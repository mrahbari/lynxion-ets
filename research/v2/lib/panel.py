"""Point-in-time daily panel built from the Binance USD-M 1h lake.

Timing convention (the single most important thing in this module):

* A 1h kline with open_time T is KNOWN at T+1h.
* Daily row labelled D (UTC midnight) aggregates the 24 hourly bars with open_time in [D-1d, D).
  Every field in row D is therefore known at time D. Signals computed on row D may only use
  rows <= D.
* `exec_px` on row D is the close of the hourly bar with open_time D + (lag_h - 1)h, i.e. the price
  available `lag_h` hours AFTER the decision time D. Default lag_h = 1: decide at 00:00, fill at
  the 01:00 close. Portfolio returns are measured exec_px -> next exec_px, so a signal never
  earns the move that produced it.
* Funding paid between exec(D) and exec(D+1) is summed into `funding_fwd` on row D (it is a
  cash-flow of the position held over that interval, not a signal input).

Wide output: dict of DataFrames index=date (UTC), columns=symbols.
"""
from __future__ import annotations

import json
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

LAKE = Path(__file__).resolve().parents[3] / "data" / "lake" / "binance_um"
CACHE = LAKE / "panel_daily"
HOUR = 3_600_000

FIELDS = ["close", "open", "high", "low", "quote_volume", "taker_buy_quote", "trades",
          "exec_px", "funding_fwd", "funding_past", "premium_close", "premium_mean", "n_hours"]


def _daily_for_symbol(sym: str, lag_h: int = 1) -> pd.DataFrame | None:
    kp = LAKE / "klines_1h" / f"{sym}.parquet"
    if not kp.exists():
        return None
    k = pd.read_parquet(kp)
    k = k[k["close"] > 0]
    if k.empty:
        return None
    k["day"] = ((k["open_time"] // (24 * HOUR)) + 1) * 24 * HOUR  # label = day END (known time)
    g = k.groupby("day")
    d = pd.DataFrame({
        "open": g["open"].first(),
        "high": g["high"].max(),
        "low": g["low"].min(),
        "close": g["close"].last(),
        "quote_volume": g["quote_volume"].sum(),
        "taker_buy_quote": g["taker_buy_quote_volume"].sum(),
        "trades": g["count"].sum(),
        "n_hours": g["close"].size(),
    })
    # exec price: close of bar with open_time = D + (lag_h-1)h
    px = k.set_index("open_time")["close"]
    exec_t = d.index.values + (lag_h - 1) * HOUR
    d["exec_px"] = px.reindex(exec_t).values
    # funding
    fp = LAKE / "funding" / f"{sym}.parquet"
    d["funding_fwd"] = 0.0
    d["funding_past"] = 0.0
    if fp.exists():
        f = pd.read_parquet(fp)
        ft = f["calc_time"].values
        fr = f["funding_rate"].fillna(0).values
        days = d.index.values
        # funding_past: events in (D-1d, D] -> label ceil(ft/day)*day, known at D
        lab = -(-ft // (24 * HOUR)) * 24 * HOUR
        d["funding_past"] = pd.Series(fr).groupby(lab).sum().reindex(days).fillna(0).values
        # funding_fwd: events in (exec(D), exec(D+1)] with exec(D) = D + lag_h hours
        lab_fwd = ((ft - lag_h * HOUR - 1) // (24 * HOUR)) * 24 * HOUR
        d["funding_fwd"] = pd.Series(fr).groupby(lab_fwd).sum().reindex(days).fillna(0).values
    pp = LAKE / "premium_1h" / f"{sym}.parquet"
    if pp.exists():
        p = pd.read_parquet(pp)
        p["day"] = ((p["open_time"] // (24 * HOUR)) + 1) * 24 * HOUR
        gp = p.groupby("day")
        d["premium_close"] = gp["close"].last().reindex(d.index).values
        d["premium_mean"] = gp["close"].mean().reindex(d.index).values
    else:
        d["premium_close"] = np.nan
        d["premium_mean"] = np.nan
    d.index = pd.to_datetime(d.index, unit="ms", utc=True)
    d.index.name = "date"
    # drop a trailing partial day
    d = d[d["n_hours"] >= 20]
    d["symbol"] = sym
    return d.reset_index()


def build_daily_cache(symbols: list[str] | None = None, lag_h: int = 1, workers: int = 8) -> Path:
    if symbols is None:
        symbols = sorted(p.stem for p in (LAKE / "klines_1h").glob("*.parquet"))
    CACHE.mkdir(parents=True, exist_ok=True)
    with ProcessPoolExecutor(workers) as ex:
        parts = [x for x in ex.map(_daily_for_symbol, symbols, [lag_h] * len(symbols)) if x is not None]
    long = pd.concat(parts, ignore_index=True)
    out = CACHE / f"daily_lag{lag_h}.parquet"
    long.to_parquet(out, index=False)
    (CACHE / f"daily_lag{lag_h}.symbols.json").write_text(json.dumps(symbols))
    return out


def load_daily(lag_h: int = 1, start: str | None = None, end: str | None = None) -> dict[str, pd.DataFrame]:
    long = pd.read_parquet(CACHE / f"daily_lag{lag_h}.parquet")
    if start:
        long = long[long["date"] >= pd.Timestamp(start, tz="UTC")]
    if end:
        long = long[long["date"] <= pd.Timestamp(end, tz="UTC")]
    wide = {}
    for f in FIELDS:
        wide[f] = long.pivot(index="date", columns="symbol", values=f).sort_index()
    idx = wide["close"].index
    full = pd.date_range(idx.min(), idx.max(), freq="1D", tz="UTC")
    for f in FIELDS:
        wide[f] = wide[f].reindex(full)
    return wide


def universe_mask(p: dict[str, pd.DataFrame], min_age_days: int = 30,
                  min_adv_usd: float = 10e6, adv_window: int = 30,
                  exclude: tuple[str, ...] = ("USDCUSDT", "BUSDUSDT", "TUSDUSDT", "FDUSDUSDT",
                                              "USDPUSDT", "DAIUSDT", "EURUSDT", "XAUTUSDT", "PAXGUSDT")) -> pd.DataFrame:
    """Eligible at date D using only data <= D: age, trailing median dollar volume, valid prices."""
    close = p["close"]
    age = close.notna().cumsum()
    adv = p["quote_volume"].rolling(adv_window, min_periods=adv_window // 2).median()
    m = (age >= min_age_days) & (adv >= min_adv_usd) & close.notna() & p["exec_px"].notna()
    for s in exclude:
        if s in m.columns:
            m[s] = False
    return m


def forward_returns(p: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return earned by a position opened at exec(D) and closed at exec(D+1); stored on row D.

    If a symbol delists (no exec(D+1)) the position is closed at its last available close
    (approximates settlement) instead of silently dropping the loss.
    """
    px = p["exec_px"]
    nxt = px.shift(-1)
    last_close = p["close"].shift(-1)
    nxt = nxt.fillna(last_close)
    # still NaN -> delisted between days: use last known close (ffill) as exit
    dead = nxt.isna() & px.notna()
    nxt = nxt.where(~dead, p["close"].ffill().shift(-1).where(dead))
    return nxt / px - 1.0
