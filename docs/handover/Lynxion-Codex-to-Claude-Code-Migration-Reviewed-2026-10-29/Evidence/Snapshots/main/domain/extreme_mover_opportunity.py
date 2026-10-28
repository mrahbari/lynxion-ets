"""Research-only point-in-time cross-sectional view; no trading integration."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Tuple


@dataclass(frozen=True)
class UniverseSnapshot:
    venue: str
    observed_at_ms: int
    received_at_ms: int
    source_hash: str
    symbols: Tuple[str, ...]


@dataclass(frozen=True)
class MetricObservation:
    symbol: str
    metric_id: str
    value: Decimal
    interval_end_ms: int
    received_at_ms: int
    source_hash: str


@dataclass(frozen=True)
class OpportunityRow:
    symbol: str
    rank_ascending: int
    metric_value: Decimal
    metric_source_hash: str


@dataclass(frozen=True)
class OpportunityView:
    decision_at_ms: int
    venue: str
    metric_id: str
    universe_source_hash: str
    rows: Tuple[OpportunityRow, ...]

    def to_record(self) -> dict:
        """Stable JSON-ready research record with no outcome or order fields."""
        return {
            "decision_at_ms": self.decision_at_ms,
            "venue": self.venue,
            "metric_id": self.metric_id,
            "universe_source_hash": self.universe_source_hash,
            "rows": [
                {"symbol": row.symbol, "rank_ascending": row.rank_ascending,
                 "metric_value": str(row.metric_value),
                 "metric_source_hash": row.metric_source_hash}
                for row in self.rows
            ],
        }


def build_opportunity_view(
    decision_at_ms: int,
    universe: UniverseSnapshot,
    observations: Tuple[MetricObservation, ...],
) -> OpportunityView:
    """Rank a complete supplied universe; never infer historical membership.

    The caller must independently qualify the snapshot's completeness and
    provenance. This function deliberately defines no momentum window, top-N
    threshold, signal, confidence, or outcome.
    """
    if not universe.venue or not universe.source_hash or not universe.symbols:
        raise ValueError("universe provenance and membership required")
    if universe.observed_at_ms > universe.received_at_ms or universe.received_at_ms > decision_at_ms:
        raise ValueError("universe not available at decision")
    members = set(universe.symbols)
    if len(members) != len(universe.symbols) or any(not symbol for symbol in members):
        raise ValueError("invalid universe membership")
    if len(observations) != len(members):
        raise ValueError("incomplete metric denominator")
    by_symbol = {item.symbol: item for item in observations}
    if set(by_symbol) != members or len(by_symbol) != len(observations):
        raise ValueError("duplicate, missing, or extraneous metric symbol")
    metric_ids = {item.metric_id for item in observations}
    if len(metric_ids) != 1 or not next(iter(metric_ids)):
        raise ValueError("one explicit metric identity required")
    if len({item.interval_end_ms for item in observations}) != 1:
        raise ValueError("mixed observation cutoffs")
    for item in observations:
        if not item.source_hash or not item.value.is_finite():
            raise ValueError("metric provenance or value invalid")
        if item.interval_end_ms > item.received_at_ms or item.received_at_ms > decision_at_ms:
            raise ValueError("metric not available at decision")
    ordered = sorted(observations, key=lambda item: (item.value, item.symbol))
    return OpportunityView(
        decision_at_ms=decision_at_ms,
        venue=universe.venue,
        metric_id=ordered[0].metric_id,
        universe_source_hash=universe.source_hash,
        rows=tuple(OpportunityRow(item.symbol, rank, item.value, item.source_hash)
                   for rank, item in enumerate(ordered, 1)),
    )
