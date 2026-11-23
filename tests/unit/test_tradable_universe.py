"""Daily BingX tradable universe (scripts/build_tradable_universe.py) and approved-list hot reload."""
import importlib.util
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DAY = 86_400_000
NOW = 1795400000000


def _builder():
    spec = importlib.util.spec_from_file_location("btu", ROOT / "scripts" / "build_tradable_universe.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _fake_api(m, monkeypatch, active=()):
    day0 = NOW // DAY * DAY
    contracts = [
        {"symbol": "LIQ-USDT", "asset": "LIQ", "status": 1, "apiStateOpen": "true", "apiStateClose": "true",
         "launchTime": NOW - 400 * DAY},
        {"symbol": "THIN-USDT", "asset": "THIN", "status": 1, "apiStateOpen": "true", "apiStateClose": "true",
         "launchTime": NOW - 400 * DAY},
        {"symbol": "NEW-USDT", "asset": "NEW", "status": 1, "apiStateOpen": "true", "apiStateClose": "true",
         "launchTime": NOW - 5 * DAY},
        {"symbol": "USDC-USDT", "asset": "USDC", "status": 1, "apiStateOpen": "true", "apiStateClose": "true",
         "launchTime": NOW - 400 * DAY},
        {"symbol": "HELD-USDT", "asset": "HELD", "status": 1, "apiStateOpen": "true", "apiStateClose": "true",
         "launchTime": NOW - 400 * DAY},
    ]
    tickers = [{"symbol": "LIQ-USDT", "quoteVolume": "5e7"}, {"symbol": "THIN-USDT", "quoteVolume": "4e6"},
               {"symbol": "NEW-USDT", "quoteVolume": "9e7"}, {"symbol": "USDC-USDT", "quoteVolume": "9e8"},
               {"symbol": "HELD-USDT", "quoteVolume": "1e5"}]

    def klines(qv_per_day):
        # newest first, like BingX; the first bar is today's incomplete day
        return [{"time": day0 - i * DAY, "volume": str(qv_per_day), "high": "1", "low": "1", "close": "1"}
                for i in range(9)]

    def get(path):
        if "contracts" in path:
            return contracts
        if "ticker" in path:
            return tickers
        if "LIQ-USDT" in path:
            return klines(2e7)
        if "THIN-USDT" in path:
            return klines(3e6)
        raise AssertionError(path)

    monkeypatch.setattr(m, "_get", get)
    monkeypatch.setattr(m, "active_symbols", lambda: set(active))


def test_universe_keeps_only_liquid_seasoned_non_stable(monkeypatch):
    m = _builder()
    _fake_api(m, monkeypatch)
    approved, rows = m.build(now_ms=NOW)
    assert approved == ["LIQUSDT"]
    reasons = {r["symbol"]: r["reason"] for r in rows}
    assert reasons["THINUSDT"] == "median_qv_7d" and reasons["NEWUSDT"] == "age" and reasons["USDCUSDT"] == "state"


def test_open_position_symbol_is_never_dropped(monkeypatch):
    m = _builder()
    _fake_api(m, monkeypatch, active={"HELDUSDT"})
    approved, _ = m.build(now_ms=NOW)
    assert "HELDUSDT" in approved


def test_failed_or_tiny_build_keeps_previous_files(monkeypatch, tmp_path):
    m = _builder()
    target = tmp_path / "approved.json"
    target.write_text(json.dumps(["OLDUSDT"]))
    monkeypatch.setattr(m, "TARGETS", [target])
    monkeypatch.setattr(m, "REPORT", tmp_path / "report.json")
    monkeypatch.setattr(m, "build", lambda: (["AUSDT"], []))          # below MIN_SYMBOLS
    monkeypatch.setattr("sys.argv", ["x"])
    assert m.main() == 1
    assert json.loads(target.read_text()) == ["OLDUSDT"]

    def boom():
        raise RuntimeError("api down")
    monkeypatch.setattr(m, "build", boom)
    assert m.main() == 1
    assert json.loads(target.read_text()) == ["OLDUSDT"]


def test_validator_hot_reloads_approved_list(tmp_path):
    from infrastructure.services.symbol_validator import SymbolValidator
    approved = tmp_path / "approved.json"
    approved.write_text(json.dumps(["AAAUSDT"]))
    (tmp_path / "bl.json").write_text("[]")
    v = SymbolValidator(config_path=str(approved), blacklist_path=str(tmp_path / "bl.json"))
    assert v.is_symbol_approved("AAAUSDT") and not v.is_symbol_approved("BBBUSDT")
    approved.write_text(json.dumps(["BBBUSDT"]))
    st = os.stat(approved)
    os.utime(approved, ns=(st.st_atime_ns, st.st_mtime_ns + 1_000_000))
    assert v.is_symbol_approved("BBBUSDT") and not v.is_symbol_approved("AAAUSDT")
    approved.write_text("{not json")
    os.utime(approved, ns=(st.st_atime_ns, st.st_mtime_ns + 2_000_000))
    assert v.is_symbol_approved("BBBUSDT")                              # broken file keeps last good list
