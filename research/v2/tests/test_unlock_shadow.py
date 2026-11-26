import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "experiments"))
from live import unlock_shadow as U  # noqa: E402
import r31_unlock_shadow_eval as R  # noqa: E402

TODAY = pd.Timestamp("2026-12-10", tz="UTC")


def _daily(close, n=31, adv=1e7):
    idx = pd.date_range(end=TODAY - pd.Timedelta(days=1), periods=n, freq="D", tz="UTC")
    return pd.DataFrame({"close": close, "qv": adv}, index=idx)


def test_run_logs_new_entry_once_and_respects_gap(tmp_path, monkeypatch):
    monkeypatch.setattr(U, "LOG", tmp_path / "u.jsonl")
    T = TODAY - pd.Timedelta(days=1) + pd.Timedelta(days=30)
    cands = [{"name": "a", "sym": "AUSDT", "T": T, "entry_day": TODAY - pd.Timedelta(days=1), "ins_size": 0.05},
             {"name": "a2", "sym": "AUSDT", "T": T + pd.Timedelta(days=1), "entry_day": TODAY - pd.Timedelta(days=1) + pd.Timedelta(days=0), "ins_size": 0.02}]
    monkeypatch.setattr(U, "candidates", lambda today: cands)
    monkeypatch.setattr(U, "daily", lambda sym, end, limit=40: _daily(2.0 if sym == "AUSDT" else 100.0))
    new = U.run(TODAY)
    assert [x["name"] for x in new] == ["a"]                      # second event same symbol inside 44 days skipped
    assert U.run(TODAY) == []                                     # idempotent
    rec = json.loads((tmp_path / "u.jsonl").read_text().splitlines()[0])
    assert rec["entry"] == 2.0 and rec["btc"] == 100.0


def test_run_skips_illiquid(tmp_path, monkeypatch):
    monkeypatch.setattr(U, "LOG", tmp_path / "u.jsonl")
    c = [{"name": "b", "sym": "BUSDT", "T": TODAY + pd.Timedelta(days=29), "entry_day": TODAY - pd.Timedelta(days=1), "ins_size": 0.05}]
    monkeypatch.setattr(U, "candidates", lambda today: c)
    monkeypatch.setattr(U, "daily", lambda sym, end, limit=40: _daily(1.0, adv=1e6))
    assert U.run(TODAY) == []


def test_eval_stop_and_hedge(monkeypatch):
    e = {"sym": "AUSDT", "T": "2026-01-31", "entry_day": "2026-01-01", "entry": 1.0, "btc": 100.0, "eth": 10.0}
    days = pd.date_range("2026-01-02", "2026-02-14", freq="D", tz="UTC")

    def bars(sym, start, end):
        if sym == "AUSDT":
            hi = [1.05] * len(days); hi[5] = 1.25                       # stop on day 6
            return pd.DataFrame({"high": hi, "close": 1.0}, index=days).loc[start:end]
        return pd.DataFrame({"high": 0, "close": 110.0 if sym == "BTCUSDT" else 11.0}, index=days).loc[start:end]
    monkeypatch.setattr(R, "bars", bars)
    monkeypatch.setattr(R, "funding", lambda s, a, b: 0.0)
    o = R.outcome(e)
    assert o["stopped"] and abs(o["net"] - (-0.20 + 0.10 - R.COST)) < 1e-9
