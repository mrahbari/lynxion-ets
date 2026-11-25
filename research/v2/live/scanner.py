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
Limit suggestion (mechanical, NOT validated): long limit = max(EMA20_4h, close - 1 ATR_4h), stop = limit - 1.5 ATR_4h;
short mirror. Funding shown per coin; flagged when your side pays >= 0.03 %/8h (3x the base rate).
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


def limit_levels(row, side: str, prec: int) -> tuple[float, float]:
    a, c, e = row["atr_4h"], row["close"], row["ema20_4h"]
    if side == "LONG":
        lim = max(e, c - a)
        stop = lim - 1.5 * a
    else:
        lim = min(e, c + a)
        stop = lim + 1.5 * a
    return round(lim, prec), round(stop, prec)


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


def _dots(r) -> str:
    return "".join("🟢" if r[k] > 0 else "🔴" for k in ("strength", "momentum", "short_term"))


def fmt_px(x: float) -> str:
    return f"{x:.6g}"


def render(longs, shorts, mv, funding, contracts, ts: str) -> tuple[str, list]:
    """Tree layout matching the platform's trade notifications (three lines per coin)."""
    def c(x):
        return f"<code>{html.escape(str(x))}</code>"
    btc = f"{'above' if mv['btc_above_ema50'] else 'below'} EMA50 · 28d {mv['btc_ret28']:+.0%}"
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
            lim, stop = limit_levels(r, side, prec)
            f = funding.get(sym, 0.0)
            pays = (side == "LONG" and f >= FUND_CROWDED) or (side == "SHORT" and f <= -FUND_CROWDED)
            ext = r["short_term"]
            flags = (" ⚠️" if abs(ext) > 2 else "") + (" 💸" if pays else "")
            last = i == len(items) - 1
            score = format(float(r["score"]) - 50, "+.0f")
            out.append(f" {'└' if last else '├'} <b>{html.escape(sym[:-4])}</b> {c(score)} {_dots(r)}{flags}")
            bar = " " if last else "│"
            out.append(f" {bar}    🎯 <b>Entry:</b> {c(fmt_px(lim))} ({lim / r['close'] - 1:+.1%} from now)")
            out.append(f" {bar}    🛑 <b>Stop:</b> {c(fmt_px(stop))} (risk {abs(stop / lim - 1):.1%})")
            rows.append({"side": side, "symbol": sym, "score": round(float(r["score"]) - 50, 1), "close": r["close"],
                         "limit": lim, "stop": stop, "ext_atr": round(float(ext), 2), "funding": f})
        out.append("")
    out.append("<i>Info only · no proven edge · ⚠️ late entry · 💸 you pay funding</i>")
    return "\n".join(out), rows


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
    telegram("Lynxion coins overview (info only)", r["text"])


if __name__ == "__main__":
    main()
