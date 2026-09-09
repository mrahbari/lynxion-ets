import json
import subprocess
import sys


def _run_demo():
    completed = subprocess.run(
        [sys.executable, "scripts/phase10_paper_trading_burst.py"],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


def test_paper_demo_is_isolated_repeatable_and_never_sends_to_exchange():
    first = _run_demo()
    second = _run_demo()

    assert first["route_distribution"] == {"PAPER": 87}
    assert second["route_distribution"] == {"PAPER": 87}
    assert first["real_sends_to_exchange"] == second["real_sends_to_exchange"] == 0
    assert first["ledger_verify_ok"] is second["ledger_verify_ok"] is True
    assert first["ledger_records"] == second["ledger_records"] == 174

    unstable = {"latency_ms", "wall_seconds", "ledger_path"}
    assert {k: v for k, v in first.items() if k not in unstable} == {
        k: v for k, v in second.items() if k not in unstable
    }
