import sys
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from live.rebalancer import plan_orders

C = {s: {"symbol": s[:-4] + "-USDT", "quantityPrecision": 2, "tradeMinUSDT": 2} for s in ("AUSDT", "BUSDT", "CUSDT", "DUSDT")}
PX = {"AUSDT": 10.0, "BUSDT": 2.0, "CUSDT": 1.0, "DUSDT": 100.0}

def _o(orders, s, ps):
    return [o for o in orders if o["symbol"] == s and o["positionSide"] == ps]

def test_flip_close_and_open():
    t = pd.Series({"AUSDT": 0.25, "BUSDT": -0.25})
    pos = {"AUSDT": {"LONG": 0.0, "SHORT": 5.0}, "CUSDT": {"LONG": 100.0, "SHORT": 0.0}}
    o = plan_orders(t, 1000, pos, PX, C)
    a_short = _o(o, "AUSDT", "SHORT")[0]; a_long = _o(o, "AUSDT", "LONG")[0]
    assert (a_short["side"], a_short["qty"], a_short["reduce"]) == ("BUY", 5.0, True)
    assert (a_long["side"], a_long["qty"]) == ("BUY", 25.0)
    b = _o(o, "BUSDT", "SHORT")[0]; assert (b["side"], b["qty"]) == ("SELL", 125.0)
    c = _o(o, "CUSDT", "LONG")[0]; assert (c["side"], c["qty"], c["reduce"]) == ("SELL", 100.0, True)
    assert all(x["reduce"] for x in o[:2])          # reducing orders first

def test_small_delta_skipped_and_partial_adjust():
    t = pd.Series({"DUSDT": 0.5})
    o = plan_orders(t, 1000, {"DUSDT": {"LONG": 4.99, "SHORT": 0}}, PX, C)
    assert o == []                                   # 0.01 * 100 = $1 < min
    o = plan_orders(t, 1000, {"DUSDT": {"LONG": 6.0, "SHORT": 0}}, PX, C)
    assert (o[0]["side"], o[0]["qty"], o[0]["reduce"]) == ("SELL", 1.0, True)
