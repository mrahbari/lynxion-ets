#!/usr/bin/env python3
"""Run the focused BingX retry regression without credentials or network."""

import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SAFE_ENV = {
    "PATH": "/usr/bin:/bin",
    "TMPDIR": "/private/tmp",
    "PYTHONDONTWRITEBYTECODE": "1",
    "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
}


def _deny(*_args, **_kwargs):
    raise RuntimeError("ISOLATED_TEST_DENIED_NETWORK_OR_BROKER")


def _run_child():
    platform_keys = {"LC_CTYPE", "__CF_USER_TEXT_ENCODING"}
    if set(os.environ) - set(SAFE_ENV) - platform_keys:
        raise SystemExit("TEST_ISOLATION_FAIL: unexpected environment")
    if any(os.environ.get(key) != value for key, value in SAFE_ENV.items()):
        raise SystemExit("TEST_ISOLATION_FAIL: environment mismatch")
    sys.path.insert(0, str(ROOT))

    import socket
    import subprocess
    import tempfile
    import urllib.request
    import dotenv
    import requests

    socket.socket.connect = _deny
    socket.socket.connect_ex = _deny
    socket.create_connection = _deny
    urllib.request.urlopen = _deny
    subprocess.Popen = _deny
    os.system = _deny
    dotenv.load_dotenv = _deny
    dotenv.dotenv_values = _deny
    requests.sessions.Session.request = _deny

    with tempfile.TemporaryDirectory(prefix="lynxion-bingx-retry-test-") as log_root:
        import shared.log_paths
        shared.log_paths.logs_dir = lambda: Path(log_root)

        from infrastructure.brokers.adapters.bingx_adapter import _BingXBroker
        _BingXBroker.__init__ = _deny

        try:
            socket.create_connection(("127.0.0.1", 1))
        except RuntimeError:
            pass
        else:
            raise SystemExit("TEST_ISOLATION_FAIL: socket guard inactive")
        try:
            _BingXBroker({})
        except RuntimeError:
            pass
        else:
            raise SystemExit("TEST_ISOLATION_FAIL: broker guard inactive")

        print("TEST_ISOLATION_PASS: credentials empty, network and broker denied", flush=True)
        import pytest
        return pytest.main([
            "-q", "--disable-warnings", "-p", "no:cacheprovider",
            str(ROOT / "tests/unit/test_bingx_order_post_retry_safety.py"),
            str(ROOT / "tests/unit/test_b6_retry.py"),
            str(ROOT / "tests/unit/test_production_cli_preflight_safety.py"),
            str(ROOT / "tests/unit/test_telegram_notification_service.py"),
            str(ROOT / "tests/unit/test_runtime_submission_safety.py"),
            str(ROOT / "tests/unit/test_b1_guaranteed_protection.py"),
            str(ROOT / "tests/unit/test_b3_durable_recovery.py"),
            str(ROOT / "tests/unit/test_b4_broker_reconciliation.py") + "::test_unknown_order_with_flat_position_remains_recoverable",
        ])


if __name__ == "__main__":
    if sys.argv[1:] == ["--isolated-child"]:
        raise SystemExit(_run_child())
    if sys.argv[1:]:
        raise SystemExit("usage: run_isolated_bingx_retry_tests.py")
    os.chdir(ROOT)
    os.execve(sys.executable, [sys.executable, "-I", str(Path(__file__).resolve()),
                            "--isolated-child"], SAFE_ENV)
