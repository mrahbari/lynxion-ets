#!/usr/bin/env python3
"""Read-only BingX VST audit for stop-loss and take-profit coverage."""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def normalize_symbol(symbol: Any) -> str:
    raw = getattr(symbol, "value", symbol)
    return str(raw or "").upper().replace("-", "").replace("/", "").replace("_", "")


def protection_coverage(positions: Iterable[Any], pending_orders: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    """Match current positions to pending exchange-side SL and TP orders."""
    pending_by_symbol = defaultdict(list)
    for order in pending_orders:
        pending_by_symbol[normalize_symbol(order.get("symbol"))].append(
            str(order.get("type") or order.get("orderType") or "").upper()
        )

    open_symbols = [normalize_symbol(getattr(position, "symbol", "")) for position in positions]
    missing_stop_loss = []
    missing_take_profit = []
    for symbol in open_symbols:
        types = pending_by_symbol[symbol]
        if not any("STOP" in order_type for order_type in types):
            missing_stop_loss.append(symbol)
        if not any("TAKE_PROFIT" in order_type or order_type == "TP" for order_type in types):
            missing_take_profit.append(symbol)

    return {
        "open_position_count": len(open_symbols),
        "pending_order_count": sum(len(types) for types in pending_by_symbol.values()),
        "pending_order_types": dict(Counter(order_type for types in pending_by_symbol.values() for order_type in types)),
        "positions_missing_stop_loss": sorted(missing_stop_loss),
        "positions_missing_take_profit": sorted(missing_take_profit),
    }


def main() -> None:
    from bootstrap.settings.loaders import load_settings
    from infrastructure.brokers.adapters.bingx_adapter import BingXBrokerAdapter

    broker_settings = load_settings().broker
    if not getattr(broker_settings, "bingx_testnet", False):
        raise SystemExit("Refusing audit: BingX VST/testnet is not enabled.")
    adapter = BingXBrokerAdapter({
        "api_key": broker_settings.bingx_api_key,
        "secret_key": broker_settings.bingx_secret_key,
        "testnet": broker_settings.bingx_testnet,
        "passphrase": getattr(broker_settings, "bingx_passphrase", ""),
    })
    print(json.dumps(protection_coverage(adapter.get_all_positions(), adapter.get_pending_orders()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
