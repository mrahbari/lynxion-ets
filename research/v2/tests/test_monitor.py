import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from live import monitor as M  # noqa: E402

TH = {k: {"warn": w, "alert": a, "bad": b, "median": 0.0, "validated_alarm": v} for k, w, a, b, v in [
    ("ex_ante_carry", 0.05, 0.0, "low", True), ("adverse_share", 0.47, 0.51, "high", True),
    ("realized_carry", 0.05, 0.035, "low", True), ("turnover", 1.01, 1.10, "high", True),
    ("slippage_bp", 6.3, 12.6, "high", True), ("max_share", 0.047, 0.079, "high", True),
    ("top5_share", 0.16, 0.37, "high", True), ("abs_net_exposure", 0.03, 0.05, "high", True),
    ("ret_56d", -0.25, -0.95, "low", False), ("drawdown", -0.12, -0.19, "low", False),
    ("abs_beta_btc", 0.21, 0.39, "high", False)]}
DAY = 86_400_000
NOCLOSE = lambda s, now: None  # noqa: E731  (no network in tests)
T0 = 1_795_000_000_000 - (1_795_000_000_000 % DAY) + 3_600_000   # 01:00 UTC


def test_status_sides_and_info():
    assert M.status(0.10, TH["ex_ante_carry"]) == "OK"
    assert M.status(0.03, TH["ex_ante_carry"]) == "WARN"
    assert M.status(-0.01, TH["ex_ante_carry"]) == "ALERT"
    assert M.status(0.52, TH["adverse_share"]) == "ALERT"
    assert M.status(-0.5, TH["drawdown"], False) == "INFO"
    assert M.status(None, TH["drawdown"]) == "NA"


def test_ex_ante_carry_sign_and_adverse():
    # short a name with positive funding (receives), long a name with negative funding (receives)
    r = M.ex_ante({"A": -0.5, "B": 0.5}, {"A": 0.01, "B": -0.01})
    assert abs(r["ex_ante_carry"] - 0.01 * 365 / 21) < 1e-12 and r["adverse_share"] == 0.0
    r = M.ex_ante({"A": 0.5, "B": -0.5}, {"A": 0.01, "B": None})
    assert r["ex_ante_carry"] < 0 and r["adverse_share"] == 1.0 and r["funding_coverage"] == 0.5


def test_concentration_and_turnover():
    pos = [{"positionAmt": "1", "positionSide": "LONG", "positionValue": "60"},
           {"positionAmt": "1", "positionSide": "SHORT", "positionValue": "40"},
           {"positionAmt": "0", "positionSide": "SHORT", "positionValue": "99"}]
    c = M.concentration(pos)
    assert abs(c["max_share"] - 0.6) < 1e-12 and abs(c["abs_net_exposure"] - 0.2) < 1e-12 and c["gross"] == 100
    assert M.turnover({"A": 0.5, "B": -0.5}, {"A": 0.5, "C": -0.5}) == 1.0
    assert M.turnover(None, {"A": 1}) is None


def test_execution_slippage_and_failures(tmp_path):
    led = tmp_path / "orders.jsonl"
    rows = [
        {"event": "order", "client_id": "xs261122AB", "side": "BUY", "qty": 10, "notional": 100.0,
         "resp": {"code": 0, "data": {"order": {"avgPrice": "10.01"}}}},       # +10 bp adverse
        {"event": "order", "client_id": "xs261122CD", "side": "SELL", "qty": 10, "notional": 100.0,
         "resp": {"code": 0, "data": {"order": {"avgPrice": "10.01"}}}},       # -10 bp (favourable)
        {"event": "order", "client_id": "xs261122EF", "side": "SELL", "qty": 1, "notional": 5.0, "resp": {"code": 1}},
        {"event": "order", "client_id": "xs261115GH", "side": "BUY", "qty": 1, "notional": 5.0, "resp": {"code": 1}},
    ]
    led.write_text("\n".join(json.dumps(r) for r in rows))
    e = M.execution(led, "2026-11-22")
    assert e["orders"] == 3 and abs(e["fail_rate"] - 1 / 3) < 1e-12 and abs(e["slippage_bp"]) < 1e-6


