"""XS-COMBO-V1 live-vs-model tracking with a SHADOW FUNDING ledger.

Why: the strategy's holdout edge is funding carry (+39.8%/yr funding, ~0 price). BingX VST does not settle
funding (2026-11-23: zero FUNDING_FEE income entries with 39 positions held across settlements), so VST
equity alone can never show the edge. Each daily run therefore books, for the sleeve's open positions,
the funding they WOULD have received/paid at the real BingX funding rates (public market data), and the
same with Binance rates (the backtest's source) for parity.

Assumption (documented): positions are taken as held over the whole window (true except on rebalance
day and after a stop-out); notional = |qty| x current mark.

Output: data/v2_live/tracking.csv (one row per run); state key "tracking_until" (ms).
"""
from __future__ import annotations

import json
import time
import urllib.request
from datetime import datetime, timezone

BINGX_PUBLIC = "https://open-api.bingx.com"
BINANCE = "https://fapi.binance.com"


def _get(url: str):
    for i in range(3):
        try:
            with urllib.request.urlopen(url, timeout=20) as r:
                return json.loads(r.read())
        except Exception:  # noqa: BLE001
            time.sleep(1 + i)
    return None


def bingx_funding(sym_dash: str, start_ms: int, end_ms: int) -> list[float]:
    d = _get(f"{BINGX_PUBLIC}/openApi/swap/v2/quote/fundingRate?symbol={sym_dash}"
             f"&startTime={start_ms}&endTime={end_ms}&limit=100")
    rows = (d or {}).get("data") or []
    return [float(x["fundingRate"]) for x in rows if start_ms < int(x["fundingTime"]) <= end_ms]


def binance_funding(sym: str, start_ms: int, end_ms: int) -> list[float] | None:
    d = _get(f"{BINANCE}/fapi/v1/fundingRate?symbol={sym}&startTime={start_ms + 1}&endTime={end_ms}&limit=100")
    if not isinstance(d, list):
        return None
    return [float(x["fundingRate"]) for x in d if start_ms < int(x["fundingTime"]) <= end_ms]


def shadow_funding(positions: list[dict], start_ms: int, end_ms: int) -> dict:
    """Funding cash flow the positions would have had: long pays a positive rate, short receives it."""
    bx = bn = 0.0
    bn_missing = 0
    per = {}
    for p in positions:
        amt = float(p.get("positionAmt") or 0)
        if amt == 0:
            continue
        side = str(p.get("positionSide") or ("LONG" if amt > 0 else "SHORT")).upper()
        sgn = 1.0 if side == "LONG" else -1.0
        notional = abs(amt) * float(p.get("markPrice") or p.get("avgPrice") or 0)
        sym_dash = p["symbol"]
        r_bx = bingx_funding(sym_dash, start_ms, end_ms)
        f_bx = -sgn * notional * sum(r_bx)
        bx += f_bx
        r_bn = binance_funding(sym_dash.replace("-", ""), start_ms, end_ms)
        if r_bn is None:
            bn_missing += 1
        else:
            bn += -sgn * notional * sum(r_bn)
        per[f"{sym_dash}:{side}"] = round(f_bx, 4)
        time.sleep(0.05)
    return {"bingx": round(bx, 4), "binance": round(bn, 4), "binance_missing": bn_missing, "per_position": per}


def track(positions: list[dict], state: dict, csv_path, now_ms: int | None = None) -> dict:
    """Book shadow funding since the last run and append a tracking row. Mutates state."""
    now_ms = now_ms or int(time.time() * 1000)
    start_ms = int(state.get("tracking_until") or state.get("tracking_start_ms") or now_ms - 86_400_000)
    sf = shadow_funding(positions, start_ms, now_ms)
    cum = round(float(state.get("shadow_funding_cum", 0.0)) + sf["bingx"], 4)
    state["tracking_until"], state["shadow_funding_cum"] = now_ms, cum
    open_pos = [p for p in positions if float(p.get("positionAmt") or 0) != 0]
    unreal = sum(float(p.get("unrealizedProfit") or 0) for p in open_pos)
    row = {"date": datetime.fromtimestamp(now_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M"),
           "window_hours": round((now_ms - start_ms) / 3.6e6, 1), "positions": len(open_pos),
           "gross": round(sum(abs(float(p.get("positionValue") or 0)) for p in open_pos), 2),
           "shadow_funding_bingx": sf["bingx"], "shadow_funding_binance": sf["binance"],
           "binance_missing": sf["binance_missing"], "shadow_funding_cum": cum,
           "unrealized": round(unreal, 2), "unrealized_plus_shadow_funding": round(unreal + cum, 2)}
    new = not csv_path.exists()
    with open(csv_path, "a") as fh:
        if new:
            fh.write(",".join(row) + "\n")
        fh.write(",".join(str(v) for v in row.values()) + "\n")
    return row
