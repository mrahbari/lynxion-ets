"""
Canonical engine adapter (E3.T7.1 — Option A: Retire & Redefine).

``EngineServiceAdapter`` is the single canonical implementation of
:class:`domain.ports.engine_ports.EnginePort`. It is a thin, pure-delegation
wrapper around the live :class:`infrastructure.engines.engine_service.EngineService`
(the only engine actually on the production path:
Watcher -> EventRouter -> engine_service.process_observation -> Fusion -> ...).

It introduces NO logic and NO transformation: it forwards ``process_observation``
verbatim so the live behavior is preserved exactly.
"""
from typing import Optional

from domain.entities import MarketObservation, InterpretedSignal
from domain.ports.engine_ports import EnginePort


class EngineServiceAdapter(EnginePort):
    """Pure-delegation EnginePort over the canonical EngineService."""

    def __init__(self, engine_service):
        self._svc = engine_service

    def process_observation(self, observation: MarketObservation) -> Optional[InterpretedSignal]:
        return self._svc.process_observation(observation)
