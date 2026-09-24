import json

from infrastructure.risk.risk_enforcement import RiskEnforcement


class GateSpy:
    def __init__(self):
        self.stops = []
        self.targets = []

    def record_stop_loss_exit(self, symbol, exit_time):
        self.stops.append((symbol, exit_time))

    def record_take_profit_exit(self, symbol):
        self.targets.append(symbol)


def test_risk_enforcement_uses_explicit_journal_and_gate(tmp_path):
    journal = tmp_path / "cooldown.json"
    journal.write_text(json.dumps({"BTCUSDT": 123.0}), encoding="utf-8")
    gate = GateSpy()
    risk = RiskEnforcement(object(), cooldown_gate=gate, cooldown_journal_path=str(journal))
    assert risk._sl_cooldowns == {"BTCUSDT": 123.0}
    risk._sl_cooldowns["ETHUSDT"] = 456.0
    risk._save_cooldown_journal()
    assert json.loads(journal.read_text(encoding="utf-8")) == {
        "BTCUSDT": 123.0, "ETHUSDT": 456.0,
    }
    risk.record_stop_loss_exit("BTCUSDT")
    risk.record_take_profit_exit("ETHUSDT")
    assert gate.stops == [("BTCUSDT", None)]
    assert gate.targets == ["ETHUSDT"]


def test_two_explicit_journals_do_not_share_state(tmp_path):
    first = RiskEnforcement(object(), cooldown_journal_path=str(tmp_path / "a.json"))
    second = RiskEnforcement(object(), cooldown_journal_path=str(tmp_path / "b.json"))
    first._sl_cooldowns["BTCUSDT"] = 1.0
    first._save_cooldown_journal()
    assert second._sl_cooldowns == {}
    assert not (tmp_path / "b.json").exists()
