"""Correctness tests for the RETIRED-slot replacement CANDIDATES (implemented + evaluated;
NOT deployed — they failed the READY bar). Tests assert mechanism behavior, not profitability."""

from domain.value_objects import Symbol
from domain.entities import SignalType
from infrastructure.strategies.adapters.short_term_reversal_strategy_adapter import ShortTermReversalStrategyAdapter
from infrastructure.strategies.adapters.donchian_breakout_strategy_adapter import DonchianBreakoutStrategyAdapter

SYM = Symbol("BTCUSDT")


def _bar(p, hi=None, lo=None, v=1.0, t=0):
    return {"open": p, "high": hi if hi is not None else p, "low": lo if lo is not None else p,
            "close": p, "volume": v, "timestamp": t}


def _feed(adapter, bars):
    sig = None
    for b in bars:
        adapter.update_with_market_data(b)
        sig = adapter.generate_signal(SYM)
    return sig


def test_str_returns_none_on_insufficient_data():
    a = ShortTermReversalStrategyAdapter({})
    assert _feed(a, [_bar(100, t=i) for i in range(10)]) is None


def test_str_fades_downward_extension_in_range():
    a = ShortTermReversalStrategyAdapter({})
    # flat ranging series, then a sharp DOWN bar -> reversal strategy should BUY (fade the drop)
    bars = [_bar(100.0 + (0.02 if i % 2 else -0.02), t=i) for i in range(120)]
    bars.append(_bar(96.0, t=120))   # ~4% down spike => large negative z in a flat range
    sig = _feed(a, bars)
    assert sig is not None and sig.signal_type == SignalType.BUY


def test_dcb_returns_none_on_insufficient_data():
    a = DonchianBreakoutStrategyAdapter({})
    assert _feed(a, [_bar(100, hi=101, lo=99, t=i) for i in range(20)]) is None


def test_dcb_buys_on_channel_breakout_with_expansion():
    a = DonchianBreakoutStrategyAdapter({})
    bars = [_bar(100.0, hi=100.5, lo=99.5, t=i) for i in range(160)]   # tight channel ~[99.5,100.5]
    # a wide, expanding bar that closes above the prior 20-bar high
    bars.append(_bar(103.0, hi=103.2, lo=100.0, t=160))
    sig = _feed(a, bars)
    assert sig is not None and sig.signal_type == SignalType.BUY
