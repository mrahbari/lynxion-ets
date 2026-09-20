#!/usr/bin/env python3
"""Controlled BingX VST LIMIT protection verification with scoped cleanup."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from decimal import Decimal, ROUND_DOWN
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

SYMBOL = "DOGEUSDT"
MAX_NOTIONAL = Decimal("20")
EVIDENCE_PATH = PROJECT_ROOT / "data" / "observability" / "vst_limit_protection_verification.json"


def normalized_symbol(value: Any) -> str:
    raw = getattr(value, "value", value)
    return str(raw or "").upper().replace("-", "").replace("/", "").replace("_", "")


def quantize_down(value: Decimal, precision: int) -> Decimal:
    return value.quantize(Decimal(1).scaleb(-precision), rounding=ROUND_DOWN)


def response_order_data(response: dict[str, Any]) -> dict[str, Any]:
    data = response.get("data")
    if not isinstance(data, dict):
        return {}
    nested = data.get("order")
    return nested if isinstance(nested, dict) else data


def attached_order(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, dict) else {}
    return {}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--enable-controlled-vst-limit", action="store_true")
    args = parser.parse_args()
    if not args.enable_controlled_vst_limit:
        raise SystemExit("Refusing order: pass --enable-controlled-vst-limit explicitly.")

    from bootstrap.settings.loaders import load_settings
    from domain.entities import Order, OrderSide, PositionSide
    from domain.value_objects import Money, Symbol
    from infrastructure.brokers.adapters.bingx_adapter import BingXBrokerAdapter

    settings = load_settings()
    broker_settings = settings.broker
    if getattr(broker_settings, "paper_trading", True):
        raise RuntimeError("refusing: paper_trading must be false for exchange-side VST verification")
    if not getattr(broker_settings, "bingx_testnet", False):
        raise RuntimeError("refusing: BingX VST/testnet is not enabled")
    if not getattr(broker_settings, "bingx_order_placement_enabled", False):
        raise RuntimeError("refusing: BingX order placement is disabled")
    enabled = [str(item).lower() for item in getattr(broker_settings, "enabled_brokers", [])]
    if enabled != ["bingx"]:
        raise RuntimeError(f"refusing: enabled_brokers must be exactly ['bingx'], got {enabled}")

    adapter = BingXBrokerAdapter({
        "api_key": broker_settings.bingx_api_key,
        "secret_key": broker_settings.bingx_secret_key,
        "testnet": broker_settings.bingx_testnet,
        "passphrase": getattr(broker_settings, "bingx_passphrase", ""),
    })
    formatted_symbol = adapter._format_symbol(SYMBOL)
    pre_positions = adapter.get_all_positions()
    pre_orders = adapter.get_pending_orders(Symbol(SYMBOL))
    if pre_positions or pre_orders:
        raise RuntimeError("refusing: controlled VST account/symbol is not clean")

    quote = adapter._broker._make_request(
        "GET", "/openApi/swap/v2/quote/price", params={"symbol": formatted_symbol}, signed=False
    )
    if quote.get("code") != 0:
        raise RuntimeError(f"quote failed: {quote.get('msg', 'unknown error')}")
    market_price = Decimal(str(quote["data"]["price"]))
    precision = adapter._broker._get_contract_precision(formatted_symbol)
    price_precision = int(precision["pricePrecision"])
    quantity_precision = int(precision["quantityPrecision"])
    limit_price = quantize_down(market_price * Decimal("0.80"), price_precision)
    stop_loss = quantize_down(market_price * Decimal("0.70"), price_precision)
    take_profit = quantize_down(market_price * Decimal("1.20"), price_precision)
    quantity = quantize_down(MAX_NOTIONAL / limit_price, quantity_precision)
    if quantity <= 0 or quantity * limit_price > MAX_NOTIONAL:
        raise RuntimeError("unable to size controlled order within notional cap")

    client_order_id = "VSTLIMIT" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    order = Order(
        symbol=Symbol(SYMBOL),
        side=OrderSide.BUY,
        position_side=PositionSide.LONG,
        quantity=quantity,
        price=Money(limit_price, "USDT"),
        order_type="LIMIT",
        time_in_force="POST_ONLY",
        stop_loss_price=Money(stop_loss, "USDT"),
        take_profit_price=Money(take_profit, "USDT"),
        requested_leverage=Decimal(str(settings.risk.max_leverage)),
        strategy_name="CONTROLLED_VST_LIMIT_PROTECTION_VERIFY",
        client_order_id=client_order_id,
        timestamp=datetime.now(timezone.utc),
    )

    evidence = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "venue": "BingX VST",
        "symbol": SYMBOL,
        "client_order_id": client_order_id,
        "reference_price": str(market_price),
        "limit_price": str(limit_price),
        "stop_loss": str(stop_loss),
        "take_profit": str(take_profit),
        "quantity": str(quantity),
        "notional": str(quantity * limit_price),
        "status": "STARTED",
    }
    order_id = None
    try:
        order_id = adapter.place_order(order)
        evidence["returned_order_id"] = str(order_id)
        readback = adapter._broker._make_request(
            "GET",
            "/openApi/swap/v2/trade/order",
            params={"symbol": formatted_symbol, "clientOrderId": client_order_id},
            signed=True,
        )
        evidence["readback_code"] = readback.get("code")
        data = response_order_data(readback)
        evidence["readback"] = {
            key: data.get(key)
            for key in (
                "symbol", "side", "positionSide", "type", "origQty", "price", "status",
                "clientOrderId", "stopLoss", "takeProfit", "stopLossPrice", "takeProfitPrice",
            )
            if key in data
        }
        if readback.get("code") != 0:
            raise RuntimeError(f"order readback failed: {readback.get('msg', 'unknown error')}")
        if normalized_symbol(data.get("symbol")) != SYMBOL:
            raise RuntimeError("readback symbol mismatch")
        if str(data.get("clientOrderId") or "").lower() != client_order_id.lower():
            raise RuntimeError("readback client identity mismatch")
        if str(data.get("side") or "").upper() != "BUY":
            raise RuntimeError("readback side mismatch")
        if str(data.get("positionSide") or "").upper() != "LONG":
            raise RuntimeError("readback position side mismatch")
        if str(data.get("type") or "").upper() != "LIMIT":
            raise RuntimeError("readback type mismatch")
        readback_stop_loss = attached_order(data.get("stopLoss"))
        readback_take_profit = attached_order(data.get("takeProfit"))
        evidence["readback_stop_loss"] = readback_stop_loss
        evidence["readback_take_profit"] = readback_take_profit
        if str(readback_stop_loss.get("type") or "").upper() not in {"STOP_MARKET", "STOP"}:
            raise RuntimeError("readback stop loss is missing or malformed")
        if str(readback_take_profit.get("type") or "").upper() not in {
            "TAKE_PROFIT_MARKET", "TAKE_PROFIT",
        }:
            raise RuntimeError("readback take profit is missing or malformed")
        if Decimal(str(readback_stop_loss.get("stopPrice"))) != stop_loss:
            raise RuntimeError("readback stop-loss trigger mismatch")
        if Decimal(str(readback_take_profit.get("stopPrice"))) != take_profit:
            raise RuntimeError("readback take-profit trigger mismatch")
        evidence["status"] = "READBACK_ACCEPTED"
    finally:
        cancel_identity = str(order_id or client_order_id)
        evidence["cancel_identity"] = cancel_identity
        evidence["cancelled"] = adapter.cancel_order(cancel_identity, Symbol(SYMBOL))
        remaining_orders = adapter.get_pending_orders(Symbol(SYMBOL))
        remaining_positions = [
            position for position in adapter.get_all_positions()
            if normalized_symbol(position.symbol) == SYMBOL
        ]
        evidence["remaining_order_count"] = len(remaining_orders)
        evidence["remaining_position_count"] = len(remaining_positions)
        if evidence["cancelled"] and not remaining_orders and not remaining_positions:
            evidence["cleanup"] = "PASS"
        else:
            evidence["cleanup"] = "FAIL"
        EVIDENCE_PATH.parent.mkdir(parents=True, exist_ok=True)
        EVIDENCE_PATH.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if evidence["cleanup"] != "PASS":
        raise RuntimeError("controlled VST cleanup failed")
    print(json.dumps(evidence, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
