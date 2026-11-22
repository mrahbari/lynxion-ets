"""Moving a stop (breakeven/trailing) must work on BingX without an unprotected window."""
import logging

from infrastructure.brokers.adapters.bingx_adapter import _BingXBroker


def _broker(responses, pending):
    b = _BingXBroker.__new__(_BingXBroker)
    b.logger = logging.getLogger("t"); b._contract_precisions = {}
    sent, cancelled = [], []

    def req(method, endpoint, params=None, data=None, signed=False, **kw):
        sent.append(dict(params or data or {}))
        return responses.pop(0)
    b._make_request = req
    b._format_symbol_str = lambda s: s
    b._format_price = lambda sym, p: f"{p}"
    b._format_quantity = lambda sym, q: f"{q}"
    b.get_pending_orders_evidence = lambda sym=None: {"status": "OK", "orders": list(pending), "error": None}
    b.cancel_order = lambda oid, sym: cancelled.append(oid) or True
    return b, sent, cancelled


OLD = {"orderId": 111, "type": "STOP_MARKET", "positionSide": "LONG", "symbol": "EVAA-USDT"}
TP = {"orderId": 222, "type": "TAKE_PROFIT_MARKET", "positionSide": "LONG", "symbol": "EVAA-USDT"}


def test_conflict_places_quantity_stop_then_cancels_old():
    b, sent, cancelled = _broker([
        {"code": 110406, "msg": "Position SL order already exists"},
        {"code": 0, "data": {"order": {"orderId": 333}}},
    ], [OLD, TP])
    r = b._place_conditional_order("EVAA-USDT", "SELL", "78", "2.588", "STOP_MARKET", "LONG")
    assert r["success"] and str(r["order_id"]) == "333"
    assert "closePosition" in sent[0] and "closePosition" not in sent[1]   # 2nd = quantity-based
    assert cancelled == ["111"]                                             # TP untouched


def test_rejected_replacement_keeps_old_stop():
    b, sent, cancelled = _broker([
        {"code": 110406, "msg": "Position SL order already exists"},
        {"code": 80001, "msg": "rejected"},
    ], [OLD])
    r = b._place_conditional_order("EVAA-USDT", "SELL", "78", "2.588", "STOP_MARKET", "LONG")
    assert r["success"] is False and cancelled == []


def test_successful_new_stop_cancels_superseded_stop():
    b, sent, cancelled = _broker([{"code": 0, "data": {"order": {"orderId": 444}}}],
                                 [OLD, dict(OLD, orderId=444), TP])
    r = b._place_conditional_order("EVAA-USDT", "SELL", "78", "2.6", "STOP_MARKET", "LONG")
    assert r["success"] and cancelled == ["111"]
