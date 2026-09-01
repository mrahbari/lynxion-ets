#!/usr/bin/env python3
"""Read-only forensic audit of recent completed BingX VST positions."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _f(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def reconstruct_completed(orders: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for order in orders:
        if str(order.get("status", "")).upper() != "FILLED":
            continue
        position_id = str(order.get("positionID") or "")
        if position_id and position_id != "0":
            grouped[position_id].append(order)

    completed = []
    for position_id, rows in grouped.items():
        entries = [row for row in rows if row.get("reduceOnly") not in (True, "true", "TRUE")]
        exits = [row for row in rows if row.get("reduceOnly") in (True, "true", "TRUE")]
        if not entries or not exits:
            continue
        entry = min(entries, key=lambda row: int(row.get("time") or 0))
        exit_order = max(exits, key=lambda row: int(row.get("updateTime") or row.get("time") or 0))
        entry_ms = int(entry.get("time") or 0)
        exit_ms = int(exit_order.get("updateTime") or exit_order.get("time") or 0)
        if not entry_ms or exit_ms < entry_ms:
            continue
        reported_leverage = _f(entry.get("leverage"))
        completed.append({
            "position_id": position_id,
            "symbol": str(entry.get("symbol") or ""),
            "side": str(entry.get("positionSide") or "").upper(),
            "leverage": reported_leverage or 1.0,
            "historical_leverage_reported": bool(reported_leverage),
            "quantity": _f(entry.get("executedQty") or entry.get("origQty")),
            "entry_price": _f(entry.get("avgPrice")),
            "exit_price": _f(exit_order.get("avgPrice")),
            "entry_ms": entry_ms,
            "exit_ms": exit_ms,
            "exit_type": str(exit_order.get("type") or exit_order.get("orderType") or "").upper(),
            "profit_usdt": sum(_f(row.get("profit")) for row in exits),
            "fees_usdt": sum(_f(row.get("commission")) for row in entries + exits),
        })
    return sorted(completed, key=lambda row: row["exit_ms"], reverse=True)


def excursion(trade: dict[str, Any], candles: list[dict[str, Any]]) -> dict[str, float]:
    entry = trade["entry_price"]
    leverage = trade["leverage"]
    highs = [_f(row.get("high")) for row in candles]
    lows = [_f(row.get("low")) for row in candles]
    if not entry or not highs or not lows:
        return {"mfe_roe_pct": 0.0, "mae_roe_pct": 0.0}
    if trade["side"] == "LONG":
        favorable = (max(highs) - entry) / entry
        adverse = (min(lows) - entry) / entry
    else:
        favorable = (entry - min(lows)) / entry
        adverse = (entry - max(highs)) / entry
    return {"mfe_roe_pct": favorable * leverage * 100, "mae_roe_pct": adverse * leverage * 100}


def summarize(trades: list[dict[str, Any]]) -> dict[str, Any]:
    for trade in trades:
        margin = trade["entry_price"] * trade["quantity"] / trade["leverage"] if trade["leverage"] else 0
        trade["net_pnl_usdt"] = trade["profit_usdt"] + trade["fees_usdt"]
        trade["net_roe_pct"] = trade["net_pnl_usdt"] / margin * 100 if margin else 0
        trade["giveback_roe_pct"] = trade["mfe_roe_pct"] - trade["net_roe_pct"]
        sensitivity_factor = 10.0 / trade["leverage"]
        trade["mfe_roe_10x_pct"] = trade["mfe_roe_pct"] * sensitivity_factor
        trade["mae_roe_10x_pct"] = trade["mae_roe_pct"] * sensitivity_factor
        trade["net_roe_10x_pct"] = trade["net_roe_pct"] * sensitivity_factor
        trade["giveback_roe_10x_pct"] = (
            trade["mfe_roe_10x_pct"] - trade["net_roe_10x_pct"]
        )
        trade["duration_minutes"] = (trade["exit_ms"] - trade["entry_ms"]) / 60000
        trade["entry_time"] = datetime.fromtimestamp(trade["entry_ms"] / 1000, timezone.utc).isoformat()
        trade["exit_time"] = datetime.fromtimestamp(trade["exit_ms"] / 1000, timezone.utc).isoformat()
        trade.pop("position_id", None)
        trade.pop("entry_ms", None)
        trade.pop("exit_ms", None)
    return {
        "sample_size": len(trades),
        "account_environment": "BingX VST",
        "candle_resolution": "1m; MFE/MAE are candle-extreme estimates",
        "configured_reference": {
            "breakeven_trigger_roe_pct": 6.0,
            "trailing_trigger_roe_pct": 10.0,
            "trail_distance_price_pct": 0.5,
            "fee_buffer_price_pct": 0.35,
        },
        "counts": {
            "historical_leverage_missing": sum(not t["historical_leverage_reported"] for t in trades),
            "net_positive": sum(t["net_roe_10x_pct"] > 0 for t in trades),
            "near_breakeven_2_to_5pct_roe_at_10x": sum(2 <= t["net_roe_10x_pct"] <= 5 for t in trades),
            "mfe_ge_10pct_roe_at_10x": sum(t["mfe_roe_10x_pct"] >= 10 for t in trades),
            "mfe_ge_12pct_roe_at_10x": sum(t["mfe_roe_10x_pct"] >= 12 for t in trades),
            "mfe_ge_10_exit_below_5pct_roe_at_10x": sum(
                t["mfe_roe_10x_pct"] >= 10 and t["net_roe_10x_pct"] < 5 for t in trades
            ),
            "stop_market_exits": sum(t["exit_type"] == "STOP_MARKET" for t in trades),
            "take_profit_market_exits": sum(t["exit_type"] == "TAKE_PROFIT_MARKET" for t in trades),
        },
        "trades": trades,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    from bootstrap.settings.loaders import load_settings
    from infrastructure.brokers.adapters.bingx_adapter import BingXBrokerAdapter

    settings = load_settings()
    broker = settings.broker
    adapter = BingXBrokerAdapter({
        "api_key": broker.bingx_api_key,
        "secret_key": broker.bingx_secret_key,
        "passphrase": broker.bingx_passphrase,
    })._broker
    response = adapter._make_request(
        "GET", "/openApi/swap/v2/trade/allOrders",
        data={"marginCoin": "VST", "limit": 500}, signed=True,
    )
    if response.get("code") != 0:
        raise RuntimeError(f"BingX history request failed: code={response.get('code')}")
    orders = (response.get("data") or {}).get("orders", [])
    trades = reconstruct_completed(orders)[: args.limit]
    if len(trades) < args.limit:
        raise RuntimeError(f"Only {len(trades)} completed positions available; need {args.limit}")

    for trade in trades:
        candle_response = adapter._make_request(
            "GET", "/openApi/swap/v3/quote/klines",
            params={
                "symbol": trade["symbol"], "interval": "1m", "limit": 1440,
                "startTime": trade["entry_ms"] - 60_000, "endTime": trade["exit_ms"] + 60_000,
            }, signed=False,
        )
        candles = candle_response.get("data") if candle_response.get("code") == 0 else []
        trade.update(excursion(trade, candles or []))

    report = summarize(trades)
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(target), **report["counts"]}, sort_keys=True))


if __name__ == "__main__":
    main()
