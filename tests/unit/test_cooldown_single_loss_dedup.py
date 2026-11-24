"""Platform review 2026-11-24: one stop-loss exit recorded by several paths is ONE loss (60 m cooldown, not 24 h)."""
import json
from datetime import datetime, timedelta, timezone

from infrastructure.risk.symbol_cooldown_gate import SymbolCooldownGate


class Clock:
    def __init__(self, t):
        self.t = t

    def now(self):
        return self.t


def gate(tmp_path, t):
    return SymbolCooldownGate(journal_path=str(tmp_path / "cd.json"),
                              trade_journal_path=str(tmp_path / "none.csv"), clock=Clock(t))


def test_duplicate_records_of_one_exit_give_60m_not_24h(tmp_path):
    t0 = datetime(2026, 11, 24, 5, 37, tzinfo=timezone.utc)
    g = gate(tmp_path, t0)
    for minutes in (0, 2, 9):                         # adapter, manager, collector
        g.record_stop_loss_exit("AVAXUSDT", t0 + timedelta(minutes=minutes))
    expiry = g._sl_cooldowns["AVAXUSDT"]
    assert expiry - t0.timestamp() < 2 * 3600
    assert len(g._symbol_loss_history["AVAXUSDT"]) == 1


def test_two_distinct_losses_within_2h_still_trip_the_breaker(tmp_path):
    t0 = datetime(2026, 11, 24, 5, 0, tzinfo=timezone.utc)
    g = gate(tmp_path, t0)
    g.record_stop_loss_exit("AVAXUSDT", t0)
    g.record_stop_loss_exit("AVAXUSDT", t0 + timedelta(minutes=50))
    assert g._sl_cooldowns["AVAXUSDT"] - t0.timestamp() > 20 * 3600


def test_corrupt_persisted_history_is_merged_on_load(tmp_path):
    t0 = datetime(2026, 11, 24, 5, 37, tzinfo=timezone.utc).timestamp()
    (tmp_path / "cd.json").write_text(json.dumps({"cooldowns": {"AVAXUSDT": t0 + 86400},
                                                  "loss_history": {"AVAXUSDT": [t0, t0 + 120, t0 + 540]}}))
    (tmp_path / "none.csv").write_text("trade_id,symbol,pnl_usdt,exit_timestamp\n1,AVAXUSDT,-2.5,2026-11-24T05:37:21+00:00\n")
    g = gate(tmp_path, datetime.fromtimestamp(t0 + 1800, tz=timezone.utc))
    assert len(g._symbol_loss_history["AVAXUSDT"]) == 1
