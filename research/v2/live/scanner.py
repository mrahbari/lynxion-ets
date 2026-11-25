"""Coins overview scanner — 4-hourly Telegram report: top 7 longs / top 7 shorts + market view (INFORMATION ONLY).

Not a watcher and not a strategy: it never feeds the engine, never places orders. Cross-sectional trend ranking has
NO proven edge in our research (E2: 18 momentum variants, best DEV Sharpe 0.59, negative 2022-23); the message says
so. Every run is appended to data/v2_live/scanner_log.jsonl so the picks can be evaluated forward later.

Universe: Binance USDT-M perpetuals (TRADING) that are also listed on BingX, 30-day median daily quote volume >= $10M
(same liquidity floor as XS-COMBO). Only CLOSED bars are used (daily and 4h).
Components (cross-sectional percentile ranks, 0..1):
  momentum   28-day return / (daily vol x sqrt 28)                      (E2's least-bad variant: vol-adjusted)
  strength   efficiency ratio(20 daily) x sign(20-day change)           (clean one-way move = strong)
  short-term (4h close - EMA20 of 4h) / ATR14 of 4h                       (recent direction, reduces lag)
Score = 100 x mean of the three ranks. LONG list: highest scores with all three components positive; SHORT list:
lowest scores with all three negative. Extension = (close - EMA20_4h) / ATR_4h; |ext| > 2 is flagged as late.
Levels (mechanical, NOT validated): multi-timeframe, see trade_levels() — 1h pullback limit, stop beyond the 1h swing
+ 15m buffer, stop distance between 1 ATR(1h) and 1 ATR(4h), TP1 = 1.5 R, TP2 = 3 R. Funding shown per coin; flagged when your side pays >= 0.03 %/8h (3x the base rate).
Market view: BTC vs daily EMA50 and 28-day return; breadth = share of the universe above daily EMA50; median funding;
  dashboard: sentiment (mean signed score), confidence (share of coins with all three components agreeing), energy
  (median 24h / 30-day volume). Displayed score = score - 50 (range -50..+50).
Usage: python3 -m live.scanner [--dry-run]
"""
from __future__ import annotations

import argparse
import html
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from live import binance_live_panel as lp  # noqa: E402
from live.bingx_vst import BingXVST  # noqa: E402

LOG = ROOT / "data" / "v2_live" / "scanner_log.jsonl"
N_PICK = 7
MIN_ADV = 10e6
H4 = 4 * 3_600_000
FUND_CROWDED = 0.0003


def ema(x: np.ndarray, n: int) -> np.ndarray:
    return pd.Series(x).ewm(span=n, adjust=False).mean().to_numpy()


def atr(h, l, c, n=14) -> float:
    tr = np.maximum(h[1:] - l[1:], np.maximum(np.abs(h[1:] - c[:-1]), np.abs(l[1:] - c[:-1])))
    return float(tr[-n:].mean())


def closed(rows: list, interval_ms: int, now_ms: int) -> list:
    return [r for r in rows if int(r[0]) + interval_ms <= now_ms]


def features(daily: list, h4: list) -> dict | None:
    """Per-symbol features from CLOSED daily (>= 51) and 4h (>= 40) klines (Binance array format)."""
    if len(daily) < 51 or len(h4) < 40:
        return None
    dc = np.array([float(r[4]) for r in daily])
    qv = np.array([float(r[7]) for r in daily])
    c4 = np.array([float(r[4]) for r in h4]); h = np.array([float(r[2]) for r in h4]); l = np.array([float(r[3]) for r in h4])
    lr = np.diff(np.log(dc))
    vol = lr[-28:].std()
    ch20 = dc[-1] - dc[-21]
    path = np.abs(np.diff(dc[-21:])).sum()
    e20 = ema(c4, 20)[-1]
    a4 = atr(h, l, c4)
    if vol <= 0 or path <= 0 or a4 <= 0:
        return None
    return {"close": float(c4[-1]), "adv30": float(np.median(qv[-30:])), "vol24h": float(qv[-1]),
            "ret1d": float(dc[-1] / dc[-2] - 1), "ret28": float(dc[-1] / dc[-29] - 1),
            "momentum": float(np.log(dc[-1] / dc[-29]) / (vol * np.sqrt(28))),
            "strength": float(abs(ch20) / path * np.sign(ch20)),
            "short_term": float((c4[-1] - e20) / a4), "ema20_4h": float(e20), "atr_4h": a4,
            "above_ema50d": bool(dc[-1] > ema(dc, 50)[-1])}


