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
OWNED = STATE_DIR / "owned_symbols.json"   # read by the platform BingX adapter (sleeve isolation)
MIN_ORDER_NOTIONAL = 6.0


def limits() -> dict:
    """Sizing/risk limits from the platform .env (call after load_env)."""
    import os
    return {"book": float(os.getenv("RISK_VST_MAX_PORTFOLIO_NOTIONAL_USDT", "3200")),     # gross notional
            "max_order": float(os.getenv("MAX_ORDER_NOTIONAL_AMOUNT", "201")),
            "max_positions": int(os.getenv("MAX_TOTAL_POSITIONS", "50")),
            # disaster stop, price distance from entry. Dev-period check (E5_stop_check_dev.csv):
            # 10-35% stops cut SR 1.94 -> 0.43-1.42; 50% keeps 1.79 and lowers max DD.
            "stop_pct": float(os.getenv("V2_STOP_LOSS_PCT", "50")) / 100}


def load_env():
    try:
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env", override=True)
    except ImportError:
        pass


def telegram(subject: str, body: str, level: str = "info"):
    try:
        from infrastructure.services.risk_alerts import TelegramNotificationService
        TelegramNotificationService().send_notification(body, subject, level, parse_mode="HTML")
    except Exception:  # noqa: BLE001
        print("telegram failed", file=sys.stderr)


def notify_trade(o: dict, r: dict, px: float):
    """One Telegram message per executed (or failed) order."""
    ok = r.get("code") == 0
    action = ("CLOSE" if o.get("close_all") else "REDUCE") if o["reduce"] else "OPEN/ADD"
    body = (f"{'✅' if ok else '❌'} {action} {o['positionSide']} {o['symbol']}\n"
            f"{o['side']} qty {o['qty']} @ ~{px:g} | notional ~{o['notional']:.2f} USDT")
    if not ok:
        body += f"\nerror {r.get('code')}: {r.get('msg')}"
    telegram("XS-COMBO-V1 trade (VST)", body, "info" if ok else "warning")
    time.sleep(1.0)     # Telegram per-chat rate limit


def platform_adapter():
    """The real platform BingX adapter (settings from .env). Must be the VST host."""
    from bootstrap.settings.loaders import load_settings
    from infrastructure.brokers.adapters.bingx_adapter import BingXBrokerAdapter
    b = load_settings().broker
    ad = BingXBrokerAdapter({"api_key": b.bingx_api_key, "secret_key": b.bingx_secret_key,
                             "testnet": b.bingx_testnet, "passphrase": getattr(b, "bingx_passphrase", "")})
    if "open-api-vst" not in ad._broker.base_url:
        raise RuntimeError("platform adapter is not on the VST host; refusing to place stops")
    return ad


def owned() -> set[str] | None:
    """Symbols (BTCUSDT form) owned by this sleeve; None if never published."""
    if not OWNED.exists():
        return None
    return {x.replace("-", "") for x in json.loads(OWNED.read_text())["symbols"]}


