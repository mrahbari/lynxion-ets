"""Approved-symbols sync (runner_sync_approved_symbols): venue-agnostic liquid universe + hot reload."""
import json
import os

import runner_sync_approved_symbols as sync

DAY = 86_400_000
NOW = 1795400000000
CFG = {"exchange": "fake", "min_median_qv": 1e7, "min_age_days": 30}


class FakeExchange:
    """ccxt-shaped venue: two id styles (BingX 'X-USDT', MEXC 'X_USDT') must normalize the same way."""

    def __init__(self, n_days=40):
        self.n_days = n_days
        mk = lambda base, mid, **kw: {"id": mid, "base": base, "quote": "USDT", "settle": "USDT", "swap": True,
                                      "linear": True, "active": True, **kw}
        self.markets = {"LIQ/USDT:USDT": mk("LIQ", "LIQ-USDT"), "THIN/USDT:USDT": mk("THIN", "THIN_USDT"),
                        "NEW/USDT:USDT": mk("NEW", "NEW-USDT"), "USDC/USDT:USDT": mk("USDC", "USDC-USDT"),
                        "HELD/USDT:USDT": mk("HELD", "HELD-USDT"),
                        "INV/USD:INV": {"id": "INV-USD", "base": "INV", "quote": "USD", "settle": "INV",
                                        "swap": True, "linear": False, "active": True}}

    def load_markets(self):
        return self.markets

    def fetch_tickers(self, symbols):
        qv = {"LIQ/USDT:USDT": 5e7, "THIN/USDT:USDT": 4e6, "NEW/USDT:USDT": 9e7, "USDC/USDT:USDT": 9e8,
              "HELD/USDT:USDT": 1e5}
        return {s: {"quoteVolume": qv.get(s, 0)} for s in symbols}

    def fetch_ohlcv(self, symbol, timeframe, limit):
        day0 = NOW // DAY * DAY
        days = 5 if symbol.startswith("NEW") else self.n_days
        vol = {"LIQ": 2e7, "THIN": 3e6, "NEW": 9e7}[symbol.split("/")[0]]
        # newest first on purpose (BingX order); bar at day0 is the incomplete current day
        return [[day0 - i * DAY, 1, 1, 1, 1, vol] for i in range(days + 1)][:limit]


def test_universe_keeps_only_liquid_seasoned_non_stable(monkeypatch):
    monkeypatch.setattr(sync, "active_symbols", lambda: set())
    approved, rows = sync.build(ex=FakeExchange(), now_ms=NOW, cfg=CFG)
    assert approved == ["LIQUSDT"]
    reasons = {r["symbol"]: r["reason"] for r in rows}
    assert reasons == {"LIQUSDT": "liquid", "THINUSDT": "median_qv_7d", "NEWUSDT": "age", "USDCUSDT": "state",
                       "HELDUSDT": "qv_24h"}                         # inverse contract not considered


def test_open_position_symbol_is_never_dropped(monkeypatch):
    monkeypatch.setattr(sync, "active_symbols", lambda: {"HELDUSDT"})
    approved, _ = sync.build(ex=FakeExchange(), now_ms=NOW, cfg=CFG)
    assert "HELDUSDT" in approved


def test_venue_follows_default_broker_with_override(monkeypatch):
    monkeypatch.delenv("UNIVERSE_EXCHANGE", raising=False)
    monkeypatch.setenv("DEFAULT_BROKER", "Binance")
    assert sync.settings()["exchange"] == "binance"
    monkeypatch.setenv("UNIVERSE_EXCHANGE", "mexc")
    assert sync.settings()["exchange"] == "mexc"


def test_failed_or_tiny_build_keeps_previous_files(monkeypatch, tmp_path):
    target = tmp_path / "approved.json"
    target.write_text(json.dumps(["OLDUSDT"]))
    monkeypatch.setattr(sync, "TARGETS", [target])
    monkeypatch.setattr(sync, "REPORT", tmp_path / "report.json")
    monkeypatch.setattr(sync, "build", lambda cfg=None: (["AUSDT"], []))      # below MIN_SYMBOLS
    assert sync.sync() == 1
    assert json.loads(target.read_text()) == ["OLDUSDT"]

    def boom(cfg=None):
        raise RuntimeError("venue unreachable")
    monkeypatch.setattr(sync, "build", boom)
    assert sync.sync() == 1
    assert json.loads(target.read_text()) == ["OLDUSDT"]

    names = [f"S{i}USDT" for i in range(25)]
    monkeypatch.setattr(sync, "build", lambda cfg=None: (names, []))
    assert sync.sync() == 0
    assert json.loads(target.read_text()) == names


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
