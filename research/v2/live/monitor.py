"""R5 — XS-COMBO-V1 degradation monitor (OBSERVATIONAL ONLY).

Runs at the end of the daily rebalancer job. It reads positions, prices, targets, the order ledger and the shadow
funding ledger, compares each indicator with thresholds derived from the frozen backtest
(research/v2/results/xs_combo_monitor_thresholds.json, built by experiments/e38_xs_combo_monitor_baseline.py), appends
one row to data/v2_live/monitor.csv and returns Telegram lines. It never places, cancels or sizes orders and never
changes schedules or parameters: any ALERT carries a proposed review for the operator, nothing more.

Status per indicator: OK / WARN (beyond the backtest p10 on the bad side) / ALERT (beyond p2.5) for indicators that
passed the E38 walk-forward false-alarm check; INFO (value + historical percentile) for those that did not
(ret_56d, drawdown, beta, leg correlation); NA when the live sample is still too short.
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from live import tracking

ROOT = Path(__file__).resolve().parents[3]
STATE_DIR = ROOT / "data" / "v2_live"
THRESH = Path(__file__).resolve().parents[1] / "results" / "xs_combo_monitor_thresholds.json"
DAY_MS = 86_400_000
MIN_DAYS = {"realized_carry": 28, "ret_56d": 56, "abs_beta_btc": 28}
REVIEW = {   # proposed operator reviews (never executed automatically)
    "ex_ante_carry": "the target book no longer earns funding; review whether the carry regime has ended",
    "adverse_share": "many target names pay funding; review the carry component before the next rebalance",
    "realized_carry": "realized funding below the backtest range; compare with the carry decay literature (R5)",
    "turnover": "unusual turnover; review the target change and its cost before trusting the next rebalance",
    "slippage_bp": "fills cost more than the backtest cost model; review execution before scaling",
    "max_share": "one position dominates the book; review stops/drift", "top5_share": "book concentrated",
    "abs_net_exposure": "book no longer dollar-neutral (drift or stop-outs); review before the next rebalance",
    "fail_rate": "orders failed at the last rebalance; book differs from target",
    "overdue_days": "rebalance overdue; check the LaunchAgent",
}


def load_thresholds() -> dict:
    return json.loads(THRESH.read_text())


def status(x, t: dict, validated: bool = True) -> str:
    if x is None or not np.isfinite(x):
        return "NA"
    if not validated:
        return "INFO"
    if t["bad"] == "low":
        return "ALERT" if x <= t["alert"] else "WARN" if x <= t["warn"] else "OK"
    return "ALERT" if x >= t["alert"] else "WARN" if x >= t["warn"] else "OK"


def funding_21d(sym: str, now_ms: int) -> float | None:
    d = tracking._get(f"{tracking.BINANCE}/fapi/v1/fundingRate?symbol={sym}&startTime={now_ms - 21 * DAY_MS}"
                      f"&endTime={now_ms}&limit=1000")
    if not isinstance(d, list):
        return None
    return float(sum(float(x["fundingRate"]) for x in d))


def daily_closes(sym: str, now_ms: int) -> list[float] | None:
    """Last 31 completed Binance daily closes (same basis as the backtest panel)."""
    d = tracking._get(f"{tracking.BINANCE}/fapi/v1/klines?symbol={sym}&interval=1d&endTime={now_ms - DAY_MS}&limit=31")
    if not isinstance(d, list) or len(d) < 31:
        return None
    return [float(x[4]) for x in d]


def avg_pair_corr(series: list[list[float]]) -> float | None:
    """Mean off-diagonal correlation of daily log returns; None if fewer than 3 names (same as E38 baseline)."""
    if len(series) < 3:
        return None
    r = np.diff(np.log(np.array(series)), axis=1)
    c = np.corrcoef(r)
    return float(c[np.triu_indices_from(c, 1)].mean())


def cluster(positions: list[dict], closes_fn, now_ms: int) -> dict:
    """Average pairwise 30-day return correlation inside the long leg and inside the short leg (INFO)."""
    legs = {"LONG": [], "SHORT": []}
    for p in positions:
        side = str(p.get("positionSide")).upper()
        if side in legs and float(p.get("positionAmt") or 0) != 0:
            c = closes_fn(p["symbol"].replace("-", ""), now_ms)
            if c:
                legs[side].append(c)
    return {"corr_long": avg_pair_corr(legs["LONG"]), "corr_short": avg_pair_corr(legs["SHORT"])}


def ex_ante(targets: dict, f21: dict) -> dict:
    """Carry the target book earns at trailing 21-day funding (annualised), same formula as E38."""
    have = {s: w for s, w in targets.items() if f21.get(s) is not None}
    if not have:
        return {"ex_ante_carry": None, "adverse_share": None, "funding_coverage": 0.0}
    carry = -sum(w * f21[s] for s, w in have.items()) * 365 / 21
    adverse = sum(1 for s, w in have.items() if np.sign(w) * f21[s] > 0) / len(have)
    return {"ex_ante_carry": carry, "adverse_share": adverse, "funding_coverage": len(have) / len(targets)}


def concentration(positions: list[dict]) -> dict:
    vals = []
    for p in positions:
        if float(p.get("positionAmt") or 0) == 0:
            continue
        v = abs(float(p.get("positionValue") or 0))
        vals.append(v if str(p.get("positionSide")).upper() == "LONG" else -v)
    g = sum(abs(v) for v in vals)
    if g <= 0:
        return {"max_share": None, "top5_share": None, "abs_net_exposure": None, "gross": 0.0}
    sh = sorted((abs(v) / g for v in vals), reverse=True)
    return {"max_share": sh[0], "top5_share": sum(sh[:5]), "abs_net_exposure": abs(sum(vals)) / g, "gross": g}


def turnover(prev: dict | None, cur: dict | None) -> float | None:
    if not prev or not cur:
        return None
    return float(sum(abs(cur.get(s, 0.0) - prev.get(s, 0.0)) for s in set(prev) | set(cur)))


def execution(ledger: Path, day: str | None) -> dict:
    """Slippage vs the plan price (notional/qty) and failure rate of the rebalance on `day` (YYYY-MM-DD)."""
    out = {"slippage_bp": None, "fail_rate": None, "orders": 0}
    if not day or not ledger.exists():
        return out
    tag = "xs" + day[2:4] + day[5:7] + day[8:10]
    slips, n, fail = [], 0, 0
    for line in ledger.read_text().splitlines():
        r = json.loads(line)
        if r.get("event") != "order" or not str(r.get("client_id", "")).startswith(tag):
            continue
        n += 1
        resp = r.get("resp") or {}
        o = (resp.get("data") or {}).get("order") or {}
        if resp.get("code") != 0:
            fail += 1
            continue
        ref = float(r["notional"]) / float(r["qty"]) if float(r.get("qty") or 0) else 0
        avg = float(o.get("avgPrice") or 0)
        if ref > 0 and avg > 0:
            sgn = 1 if r["side"] == "BUY" else -1
            slips.append(sgn * (avg / ref - 1) * 1e4)
    if n:
        out.update({"orders": n, "fail_rate": fail / n, "slippage_bp": float(np.mean(slips)) if slips else None})
    return out


def _series_stats(series: list[dict], btc_now: float | None) -> dict:
    rets = [x["ret"] for x in series if x.get("ret") is not None]
    out = {"live_days": len(rets), "drawdown": None, "ret_56d": None, "abs_beta_btc": None, "cum_ret": None}
    if not rets:
        return out
    eq = np.cumprod(1 + np.array(rets))
    out["cum_ret"] = float(eq[-1] - 1)
    out["drawdown"] = float(eq[-1] / max(1.0, eq.max()) - 1)
    if len(rets) >= MIN_DAYS["ret_56d"]:
        out["ret_56d"] = float(np.mean(rets[-56:]) * 365)
    bt = [(x["ret"], x["btc_ret"]) for x in series if x.get("ret") is not None and x.get("btc_ret") is not None]
    if len(bt) >= MIN_DAYS["abs_beta_btc"]:
        r, b = np.array(bt[-28:]).T
        out["abs_beta_btc"] = float(abs(np.cov(r, b)[0, 1] / np.var(b, ddof=1))) if np.var(b) > 0 else None
    return out


def realized_carry(tracking_csv: Path) -> dict:
    """Annualised Binance-rate shadow funding / gross over the last 28 days (same basis as the backtest)."""
    if not tracking_csv.exists():
        return {"realized_carry": None, "carry_days": 0.0, "venue_ratio": None}
    lines = tracking_csv.read_text().splitlines()
    head = lines[0].split(",")
    rows = [dict(zip(head, ln.split(","))) for ln in lines[1:] if ln]
    hours, acc, bx, bn = 0.0, 0.0, 0.0, 0.0
    for r in reversed(rows):
        if hours >= 28 * 24:
            break
        h, g = float(r["window_hours"]), float(r["gross"])
        if g > 0:
            acc += float(r["shadow_funding_binance"]) / g
        hours += h
        bx += float(r["shadow_funding_bingx"]); bn += float(r["shadow_funding_binance"])
    days = hours / 24
    out = {"carry_days": round(days, 1), "venue_ratio": (bx / bn) if bn else None, "realized_carry": None}
    if days >= MIN_DAYS["realized_carry"]:
        out["realized_carry"] = acc / days * 365
    return out


def run(positions: list[dict], prices: dict, book: float, state_dir: Path = STATE_DIR,
        now_ms: int | None = None, f21_fn=funding_21d, thresholds: dict | None = None, closes_fn=daily_closes) -> dict:
    now_ms = now_ms or int(time.time() * 1000)
    th = thresholds or load_thresholds()
    st_path = state_dir / "monitor_state.json"
    ms = json.loads(st_path.read_text()) if st_path.exists() else {}
    rb_state = json.loads((state_dir / "state.json").read_text()) if (state_dir / "state.json").exists() else {}
    tdir = state_dir / "targets"
    tfiles = sorted(tdir.glob("*.json")) if tdir.exists() else []
    cur = json.loads(tfiles[-1].read_text()) if tfiles else None
    prev = json.loads(tfiles[-2].read_text()) if len(tfiles) > 1 else None
    pos = [p for p in positions if float(p.get("positionAmt") or 0) != 0]

    # daily sleeve P&L: yesterday's book x price change + shadow funding booked since then
    snap = {f"{p['symbol']}:{str(p.get('positionSide')).upper()}":
            {"qty": abs(float(p["positionAmt"])), "px": float(p.get("markPrice") or p.get("avgPrice") or 0)} for p in pos}
    btc = prices.get("BTCUSDT")
    series = ms.get("series", [])
    ret = btc_ret = None
    if ms.get("snapshot") is not None:
        pnl = 0.0
        for k, v in ms["snapshot"].items():
            sym, side = k.split(":")
            px = prices.get(sym.replace("-", ""))
            if px:
                pnl += (1 if side == "LONG" else -1) * v["qty"] * (px - v["px"])
        fund = 0.0
        tcsv = state_dir / "tracking.csv"
        if tcsv.exists():
            last = tcsv.read_text().splitlines()[-1].split(",")
            if datetime.fromtimestamp(now_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d") == last[0][:10]:
                fund = float(last[4])                      # shadow_funding_bingx of today's run
        ret = (pnl + fund) / book if book else None
        if btc and ms.get("btc"):
            btc_ret = btc / ms["btc"] - 1
    day = datetime.fromtimestamp(now_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
    series = [x for x in series if x["date"] != day] + [{"date": day, "ret": ret, "btc_ret": btc_ret}]

    v = {}
    v.update(ex_ante(cur or {}, {s: f21_fn(s, now_ms) for s in (cur or {})}))
    v.update(concentration(pos))
    v.update(cluster(pos, closes_fn, now_ms))
    v["turnover"] = turnover(prev, cur)
    v.update(execution(state_dir / "orders.jsonl", rb_state.get("last_rebalance")))
    v.update(realized_carry(state_dir / "tracking.csv"))
    v.update(_series_stats(series, btc))
    last_rb = rb_state.get("last_rebalance")
    v["overdue_days"] = ((now_ms - datetime.fromisoformat(last_rb).replace(tzinfo=timezone.utc).timestamp() * 1000)
                         / DAY_MS) if last_rb else None

    stat = {}
    for k in ("ex_ante_carry", "adverse_share", "realized_carry", "turnover", "slippage_bp", "max_share",
              "top5_share", "abs_net_exposure", "ret_56d", "drawdown", "abs_beta_btc", "corr_long", "corr_short"):
        t = th.get(k)
        if t is None:
            stat[k] = "NA"
            continue
        stat[k] = status(v.get(k), t, t.get("validated_alarm", True))
    fr = v.get("fail_rate")
    stat["fail_rate"] = "NA" if fr is None else ("WARN" if fr > 0 else "OK")
    od = v.get("overdue_days")
    stat["overdue_days"] = "NA" if od is None else ("ALERT" if od >= 9 else "WARN" if od >= 8 else "OK")

    row = {"date": datetime.fromtimestamp(now_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M"),
           **{k: (round(x, 6) if isinstance(x, float) else x) for k, x in v.items()},
           **{f"s_{k}": s for k, s in stat.items()}}
    csv = state_dir / "monitor.csv"
    new = not csv.exists()
    with open(csv, "a") as fh:
        if new:
            fh.write(",".join(row) + "\n")
        fh.write(",".join("" if x is None else str(x) for x in row.values()) + "\n")
    ms.update({"snapshot": snap, "btc": btc, "series": series[-400:], "updated": row["date"]})
    st_path.write_text(json.dumps(ms, indent=1))

    def f(k, scale=1.0, fmt="{:+.1%}"):
        x = v.get(k)
        return "n/a" if x is None else fmt.format(x * scale)
    bad = [k for k, s in stat.items() if s in ("WARN", "ALERT")]
    lines = [
        "R5 monitor (observational, no automatic action):",
        f"carry ex-ante {f('ex_ante_carry')}/yr [{stat['ex_ante_carry']}] (backtest median "
        f"{th['ex_ante_carry']['median']:+.1%}); adverse names {f('adverse_share', fmt='{:.0%}')} [{stat['adverse_share']}]",
        f"realized carry {f('realized_carry')}/yr [{stat['realized_carry']}] ({v['carry_days']:.0f}/28 d); "
        f"BingX/Binance funding {f('venue_ratio', fmt='{:.2f}')}",
        f"concentration max {f('max_share', fmt='{:.1%}')} top5 {f('top5_share', fmt='{:.1%}')} "
        f"net {f('abs_net_exposure', fmt='{:.1%}')} [{stat['max_share']}/{stat['top5_share']}/{stat['abs_net_exposure']}]",
        f"last rebalance: slippage {f('slippage_bp', fmt='{:+.1f} bp')} [{stat['slippage_bp']}], "
        f"failed {f('fail_rate', fmt='{:.0%}')}, turnover {f('turnover', fmt='{:.2f}')} [{stat['turnover']}]",
        f"leg correlation 30d long {f('corr_long', fmt='{:.2f}')} short {f('corr_short', fmt='{:.2f}')} "
        f"(backtest median {th.get('corr_long', {}).get('median', float('nan')):.2f}/"
        f"{th.get('corr_short', {}).get('median', float('nan')):.2f}) [INFO]",
        f"sleeve since monitor start {f('cum_ret')} (DD {f('drawdown')}, {v['live_days']} d) [INFO]",
    ]
    for k in bad:
        lines.append(f"{stat[k]} {k}: {REVIEW.get(k, 'review')}")
    return {"values": v, "status": stat, "lines": lines, "row": row}