def publish_owned(symbols) -> None:
    """Atomic write so the platform never reads a partial file."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    tmp = OWNED.with_suffix(".tmp")
    tmp.write_text(json.dumps({"symbols": sorted({s.replace("-", "") for s in symbols}),
                               "updated": datetime.now(timezone.utc).isoformat()}, indent=1))
    tmp.replace(OWNED)


def ensure_stops(cli: BingXVST, contracts: dict, stop_pct: float) -> dict:
    """Every open position side gets exactly one closePosition STOP_MARKET at entry*(1 -/+ stop_pct).
    Orphan stops (no position) are cancelled. Idempotent; safe to run daily."""
    mine = owned() or set()
    pos = [x for x in cli.positions() if float(x.get("positionAmt") or 0) != 0
           and x["symbol"].replace("-", "") in mine]
    stops: dict[tuple, list] = {}
    for o in cli.open_orders():
        if str(o.get("type")).upper() == "STOP_MARKET" and o["symbol"].replace("-", "") in mine:
            stops.setdefault((o["symbol"], str(o.get("positionSide")).upper()), []).append(o)
    placed = kept = failed = cancelled = 0
    live = set()
    ad = platform_adapter()
    for x in pos:
        bx = x["symbol"]; side = str(x.get("positionSide")).upper(); live.add((bx, side))
        entry = float(x.get("avgPrice") or 0)
        if entry <= 0:
            failed += 1; continue
        prec = int(contracts.get(bx.replace("-", ""), {}).get("pricePrecision", 6))
        tgt = round(entry * (1 - stop_pct) if side == "LONG" else entry * (1 + stop_pct), prec)
        have = stops.get((bx, side), [])
        if len(have) == 1 and abs(float(have[0].get("stopPrice") or 0) / tgt - 1) < 0.02:
            kept += 1; continue
        for o in have:
            ad._broker.cancel_order(str(o["orderId"]), bx); cancelled += 1
        qty = abs(float(x.get("positionAmt") or 0))
        r = ad._broker._place_conditional_order(bx, "SELL" if side == "LONG" else "BUY", f"{qty}",
                                                f"{tgt:.{prec}f}", "STOP_MARKET", side)
        log({"event": "stop", "symbol": bx, "positionSide": side, "entry": entry, "stopPrice": tgt,
             "resp": {k: v for k, v in r.items() if k != "response"}})
        if r.get("success"):
            placed += 1
        else:
            failed += 1
        time.sleep(0.25)
    for key, orders in stops.items():
        if key not in live:
            for o in orders:
                ad._broker.cancel_order(str(o["orderId"]), key[0]); cancelled += 1
    res = {"positions": len(pos), "placed": placed, "kept": kept, "cancelled": cancelled, "failed": failed}
    log({"event": "ensure_stops", **res})
    return res


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


def current_positions(cli: BingXVST, only: set[str] | None = None) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for x in cli.positions():
        if only is not None and x["symbol"].replace("-", "") not in only:
            continue
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
                           "qty": abs(q), "notional": round(notional, 2), "reduce": reduce, "close_all": close_all})
    # reducing orders first (frees margin)
    return sorted(orders, key=lambda o: (not o["reduce"], o["symbol"]))


def rebalance(cli: BingXVST, book: float, dry: bool, asof: pd.Timestamp, lim: dict) -> dict:
    contracts = BingXVST.contracts()
    prices = BingXVST.prices()
    allpos = current_positions(cli)
    mine = owned()
    if mine is None:                      # first run with isolation: every open position is ours
        mine = set(allpos)
    foreign = set(allpos) - mine          # platform positions: never trade these symbols
    targets = target_weights(asof, {k: v for k, v in contracts.items() if k not in foreign})
    pos = {k: v for k, v in allpos.items() if k in mine}
    publish_owned(set(targets.index) | set(pos))   # before any order: platform keeps out
    orders = plan_orders(targets, book, pos, prices, contracts)
    gross = float(targets.abs().sum() * book)
    if (gross > book * 1.05 or len(targets) > lim["max_positions"]
            or any(o["notional"] > lim["max_order"] and not o["reduce"] for o in orders)):
        raise RuntimeError(f"safety cap violated: gross={gross:.0f} names={len(targets)} "
                           f"max order={max((o['notional'] for o in orders), default=0)}")
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
        notify_trade(o, r, prices[o["symbol"]])
        if r.get("code") == 0:
            ok += 1
        else:
            fail += 1
        time.sleep(0.25)
    st = state(); st["leverage_set"] = sorted(lev_done)
    if not dry:
        st["last_rebalance"] = str(asof.date())
    save_state(st)
    if not dry:
        publish_owned(set(targets.index) | set(current_positions(cli, mine | set(targets.index))))
    stops = ensure_stops(cli, contracts, lim["stop_pct"]) if not dry else {}
    nL = int((targets > 0).sum()); nS = int((targets < 0).sum())
    summary = {"asof": str(asof.date()), "dry": dry, "longs": nL, "shorts": nS, "orders": len(orders), "ok": ok,
               "fail": fail, "book": book, "stops": stops, "top_long": list(targets.tail(5).index), "top_short": list(targets.head(5).index)}
    log({"event": "rebalance_summary", **summary})
    return summary


def report(cli: BingXVST) -> dict:
    b = cli.balance(); mine = owned()
    pos = [x for x in cli.positions() if mine is None or x["symbol"].replace("-", "") in mine]
    eq = float(b.get("equity") or 0)              # account-wide (shared with the platform sleeve)
    upnl = sum(float(x.get("unrealizedProfit") or 0) for x in pos)   # this sleeve only
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


def closed_since_rebalance(cli: BingXVST) -> list[str]:
    """Target names from the last rebalance that no longer have a position (e.g. stopped out)."""
    last = state().get("last_rebalance")
    f = STATE_DIR / "targets" / f"{last}.json"
    if not last or not f.exists():
        return []
    tg = json.loads(f.read_text())
    have = current_positions(cli, owned() or set(tg))
    out = []
    for s, w in tg.items():
        side = "LONG" if w > 0 else "SHORT"
        if have.get(s, {}).get(side, 0) == 0:
            out.append(f"{s} {side}")
    return sorted(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["auto", "rebalance", "report"], default="auto")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--book", type=float, default=None, help="gross notional; default RISK_VST_MAX_PORTFOLIO_NOTIONAL_USDT")
    a = ap.parse_args()
    load_env()
    lim = limits()
    book = a.book if a.book is not None else lim["book"]
    cli = BingXVST()
    now = pd.Timestamp.now(tz="UTC")
    asof = now.normalize()
    try:
        msgs = []
        if a.mode in ("auto", "report"):
            r = report(cli)
            msgs.append(f"Account equity {r['equity']:.2f} VST (since start {r['pnl_since_start']:+.2f}, all sleeves)\n"
                        f"XS-COMBO: positions {r['positions']} | gross {r['gross_notional']:.0f} | "
                        f"unrealized {r['unrealized']:+.2f}")
            gone = closed_since_rebalance(cli)
            if gone:
                msgs.append(f"Closed since last rebalance (stop?): {', '.join(gone)}")
            if not a.dry_run:
                st = ensure_stops(cli, BingXVST.contracts(), lim["stop_pct"])
                msgs.append(f"Stops: {st['placed'] + st['kept']}/{st['positions']} protected, failed {st['failed']}")
        due = a.mode == "rebalance"
        if a.mode == "auto":
            last = state().get("last_rebalance")
            due = last is None or (asof.date() - pd.Timestamp(last).date()).days >= S.PARAMS["rebalance_every"]
        if due:
            if STOP.exists():
                msgs.append("STOP file present: rebalance skipped")
            else:
                s = rebalance(cli, book, a.dry_run, asof, lim)
                msgs.append(f"Rebalance {s['asof']}{' (dry-run)' if s['dry'] else ''}: {s['longs']} long / "
                            f"{s['shorts']} short, book {book:.0f}, orders ok {s['ok']} fail {s['fail']} of {s['orders']}")
                if s.get("stops"):
                    msgs.append(f"Stops ({lim['stop_pct']:.0%}): placed {s['stops']['placed']} kept {s['stops']['kept']} "
                                f"failed {s['stops']['failed']}")
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
