"""Bounded local process supervision for a frozen public depth pilot.

This is not a trading runner. It starts only the committed public collector,
records child exit/staleness, and never manufactures missing book state.
"""

from __future__ import annotations

import argparse
import fcntl
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from typing import Any
from uuid import uuid4


COLLECTOR = Path(__file__).with_name("microstructure_pilot_7d.py")
# Leave five seconds of scheduling margin for the frozen <=30 s detection gate.
STALE_NS = 25_000_000_000
START_GRACE_NS = 25_000_000_000
RESTART_WINDOW_NS = 600_000_000_000
MAX_DEATHS_IN_WINDOW = 3


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.{uuid4().hex}.tmp")
    with tmp.open("x") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(tmp, path)


def read_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def health_problem(health: dict[str, Any] | None, pid: int, now_mono_ns: int) -> str | None:
    if health is None or health.get("pid") != pid:
        return "missing_or_wrong_pid_heartbeat"
    if not isinstance(health.get("heartbeat_monotonic_ns"), int):
        return "missing_monotonic_heartbeat"
    if now_mono_ns - health["heartbeat_monotonic_ns"] > STALE_NS:
        return "stale_process_heartbeat"
    for symbol in ("BTCUSDT", "ETHUSDT"):
        receipt = health.get("symbols", {}).get(symbol, {}).get("last_receipt_monotonic_ns")
        if not isinstance(receipt, int) or now_mono_ns - receipt > STALE_NS:
            return f"stale_{symbol}_feed"
    return None


def too_many_deaths(events: list[dict[str, Any]], now_ns: int) -> bool:
    return sum(event.get("kind") == "child_exit" and
               0 <= now_ns - event.get("utc_ns", 0) <= RESTART_WINDOW_NS
               for event in events) > MAX_DEATHS_IN_WINDOW


def supervise(activation_path: Path, contract_path: Path, poll_seconds: float = 2.0) -> int:
    activation = json.loads(activation_path.read_text())
    root = Path(activation["output_root"]).resolve()
    root.mkdir(parents=True, exist_ok=True)
    lock_handle = (root / "supervisor.lock").open("a+")
    fcntl.flock(lock_handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    state_path = root / "supervisor_state.json"
    state = read_json(state_path) or {"events": [], "status": "STARTING"}
    if state.get("status") == "TERMINAL_FAILURE":
        return 0  # Durable failure state prevents a launch-agent restart loop.
    stop_ns = int(activation["stop_utc_ns"])
    start_ns = int(activation["start_utc_ns"])
    if time.time_ns() >= stop_ns:
        return 0  # The manifest/state, not process exit status, is the verdict.

    child: subprocess.Popen[bytes] | None = None
    child_started_mono_ns = 0
    stream_grace_mono_ns = 0
    prior_clocks: tuple[int, int] | None = None
    log_stream = None

    def record(kind: str, **detail: Any) -> None:
        state["events"].append({"kind": kind, "utc_ns": time.time_ns(), **detail})
        state["status"] = kind.upper()
        atomic_json(state_path, state)

    try:
        while True:
            now_ns = time.time_ns()
            now_mono_ns = time.monotonic_ns()
            if prior_clocks is not None:
                delta_ns = (now_ns - prior_clocks[0]) - (now_mono_ns - prior_clocks[1])
                if abs(delta_ns) > 1_000_000_000:
                    record("wall_monotonic_discontinuity", delta_ns=delta_ns)
            prior_clocks = now_ns, now_mono_ns
            if child is None:
                if now_ns >= stop_ns:
                    break
                if too_many_deaths(state["events"], now_ns):
                    record("terminal_failure", reason="restart_budget_exhausted")
                    state["status"] = "TERMINAL_FAILURE"
                    atomic_json(state_path, state)
                    return 0
                log_path = root / "supervisor" / f"collector-{now_ns}.log"
                log_path.parent.mkdir(parents=True, exist_ok=True)
                log_stream = log_path.open("xb")
                child = subprocess.Popen(
                    [sys.executable, str(COLLECTOR), "--activation", str(activation_path),
                     "--contract", str(contract_path)],
                    stdout=log_stream, stderr=subprocess.STDOUT, start_new_session=True,
                )
                child_started_mono_ns = time.monotonic_ns()
                stream_grace_mono_ns = child_started_mono_ns if now_ns >= start_ns else 0
                record("child_start", pid=child.pid, log=str(log_path))

            exit_code = child.poll()
            if exit_code is not None:
                log_stream.close()
                record("child_exit", pid=child.pid, exit_code=exit_code)
                child, log_stream = None, None
                if exit_code == 0 and (read_json(root / "capture_manifest.json") or {}).get("completed_utc_ns"):
                    record("completed")
                    return 0
                time.sleep(min(poll_seconds, 2.0))
                continue

            if now_ns >= stop_ns:
                # Allow normal collector finalization. A stuck child is not healthy.
                try:
                    child.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    record("stale_at_stop", pid=child.pid)
                    child.send_signal(signal.SIGINT)
                    try:
                        child.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        child.kill()
                        child.wait()
                log_stream.close()
                child, log_stream = None, None
                break

            if now_ns >= start_ns and not stream_grace_mono_ns:
                stream_grace_mono_ns = time.monotonic_ns()
            if now_ns >= start_ns and time.monotonic_ns() - stream_grace_mono_ns > START_GRACE_NS:
                problem = health_problem(read_json(root / "health.json"), child.pid,
                                         time.monotonic_ns())
                if problem:
                    record("child_stale", pid=child.pid, reason=problem)
                    child.send_signal(signal.SIGINT)
                    try:
                        child.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        child.kill()
                        child.wait()
            time.sleep(poll_seconds)
    finally:
        if child is not None and child.poll() is None:
            child.send_signal(signal.SIGINT)
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()
        if log_stream is not None:
            log_stream.close()

    completed = bool((read_json(root / "capture_manifest.json") or {}).get("completed_utc_ns"))
    record("completed" if completed else "terminal_failure", reason="frozen_stop_boundary")
    if not completed:
        state["status"] = "TERMINAL_FAILURE"
        atomic_json(state_path, state)
    return 0  # A completed or durable terminal state must not be relaunched.


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--activation", required=True, type=Path)
    parser.add_argument("--contract", required=True, type=Path)
    args = parser.parse_args()
    raise SystemExit(supervise(args.activation, args.contract))
