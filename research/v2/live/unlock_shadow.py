"""R31 — prospective calendar shadow of large insider unlock shorts (LOG ONLY; pre-registered 2026-11-26).

Daily: refresh the free DefiLlama emissions dataset weekly, find insider cliff unlocks (E47 definition) whose entry day
T-30 has just passed, and append the shadow entry (Binance daily close of T-30 for the token, BTC and ETH) to
data/v2_live/unlock_shadow.jsonl. No orders, no Telegram, no effect on any live sleeve. Outcomes are computed only by
experiments/r31_unlock_shadow_eval.py under the pre-registered rule (docs/v2/reports/R31_unlock_shadow_prereg_2026-11-26.md).
Usage: cd research/v2 && python3 -m live.unlock_shadow
"""
from __future__ import annotations

import json
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "experiments"))
import e47_token_unlocks as E47  # noqa: E402  (event definition, unchanged)
from live import binance_live_panel as lp  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
LOG = ROOT / "data" / "v2_live" / "unlock_shadow.jsonl"
STATE = ROOT / "data" / "v2_live" / "unlock_shadow_state.json"
DS = "https://defillama-datasets.llama.fi"
REFRESH_DAYS, LOOKBACK_DAYS, MIN_SIZE, MIN_ADV, GAP_DAYS = 7, 5, 0.01, 5e6, 44
DAY = 86_400_000


def _get_bytes(url: str) -> bytes:
    for i in range(3):
        try:
            return urllib.request.urlopen(url, timeout=60).read()
        except Exception:  # noqa: BLE001
            time.sleep(2 + 2 * i)
    raise RuntimeError(url)


def refresh(force: bool = False) -> int:
    """Weekly re-download of the emissions dataset (schedules can change); returns files written."""
    st = json.loads(STATE.read_text()) if STATE.exists() else {}
    if not force and time.time() - st.get("refreshed", 0) < REFRESH_DAYS * 86400:
        return 0
    names = json.loads(_get_bytes(f"{DS}/emissionsProtocolsList"))

    def one(n):
        try:
            b = _get_bytes(f"{DS}/emissions/{n}")
            json.loads(b)
            (E47.EM / f"{n}.json").write_bytes(b)
            return 1
        except Exception:  # noqa: BLE001
            return 0
    with ThreadPoolExecutor(8) as ex:
        n_ok = sum(ex.map(one, names))
    cg = _get_bytes("https://api.coingecko.com/api/v3/coins/list")
    (E47.EM / "_coingecko_coins_list.json").write_bytes(cg)
    st["refreshed"] = time.time()
    STATE.write_text(json.dumps(st))
    return n_ok


def daily(sym: str, end_ms: int, limit: int = 40) -> pd.DataFrame:
    k = lp._get(f"/fapi/v1/klines?symbol={sym}&interval=1d&endTime={end_ms - 1}&limit={limit}")
    d = pd.DataFrame([{"t": pd.Timestamp(int(r[0]), unit="ms", tz="UTC"), "close": float(r[4]), "qv": float(r[7])}
                      for r in k if int(r[6]) < end_ms])
    return d.set_index("t")


def logged() -> list:
    return [json.loads(x) for x in LOG.read_text().splitlines() if x.strip()] if LOG.exists() else []


def candidates(today: pd.Timestamp) -> list:
    """Insider cliff >= 1 % whose entry day T-30 lies in [today - LOOKBACK_DAYS, today - 1]."""
    out = []
    for name, sym in E47.mapping().items():
        for e in E47.events_for(name):
            entry_day = e["T"] - pd.Timedelta(days=30)
            if e["ins_size"] >= MIN_SIZE and today - pd.Timedelta(days=LOOKBACK_DAYS) <= entry_day <= today - pd.Timedelta(days=1):
                out.append({"name": name, "sym": sym, "T": e["T"], "entry_day": entry_day, "ins_size": e["ins_size"]})
    return out


def run(today: pd.Timestamp | None = None) -> list:
    today = today or pd.Timestamp.now(tz="UTC").normalize()
    have = logged()
    keys = {(x["name"], x["T"]) for x in have}
    last_by_sym = {}
    for x in have:
        last_by_sym[x["sym"]] = max(last_by_sym.get(x["sym"], ""), x["T"])
    new = []
    for c in sorted(candidates(today), key=lambda x: x["T"]):
        T = str(c["T"].date())
        if (c["name"], T) in keys:
            continue
        prev = last_by_sym.get(c["sym"])
        if prev and (c["T"] - pd.Timestamp(prev, tz="UTC")).days < GAP_DAYS:
            continue
        end = int((c["entry_day"] + pd.Timedelta(days=1)).timestamp() * 1000)     # close of T-30 is known at T-29 00:00
        try:
            tok, btc, eth = daily(c["sym"], end), daily("BTCUSDT", end, 2), daily("ETHUSDT", end, 2)
        except Exception:  # noqa: BLE001
            continue
        if tok.empty or tok.index[-1] != c["entry_day"]:
            continue
        adv = float(tok.qv.iloc[-30:].median())
        if adv < MIN_ADV:
            continue
        rec = {"logged_at": datetime.now(timezone.utc).isoformat(), "name": c["name"], "sym": c["sym"], "T": T,
               "entry_day": str(c["entry_day"].date()), "ins_size": round(float(c["ins_size"]), 6), "adv30": adv,
               "entry": float(tok.close.iloc[-1]), "btc": float(btc.close.iloc[-1]), "eth": float(eth.close.iloc[-1])}
        new.append(rec)
        last_by_sym[c["sym"]] = T
        keys.add((c["name"], T))
    if new:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG, "a") as fh:
            for r in new:
                fh.write(json.dumps(r) + "\n")
    return new


def main():
    n = refresh()
    new = run()
    print(f"{datetime.now(timezone.utc):%Y-%m-%d %H:%M} refresh={n} new_shadow_entries={len(new)} "
          f"{[(r['sym'], r['T'], round(r['ins_size'], 3)) for r in new]}")


if __name__ == "__main__":
    main()