def rank_table(feat: dict[str, dict]) -> pd.DataFrame:
    df = pd.DataFrame(feat).T
    for k in ("momentum", "strength", "short_term"):
        df[k] = df[k].astype(float)
        df[f"r_{k}"] = df[k].rank(pct=True)
    df["score"] = 100 * df[["r_momentum", "r_strength", "r_short_term"]].mean(1)
    return df.sort_values("score", ascending=False)


def pick(df: pd.DataFrame, n: int = N_PICK) -> tuple[pd.DataFrame, pd.DataFrame]:
    bull = (df.momentum > 0) & (df.strength > 0) & (df.short_term > 0)
    bear = (df.momentum < 0) & (df.strength < 0) & (df.short_term < 0)
    return df[bull].head(n), df[bear].sort_values("score").head(n)


def trade_levels(side: str, close: float, atr_4h: float, k1h: list, k15: list) -> dict | None:
    """Multi-timeframe levels (mechanical, NOT validated; replaces the 4h-only ATR levels, 2026-11-25).
    1h  : limit = pullback to EMA20(1h) or 1 ATR(1h), whichever is closer; stop beyond the 12-hour 1h swing.
    15m : 0.5 ATR(15m) buffer behind the swing (avoids stops exactly on the obvious level).
    4h  : caps the stop distance at 1 ATR(4h); the floor is 1 ATR(1h) (noise).
    R = |limit - stop|; TP1 = 1.5 R (partial), TP2 = 3 R. Entry zone = current price .. limit."""
    if len(k1h) < 30 or len(k15) < 20:
        return None
    c1 = np.array([float(r[4]) for r in k1h]); h1 = np.array([float(r[2]) for r in k1h]); l1 = np.array([float(r[3]) for r in k1h])
    c15 = np.array([float(r[4]) for r in k15]); h15 = np.array([float(r[2]) for r in k15]); l15 = np.array([float(r[3]) for r in k15])
    a1, a15 = atr(h1, l1, c1), atr(h15, l15, c15)
    e1 = float(ema(c1, 20)[-1])
    if side == "LONG":
        lim = max(e1, close - a1) if e1 < close else close
        sl = min(float(l1[-12:].min()), lim - a1) - 0.5 * a15
        d = min(max(lim - sl, a1), atr_4h)
        sl = lim - d
    else:
        lim = min(e1, close + a1) if e1 > close else close
        sl = max(float(h1[-12:].max()), lim + a1) + 0.5 * a15
        d = min(max(sl - lim, a1), atr_4h)
        sl = lim + d
    sgn = 1 if side == "LONG" else -1
    return {"limit": lim, "sl": sl, "tp1": lim + sgn * 1.5 * d, "tp2": lim + sgn * 3 * d,
            "zone": tuple(sorted((close, lim))), "atr_1h": a1, "atr_15m": a15}


