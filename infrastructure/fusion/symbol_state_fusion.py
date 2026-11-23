"""Symbol-state fusion (E15-F1 / E16, 2026-11-23): fuse the latest state of ALL watchers of a symbol.

Why: the event system calls Fusion once per interpreted signal (one watcher at a time), so the
hierarchical fusion never saw two watchers together and every live fused signal was NEUTRAL with 0 %
confidence; its role table also did not match the names the Engine sends and filed Liquidity as a
direction watcher. This fuser keeps, per symbol, the latest observation of every watcher (until it goes
stale) and fuses that state on every call, using each watcher's declared contract (role, validated).

Output (same FusedSignal contract, one fused signal per incoming signal as before):
  regime_context  from REGIME evidence, validated watchers first:
                  anomaly (validated) or volatility_expansion (validated) -> 'volatile';
                  trend_mtf positive/negative -> 'bullish_trending' / 'bearish_trending' (descriptive);
                  volatility_compression (validated) -> 'ranging'; otherwise 'normal'.
  direction       confidence-weighted vote of fresh DIRECTION watchers (neutral labels vote 0), in
                  [-1, 1]; dominant_bias BUY / SELL beyond +/-0.1. Descriptive: no directional watcher
                  has a validated predictive claim (E18), recorded as metadata['validated_direction'].
  confidence      |direction| (agreement strength of the directional state), 0 when neutral.
  metadata        contributors {watcher: label}, roles, positioning (funding), execution (liquidity),
                  regime_basis, plus the triggering signal's watcher / observation identifiers.
Strategies do not gate on these fields today (E12); they feed ranking and attribution.
"""
from __future__ import annotations

import threading
import time
from decimal import Decimal
from typing import Any, Dict, Optional

from domain.entities import FusedSignal, InterpretedSignal, SignalType
from domain.value_objects import Percentage

CLASS_TO_WATCHER = {
    'VolatilityWatcher': 'volatility', 'TrendMTFWatcher': 'trend_mtf', 'MarketPulseWatcher': 'market_pulse',
    'FundingRateWatcher': 'funding_rate', 'LiquidityWatcher': 'liquidity', 'OrderFlowWSWatcher': 'orderflow_ws',
    'HistoricalCandleWatcherAdapter': 'historical_candle', 'AnomalyMLWatcher': 'anomaly_ml',
    'TickWatcherAdapter': 'tick_watcher', 'CMCScreener': 'cmc_screener',
}
FALLBACK_ROLE = {
    'volatility': 'regime', 'anomaly_ml': 'regime', 'funding_rate': 'positioning', 'liquidity': 'execution',
    'trend_mtf': 'direction', 'market_pulse': 'direction', 'historical_candle': 'direction',
    'orderflow_ws': 'direction', 'tick_watcher': 'execution', 'cmc_screener': 'regime',
}
TTL_S = {'funding_rate': 1200.0}
DEFAULT_TTL_S = 300.0


def _side(label: str) -> int:
    lab = label.lower()
    if any(k in lab for k in ('neutral', 'normal', 'caution', 'without_direction')):
        return 0
    if any(k in lab for k in ('positive', 'bullish', 'upward', 'buy_pressure', 'moderate_buy')):
        return 1
    if any(k in lab for k in ('negative', 'bearish', 'downward', 'sell_pressure', 'moderate_sell')):
        return -1
    return 0


class SymbolStateFusion:
    def __init__(self, clock=None):
        self._now = (lambda: clock.now().timestamp()) if clock is not None else time.time
        self._state: Dict[str, Dict[str, Dict[str, Any]]] = {}
        self._lock = threading.Lock()

    @staticmethod
    def watcher_key(signal: InterpretedSignal) -> str:
        meta = signal.metadata or {}
        name = str(meta.get('watcher_name') or getattr(signal, 'source_watcher', '') or 'unknown')
        return CLASS_TO_WATCHER.get(name, name)

    def update(self, signal: InterpretedSignal) -> FusedSignal:
        meta = signal.metadata or {}
        watcher = self.watcher_key(signal)
        contract = meta.get('contract') if isinstance(meta.get('contract'), dict) else {}
        role = contract.get('role') or FALLBACK_ROLE.get(watcher, 'direction')
        sym = getattr(signal.symbol, 'value', str(signal.symbol))
        now = self._now()
        entry = {'label': str(meta.get('observation_type') or signal.signal_type.value).lower(),
                 'conf': float(signal.confidence.value), 'role': role,
                 'validated': contract.get('validated'), 'ts': now}
        with self._lock:
            book = self._state.setdefault(sym, {})
            book[watcher] = entry
            fresh = {w: e for w, e in book.items() if now - e['ts'] <= TTL_S.get(w, DEFAULT_TTL_S)}
            for w in [w for w in book if w not in fresh]:
                del book[w]
        return self._fuse(signal, fresh)

    def _fuse(self, signal: InterpretedSignal, fresh: Dict[str, Dict[str, Any]]) -> FusedSignal:
        def label(w):
            return fresh[w]['label'] if w in fresh else ''

        if label('anomaly_ml').startswith('anomaly_') and label('anomaly_ml') != 'anomaly_normal':
            regime, basis = 'volatile', 'anomaly_ml'
        elif label('volatility') == 'volatility_expansion':
            regime, basis = 'volatile', 'volatility'
        elif label('trend_mtf') in ('trend_positive', 'trend_negative'):
            regime = 'bullish_trending' if label('trend_mtf') == 'trend_positive' else 'bearish_trending'
            basis = 'trend_mtf'
        elif label('volatility') == 'volatility_compression':
            regime, basis = 'ranging', 'volatility'
        else:
            regime, basis = 'normal', None

        voters = {w: e for w, e in fresh.items() if e['role'] == 'direction'}
        weight = sum(e['conf'] for e in voters.values())
        direction = (sum(e['conf'] * _side(e['label']) for e in voters.values()) / weight) if weight > 0 else 0.0
        direction = max(-1.0, min(1.0, direction))
        bias = SignalType.BUY if direction > 0.1 else SignalType.SELL if direction < -0.1 else SignalType.NEUTRAL
        confidence = abs(direction) if bias is not SignalType.NEUTRAL else 0.0
        meta = signal.metadata or {}
        return FusedSignal(
            symbol=signal.symbol, dominant_bias=bias, direction=float(direction),
            dominance_score=float(abs(direction)), regime_context=regime,
            confidence=Percentage(Decimal(str(round(confidence, 6)))),
            timestamp=getattr(signal, 'timestamp', None) or __import__('datetime').datetime.now(),
            metadata={
                'state_fusion': True,
                'contributors': {w: e['label'] for w, e in fresh.items()},
                'roles': {w: e['role'] for w, e in fresh.items()},
                'direction_voters': {w: _side(e['label']) for w, e in voters.items()},
                'validated_direction': False,
                'regime_basis': basis,
                'positioning': label('funding_rate') or None,
                'execution': {w: fresh[w]['label'] for w in fresh if fresh[w]['role'] == 'execution'},
                'watcher_name': meta.get('watcher_name') or getattr(signal, 'source_watcher', None),
                'primary_watcher': meta.get('watcher_name') or getattr(signal, 'source_watcher', None),
                'observation_type': meta.get('observation_type'),
            })

