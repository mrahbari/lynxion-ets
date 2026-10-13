import unittest
import json
import hashlib
from decimal import Decimal

from domain.extreme_mover_opportunity import (
    MetricObservation, UniverseSnapshot, build_opportunity_view,
)


class OpportunityViewTests(unittest.TestCase):
    def setUp(self):
        self.universe = UniverseSnapshot("venue", 90, 95, "universe-hash", ("AAA", "BBB"))
        self.observations = (
            MetricObservation("AAA", "externally-defined-metric", Decimal("2"), 90, 96, "a-hash"),
            MetricObservation("BBB", "externally-defined-metric", Decimal("1"), 90, 97, "b-hash"),
        )

    def test_complete_causal_view_is_deterministic(self):
        left = build_opportunity_view(100, self.universe, self.observations)
        right = build_opportunity_view(100, self.universe, tuple(reversed(self.observations)))
        self.assertEqual(left, right)
        self.assertEqual([(r.symbol, r.rank_ascending) for r in left.rows], [("BBB", 1), ("AAA", 2)])
        self.assertEqual(left.universe_source_hash, "universe-hash")
        payload = json.dumps(left.to_record(), sort_keys=True, separators=(",", ":"))
        self.assertEqual(payload, json.dumps(right.to_record(), sort_keys=True, separators=(",", ":")))
        self.assertEqual(hashlib.sha256(payload.encode()).hexdigest(),
                         "d2817f155c90edb3ee708c6cfde9f21fed7c53ff9851057bed6eabed808cc98b")

    def test_universe_must_arrive_by_decision(self):
        late = UniverseSnapshot("venue", 90, 101, "hash", ("AAA", "BBB"))
        with self.assertRaises(ValueError):
            build_opportunity_view(100, late, self.observations)

    def test_missing_member_cannot_be_ranked(self):
        with self.assertRaises(ValueError):
            build_opportunity_view(100, self.universe, self.observations[:1])

    def test_duplicate_or_outside_member_cannot_be_ranked(self):
        with self.assertRaises(ValueError):
            build_opportunity_view(100, self.universe, (self.observations[0], self.observations[0]))

    def test_late_or_incomplete_metric_cannot_be_ranked(self):
        late = MetricObservation("AAA", "externally-defined-metric", Decimal("2"), 90, 101, "a-hash")
        with self.assertRaises(ValueError):
            build_opportunity_view(100, self.universe, (late, self.observations[1]))
        incomplete = MetricObservation("AAA", "externally-defined-metric", Decimal("2"), 101, 101, "a-hash")
        with self.assertRaises(ValueError):
            build_opportunity_view(100, self.universe, (incomplete, self.observations[1]))

    def test_metric_identity_and_finite_value_required(self):
        other = MetricObservation("AAA", "other", Decimal("2"), 90, 96, "a-hash")
        with self.assertRaises(ValueError):
            build_opportunity_view(100, self.universe, (other, self.observations[1]))
        nan = MetricObservation("AAA", "externally-defined-metric", Decimal("NaN"), 90, 96, "a-hash")
        with self.assertRaises(ValueError):
            build_opportunity_view(100, self.universe, (nan, self.observations[1]))

    def test_mixed_cutoff_cannot_be_ranked(self):
        stale = MetricObservation("AAA", "externally-defined-metric", Decimal("2"), 80, 96, "a-hash")
        with self.assertRaises(ValueError):
            build_opportunity_view(100, self.universe, (stale, self.observations[1]))

    def test_equal_values_have_stable_symbol_tie_break(self):
        same = MetricObservation("AAA", "externally-defined-metric", Decimal("1"), 90, 96, "a-hash")
        view = build_opportunity_view(100, self.universe, (same, self.observations[1]))
        self.assertEqual(tuple(r.symbol for r in view.rows), ("AAA", "BBB"))


if __name__ == "__main__":
    unittest.main()
