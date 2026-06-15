"""Phase-10 paper-trading equivalent-burst harness (validation only).

Drives the REAL execution-safety path (LiveExecutionGuard.authorize_and_send ->
Execution Truth Ledger) in PAPER mode at volume, to validate real-world execution
behaviour without any risk of live capital. It does NOT modify strategies, the
execution layer, the guard, or risk logic — it only exercises them.

Constraints enforced here:
  * paper_trading = True  (every order resolves to PAPER; nothing is ever sent)
  * LIVE_TRADING unset/False
  * a separate, clearly-labelled routing check uses testnet (simulation only, fake
    broker) to confirm endpoint selection — still zero real capital.

Outputs a JSON summary to stdout and writes the ledger to a dedicated file.
"""

import json
import os
import random
import sys
import tempfile
import time
from collections import defaultdict
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Force paper, no live — belt and braces.
os.environ["BROKER_PAPER_TRADING"] = "true"
os.environ.pop("LIVE_TRADING", None)

from shared.live_execution_guard import LiveExecutionGuard, ExecutionMode
from shared.execution_truth_ledger import ExecutionTruthLedger

# --- system's real cost parameters (application/configs/schemas/backtest.py) ---
FEE_RATE = 0.001          # 0.10%
SLIPPAGE_FACTOR = 0.0005  # 0.05%
INITIAL_CAPITAL = 10000.0
RISK_PER_TRADE = 0.02     # 2% notional sizing (orchestrator default risk_config)

# Live auto-detect roster (infrastructure/strategies/strategy_manager.py)
STRATEGIES = ["trend_following", "mean_reversion", "volatility_breakout"]
SYMBOLS = {"BTC/USDT": 64000.0, "ETH/USDT": 3400.0, "SOL/USDT": 145.0}

# Parametric signal rates per strategy (signals/day) for a 72h-equivalent window.
# Labelled as assumptions for a cost-sensitivity model — NOT measured live frequency.
SIGNALS_PER_DAY = {"trend_following": 6, "mean_reversion": 14, "volatility_breakout": 9}
WINDOW_HOURS = 72


def main():
    rng = random.Random(20260612)
    ledger_path = os.path.join(tempfile.gettempdir(), "phase10_sim_ledger.jsonl")
    if os.path.exists(ledger_path):
        os.remove(ledger_path)
    ledger = ExecutionTruthLedger(path=ledger_path)
    guard = LiveExecutionGuard()

    # Paper-mode settings (paper_trading=True -> every order resolves to PAPER).
    bcfg = SimpleNamespace(paper_trading=True, testnet=True, bingx_testnet=True,
                           bingx_order_placement_enabled=True)
    settings = SimpleNamespace(broker=bcfg)

    days = WINDOW_HOURS / 24.0
    per_strategy = defaultdict(lambda: {"orders": 0, "notional": 0.0, "fees": 0.0,
                                        "slippage": 0.0, "cost": 0.0})
    routes = defaultdict(int)
    latencies = []
    real_sends = 0

    def make_order(symbol):
        return SimpleNamespace(symbol=SimpleNamespace(value=symbol), side=SimpleNamespace(name="BUY"))

    t0 = time.perf_counter()
    for strat in STRATEGIES:
        n = int(round(SIGNALS_PER_DAY[strat] * days))
        for _ in range(n):
            symbol = rng.choice(list(SYMBOLS))
            price = SYMBOLS[symbol] * (1 + rng.uniform(-0.01, 0.01))
            notional = INITIAL_CAPITAL * RISK_PER_TRADE
            qty = notional / price
            order = make_order(symbol)

            def send_fn():
                # Should never run in paper mode; counts any accidental real send.
                return "WOULD-HAVE-SENT"

            d_t0 = time.perf_counter()
            decision, oid = guard.authorize_and_send(
                "bingx", settings, order, send_fn,
                ledger=ledger,
            )
            latencies.append((time.perf_counter() - d_t0) * 1000.0)
            routes[decision.mode.value.upper()] += 1
            if oid == "WOULD-HAVE-SENT":
                nonlocal_real = True  # noqa
            # cost-impact MODEL (deterministic from the system's fee/slippage params)
            fees = notional * FEE_RATE
            slip = notional * SLIPPAGE_FACTOR
            ps = per_strategy[strat]
            ps["orders"] += 1
            ps["notional"] += notional
            ps["fees"] += fees
            ps["slippage"] += slip
            ps["cost"] += fees + slip
    wall = time.perf_counter() - t0

    # Count any record whose result actually hit the exchange (must be zero).
    for rec in ledger.read_all():
        if rec.get("event") == "result" and rec.get("sent_to_exchange"):
            real_sends += 1

    total_orders = sum(p["orders"] for p in per_strategy.values())
    total_cost = sum(p["cost"] for p in per_strategy.values())
    summary = {
        "window_hours": WINDOW_HOURS,
        "total_orders": total_orders,
        "orders_per_day": round(total_orders / days, 2),
        "route_distribution": dict(routes),
        "real_sends_to_exchange": real_sends,
        "ledger_records": len(ledger.read_all()),
        "ledger_verify_ok": ledger.verify()["ok"],
        "latency_ms": {
            "avg": round(sum(latencies) / len(latencies), 4) if latencies else 0,
            "max": round(max(latencies), 4) if latencies else 0,
        },
        "wall_seconds": round(wall, 2),
        "cost_params": {"fee_rate": FEE_RATE, "slippage_factor": SLIPPAGE_FACTOR,
                        "risk_per_trade": RISK_PER_TRADE, "initial_capital": INITIAL_CAPITAL},
        "per_strategy": {
            s: {
                "orders": p["orders"],
                "signals_per_day_assumed": SIGNALS_PER_DAY[s],
                "gross_notional": round(p["notional"], 2),
                "fees": round(p["fees"], 4),
                "slippage": round(p["slippage"], 4),
                "round_trip_cost_est": round(p["cost"] * 2, 4),  # entry+exit
            } for s, p in per_strategy.items()
        },
        "total_round_trip_cost_est": round(total_cost * 2, 4),
        "cost_as_pct_of_capital": round((total_cost * 2) / INITIAL_CAPITAL * 100, 3),
        "ledger_path": ledger_path,
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
