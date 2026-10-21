"""Standard-library, fake-only tests against the selected checkout's actual files.

No broker/container construction. Run with python -I -B <script> <checkout>.
"""
import contextlib
import io
import json
import os
from pathlib import Path
import runpy
import socket
import subprocess
import sys
import tempfile
import types
import unittest

ROOT = Path(sys.argv[1]).resolve()
if os.environ.get("LYNXION_OFFLINE_CHILD") != "1":
    os.execve(sys.executable, [sys.executable, "-I", "-B", str(Path(__file__).resolve()), str(ROOT)],
              {"LYNXION_OFFLINE_CHILD": "1", "PYTHONDONTWRITEBYTECODE": "1", "TMPDIR": "/private/tmp"})

def deny(*args, **kwargs):
    raise RuntimeError("OFFLINE_TEST_DENIED")

socket.socket = deny
socket.create_connection = deny
subprocess.Popen = deny
os.system = deny
scratch = tempfile.TemporaryDirectory(prefix="lynxion-target-recovery-")
TMP = Path(scratch.name)
os.environ["LIVE_ORDER_JOURNAL_PATH"] = str(TMP / "singleton.jsonl")

def audit(event, args):
    if event == "open" and isinstance(args[0], (str, bytes, os.PathLike)):
        path = Path(os.fsdecode(args[0])).resolve()
        if path.name == ".env" or ROOT / "data" in path.parents:
            raise RuntimeError("OFFLINE_TEST_DENIED_OPERATIONAL_READ")
        mode = args[1]
        flags = args[2] if len(args) > 2 else 0
        writing = (isinstance(mode, str) and any(c in mode for c in "wax+")) or (
            isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC))
        if writing and TMP not in path.parents:
            raise RuntimeError("OFFLINE_TEST_DENIED_EXTERNAL_WRITE")

sys.addaudithook(audit)
journal_module = runpy.run_path(str(ROOT / "infrastructure/execution/live_order_journal.py"))
Journal = journal_module["LiveOrderJournal"]

class JournalTests(unittest.TestCase):
    def test_invalid_inputs_block_recovery_and_writes(self):
        records = ["{broken", "[]", "{}", '{"order_ref":"r"}',
                   '{"order_ref":"r","status":"TYPO"}',
                   '{"order_ref":7,"status":"INTENT"}',
                   '{"order_ref":" ","status":"INTENT"}']
        for index, record in enumerate(records):
            with self.subTest(record=record):
                path = TMP / str(index)
                path.write_text(record + "\n")
                journal = Journal(str(path))
                with self.assertRaises(RuntimeError):
                    journal.recover()
                with self.assertRaises(RuntimeError):
                    journal.record_intent("TESTUSDT", "BUY", 1, "fake")
                self.assertEqual(path.read_text(), record + "\n")

    def test_valid_lifecycle_and_missing_file(self):
        journal = Journal(str(TMP / "valid.jsonl"))
        self.assertEqual(journal.recover()["total_orders"], 0)
        ref = journal.record_intent("TESTUSDT", "BUY", 1, "fake")
        self.assertEqual(Journal(journal.path).recover()["status_counts"], {"INTENT": 1})
        journal.record_submitted(ref, "FAKE-ID", "fake")
        self.assertEqual(Journal(journal.path).recover()["status_counts"], {"SUBMITTED": 1})

    def test_read_failure_blocks_recovery(self):
        with self.assertRaises(RuntimeError):
            Journal(str(TMP)).recover()

def module(name, **values):
    result = types.ModuleType(name)
    result.__dict__.update(values)
    sys.modules[name] = result
    return result

for name in ("application", "application.use_cases", "bootstrap", "bootstrap.settings", "shared",
             "infrastructure", "infrastructure.execution"):
    package = module(name)
    package.__path__ = []
started = []
def use_case(**kwargs):
    return types.SimpleNamespace(run=lambda **options: started.append(True) or 0)
@contextlib.contextmanager
def fake_lifespan():
    yield types.SimpleNamespace(resolve=lambda name: object())
module("application.use_cases.run_live_trading", RunLiveTradingUseCase=use_case)
module("application.use_cases.run_auto_detection", RunAutoDetectionUseCase=use_case)
module("bootstrap.lifecycle", lifespan=fake_lifespan)
module("bootstrap.settings.loaders", load_settings=lambda: object())
preflight = module("shared.preflight")
selected_journal = module("infrastructure.execution.live_order_journal")
cli = runpy.run_path(str(ROOT / "interface/cli/trading_system_production.py"))

class StartupTests(unittest.TestCase):
    def test_decision_matrix(self):
        for mode in ("TESTNET", "LIVE", "PAPER"):
            for auto in (False, True):
                for status in ("INTENT", "PROTECTION_UNKNOWN", "SUBMITTED", "READ_ERROR", "BAD_SUMMARY"):
                    with self.subTest(mode=mode, auto=auto, status=status):
                        started.clear()
                        preflight.run_preflight = lambda _: dict(mode=mode, ok=True, flags={}, warnings=[], blocking=[])
                        def recover():
                            if status == "READ_ERROR":
                                raise OSError("synthetic")
                            return {"status_counts": None if status == "BAD_SUMMARY" else {status: 1}}
                        selected_journal.live_order_journal = types.SimpleNamespace(recover=recover)
                        blocked = mode != "PAPER" and status != "SUBMITTED"
                        with contextlib.redirect_stdout(io.StringIO()):
                            result = cli["main"](["--mode", "production"] + (["--auto-detect"] if auto else []))
                        self.assertEqual(result, 2 if blocked else 0)
                        self.assertEqual(started, [] if blocked else [True])

suite = unittest.defaultTestLoader.loadTestsFromTestCase(JournalTests)
suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(StartupTests))
result = unittest.TextTestRunner(verbosity=2).run(suite)
print("ISOLATION: clean child environment; transports/subprocess denied; operational reads and external writes denied")
scratch.cleanup()
raise SystemExit(0 if result.wasSuccessful() else 1)
