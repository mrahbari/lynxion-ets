"""XS-COMBO-V1 forward paper trading on BingX VST.

  python3 -m live.rebalancer --mode auto            # daily: equity report; rebalance when 7 days elapsed
  python3 -m live.rebalancer --mode rebalance --dry-run
  python3 -m live.rebalancer --mode report

Data in: Binance public REST (daily klines + funding) -> same signal code as the frozen backtest.
Orders out: BingX VST only (hard-coded demo host). Crypto PERPETUAL contracts only.
Kill switch: create data/v2_live/STOP to block all orders.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from lib import backtest as bt, panel as pn  # noqa: E402
from live import binance_live_panel as lp  # noqa: E402
from live.bingx_vst import BingXVST  # noqa: E402
from strategies import xs_combo_v1 as S  # noqa: E402

STATE_DIR = ROOT / "data" / "v2_live"
STATE = STATE_DIR / "state.json"
LEDGER = STATE_DIR / "orders.jsonl"
EQUITY = STATE_DIR / "equity.csv"
STOP = STATE_DIR / "STOP"
DEFAULT_BOOK = 20_000.0          # gross notional (VST): 10k long + 10k short
MAX_ORDER_NOTIONAL = 2_000.0
MIN_ORDER_NOTIONAL = 6.0


def load_env():
    try:
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env", override=True)
    except ImportError:
        pass


def telegram(subject: str, body: str):
    try:
        from infrastructure.services.risk_alerts import TelegramNotificationService
        TelegramNotificationService().send_notification(body, subject, "info", parse_mode="HTML")
    except Exception:  # noqa: BLE001
        print("telegram failed", file=sys.stderr)


def state() -> dict:
    return json.loads(STATE.read_text()) if STATE.exists() else {}


def save_state(s: dict):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(s, indent=1, default=str))


def log(rec: dict):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    rec["ts"] = datetime.now(timezone.utc).isoformat()
    with open(LEDGER, "a") as fh:
        fh.write(json.dumps(rec, default=str) + "\n")


def target_weights(asof: pd.Timestamp, contracts: dict) -> pd.Series:
    syms = lp.universe_symbols()["symbol"].tolist()          # crypto PERPETUAL, TRADING
    p = lp.build(asof, days=60, symbols=syms)
    m = pn.universe_mask(p)
    m.loc[:, [c for c in m.columns if c not in contracts]] = False   # tradable on BingX
    w = bt.rank_long_short(S.signal(p, m), m, frac=S.PARAMS["frac"], gross=S.PARAMS["gross"],
                           min_names=S.PARAMS["min_names"])
    row = w.loc[asof]
    return row[row != 0].sort_values()


def _round_qty(q: float, prec: int) -> float:
    f = 10 ** prec
    return math.floor(abs(q) * f) / f


def current_positions(cli: BingXVST) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for x in cli.positions():
        amt = abs(float(x.get("positionAmt") or 0))
        if amt == 0:
            continue
        s = x["symbol"].replace("-", "")
        d = out.setdefault(s, {"LONG": 0.0, "SHORT": 0.0})
        d[str(x.get("positionSide")).upper()] += amt
    return out


def plan_orders(targets: pd.Series, book: float, pos: dict, prices: dict, contracts: dict) -> list[dict]:
    orders = []
    for s in sorted(set(targets.index) | set(pos)):
        if s not in contracts or s not in prices:
            continue
        c = contracts[s]; px = prices[s]; prec = int(c.get("quantityPrecision", 0))
        tgt = float(targets.get(s, 0.0)) * book / px
        L = pos.get(s, {}).get("LONG", 0.0); Sh = pos.get(s, {}).get("SHORT", 0.0)
        tl, ts = (max(tgt, 0.0), max(-tgt, 0.0))
        for side_name, have, want in (("LONG", L, tl), ("SHORT", Sh, ts)):
            delta = want - have
            close_all = want == 0 and have > 0
            q = have if close_all else _round_qty(delta, prec)
            if q == 0:
                continue
            notional = abs(q) * px
            if not close_all and notional < max(MIN_ORDER_NOTIONAL, float(c.get("tradeMinUSDT") or 0)):
                continue
            if side_name == "LONG":
                side = "BUY" if delta > 0 else "SELL"
            else:
                side = "SELL" if delta > 0 else "BUY"
            reduce = (side_name == "LONG" and side == "SELL") or (side_name == "SHORT" and side == "BUY")
            orders.append({"symbol": s, "bx": c["symbol"], "side": side, "positionSide": side_name,
                           "qty": abs(q), "notional": round(notional, 2), "reduce": reduce})
    # reducing orders first (frees margin)
    return sorted(orders, key=lambda o: (not o["reduce"], o["symbol"]))


def rebalance(cli: BingXVST, book: float, dry: bool, asof: pd.Timestamp) -> dict:
    contracts = BingXVST.contracts()
    prices = BingXVST.prices()
    targets = target_weights(asof, contracts)
    pos = current_positions(cli)
    orders = plan_orders(targets, book, pos, prices, contracts)
    gross = float(targets.abs().sum() * book)
    if gross > book * 1.05 or any(o["notional"] > MAX_ORDER_NOTIONAL and not o["reduce"] for o in orders):
        raise RuntimeError(f"safety cap violated: gross={gross:.0f} max order={max((o['notional'] for o in orders), default=0)}")
    (STATE_DIR / "targets").mkdir(parents=True, exist_ok=True)
    (STATE_DIR / "targets" / f"{asof.date()}.json").write_text(json.dumps(targets.round(6).to_dict(), indent=1))
    ok = fail = 0
    lev_done = set(state().get("leverage_set", []))
    for o in orders:
        if dry:
            continue
        if STOP.exists():
            log({"event": "STOPPED", "remaining": len(orders) - ok - fail})
            break
        key = f"{o['bx']}:{o['positionSide']}"
        if not o["reduce"] and key not in lev_done:
            r = cli.set_leverage(o["bx"], o["positionSide"], 1)
            log({"event": "leverage", "key": key, "resp": r})
            if r.get("code") == 0:
                lev_done.add(key)
            else:
                fail += 1
                continue
        cid = f"xs{asof.strftime('%y%m%d')}{o['symbol'][:10]}{o['positionSide'][0]}{o['side'][0]}"[:40]
        r = cli.market_order(o["bx"], o["side"], o["positionSide"], o["qty"], cid)
        log({"event": "order", **o, "client_id": cid, "resp": r})
        if r.get("code") == 0:
            ok += 1
        else:
            fail += 1
        time.sleep(0.25)
    st = state(); st["leverage_set"] = sorted(lev_done)
    if not dry:
        st["last_rebalance"] = str(asof.date())
    save_state(st)
    nL = int((targets > 0).sum()); nS = int((targets < 0).sum())
    summary = {"asof": str(asof.date()), "dry": dry, "longs": nL, "shorts": nS, "orders": len(orders), "ok": ok,
               "fail": fail, "book": book, "top_long": list(targets.tail(5).index), "top_short": list(targets.head(5).index)}
    log({"event": "rebalance_summary", **summary})
    return summary


def report(cli: BingXVST) -> dict:
    b = cli.balance(); pos = cli.positions()
    eq = float(b.get("equity") or 0); upnl = float(b.get("unrealizedProfit") or 0)
    st = state()
    if "start_equity" not in st:
        st["start_equity"] = eq; st["start_date"] = str(datetime.now(timezone.utc).date()); save_state(st)
    n = sum(1 for x in pos if float(x.get("positionAmt") or 0) != 0)
    gross = sum(abs(float(x.get("positionValue") or 0)) for x in pos)
    row = {"date": str(datetime.now(timezone.utc).date()), "equity": eq, "unrealized": upnl, "positions": n,
           "gross_notional": round(gross, 2), "pnl_since_start": round(eq - st["start_equity"], 2)}
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    new = not EQUITY.exists()
    with open(EQUITY, "a") as fh:
        if new:
            fh.write(",".join(row) + "\n")
        fh.write(",".join(str(v) for v in row.values()) + "\n")
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["auto", "rebalance", "report"], default="auto")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--book", type=float, default=DEFAULT_BOOK)
    a = ap.parse_args()
    load_env()
    cli = BingXVST()
    now = pd.Timestamp.now(tz="UTC")
    asof = now.normalize()
    try:
        msgs = []
        if a.mode in ("auto", "report"):
            r = report(cli)
            msgs.append(f"Equity {r['equity']:.2f} VST | PnL since start {r['pnl_since_start']:+.2f} | "
                        f"positions {r['positions']} | gross {r['gross_notional']:.0f}")
        due = a.mode == "rebalance"
        if a.mode == "auto":
            last = state().get("last_rebalance")
            due = last is None or (asof.date() - pd.Timestamp(last).date()).days >= S.PARAMS["rebalance_every"]
        if due:
            if STOP.exists():
                msgs.append("STOP file present: rebalance skipped")
            else:
                s = rebalance(cli, a.book, a.dry_run, asof)
                msgs.append(f"Rebalance {s['asof']}{' (dry-run)' if s['dry'] else ''}: {s['longs']} long / "
                            f"{s['shorts']} short, orders ok {s['ok']} fail {s['fail']} of {s['orders']}")
        text = "\n".join(msgs)
        print(text)
        if not a.dry_run:
            telegram("Lynxion XS-COMBO-V1 (VST)", text)
    except Exception as e:  # noqa: BLE001
        log({"event": "error", "error": repr(e), "tb": traceback.format_exc()})
        telegram("Lynxion XS-COMBO-V1 ERROR", f"{type(e).__name__}: {e}")
        raise


if __name__ == "__main__":
    main()