def test_realized_carry_needs_28_days(tmp_path):
    csv = tmp_path / "tracking.csv"
    head = "date,window_hours,positions,gross,shadow_funding_bingx,shadow_funding_binance,binance_missing,shadow_funding_cum,unrealized,unrealized_plus_shadow_funding"
    row = "2026-11-24 01:15,24.0,38,1000,0.8,1.0,0,1,0,0"
    csv.write_text(head + "\n" + "\n".join([row] * 10))
    r = M.realized_carry(csv)
    assert r["realized_carry"] is None and r["carry_days"] == 10 and abs(r["venue_ratio"] - 0.8) < 1e-12
    csv.write_text(head + "\n" + "\n".join([row] * 30))
    r = M.realized_carry(csv)
    assert abs(r["realized_carry"] - 0.001 * 365) < 1e-9 and r["carry_days"] == 28


def _pos(sym, side, qty, px):
    return {"symbol": sym, "positionSide": side, "positionAmt": str(qty), "markPrice": str(px),
            "positionValue": str(qty * px)}


def test_run_is_read_only_and_books_daily_pnl(tmp_path):
    (tmp_path / "targets").mkdir()
    (tmp_path / "targets" / "2026-11-22.json").write_text(json.dumps({"AUSDT": 0.5, "BUSDT": -0.5}))
    (tmp_path / "state.json").write_text(json.dumps({"last_rebalance": "2026-11-22"}))
    pos = [_pos("A-USDT", "LONG", 50, 10.0), _pos("B-USDT", "SHORT", 50, 10.0)]
    f21 = lambda s, now: {"AUSDT": -0.002, "BUSDT": 0.004}[s]  # noqa: E731
    r1 = M.run(pos, {"AUSDT": 10.0, "BUSDT": 10.0, "BTCUSDT": 100.0}, 1000, tmp_path, T0, f21, TH, NOCLOSE)
    assert r1["values"]["live_days"] == 0 and r1["status"]["ex_ante_carry"] == "OK"
    assert r1["status"]["abs_net_exposure"] == "OK" and r1["status"]["fail_rate"] == "NA"
    # next day: A +2 %, B -2 % -> long +10, short +10 = +20 on a 1000 book
    r2 = M.run(pos, {"AUSDT": 10.2, "BUSDT": 9.8, "BTCUSDT": 101.0}, 1000, tmp_path, T0 + DAY, f21, TH, NOCLOSE)
    assert abs(r2["values"]["cum_ret"] - 0.02) < 1e-12 and r2["values"]["live_days"] == 1
    assert r2["status"]["drawdown"] == "INFO"
    assert len((tmp_path / "monitor.csv").read_text().splitlines()) == 3
    assert not (tmp_path / "orders.jsonl").exists()          # never writes orders


def test_alert_lines_carry_a_review_not_an_action(tmp_path):
    (tmp_path / "targets").mkdir()
    (tmp_path / "targets" / "2026-11-22.json").write_text(json.dumps({"AUSDT": 0.5, "BUSDT": -0.5}))
    pos = [_pos("A-USDT", "LONG", 90, 10.0), _pos("B-USDT", "SHORT", 10, 10.0)]
    f21 = lambda s, now: {"AUSDT": 0.01, "BUSDT": -0.01}[s]  # noqa: E731  (book pays funding)
    r = M.run(pos, {"AUSDT": 10.0, "BUSDT": 10.0}, 1000, tmp_path, T0, f21, TH, NOCLOSE)
    assert r["status"]["ex_ante_carry"] == "ALERT" and r["status"]["abs_net_exposure"] == "ALERT"
    assert any(line.startswith("ALERT ex_ante_carry") for line in r["lines"])


def test_leg_correlation_info():
    import numpy as np
    rng = np.random.default_rng(1)
    common = np.cumsum(rng.normal(0, 0.03, 31))
    same = {s: list(np.exp(common + rng.normal(0, 0.001, 31))) for s in ("AUSDT", "BUSDT", "CUSDT")}
    indep = {s: list(np.exp(np.cumsum(rng.normal(0, 0.03, 31)))) for s in ("DUSDT", "EUSDT", "FUSDT")}
    closes = {**same, **indep}
    pos = [_pos(s[:-4] + "-USDT", "LONG", 1, 1.0) for s in same] + [_pos(s[:-4] + "-USDT", "SHORT", 1, 1.0) for s in indep]
    c = M.cluster(pos, lambda s, now: closes[s], T0)
    assert c["corr_long"] > 0.95 and abs(c["corr_short"]) < 0.5
    assert M.cluster(pos[:2], lambda s, now: closes[s], T0)["corr_long"] is None    # < 3 names
