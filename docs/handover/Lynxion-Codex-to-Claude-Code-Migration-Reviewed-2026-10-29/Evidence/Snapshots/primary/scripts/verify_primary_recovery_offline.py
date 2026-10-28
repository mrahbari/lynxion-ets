"""Standard-library, fake-only tests against the selected checkout's actual files.

No broker/container construction. Run with python -I -B <script> <checkout>.
"""
import contextlib
import ast
from datetime import datetime
from decimal import Decimal
import time
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
import typing
import math
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

    def test_acknowledged_protection_remains_visible_separately(self):
        journal = Journal(str(TMP / "readout.jsonl"))
        ref = journal.record_protection_unknown("TESTUSDT", "SELL", 1, "fake")
        journal.record_submitted(ref, "FAKE-PROTECTION", "fake")
        before = Path(journal.path).read_bytes()
        records = journal.protection_records()
        self.assertEqual(records[0]["order_id"], "FAKE-PROTECTION")
        records[0]["status"] = "MUTATED-COPY"
        self.assertEqual(journal.protection_records()[0]["status"], "SUBMITTED")
        self.assertEqual(journal.in_flight(), [])
        self.assertEqual(journal.net_positions(), {})
        self.assertEqual(Path(journal.path).read_bytes(), before)

    def test_protection_unknown_survives_restart_and_blocks_admission(self):
        journal = Journal(str(TMP / "protection.jsonl"))
        parent = journal.record_intent("TESTUSDT", "BUY", 1, "fake")
        journal.record_submitted(parent, "FAKE-ENTRY", "fake")
        ref = journal.record_protection_unknown("TESTUSDT", "SELL", 1, "fake", entry_order_ref=parent)
        reopened = Journal(journal.path)
        marker = next(record for record in reopened.in_flight() if record["order_ref"] == ref)
        self.assertEqual(marker["status"], "PROTECTION_UNKNOWN")
        self.assertEqual(marker["entry_order_ref"], parent)
        self.assertIsNone(marker["order_id"])
        with self.assertRaises(RuntimeError):
            reopened.record_intent("OTHERUSDT", "BUY", 1, "fake")

    def test_protection_unknown_requires_durable_write(self):
        journal = Journal(str(TMP / "durable-protection.jsonl"))
        original = os.fsync
        def fail(_descriptor):
            raise OSError("synthetic fsync failure")
        os.fsync = fail
        try:
            with self.assertRaises(OSError):
                journal.record_protection_unknown("TESTUSDT", "SELL", 1, "fake")
        finally:
            os.fsync = original

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
class PositionSnapshotTests(unittest.TestCase):
    def method(self):
        tree = ast.parse((ROOT / "infrastructure/brokers/adapters/bingx_adapter.py").read_text())
        cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "BingXBrokerAdapter")
        method = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == "get_all_positions")
        namespace = dict(List=list, Position=lambda **kw: types.SimpleNamespace(**kw),
                         PositionSide=types.SimpleNamespace(SHORT="SHORT", LONG="LONG"),
                         Money=lambda **kw: types.SimpleNamespace(**kw), Decimal=Decimal,
                         datetime=datetime, time=time)
        exec(compile(ast.Module(body=[method], type_ignores=[]), "actual-adapter-method", "exec"), namespace)
        return namespace["get_all_positions"]

    def adapter(self, rows):
        return types.SimpleNamespace(connected=True, _broker=types.SimpleNamespace(get_open_positions=lambda: rows),
                                     _parse_symbol=lambda s: s, logger=types.SimpleNamespace(warning=lambda *args: None))

    def row(self, quantity="1"):
        return dict(symbol="TEST-USDT", positionAmt=quantity, avgPrice="10", time=0,
                    positionSide="LONG", leverage="5", isolated=True)

    def test_invalid_rows_never_become_partial_or_flat(self):
        for bad in ({}, {"positionAmt": "bad"}, self.row("NaN"), self.row("Infinity")):
            with self.subTest(bad=bad):
                with self.assertRaises(RuntimeError):
                    self.method()(self.adapter([self.row(), bad]))

    def test_valid_metadata_and_zero_preserved(self):
        result = self.method()(self.adapter([self.row("0"), self.row("-2")]))
        self.assertEqual(len(result), 1)
        self.assertEqual((result[0].quantity, result[0].side), (2, "SHORT"))
        self.assertEqual(result[0].leverage, Decimal("5"))
        self.assertIs(result[0].isolated, True)

suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(PositionSnapshotTests))
class ProtectionMutationTests(unittest.TestCase):
    def setUp(self):
        self.journal = Journal(str(TMP / (self.id().split(".")[-1] + ".jsonl")))
        selected_journal.live_order_journal = self.journal
        package = module("infrastructure.utils")
        package.__path__ = []
        module("infrastructure.utils.symbol_format_helper", SymbolFormatHelper=types.SimpleNamespace(
            format_symbol_for_exchange=lambda symbol, exchange: symbol))
        tree = ast.parse((ROOT / "infrastructure/risk/active_position_manager.py").read_text())
        cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "ActivePositionManager")
        method = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == "_sync_sl_to_exchange")
        self.logger = types.SimpleNamespace(warning=lambda *args: None, error=lambda *args: None)
        namespace = dict(Any=typing.Any, Dict=typing.Dict, Optional=typing.Optional, time=time, logger=self.logger)
        exec(compile(ast.Module(body=[method], type_ignores=[]), "actual-manager-method", "exec"), namespace)
        self.sync = namespace["_sync_sl_to_exchange"]
        self.manager = types.SimpleNamespace(_positions_state={}, _resolve_target_broker=lambda broker: broker,
            _classify_stop_failure=lambda error: "AMBIGUOUS_TERMINAL",
            _query_pending_stop_visibility=lambda *args, **kwargs: {"verified": True})
        self.calls = []

    def broker(self, response=None, error=False):
        def place(**kwargs):
            self.calls.append(kwargs)
            if error:
                raise TimeoutError("synthetic lost acknowledgement")
            return response
        return types.SimpleNamespace(name="fake", _place_conditional_order=place)

    def invoke(self, broker):
        return self.sync(self.manager, broker, "TESTUSDT", True, 1, 9)

    def test_unknown_response_blocks_repeat_after_reopen(self):
        broker = self.broker({"success": False, "unknown_submission": True})
        self.assertFalse(self.invoke(broker))
        reopened = Journal(self.journal.path)
        self.assertEqual(reopened.recover()["status_counts"], {"PROTECTION_UNKNOWN": 1})
        selected_journal.live_order_journal = reopened
        self.assertFalse(self.invoke(broker))
        self.assertEqual(len(self.calls), 1)

    def test_transport_exception_blocks_repeat(self):
        broker = self.broker(error=True)
        self.assertFalse(self.invoke(broker))
        self.assertFalse(self.invoke(broker))
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.journal.recover()["status_counts"], {"PROTECTION_UNKNOWN": 1})

    def test_unusable_ack_identity_blocks_repeat(self):
        for index, identity in enumerate((" ", True, 1.5)):
            with self.subTest(identity=identity):
                self.journal = Journal(str(TMP / ("bad-ack-" + str(index) + ".jsonl")))
                selected_journal.live_order_journal = self.journal
                self.calls.clear()
                broker = self.broker({"success": True, "order_id": identity})
                self.assertFalse(self.invoke(broker))
                self.assertFalse(self.invoke(broker))
                self.assertEqual(len(self.calls), 1)

    def test_unverified_visibility_never_retries(self):
        self.manager._query_pending_stop_visibility = lambda *args, **kwargs: {"verified": False}
        broker = self.broker({"success": True, "order_id": "FAKE-SL"})
        self.assertFalse(self.invoke(broker))
        self.assertFalse(self.invoke(broker))
        self.assertEqual(len(self.calls), 1)

    def test_verified_ack_is_not_an_entry_fill(self):
        for index, identity in enumerate(("FAKE-SL", 123)):
            with self.subTest(identity=identity):
                self.journal = Journal(str(TMP / ("valid-ack-" + str(index) + ".jsonl")))
                selected_journal.live_order_journal = self.journal
                broker = self.broker({"success": True, "order_id": identity})
                self.assertTrue(self.invoke(broker))
                reopened = Journal(self.journal.path)
                self.assertEqual(reopened.recover()["status_counts"], {"SUBMITTED": 1})
                self.assertEqual(reopened.in_flight(), [])
                self.assertEqual(reopened.net_positions(), {})

    def test_pre_send_fsync_failure_prevents_mutation(self):
        original = os.fsync
        os.fsync = lambda _fd: (_ for _ in ()).throw(OSError("synthetic"))
        try:
            self.assertFalse(self.invoke(self.broker({"success": True, "order_id": "FAKE-SL"})))
        finally:
            os.fsync = original
        self.assertEqual(self.calls, [])

    def test_ack_persistence_failure_is_not_success(self):
        self.journal.record_submitted = lambda *args: (_ for _ in ()).throw(OSError("synthetic"))
        broker = self.broker({"success": True, "order_id": "FAKE-SL"})
        self.assertFalse(self.invoke(broker))
        self.assertFalse(self.invoke(broker))
        self.assertEqual(len(self.calls), 1)

suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(ProtectionMutationTests))
class ConditionalAcknowledgementTests(unittest.TestCase):
    def test_missing_identity_and_transport_are_unknown(self):
        tree = ast.parse((ROOT / "infrastructure/brokers/adapters/bingx_adapter.py").read_text())
        nodes = [node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.ClassDef))
                 and node.name in {"extract_bingx_order_id", "RateLimitAdmissionTimeout"}]
        cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "_BingXBroker")
        method = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == "_place_conditional_order")
        namespace = dict(Dict=typing.Dict, Any=typing.Any, math=math)
        exec(compile(ast.Module(body=nodes + [method], type_ignores=[]), "actual-conditional-method", "exec"), namespace)
        responses = [{"code": 0, "data": {"order": {}}}, None]
        responses += [{"code": 0, "data": {"orderId": identity}} for identity in (" ", True, 1.5)]
        responses += [{"code": 0, "data": {"orderId": identity}} for identity in ("FAKE-VALID", 123)]
        for response in responses:
            with self.subTest(response=response):
                calls = []
                def request(*args, **kwargs):
                    calls.append(True)
                    if response is None:
                        raise TimeoutError("synthetic")
                    return response
                broker = types.SimpleNamespace(_format_symbol_str=lambda symbol: symbol,
                    _format_price=lambda symbol, value: str(value), _format_quantity=lambda symbol, value: str(value),
                    _make_request=request, logger=types.SimpleNamespace(error=lambda *args: None))
                result = namespace["_place_conditional_order"](broker, "TESTUSDT", "SELL", "1", "9", "STOP_MARKET", "LONG")
                expected_id = response.get("data", {}).get("orderId") if response else None
                if expected_id in ("FAKE-VALID", 123):
                    self.assertTrue(result["success"])
                    self.assertEqual(result["order_id"], expected_id)
                else:
                    self.assertFalse(result["success"])
                    self.assertTrue(result["unknown_submission"])
                self.assertEqual(len(calls), 1)

suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(ConditionalAcknowledgementTests))
class ReconciliationIntegrityTests(unittest.TestCase):
    def test_inspect_labels_protection_as_local_evidence_only(self):
        journal = Journal(str(TMP / "inspect-protection.jsonl"))
        ref = journal.record_protection_unknown("TESTUSDT", "SELL", 1, "fake")
        journal.record_submitted(ref, "FAKE-PROTECTION", "fake")
        before = Path(journal.path).read_bytes()
        tree = ast.parse((ROOT / "infrastructure/execution/broker_reconciliation.py").read_text())
        cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "BrokerReconciliationService")
        method = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == "inspect")
        namespace = dict(Dict=typing.Dict, Any=typing.Any)
        exec(compile(ast.Module(body=[method], type_ignores=[]), "actual-inspection-method", "exec"), namespace)
        report = namespace["inspect"](types.SimpleNamespace(), types.SimpleNamespace(get_all_positions=lambda: []), journal)
        self.assertEqual(report["protection_evidence_status"], "LOCAL_JOURNAL_ONLY")
        self.assertEqual(report["protective_orders"][0]["order_id"], "FAKE-PROTECTION")
        self.assertEqual(report["journal_net_positions"], {})
        self.assertEqual(Path(journal.path).read_bytes(), before)

    def check(self, name):
        path = TMP / (name + "-corrupt.jsonl")
        path.write_text("{broken\n")
        journal = Journal(str(path))
        tree = ast.parse((ROOT / "infrastructure/execution/broker_reconciliation.py").read_text())
        cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "BrokerReconciliationService")
        method = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == name)
        namespace = dict(Dict=typing.Dict, Any=typing.Any)
        exec(compile(ast.Module(body=[method], type_ignores=[]), "actual-reconciliation-method", "exec"), namespace)
        effects = []
        def positions():
            effects.append("broker_read")
            return []
        service = types.SimpleNamespace(_process_position_closures=lambda *args: effects.append("closure"))
        report = namespace[name](service, types.SimpleNamespace(get_all_positions=positions), journal)
        self.assertTrue(report["errors"])
        self.assertEqual(effects, [])
        self.assertEqual(path.read_text(), "{broken\n")
        if name == "reconcile":
            self.assertFalse(report["in_sync"])

    def test_inspect_corrupt_journal_has_no_broker_read(self):
        self.check("inspect")

    def test_reconcile_corrupt_journal_has_no_closure_side_effect(self):
        self.check("reconcile")

suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(ReconciliationIntegrityTests))
class PendingProtectionEvidenceTests(unittest.TestCase):
    def query(self, order):
        tree = ast.parse((ROOT / "infrastructure/risk/active_position_manager.py").read_text())
        cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "ActivePositionManager")
        method = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == "_query_pending_stop_visibility")
        method.decorator_list = []
        namespace = dict(Any=typing.Any, Dict=typing.Dict, Optional=typing.Optional,
            ActivePositionManager=types.SimpleNamespace(_extract_float=float),
            time=types.SimpleNamespace(sleep=lambda delay: None), datetime=datetime,
            timezone=__import__("datetime").timezone,
            logger=types.SimpleNamespace(warning=lambda *args: None))
        exec(compile(ast.Module(body=[method], type_ignores=[]), "actual-pending-visibility-method", "exec"), namespace)
        broker = types.SimpleNamespace(get_pending_orders_evidence=lambda symbol: {"status": "OK", "orders": [order]})
        return namespace["_query_pending_stop_visibility"](broker, "TEST-USDT", "SELL", "LONG", 9, "FAKE-ID")

    def valid(self):
        return dict(symbol="TEST-USDT", type="STOP_MARKET", side="SELL", positionSide="LONG",
                    stopPrice=9, orderId="FAKE-ID", status="NEW")

    def test_terminal_or_unattributed_pending_order_not_verified(self):
        for change in ({"symbol": None}, {"symbol": "OTHER-USDT"}, {"status": "CANCELED"}, {"status": "FILLED"}):
            with self.subTest(change=change):
                order = self.valid()
                order.update(change)
                self.assertFalse(self.query(order)["verified"])

    def test_exact_pending_identity_and_symbol_verified(self):
        self.assertTrue(self.query(self.valid())["verified"])
        legacy = self.valid()
        legacy.pop("status")
        self.assertTrue(self.query(legacy)["verified"])

suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(PendingProtectionEvidenceTests))
result = unittest.TextTestRunner(verbosity=2).run(suite)
print("ISOLATION: clean child environment; transports/subprocess denied; operational reads and external writes denied")
scratch.cleanup()
raise SystemExit(0 if result.wasSuccessful() else 1)
