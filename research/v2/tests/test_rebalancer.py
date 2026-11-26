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


def test_ensure_stops_places_sl_and_tp_on_correct_sides(monkeypatch, tmp_path):
    from types import SimpleNamespace
    from live import rebalancer as R
    monkeypatch.setattr(R, "STATE_DIR", tmp_path); monkeypatch.setattr(R, "LEDGER", tmp_path / "o.jsonl")
    monkeypatch.setattr(R, "owned", lambda: {"AAAUSDT", "BBBUSDT"})
    monkeypatch.setattr(R.time, "sleep", lambda s: None)
    placed = []
    ad = SimpleNamespace(_broker=SimpleNamespace(
        cancel_order=lambda oid, sym: None,
        _place_conditional_order=lambda sym, side, qty, px, typ, ps: placed.append((sym, side, typ, ps, float(px))) or {"success": True}))
    monkeypatch.setattr(R, "platform_adapter", lambda: ad)
    cli = SimpleNamespace(
        positions=lambda: [{"symbol": "AAA-USDT", "positionSide": "LONG", "positionAmt": "10", "avgPrice": "100"},
                           {"symbol": "BBB-USDT", "positionSide": "SHORT", "positionAmt": "-5", "avgPrice": "10"},
                           {"symbol": "CCC-USDT", "positionSide": "LONG", "positionAmt": "1", "avgPrice": "1"}],
        open_orders=lambda: [])
    res = R.ensure_stops(cli, {"AAAUSDT": {"pricePrecision": 2}, "BBBUSDT": {"pricePrecision": 3}}, 0.5, 0.4)
    assert res["placed"] == 4 and res["failed"] == 0
    assert ("AAA-USDT", "SELL", "STOP_MARKET", "LONG", 50.0) in placed
    assert ("AAA-USDT", "SELL", "TAKE_PROFIT_MARKET", "LONG", 140.0) in placed
    assert ("BBB-USDT", "BUY", "STOP_MARKET", "SHORT", 15.0) in placed
    assert ("BBB-USDT", "BUY", "TAKE_PROFIT_MARKET", "SHORT", 6.0) in placed
    assert not any(p[0] == "CCC-USDT" for p in placed)       # platform symbol untouched


def test_render_daily_tree_sections_and_status_icons():
    from live.rebalancer import render_daily
    th = {"ex_ante_carry": {"median": 0.145}, "corr_long": {"median": 0.5}, "corr_short": {"median": 0.56}}
    v = {"ex_ante_carry": 0.8, "adverse_share": 0.08, "realized_carry": None, "carry_days": 4, "max_share": 0.035,
         "top5_share": 0.15, "abs_net_exposure": 0.02, "slippage_bp": 5.1, "fail_rate": 0.0, "corr_long": 0.19,
         "corr_short": 0.47}
    st = {"ex_ante_carry": "OK", "adverse_share": "WARN", "realized_carry": "NA", "max_share": "OK", "top5_share": "OK",
          "abs_net_exposure": "ALERT", "slippage_bp": "OK"}
    rep = {"time": "t", "next_rebalance": "2026-11-29",
           "account": {"equity": 73624.2, "pnl_since_start": 4.86, "positions": 38, "gross_notional": 2996, "unrealized": -59.83},
           "funding": {"window_hours": 24, "shadow_funding_bingx": 1.31, "shadow_funding_binance": 1.55,
                       "shadow_funding_cum": 9.49, "unrealized_plus_shadow_funding": -50.23},
           "protection": {"in_place": 76, "expected": 76, "failed": 0, "closed": []},
           "health": {"values": v, "status": st, "thresholds": th, "reviews": ["abs_net_exposure ALERT: review"]}}
    t = render_daily(rep)
    assert "💼 <b>Account:</b>" in t and "73,624.20 VST" in t and "└ <b>Next rebalance:</b>" in t
    assert "<b>Adverse names:</b> <code>8%</code> ⚠️" in t and "net 2.0%</code> 🚨" in t
    assert "building 4/28 days" in t and "⚠️ <b>Review:</b> abs_net_exposure ALERT" in t
    assert "Closed since rebalance" not in t and t.endswith("<code>t</code>")
