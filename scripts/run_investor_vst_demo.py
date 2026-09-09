#!/usr/bin/env python3
"""Place exactly one small, protected investor-demo order on BingX VST."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from decimal import Decimal, ROUND_DOWN
from pathlib import Path
from typing import Any, Dict, Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

MAX_NOTIONAL = Decimal("20")
SYMBOL = "DOGEUSDT"
DEMO_PURPOSE = "INVESTOR_TECHNICAL_DEMO"
DEMO_REGISTRY = PROJECT_ROOT / "data" / "research" / "investor_release" / "demo_order_registry.jsonl"


def normalize_symbol(value: Any) -> str:
    raw = getattr(value, "value", value)
    return str(raw or "").upper().replace("-", "").replace("/", "").replace("_", "")


def validate_preflight(settings: Any, positions: Iterable[Any], coverage: Dict[str, Any]) -> None:
    broker = settings.broker
    if getattr(broker, "paper_trading", True):
        raise RuntimeError("refusing: paper_trading must be false for the VST exchange demo")
    if not getattr(broker, "bingx_testnet", False):
        raise RuntimeError("refusing: BingX VST/testnet is not enabled")
    if not getattr(broker, "bingx_order_placement_enabled", False):
        raise RuntimeError("refusing: BingX order placement is disabled")
    enabled = [str(item).lower() for item in getattr(broker, "enabled_brokers", [])]
    if enabled != ["bingx"]:
        raise RuntimeError(f"refusing: enabled_brokers must be exactly ['bingx'], got {enabled}")
    if coverage["positions_missing_stop_loss"] or coverage["positions_missing_take_profit"]:
        raise RuntimeError("refusing: an existing VST position lacks exchange-side SL/TP")
    if any(normalize_symbol(getattr(position, "symbol", "")) == SYMBOL for position in positions):
        raise RuntimeError(f"refusing: {SYMBOL} already has an open position")


def sized_quantity(price: Decimal, quantity_precision: int) -> Decimal:
    if price <= 0:
        raise ValueError("price must be positive")
    quantum = Decimal(1).scaleb(-quantity_precision)
    quantity = (MAX_NOTIONAL / price).quantize(quantum, rounding=ROUND_DOWN)
    if quantity <= 0 or quantity * price > MAX_NOTIONAL:
        raise ValueError("unable to create a positive quantity within the notional cap")
    return quantity


def record_demo_identity(client_order_id: str, order_id: str | None = None) -> None:
    """Durably identify demo activity before send so it cannot enter edge evidence."""
    DEMO_REGISTRY.parent.mkdir(parents=True, exist_ok=True)
    record = {"purpose": DEMO_PURPOSE, "client_order_id": client_order_id}
    if order_id is not None:
        record["order_id"] = str(order_id)
    with DEMO_REGISTRY.open("a", encoding="utf-8") as target:
        target.write(json.dumps(record, sort_keys=True) + "\n")
        target.flush()
        os.fsync(target.fileno())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--enable-vst-order", action="store_true")
    args = parser.parse_args()
    if not args.enable_vst_order:
        raise SystemExit("Refusing order: pass --enable-vst-order explicitly.")

    from bootstrap.settings.loaders import load_settings
    from domain.entities import Order, OrderSide, PositionSide
    from domain.value_objects import Money, Symbol
    from infrastructure.brokers.adapters.bingx_adapter import BingXBrokerAdapter
    from scripts.audit_vst_protection import protection_coverage

    settings = load_settings()
    broker = settings.broker
    adapter = BingXBrokerAdapter({
        "api_key": broker.bingx_api_key,
        "secret_key": broker.bingx_secret_key,
        "testnet": broker.bingx_testnet,
        "passphrase": getattr(broker, "bingx_passphrase", ""),
    })
    positions = adapter.get_all_positions()
    coverage = protection_coverage(positions, adapter.get_pending_orders())
    validate_preflight(settings, positions, coverage)

    formatted = adapter._format_symbol(SYMBOL)
    quote = adapter._broker._make_request(
        "GET", "/openApi/swap/v2/quote/price", params={"symbol": formatted}, signed=False
    )
    if quote.get("code") != 0:
        raise RuntimeError(f"quote failed: {quote.get('msg', 'unknown error')}")
    price = Decimal(str(quote["data"]["price"]))
    precision = adapter._broker._get_contract_precision(formatted)
    quantity = sized_quantity(price, int(precision["quantityPrecision"]))
    leverage = Decimal(str(settings.risk.max_leverage))
    stop_loss = price * Decimal("0.97")
    take_profit = price * Decimal("1.06")
    client_order_id = "INVESTORTECHDEMO" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    order = Order(
        symbol=Symbol(SYMBOL), side=OrderSide.BUY, position_side=PositionSide.LONG,
        quantity=quantity, price=Money(price, "USDT"), order_type="MARKET",
        stop_loss_price=Money(stop_loss, "USDT"),
        take_profit_price=Money(take_profit, "USDT"),
        requested_leverage=leverage, strategy_name=DEMO_PURPOSE,
        client_order_id=client_order_id,
        timestamp=datetime.now(timezone.utc),
    )
    record_demo_identity(client_order_id)
    order_id = adapter.place_order(order)
    record_demo_identity(client_order_id, order_id)

    post_positions = adapter.get_all_positions()
    post_orders = adapter.get_pending_orders(Symbol(SYMBOL))
    post_coverage = protection_coverage(
        [p for p in post_positions if normalize_symbol(p.symbol) == SYMBOL], post_orders
    )
    if post_coverage["open_position_count"] != 1:
        raise RuntimeError(f"postflight failed: {SYMBOL} position not visible on VST")
    if post_coverage["positions_missing_stop_loss"] or post_coverage["positions_missing_take_profit"]:
        raise RuntimeError(f"postflight failed: {SYMBOL} lacks exchange-side protection")
    print(json.dumps({
        "venue": "BingX VST", "symbol": SYMBOL, "side": "BUY", "position_side": "LONG",
        "order_id": str(order_id), "quantity": str(quantity), "reference_price": str(price),
        "notional_cap_usdt": str(MAX_NOTIONAL), "requested_leverage": str(leverage),
        "margin_mode": "ISOLATED", "stop_loss_pct": "3", "take_profit_pct": "6",
        "postflight": post_coverage,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
