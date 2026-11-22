"""S1 — test platform strategies one at a time on BingX VST.

Run hourly (launchd com.lynxion.s1-rotation). The active strategy trades alone until it has
MIN_TRADES closed trades (journal label, entries since its start) or MAX_HOURS elapsed; then its
result is sent to Telegram, STRATEGY_ALLOWLIST in .env is switched to the next strategy and the
runner is restarted through the safe launcher. Open positions keep their exchange SL/TP and are
still managed by the position manager after the switch.

State: data/s1_rotation_state.json. `--status` prints progress without changing anything.
"""
from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env", override=False)
except ImportError:
    pass
STATE = ROOT / "data" / "s1_rotation_state.json"
ENV = ROOT / ".env"
JOURNAL = ROOT / "data" / "trade_journal.csv"
MIN_TRADES = int(os.getenv("S1_MIN_TRADES", "40"))
MAX_HOURS = float(os.getenv("S1_MAX_HOURS", "48"))

# (journal label, STRATEGY_ALLOWLIST value)
ORDER = [
    ("VWAPReversal", "VWAPReversal"),
    ("OIFootprint", "OIFootprint"),
    ("TrendFollow", "trend_following,TrendFollow"),
    ("MeanReversion", "mean_reversion"),
    ("MTFTrend", "mtf_trend"),
    ("SweepScalper", "sweep_scalper"),
    ("Breakout", "breakout"),
    ("volatility_breakout", "volatility_breakout"),
    ("Liquidity", "liquidity"),
]


def now() -> datetime:
    return datetime.now(timezone.utc)


def stats(label: str, since: str) -> dict:
    if not JOURNAL.exists():
        return {"n": 0}
    d = pd.read_csv(JOURNAL)
    d = d[(d.strategy == label) & (pd.to_datetime(d.entry_timestamp, utc=True, errors="coerce")
                                   >= pd.Timestamp(since))].sort_values("entry_timestamp")
    pnl = pd.to_numeric(d.pnl_usdt, errors="coerce").fillna(0.0)
    wins, losses = pnl[pnl > 0].sum(), -pnl[pnl < 0].sum()
    half = len(pnl) // 2
    return {"n": int(len(pnl)), "pnl": round(float(pnl.sum()), 2),
            "pf": round(float(wins / losses), 2) if losses else None,
            "win_rate": round(float((pnl > 0).mean()), 2) if len(pnl) else None,
            "first_half": round(float(pnl.iloc[:half].sum()), 2) if half else None,
            "second_half": round(float(pnl.iloc[half:].sum()), 2) if half else None}


def set_allowlist(value: str) -> None:
    lines = ENV.read_text().splitlines(keepends=True)
    out, done = [], False
    for line in lines:
        if line.startswith("STRATEGY_ALLOWLIST="):
            out.append(f"STRATEGY_ALLOWLIST={value}\n")
            done = True
        else:
            out.append(line)
    if not done:
        out.append(f"STRATEGY_ALLOWLIST={value}\n")
    tmp = ENV.with_suffix(".s1tmp")
    tmp.write_text("".join(out))
    os.replace(tmp, ENV)


def restart_runner() -> dict:
    pids = subprocess.run(["pgrep", "-f", "run_trading_system.py"], capture_output=True, text=True).stdout.split()
    for pid in pids:
        try:
            os.kill(int(pid), signal.SIGTERM)
        except ProcessLookupError:
            pass
    for _ in range(60):
        if not subprocess.run(["pgrep", "-f", "run_trading_system.py"], capture_output=True).stdout:
            break
        time.sleep(1)
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "lynxion_safe_testnet_launcher.py")],
                       capture_output=True, text=True, cwd=ROOT)
    try:
        return json.loads(r.stdout.strip().splitlines()[-1])
    except Exception:
        return {"launched": False, "reason": (r.stdout + r.stderr)[-300:]}


def telegram(text: str) -> None:
    try:
        from infrastructure.services.risk_alerts import send_telegram
        send_telegram(text)
    except Exception as exc:
        print(f"telegram failed: {exc}")


def save(state: dict) -> None:
    STATE.write_text(json.dumps(state, indent=2))


def start(state: dict, idx: int) -> None:
    label, allow = ORDER[idx]
    set_allowlist(allow)
    res = restart_runner()
    state.update(index=idx, started=now().isoformat(), launched=bool(res.get("launched")), launch=res)
    save(state)
    if res.get("launched"):
        telegram(f"🔁 <b>S1 strategy test</b>\n\n• Now testing alone: <code>{label}</code> "
                 f"({idx + 1}/{len(ORDER)})\n• Ends at {MIN_TRADES} closed trades or {MAX_HOURS:.0f}h")
    else:
        telegram(f"⚠️ <b>S1 rotation: runner restart blocked</b>\n\n• Strategy: <code>{label}</code>\n"
                 f"• {res.get('reason') or res}")


def main() -> None:
    state = json.loads(STATE.read_text()) if STATE.exists() else {"results": []}
    if "--status" in sys.argv:
        if "index" in state:
            label = ORDER[state["index"]][0]
            print(json.dumps({"testing": label, "since": state["started"],
                              **stats(label, state["started"]), "done": state["results"]}, indent=2))
        else:
            print("not started")
        return
    if "index" not in state:
        start(state, 0)
        return
    if state.get("finished"):
        return
    if not state.get("launched"):          # retry a blocked restart
        start(state, state["index"])
        return
    label = ORDER[state["index"]][0]
    s = stats(label, state["started"])
    hours = (now() - datetime.fromisoformat(state["started"])).total_seconds() / 3600
    if s["n"] < MIN_TRADES and hours < MAX_HOURS:
        return
    s.update(strategy=label, hours=round(hours, 1), started=state["started"])
    state["results"].append(s)
    telegram(f"📊 <b>S1 result: {label}</b>\n\n• Closed trades: {s['n']} in {hours:.0f}h\n"
             f"• PnL: <code>{s.get('pnl')} USDT</code> · PF {s.get('pf')} · win {s.get('win_rate')}\n"
             f"• Halves: {s.get('first_half')} / {s.get('second_half')} USDT")
    nxt = state["index"] + 1
    if nxt >= len(ORDER):
        state["finished"] = now().isoformat()
        save(state)
        telegram("✅ <b>S1 rotation finished</b> — all strategies tested. Runner keeps the last allowlist.")
        return
    save(state)
    start(state, nxt)


if __name__ == "__main__":
    main()
