"""Latest real order-flow values per symbol for the execution confirmation stage (roadmap E14).

DecisionPipeline's OBI/CVD confirmation used to read ``obi_ratio``/``cvd`` from the strategy's latest bar,
which never carries them, so built-in defaults always passed. The monitoring loop now records real values
here from BingX public data:
  obi  = (bid qty - ask qty) / (bid qty + ask qty) over the top-20 book levels
  cvd  = aggressive buy quote volume - aggressive sell quote volume over recent public trades (last 5 min)
Process-local, in memory; readers get None when a symbol has no value or the value is older than max_age_s.
"""
from __future__ import annotations

import threading
import time
from typing import Dict, Iterable, Optional, Tuple

CVD_WINDOW_MS = 300_000
_lock = threading.Lock()
_store: Dict[str, dict] = {}


def norm(symbol) -> str:
    s = getattr(symbol, "value", symbol)
    return str(s).upper().replace("-", "").replace("_", "").replace("/", "")


def book_imbalance(bids: Iterable[Tuple[float, float]], asks: Iterable[Tuple[float, float]]) -> Optional[float]:
    b = sum(float(q) for _, q in bids)
    a = sum(float(q) for _, q in asks)
    return (b - a) / (b + a) if b + a > 0 else None


def trade_delta(trades: Iterable[dict], now_ms: Optional[int] = None) -> Optional[float]:
    """BingX public trades: isBuyerMaker True -> the seller was aggressive."""
    trades = list(trades)
    if not trades:
        return None
    end = now_ms or max(int(t.get("time", 0)) for t in trades)
    recent = [t for t in trades if int(t.get("time", 0)) >= end - CVD_WINDOW_MS]
    if not recent:
        return None
    return sum(-float(t["quoteQty"]) if t.get("isBuyerMaker") else float(t["quoteQty"]) for t in recent)


def record(symbol, obi: Optional[float], cvd: Optional[float], ts: Optional[float] = None) -> None:
    if obi is None or cvd is None:
        return
    with _lock:
        _store[norm(symbol)] = {"obi": float(obi), "cvd": float(cvd), "ts": ts if ts is not None else time.time()}


def get(symbol, max_age_s: float = 180.0) -> Optional[dict]:
    with _lock:
        v = _store.get(norm(symbol))
    if v is None:
        return None
    age = time.time() - v["ts"]
    return {**v, "age_s": age} if age <= max_age_s else None


def clear() -> None:
    with _lock:
        _store.clear()
