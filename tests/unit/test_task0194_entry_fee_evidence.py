from copy import deepcopy

from infrastructure.observability.entry_fee_evidence_extractor import extract_entry_fee_evidence


def identity(**updates):
    value = {
        "symbol": "BTCUSDT", "side": "LONG", "entry_price": 100.0, "quantity": 2.0,
        "exchange_position_id": "p1", "first_observed_utc": "2026-09-07T00:01:00+00:00",
    }
    value.update(updates)
    return value


def order(**updates):
    value = {
        "orderId": "e1", "positionID": "p1", "symbol": "BTC-USDT",
        "positionSide": "LONG", "status": "FILLED", "reduceOnly": False,
        "avgPrice": "100", "executedQty": "2", "commission": "-0.10",
        "time": 1788739230000,
    }
    value.update(updates)
    return value


def test_exact_position_link_admits_signed_commission_and_rate():
    result = extract_entry_fee_evidence([order()], identity())
    assert result["eligible"] is True
    assert result["match_mode"] == "POSITION_ID"
    assert result["signed_entry_commission"] == -0.10
    assert result["entry_fee_price_pct"] == 0.05


def test_unique_attribute_fallback_is_explicit():
    result = extract_entry_fee_evidence([order()], identity(exchange_position_id=None))
    assert result["eligible"] is True
    assert result["match_mode"] == "UNIQUE_ATTRIBUTES"


def test_ambiguous_fallback_and_wrong_position_fail_closed():
    duplicate = deepcopy(order())
    duplicate["orderId"] = "e2"
    result = extract_entry_fee_evidence(
        [order(), duplicate], identity(exchange_position_id=None)
    )
    assert result["eligible"] is False
    assert result["exclusion_reason"] == "entry order linkage ambiguous"
    assert extract_entry_fee_evidence([order(positionID="other")], identity())["eligible"] is False


def test_reduce_only_future_or_missing_commission_is_ineligible():
    assert extract_entry_fee_evidence([order(reduceOnly=True)], identity())["eligible"] is False
    assert extract_entry_fee_evidence(
        [order(time=1788739400000)], identity()
    )["eligible"] is False
    assert extract_entry_fee_evidence([order(commission=None)], identity())["eligible"] is False
    assert extract_entry_fee_evidence(
        [order()], identity(first_observed_utc="2026-09-07T00:01:00")
    )["eligible"] is False
