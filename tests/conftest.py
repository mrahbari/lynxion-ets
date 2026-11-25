"""Root test configuration.

Ensures the project root is importable so tests can import the
``application`` / ``domain`` / ``infrastructure`` / ``shared`` packages
without the project being installed as a distribution.
"""

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Tests must not depend on the live v2 sleeve ownership file (data/v2_live/owned_symbols.json).
import os  # noqa: E402
os.environ.setdefault("V2_OWNED_SYMBOLS_FILE", str(ROOT / "tests" / "_no_v2_owned_symbols.json"))

# Tests must never write the live runtime state in data/ (order journal, SL cooldowns,
# active positions). Before this, a unit-test run left synthetic PROTECTION_UNKNOWN rows in
# data/live_order_journal.json, which blocks the TESTNET launcher.
import tempfile  # noqa: E402
_STATE_DIR = Path(tempfile.mkdtemp(prefix="lynxion-test-state-"))
os.environ.setdefault("LIVE_ORDER_JOURNAL_PATH", str(_STATE_DIR / "live_order_journal.json"))
# Operator runtime allowlist from .env must not filter test strategies (dotenv never overrides).
os.environ["STRATEGY_ALLOWLIST"] = ""
# Tests must never message the operator's real Telegram chat (a test run sent a fake
# "POSITION STATE UNVERIFIED TUTUSDT" alert). Empty values block .env loading (override=False).
os.environ["TELEGRAM_BOT_TOKEN"] = ""
os.environ["TELEGRAM_CHAT_ID"] = "0"   # settings parse it as int; empty token already blocks sending
os.environ["TRADE_JOURNAL_SYMBOL_PACING_SECONDS"] = "0"  # no real-time pacing inside unit tests
# Legacy ActivePositionManager contract tests drive stop requests through ROE triggers; the
# R-multiple default mode reuses the same request path and has its own tests (opt in per test).
os.environ["APM_STOP_MODE"] = "legacy"


@pytest.fixture(autouse=True)
def _fresh_live_order_journal(tmp_path, monkeypatch):
    """Each test gets its own order journal: a PROTECTION_UNKNOWN left by one test made the stop-path
    (ActivePositionManager._sync_sl_to_exchange) return early in later tests."""
    import infrastructure.execution.live_order_journal as journal_mod
    path = str(tmp_path / "live_order_journal.json")
    monkeypatch.setenv("LIVE_ORDER_JOURNAL_PATH", path)
    monkeypatch.setattr(journal_mod, "live_order_journal", journal_mod.LiveOrderJournal(path))


@pytest.fixture(autouse=True, scope="session")
def _isolate_runtime_state_files():
    import infrastructure.risk.symbol_cooldown_gate as gate_mod
    import infrastructure.risk.risk_enforcement as enf_mod
    import infrastructure.execution.broker_reconciliation as rec_mod
    cooldown = str(_STATE_DIR / "sl_cooldown_journal.json")
    gate_mod.COOLDOWN_JOURNAL_PATH = cooldown
    enf_mod.COOLDOWN_JOURNAL_PATH = cooldown
    gate_mod.symbol_cooldown_gate._journal_path = cooldown
    # Tests assert the default active-positions path, so snapshot/restore that file instead.
    active = Path(rec_mod.ACTIVE_POSITIONS_JOURNAL_PATH)
    saved = active.read_bytes() if active.exists() else None
    yield
    if saved is not None:
        active.write_bytes(saved)


@pytest.fixture
def approved_symbols_config(tmp_path):
    """Factory fixture: write an approved-symbols JSON file and return its path.

    Lets tests build a SymbolValidator against a known, isolated symbol list
    instead of the committed application/configs/approved_symbols.json.
    Usage: ``SymbolValidator(config_path=approved_symbols_config(["BTCUSDT"]))``.
    """
    def _make(symbols):
        path = tmp_path / "approved_symbols.json"
        path.write_text(json.dumps(symbols), encoding="utf-8")
        return str(path)
    return _make


@pytest.fixture(autouse=True)
def _no_live_position_snapshot(monkeypatch):
    """The orchestrator's open-position skip must never read the live reconciler snapshot in tests."""
    from infrastructure.orchestrators._auto_detection_intent import _AutoDetectionIntentMixin
    if "_position_snapshot_path" not in _AutoDetectionIntentMixin.__dict__:
        monkeypatch.setattr(_AutoDetectionIntentMixin, "_position_snapshot_path",
                            "/nonexistent/active_positions_journal.json", raising=False)


@pytest.fixture(autouse=True)
def _fresh_position_snapshot_guard():
    """E11-1 empty-snapshot guard keeps process state; every test starts with none."""
    from infrastructure.brokers.adapters import bingx_adapter as bx
    bx._snapshot_state.update(last_nonempty=None, first_empty=None)
    yield
    bx._snapshot_state.update(last_nonempty=None, first_empty=None)