def market_view(df: pd.DataFrame, funding: dict) -> dict:
    btc = df.loc["BTCUSDT"] if "BTCUSDT" in df.index else None
    breadth = float(df.above_ema50d.astype(bool).mean())
    med_f = float(np.median([funding.get(s, 0.0) for s in df.index]))
    btc_up = bool(btc is not None and btc.above_ema50d)
    if btc_up and breadth > 0.6:
        label = "TRENDING UP"
    elif btc is not None and not btc.above_ema50d and breadth < 0.4:
        label = "TRENDING DOWN"
    else:
        label = "MIXED / RANGE"
    # dashboard (descriptive, no predictive claim):
    #   sentiment  = 50 x mean over coins of (sign momentum + sign strength + sign short-term) / 3, range -50..+50
    #                (absolute signs, not ranks: ranks average to 50 by construction) -> Bearish / Neutral / Bullish
    #   confidence = 0..10: share of coins whose three components ALL agree with the sentiment direction, x10
    #   energy     = median 24h volume / 30-day median volume: < 0.8 Low, > 1.2 High, else Mid
    comp = np.sign(df[["momentum", "strength", "short_term"]].astype(float))
    signed = float(50 * comp.mean(1).mean())
    sentiment = "Bullish" if signed > 5 else "Bearish" if signed < -5 else "Neutral"
    sgn = 1 if signed > 0 else -1
    agree = ((np.sign(df.momentum) == sgn) & (np.sign(df.strength) == sgn) & (np.sign(df.short_term) == sgn)).mean()
    vr = float((df.vol24h.astype(float) / df.adv30.astype(float)).median())
    energy = "Low" if vr < 0.8 else "High" if vr > 1.2 else "Mid"
    return {"label": label, "breadth": breadth, "median_funding": med_f, "btc_above_ema50": btc_up,
            "sentiment": sentiment, "sentiment_score": signed, "confidence": float(10 * agree),
            "energy": energy, "volume_ratio": vr,
            "btc_ret28": float(btc.ret28) if btc is not None else None, "btc_close": float(btc.close) if btc is not None else None}


def fmt_px(x: float) -> str:
    return f"{x:.6g}"


def render(longs, shorts, mv, funding, contracts, ts: str) -> tuple[str, list]:
    """Tree layout: per coin an entry zone (current price .. limit), Target1/Target2 at 1R/2R from the limit, stop."""
    def c(x):
        return f"<code>{html.escape(str(x))}</code>"
    # BTC trend = price vs its 50-day average; change = last 28 days
    btc = f"{'Rising' if mv['btc_above_ema50'] else 'Falling'} {mv['btc_ret28']:+.0%} over the last 4 weeks"
    out = ["📊 <b>Coins overview (4h)</b>", f" └ <b>Time:</b> {c(ts + ' UTC')}", "",
           "🌐 <b>Market:</b>",
           f" ├ <b>Sentiment:</b> {c(mv['sentiment'] + ' (' + format(mv['sentiment_score'], '+.0f') + ')')}",
           f" ├ <b>Confidence:</b> {c(format(mv['confidence'], '.1f') + '/10')}",
           f" ├ <b>Energy:</b> {c(mv['energy'])}",
           f" └ <b>BTC:</b> {c(btc)}", ""]
    rows = []
    for title, tab, side in (("🟢 <b>Top Longs:</b>", longs, "LONG"), ("🔴 <b>Top Shorts:</b>", shorts, "SHORT")):
        out.append(title)
        items = list(tab.iterrows())
        if not items:
            out.append(" └ none")
        for i, (sym, r) in enumerate(items):
            prec = int(contracts.get(sym, {}).get("pricePrecision", 6))
            lv = r["levels"]
            lim, stop = round(lv["limit"], prec), round(lv["sl"], prec)
            f = funding.get(sym, 0.0)
            pays = (side == "LONG" and f >= FUND_CROWDED) or (side == "SHORT" and f <= -FUND_CROWDED)
            ext = r["short_term"]
            # late = price already > 2 ATR(4h) away from its 4h EMA20: most of the move is done, bounce risk
            flags = (" ⚠️ late" if abs(ext) > 2 else "") + (" 💸 funding" if pays else "")
            last = i == len(items) - 1
            score = f"{'▲' if side == 'LONG' else '▼'}{abs(float(r['score']) - 50):.0f}"
            out.append(f" {'└' if last else '├'} <b>{html.escape(sym[:-4])}</b>  {score}{flags}")
            bar = "│"
            t1, t2 = round(lv["tp1"], prec), round(lv["tp2"], prec)
            lo, hi = (round(x, prec) for x in lv["zone"])
            pct = lambda x: f"{x / lim - 1:+.1%}"  # noqa: E731
            out.append(f" {bar}    ▸ Entry  {c(fmt_px(lo) + ' – ' + fmt_px(hi))}")
            out.append(f" {bar}    ▸ TP1  {c(fmt_px(t1))} ({pct(t1)})")
            out.append(f" {bar}    ▸ TP2  {c(fmt_px(t2))} ({pct(t2)})")
            out.append(f" {bar}    ▸ SL  {c(fmt_px(stop))} ({pct(stop)})")
            if not last:
                out.append(" │")
            rows.append({"side": side, "symbol": sym, "score": round(float(r["score"]) - 50, 1), "close": r["close"],
                         "limit": lim, "stop": stop, "target1": t1, "target2": t2,
                         "zone": [lo, hi], "ext_atr": round(float(ext), 2),
                         "funding": f})
        out.append("")
    return "\n".join(out).rstrip() + "\n\u2800", rows        # U+2800 keeps a blank last line in Telegram


