#!/usr/bin/env python3
"""Run selected offline execution tests with credentials and transport disabled.

The launcher re-execs a clean child before importing pytest or project code.
This is a test boundary, not a production execution entry point.
"""

import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ALLOWED_ENV = {"PATH": "/usr/bin:/bin", "TMPDIR": "/private/tmp",
               "PYTHONDONTWRITEBYTECODE": "1", "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"}
BROKER_CLASSES = (
    ("infrastructure.brokers.adapters.bingx_adapter", "BingXBrokerAdapter"),
    ("infrastructure.brokers.adapters.bingx_adapter", "_BingXBroker"),
    ("infrastructure.brokers.adapters.binance_adapter", "BinanceBrokerAdapter"),
    ("infrastructure.brokers.adapters.mexc_adapter", "MEXCBrokerAdapter"),
    ("infrastructure.brokers.adapters.phemex_adapter", "PhemexBrokerAdapter"),
)
ALLOWED_TEST_FILES = frozenset({
    "tests/unit/test_epic01_maker_execution.py",
    "tests/unit/test_epic01_observed_mtf.py",
    "tests/unit/test_epic01_indicator_causality.py",
    "tests/unit/test_epic01_hyperopt_objective_binding.py",
    "tests/unit/test_structural_pullback_failure_v1.py",
    "tests/unit/test_extreme_mover_opportunity.py",
    "tests/unit/test_epic01_wfo_calendar_windows.py",
    "tests/unit/test_epic01_wfo_cv_error_gate.py",
    "tests/unit/test_epic01_wfo_empty_windows_gate.py",
    "tests/unit/test_epic01_wfo_loader_15m.py",
    "tests/unit/test_epic01_wfo_missing_strategy_gate.py",
    "tests/unit/test_epic01_wfo_rerun_isolation.py",
    "tests/unit/test_epic01_wfo_strategy_wiring.py",
    "tests/unit/test_epic01_wfo_train_only_gate.py",
    "tests/unit/test_opportunity_radar_v1.py",
    "tests/unit/test_historical_closed_bar_source.py",
    "tests/unit/test_epic01_backtest_next_available.py",
    "tests/unit/test_epic01_gap_stop_pricing.py",
    "tests/unit/test_epic01_gap_entry_protection.py",
    "tests/unit/test_epic01_closed_bar_availability.py",
    "tests/unit/test_epic01_strategy_provider_clock.py",
    "tests/unit/test_short_position_lifecycle.py",
    "tests/unit/test_runtime_submission_safety.py",
    "tests/unit/test_telegram_notification_service.py",
    "tests/unit/test_b3_durable_recovery.py",
    "tests/unit/test_p0_submission_safety.py",
    "tests/unit/test_b4_broker_reconciliation.py",
    "tests/unit/test_execution_truth_ledger.py",
    "tests/unit/test_b2_idempotency.py",
    "tests/unit/test_b1_guaranteed_protection.py",
})


def _deny(*_args, **_kwargs):
    raise RuntimeError("ISOLATED_TEST_DENIED_NETWORK_OR_AUTHENTICATED_BROKER")


def _child(test_targets):
    platform_keys = {"LC_CTYPE", "__CF_USER_TEXT_ENCODING"}
    if (set(os.environ) - set(ALLOWED_ENV) - platform_keys or
            any(os.environ.get(key) != value for key, value in ALLOWED_ENV.items())):
        raise SystemExit("TEST_ISOLATION_FAIL: unexpected child environment")
    if (ROOT / ".env").exists():
        raise SystemExit("TEST_ISOLATION_FAIL: worktree .env exists")
    sys.path.insert(0, str(ROOT))

    import socket
    import subprocess
    import tempfile
    import urllib.request

    socket.socket.connect = _deny
    socket.socket.connect_ex = _deny
    socket.create_connection = _deny
    urllib.request.urlopen = _deny
    subprocess.Popen = _deny
    os.system = _deny

    import dotenv
    import requests

    dotenv.load_dotenv = _deny
    requests.sessions.Session.request = _deny

    # Import-time production logging otherwise writes into this checkout.
    log_temp = tempfile.TemporaryDirectory(prefix="lynxion-isolated-logs-")
    import shared.log_paths

    shared.log_paths.logs_dir = lambda: Path(log_temp.name)

    from importlib import import_module

    for module_name, class_name in BROKER_CLASSES:
        adapter_class = getattr(import_module(module_name), class_name)
        adapter_class.__init__ = _deny

    # Prove the installed guards before loading pytest or any test module.
    try:
        socket.socket().connect(("127.0.0.1", 1))
    except RuntimeError:
        pass
    else:
        raise SystemExit("TEST_ISOLATION_FAIL: socket guard inactive")
    try:
        getattr(import_module(BROKER_CLASSES[0][0]), BROKER_CLASSES[0][1])({})
    except RuntimeError:
        pass
    else:
        raise SystemExit("TEST_ISOLATION_FAIL: broker guard inactive")

    for guarded_call in (
        lambda: socket.create_connection(("127.0.0.1", 1)),
        lambda: requests.get("https://example.invalid/"),
        lambda: urllib.request.urlopen("https://example.invalid/"),
        lambda: dotenv.load_dotenv(),
        lambda: subprocess.Popen(["/usr/bin/true"]),
    ):
        try:
            guarded_call()
        except RuntimeError:
            pass
        else:
            raise SystemExit("TEST_ISOLATION_FAIL: transport/process guard inactive")
    for module_name, class_name in BROKER_CLASSES:
        try:
            getattr(import_module(module_name), class_name)({})
        except RuntimeError:
            pass
        else:
            raise SystemExit("TEST_ISOLATION_FAIL: broker guard inactive")

    print("TEST_ISOLATION_PASS: clean environment, dotenv/network/order clients denied", flush=True)
    if not test_targets:
        return 0
    if any(target.split("::", 1)[0] not in ALLOWED_TEST_FILES for target in test_targets):
        raise SystemExit("TEST_ISOLATION_FAIL: unreviewed test target")
    import pytest

    return pytest.main(["-q", "--disable-warnings", "-p", "no:cacheprovider", *test_targets])


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "--isolated-child":
        raise SystemExit(_child(sys.argv[2:]))
    if not sys.argv[1:]:
        raise SystemExit("usage: run_isolated_execution_tests.py TEST_NODE_ID [...] or --self-test")
    targets = [] if sys.argv[1:] == ["--self-test"] else sys.argv[1:]
    os.chdir(ROOT)
    os.execve(sys.executable, [sys.executable, "-I", str(Path(__file__).resolve()),
                            "--isolated-child", *targets], ALLOWED_ENV)
