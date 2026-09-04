from copy import deepcopy

from infrastructure.observability.terminal_evidence_extractor import extract_terminal_evidence


def identity():
    return {
        "record_id": "record-1",
        "position_key": "BTCUSDT:LONG:100",
        "observer_run_id": "run-1",
        "symbol": "BTCUSDT",
        "side": "LONG",
        "entry_price": 100.0,
        "exchange_leverage": 5.0,
        "lifecycle_state": "OPEN",
    }


def complete_order():
    return {
        "orderId": "exit-7",
        "symbol": "BTC-USDT",
        "positionSide": "LONG",
        "type": "STOP_MARKET",
        "status": "FILLED",
        "avgPrice": "101.25",
        "executedQty": "2.5",
        "realizedProfit": "3.125",
        "commission": "0.19",
        "updateTime": 1788552000123,
        "stopPrice": "101.30",
        "workingType": "MARK_PRICE",
    }


def test_complete_authoritative_terminal_evidence_is_admitted():
    result = extract_terminal_evidence(complete_order(), identity())
    assert result["eligible"] is True
    assert result["terminal_evidence_complete"] is True
    assert result["missing_fields"] == []
    assert result["terminal_order_id"] == "exit-7"
    assert result["fill_price"] == 101.25
    assert result["fill_quantity"] == 2.5
    assert result["realized_pnl"] == 3.125
    assert result["fees"] == 0.19
    assert result["fill_time_utc"] == "2026-09-04T20:00:00.123000+00:00"
    assert result["trigger_price"] == 101.30
    assert result["trigger_basis"] == "MARK_PRICE"


def test_missing_or_malformed_economics_remain_null_and_incomplete():
    order = complete_order()
    order.update({"avgPrice": "bad", "executedQty": "", "commission": None, "updateTime": -1})
    result = extract_terminal_evidence(order, identity())
    assert result["eligible"] is True
    assert result["terminal_evidence_complete"] is False
    assert result["fill_price"] is None
    assert result["fill_quantity"] is None
    assert result["fees"] is None
    assert result["fill_time_utc"] is None
    assert result["missing_fields"] == ["fees", "fill_price", "fill_quantity", "fill_time_utc"]


def test_unknown_order_or_ambiguous_side_fails_closed():
    order = complete_order()
    order["orderId"] = "UNKNOWN"
    assert extract_terminal_evidence(order, identity())["eligible"] is False
    order = complete_order()
    order.pop("positionSide")
    assert extract_terminal_evidence(order, identity())["exclusion_reason"] == (
        "explicit terminal position side unavailable"
    )


def test_symbol_side_and_lifecycle_mismatch_fail_closed():
    order = complete_order()
    order["symbol"] = "ETHUSDT"
    assert extract_terminal_evidence(order, identity())["eligible"] is False
    order = complete_order()
    order["positionSide"] = "SHORT"
    assert extract_terminal_evidence(order, identity())["eligible"] is False
    closed = identity()
    closed["lifecycle_state"] = "CLOSURE_OBSERVED"
    assert extract_terminal_evidence(complete_order(), closed)["eligible"] is False


def test_extraction_does_not_mutate_order_or_identity():
    order = complete_order()
    position = identity()
    order_before = deepcopy(order)
    identity_before = deepcopy(position)
    extract_terminal_evidence(order, position)
    assert order == order_before
    assert position == identity_before
