import importlib.util
import json
import os
from pathlib import Path
import sys
import threading
import time


def module():
    path = Path(__file__).resolve().parents[2] / "scripts/microstructure_pilot_supervisor.py"
    spec = importlib.util.spec_from_file_location("microstructure_pilot_supervisor", path)
    loaded = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = loaded
    spec.loader.exec_module(loaded)
    return loaded


def test_health_requires_current_pid_and_both_recent_feeds():
    s = module()
    now = 100_000_000_000
    health = {"pid": 42, "heartbeat_monotonic_ns": now - 1_000_000_000,
              "symbols": {name: {"last_receipt_monotonic_ns": now - 1_000_000_000}
                          for name in ("BTCUSDT", "ETHUSDT")}}
    assert s.health_problem(health, 42, now) is None
    assert s.health_problem(health, 99, now) == "missing_or_wrong_pid_heartbeat"
    health["symbols"]["ETHUSDT"]["last_receipt_monotonic_ns"] = now - 31_000_000_000
    assert s.health_problem(health, 42, now) == "stale_ETHUSDT_feed"
    health["heartbeat_monotonic_ns"] = now - 31_000_000_000
    assert s.health_problem(health, 42, now) == "stale_process_heartbeat"
    health["heartbeat_monotonic_ns"] = now - 26_000_000_000
    health["symbols"]["ETHUSDT"]["last_receipt_monotonic_ns"] = now - 1_000_000_000
    assert s.health_problem(health, 42, now) == "stale_process_heartbeat"


def test_restart_budget_is_durable_and_bounded():
    s = module()
    now = 1_000_000_000_000
    events = [{"kind": "child_exit", "utc_ns": now - i * 1_000_000_000}
              for i in range(3)]
    assert not s.too_many_deaths(events, now)
    events.append({"kind": "child_exit", "utc_ns": now})
    assert s.too_many_deaths(events, now)
    assert not s.too_many_deaths(events, now + s.RESTART_WINDOW_NS + 1)


def test_atomic_supervisor_state_round_trip(tmp_path):
    s = module()
    path = tmp_path / "supervisor_state.json"
    value = {"events": [{"kind": "child_exit", "exit_code": -9}], "status": "CHILD_EXIT"}
    s.atomic_json(path, value)
    assert s.read_json(path) == value
    assert list(tmp_path.iterdir()) == [path]


def test_forced_child_death_is_recorded_and_restarted(tmp_path, monkeypatch):
    s = module()
    child_script = tmp_path / "fake_public_collector.py"
    child_script.write_text(
        "import json,os,pathlib,sys,time,uuid\n"
        "a=json.load(open(sys.argv[sys.argv.index('--activation')+1]));"
        "root=pathlib.Path(a['output_root']);stop=a['stop_utc_ns']\n"
        "while time.time_ns()<stop:\n"
        " now=time.monotonic_ns();h={'pid':os.getpid(),"
        "'heartbeat_monotonic_ns':now,'symbols':{x:{'last_receipt_monotonic_ns':now}"
        " for x in ('BTCUSDT','ETHUSDT')}}\n"
        " p=root/('health.'+uuid.uuid4().hex+'.tmp');p.write_text(json.dumps(h));"
        "os.replace(p,root/'health.json');time.sleep(.05)\n"
        "(root/'capture_manifest.json').write_text(json.dumps({'completed_utc_ns':time.time_ns()}))\n"
    )
    monkeypatch.setattr(s, "COLLECTOR", child_script)
    root = tmp_path / "capture"
    root.mkdir()
    now = time.time_ns()
    activation = tmp_path / "activation.json"
    activation.write_text(json.dumps({"output_root": str(root), "start_utc_ns": now,
                                      "stop_utc_ns": now + 6_000_000_000}))
    contract = tmp_path / "contract.md"
    contract.write_text("test only")
    result = []
    thread = threading.Thread(target=lambda: result.append(
        s.supervise(activation, contract, poll_seconds=.1)))
    thread.start()
    deadline = time.monotonic() + 3
    first_pid = None
    while time.monotonic() < deadline:
        state = s.read_json(root / "supervisor_state.json") or {}
        starts = [e for e in state.get("events", []) if e["kind"] == "child_start"]
        if starts:
            first_pid = starts[0]["pid"]
            break
        time.sleep(.05)
    assert first_pid is not None
    os.kill(first_pid, 9)
    thread.join(timeout=12)
    assert not thread.is_alive() and result == [0]
    events = s.read_json(root / "supervisor_state.json")["events"]
    assert any(e["kind"] == "child_exit" and e["pid"] == first_pid and e["exit_code"] == -9
               for e in events)
    assert len([e for e in events if e["kind"] == "child_start"]) >= 2