def scan(now_ms: int | None = None) -> dict:
    now_ms = now_ms or int(time.time() * 1000)
    contracts = BingXVST.contracts()
    syms = set(lp.universe_symbols()["symbol"]) & set(contracts)
    tick = {x["symbol"]: float(x["quoteVolume"]) for x in lp._get("/fapi/v1/ticker/24hr")}
    syms = sorted(s for s in syms if tick.get(s, 0) >= MIN_ADV / 2)          # cheap prefilter, ADV checked below
    prem = {x["symbol"]: float(x.get("lastFundingRate") or 0) for x in lp._get("/fapi/v1/premiumIndex")}

    def one(s):
        try:
            d = closed(lp._get(f"/fapi/v1/klines?symbol={s}&interval=1d&limit=62"), 86_400_000, now_ms)
            h = closed(lp._get(f"/fapi/v1/klines?symbol={s}&interval=4h&limit=100"), H4, now_ms)
            return s, features(d, h)
        except Exception:  # noqa: BLE001
            return s, None
    with ThreadPoolExecutor(8) as ex:
        feat = {s: f for s, f in ex.map(one, syms) if f and f["adv30"] >= MIN_ADV}
    df = rank_table(feat)
    longs, shorts = pick(df)

    def lv(sym, side):
        k1 = closed(lp._get(f"/fapi/v1/klines?symbol={sym}&interval=1h&limit=60"), 3_600_000, now_ms)
        k15 = closed(lp._get(f"/fapi/v1/klines?symbol={sym}&interval=15m&limit=60"), 900_000, now_ms)
        return trade_levels(side, float(df.loc[sym, "close"]), float(df.loc[sym, "atr_4h"]), k1, k15)
    longs = longs.assign(levels=[lv(s_, "LONG") for s_ in longs.index])
    shorts = shorts.assign(levels=[lv(s_, "SHORT") for s_ in shorts.index])
    longs, shorts = longs[longs.levels.notna()], shorts[shorts.levels.notna()]
    mv = market_view(df, prem)
    ts = datetime.fromtimestamp(now_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")
    text, rows = render(longs, shorts, mv, prem, contracts, ts)
    return {"text": text, "rows": rows, "market": mv, "universe": len(df), "ts": ts}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    from live.rebalancer import load_env, telegram
    load_env()
    r = scan()
    print(r["text"])
    if a.dry_run:
        return
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG, "a") as fh:
        fh.write(json.dumps({"ts": r["ts"], "universe": r["universe"], "market": r["market"], "picks": r["rows"]}) + "\n")
    telegram("📡 Lynxion Radar · 4H", r["text"])


if __name__ == "__main__":
    main()
