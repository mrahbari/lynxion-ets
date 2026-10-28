"""Pure closed-M15 structural pullback-failure candidate detector.

No strategy, intent, broker, risk, network or future-outcome dependency.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta
from hashlib import sha256
from math import isfinite
from typing import Iterable, Optional, Tuple


M15 = timedelta(minutes=15)
BEAR = "BEARISH_STRUCTURAL_PULLBACK_FAILURE"
BULL = "BULLISH_STRUCTURAL_PULLBACK_FAILURE"


@dataclass(frozen=True)
class ResearchBar:
    symbol: str
    timeframe: timedelta
    open_time: datetime
    close_time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0


@dataclass(frozen=True)
class Candidate:
    candidate_id: str
    symbol: str
    timeframe: str
    direction: str
    detector_version: str
    contract_sha256: str
    dataset_sha256: str
    observation_time: datetime
    earliest_knowable_time: datetime
    signal_confirmation_time: datetime
    decision_time: datetime
    original_anchor_pivot_time: datetime
    anchor_confirmation_time: datetime
    original_recovery_pivot_time: datetime
    recovery_confirmation_time: datetime
    prior_structure: Tuple[Tuple[str, datetime, datetime, float], ...]
    recovery_closes: Tuple[Tuple[datetime, float], ...]
    failed_reclaim_level: float
    failed_reclaim_extreme: float
    trigger_close: float
    trigger_level: float
    structural_invalidation_level: float
    feature_provenance: str = "DERIVED_FROM_OBSERVED_OHLC"
    data_quality_status: str = "CONTIGUOUS_CLOSED_BARS"
    missing_data_annotations: Tuple[str, ...] = ()
    htf_context_status: str = "HTF_CONTEXT_UNAVAILABLE"


@dataclass(frozen=True)
class _Pivot:
    kind: str
    index: int
    confirmed: int
    value: float


def _valid(bar: ResearchBar) -> bool:
    return (bool(bar.symbol) and bar.timeframe == M15
            and bar.open_time.tzinfo is not None and bar.close_time.tzinfo is not None
            and bar.open_time.utcoffset() == timedelta(0)
            and bar.close_time.utcoffset() == timedelta(0)
            and bar.close_time - bar.open_time == M15
            and all(isfinite(float(x)) for x in
                    (bar.open, bar.high, bar.low, bar.close, bar.volume))
            and min(bar.open, bar.high, bar.low, bar.close) > 0
            and bar.volume >= 0 and bar.high >= max(bar.open, bar.close, bar.low)
            and bar.low <= min(bar.open, bar.close, bar.high))


def _new_pivot(bars: list, at: int) -> Optional[_Pivot]:
    center = at - 2
    if center < 2:
        return None
    near = (center - 2, center - 1, center + 1, center + 2)
    high = all(bars[center].high > bars[j].high for j in near)
    low = all(bars[center].low < bars[j].low for j in near)
    if high == low:
        return None
    return _Pivot("H" if high else "L", center, at,
                  bars[center].high if high else bars[center].low)


def _prior_chain(pivots: list, anchor: _Pivot, bars: list):
    direction = BEAR if anchor.kind == "L" else BULL
    wanted = ("H", "L", "H") if direction == BEAR else ("L", "H", "L")
    first = anchor.confirmed - 31
    previous = [p for p in pivots if first <= p.index < anchor.index]
    # Lexicographically latest eligible original-index chain, walking backward.
    for near in reversed(previous):
        if near.kind != wanted[2]:
            continue
        for middle in reversed(previous):
            if middle.kind != wanted[1] or middle.index >= near.index:
                continue
            for old in reversed(previous):
                if old.kind != wanted[0] or old.index >= middle.index:
                    continue
                if direction == BEAR:
                    valid = near.value < old.value and anchor.value < middle.value
                else:
                    valid = near.value > old.value and anchor.value > middle.value
                if valid:
                    return direction, (old, middle, near, anchor)
    return None


def _recovery_pair(bars: list, anchor_confirmed: int, p_original: int, direction: str):
    for second in range(anchor_confirmed + 2, p_original + 1):
        a, b, c = (bars[j].close for j in (second - 2, second - 1, second))
        if (a < b < c) if direction == BEAR else (a > b > c):
            return ((bars[second - 1].close_time, b), (bars[second].close_time, c))
    return None


def _reclaimed(bars: list, start: int, end: int, direction: str, level: float) -> bool:
    if direction == BEAR:
        return any(bars[j].high >= level for j in range(start, end + 1))
    return any(bars[j].low <= level for j in range(start, end + 1))


def _candidate(bars: list, direction: str, chain: tuple, p: _Pivot,
               recovery: tuple, at: int, contract_sha256: str,
               dataset_sha256: str) -> Candidate:
    anchor = chain[-1]
    level = chain[-2].value
    trigger_level = bars[p.index].low if direction == BEAR else bars[p.index].high
    observed = (max(b.high for b in bars[anchor.confirmed + 1:at + 1]) if direction == BEAR
                else min(b.low for b in bars[anchor.confirmed + 1:at + 1]))
    bar = bars[at]
    identity = "|".join(("STRUCTURAL_PULLBACK_FAILURE_V1", contract_sha256,
                         dataset_sha256, bar.symbol, "M15", direction,
                         anchor_time(bars, anchor), anchor_time(bars, p),
                         bar.close_time.strftime("%Y-%m-%dT%H:%M:%SZ")))
    event_id = sha256(identity.encode("utf-8")).hexdigest()
    prior = tuple((node.kind, bars[node.index].open_time,
                   bars[node.confirmed].close_time, node.value) for node in chain)
    return Candidate(event_id, bar.symbol, "M15", direction, "1.1-research",
                     contract_sha256, dataset_sha256, bar.close_time, bar.close_time,
                     bar.close_time, bar.close_time, bars[anchor.index].open_time,
                     bars[anchor.confirmed].close_time, bars[p.index].open_time,
                     bars[p.confirmed].close_time, prior, recovery, level, observed,
                     bar.close, trigger_level, level)


def anchor_time(bars: list, pivot: _Pivot) -> str:
    return bars[pivot.index].open_time.strftime("%Y-%m-%dT%H:%M:%SZ")


def _detect_segment(bars: list, contract_sha256: str, dataset_sha256: str) -> tuple:
    pivots = []
    anchors = []  # [direction, chain]
    setups = []  # [direction, chain, recovery pivot, recovery pair]
    emitted = []
    for at, bar in enumerate(bars):
        next_setups = []
        for direction, chain, p, recovery in setups:
            anchor = chain[-1]
            level = chain[-2].value
            if at > p.confirmed + 8 or _reclaimed(bars, at, at, direction, level):
                continue
            if at > p.confirmed:
                triggered = (bar.close < bars[p.index].low if direction == BEAR
                             else bar.close > bars[p.index].high)
                if triggered:
                    emitted.append(_candidate(bars, direction, chain, p, recovery,
                                              at, contract_sha256, dataset_sha256))
                    continue
            next_setups.append((direction, chain, p, recovery))
        setups = next_setups

        pivot = _new_pivot(bars, at)
        next_anchors = []
        for direction, chain in anchors:
            anchor = chain[-1]
            level = chain[-2].value
            if at > anchor.confirmed + 12 or _reclaimed(bars, at, at, direction, level):
                continue
            if (pivot is not None and pivot.index > anchor.confirmed
                    and pivot.kind == ("H" if direction == BEAR else "L")):
                pair = _recovery_pair(bars, anchor.confirmed, pivot.index, direction)
                if pair is not None:
                    setups.append((direction, chain, pivot, pair))
            next_anchors.append((direction, chain))
        anchors = next_anchors
        if pivot is not None:
            result = _prior_chain(pivots, pivot, bars)
            if result is not None:
                anchors.append(result)
            pivots.append(pivot)
    return tuple(emitted)


def detect(bars: Iterable[ResearchBar], *, contract_sha256: str,
           dataset_sha256: str, as_of: Optional[datetime] = None) -> Tuple[Candidate, ...]:
    """Return every causal candidate; corrupt/discontinuous input resets its segment.

    `as_of` prevents an incomplete final bar from entering the detector. Inputs
    are never sorted or repaired; original event order is authoritative.
    """
    if len(contract_sha256) != 64 or len(dataset_sha256) != 64:
        raise ValueError("64-character contract and dataset hashes required")
    if as_of is not None and (as_of.tzinfo is None or as_of.utcoffset() != timedelta(0)):
        raise ValueError("as_of must be UTC-aware")
    runs = {}
    for bar in bars:
        key = (bar.symbol, bar.timeframe)
        if as_of is not None and bar.close_time > as_of:
            continue
        valid = _valid(bar)
        current = runs.setdefault(key, [[]])
        segment = current[-1]
        contiguous = (not segment or
                      (bar.open_time == segment[-1].close_time and
                       bar.close_time > segment[-1].close_time))
        if not valid or not contiguous:
            current.append([])
        if valid:
            current[-1].append(bar)
    output = [event for parts in runs.values() for segment in parts if segment
              for event in _detect_segment(segment, contract_sha256, dataset_sha256)]
    return tuple(sorted(output, key=lambda c: (c.decision_time, c.symbol, c.candidate_id)))
