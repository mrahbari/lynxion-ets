"""Canonical identity checks for the existing hierarchical watcher path."""

import unittest
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import patch

from domain.entities import MarketObservation
from domain.value_objects import Percentage, Symbol
from infrastructure.fusion.hierarchical.confidence_thresholds import ConfidenceThresholds
from infrastructure.fusion.hierarchical.watcher_classifier import WatcherClassifier, WatcherRole
from infrastructure.fusion.hierarchical.hierarchical_fusion_service import HierarchicalFusionService


class WatcherIdentityTest(unittest.TestCase):
    def _observation(self, when, observation_type="trend_direction", confidence="0.60"):
        return MarketObservation(
            symbol=Symbol("BTCUSDT"),
            observation_type=observation_type,
            observation_value=1.0,
            confidence=Percentage(Decimal(confidence)),
            timestamp=when,
        )

    def test_registered_class_name_uses_existing_direction_role_and_threshold(self):
        self.assertEqual(WatcherClassifier.canonical_name("TrendMTFWatcher"), "trend_mtf")
        self.assertEqual(WatcherClassifier.get_watcher_role("TrendMTFWatcher"), WatcherRole.DIRECTION)
        self.assertEqual(ConfidenceThresholds.get_threshold("TrendMTFWatcher"), 0.55)
        self.assertEqual(WatcherClassifier.get_watcher_role("trend_mtf"), WatcherRole.DIRECTION)

    def test_unknown_and_unrelated_names_remain_unchanged(self):
        self.assertIsNone(WatcherClassifier.get_watcher_role("UnknownWatcher"))
        self.assertEqual(WatcherClassifier.canonical_name("liquidity"), "liquidity")
        self.assertEqual(WatcherClassifier.get_watcher_role("liquidity"), WatcherRole.DIRECTION)

    def test_alias_duplicate_is_one_contributor_but_distinct_events_survive(self):
        when = datetime(2026, 10, 16, 12, tzinfo=timezone.utc)
        first = self._observation(when)
        duplicate = self._observation(when)
        later = self._observation(when.replace(minute=15))
        records = [
            {"watcher_name": "TrendMTFWatcher", "observation": first},
            {"watcher_name": "trend_mtf", "observation": duplicate},
            {"watcher_name": "trend_mtf", "observation": later},
        ]
        result = WatcherClassifier.canonicalize_observation_batch(records)
        self.assertEqual(len(result), 2)
        self.assertEqual([row["watcher_name"] for row in result], ["trend_mtf", "trend_mtf"])
        self.assertEqual([row["observation"].timestamp for row in result], [when, later.timestamp])
        self.assertEqual(records[0]["watcher_name"], "TrendMTFWatcher")

    def test_corrected_confidence_is_not_dropped_in_either_order(self):
        when = datetime(2026, 10, 16, 12, tzinfo=timezone.utc)
        low = self._observation(when)
        low.confidence = Percentage(Decimal("0.40"))
        high = self._observation(when)
        for names, observations in (
            (("TrendMTFWatcher", "trend_mtf"), (low, high)),
            (("trend_mtf", "TrendMTFWatcher"), (high, low)),
        ):
            records = [
                {"watcher_name": names[0], "observation": observations[0]},
                {"watcher_name": names[1], "observation": observations[1]},
            ]
            result = WatcherClassifier.canonicalize_observation_batch(records)
            self.assertEqual(len(result), 2)
            self.assertIn(high, [row["observation"] for row in result])

    def test_unrelated_watcher_duplicates_are_not_changed(self):
        when = datetime(2026, 10, 16, 12, tzinfo=timezone.utc)
        observation = self._observation(when)
        records = [
            {"watcher_name": "liquidity", "observation": observation},
            {"watcher_name": "liquidity", "observation": observation},
        ]
        self.assertEqual(len(WatcherClassifier.canonicalize_observation_batch(records)), 2)

    def test_same_spelling_trend_observations_keep_prior_behavior(self):
        when = datetime(2026, 10, 16, 12, tzinfo=timezone.utc)
        observation = self._observation(when)
        records = [
            {"watcher_name": "trend_mtf", "observation": observation},
            {"watcher_name": "trend_mtf", "observation": self._observation(when)},
        ]
        self.assertEqual(len(WatcherClassifier.canonicalize_observation_batch(records)), 2)

    def test_fusion_classifies_one_exact_alias_pair(self):
        when = datetime(2026, 10, 16, 12, tzinfo=timezone.utc)
        records = [
            {"watcher_name": "TrendMTFWatcher", "observation": self._observation(when)},
            {"watcher_name": "trend_mtf", "observation": self._observation(when)},
        ]
        service = HierarchicalFusionService()
        with patch(
            "infrastructure.fusion.hierarchical.hierarchical_fusion_service.ObservationClassifier.classify_observation",
            side_effect=RuntimeError("classification reached"),
        ) as classify:
            with self.assertRaisesRegex(RuntimeError, "classification reached"):
                service.fuse_signals_hierarchically(records, Symbol("BTCUSDT"))
        self.assertEqual(classify.call_count, 1)
        self.assertEqual(classify.call_args.args[1], "trend_mtf")

    def test_fusion_alias_pair_does_not_supply_two_direction_votes(self):
        when = datetime(2026, 10, 16, 12, tzinfo=timezone.utc)

        class SilentLogger:
            def __getattr__(self, name):
                return lambda *args, **kwargs: None

        trend = self._observation(when, "trend_positive", "0.80")
        duplicate = self._observation(when, "trend_positive", "0.80")
        records = [
            {"watcher_name": "TrendMTFWatcher", "observation": trend},
            {"watcher_name": "trend_mtf", "observation": duplicate},
        ]
        service = HierarchicalFusionService()
        service.logger = SilentLogger()
        signal = service.fuse_signals_hierarchically(records, Symbol("BTCUSDT"))
        self.assertEqual(signal.dominant_bias.name, "NEUTRAL")


if __name__ == "__main__":
    unittest.main()
