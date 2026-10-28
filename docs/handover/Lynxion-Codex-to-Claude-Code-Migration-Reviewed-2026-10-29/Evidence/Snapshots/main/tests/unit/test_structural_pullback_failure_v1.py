"""Pre-implementation, manually specified causal fixtures for V1.

Authorship: Codex root, before detector implementation. Expected pivot indices
were derived from the hand-written OHLC geometry, not detector output.
"""
import unittest
from unittest.mock import patch
from datetime import datetime, timedelta, timezone

from domain.research.structural_pullback_failure_v1 import detect, ResearchBar


START = datetime(2026, 1, 1, tzinfo=timezone.utc)
M15 = timedelta(minutes=15)
DATASET = "a" * 64
CONTRACT = "b" * 64

# H0=2, L0=4, H1=6, L1=8 (confirmed at 10), recovery P=13
# (confirmed at 15), trigger=16. The pattern is known only at close(16).
BEAR = [
    (10, 10, 9, 9.5), (10.5, 11, 9.5, 10), (14, 15, 11, 14),
    (10, 13, 9, 10), (8, 12, 7, 8), (12, 13, 8, 12),
    (13, 14, 10, 13), (10, 12, 8, 10), (6, 11, 5, 6),
    (8, 10, 6, 8), (8.5, 9, 7, 8.5), (8.8, 9, 8, 8.8),
    (9.2, 10, 8.5, 9.2), (10, 12, 9, 10), (9, 11, 8, 9),
    (8, 10, 7, 8), (8, 9, 7.5, 8),
]


def bars(rows=BEAR, symbol="TESTUSDT", start=START):
    return tuple(ResearchBar(symbol, M15, start + i * M15,
                             start + (i + 1) * M15, *row)
                 for i, row in enumerate(rows))


def bull_rows():
    return [(20 - o, 20 - low, 20 - high, 20 - close)
            for o, high, low, close in BEAR]


class StructuralPullbackFailureFixtures(unittest.TestCase):
    def run_detector(self, source):
        return detect(source, contract_sha256=CONTRACT, dataset_sha256=DATASET)

    def test_bearish_exact_first_knowable_close(self):
        got = self.run_detector(bars())
        self.assertEqual(len(got), 1)
        event = got[0]
        self.assertEqual(event.direction, "BEARISH_STRUCTURAL_PULLBACK_FAILURE")
        self.assertEqual(event.original_anchor_pivot_time, START + 8 * M15)
        self.assertEqual(event.anchor_confirmation_time, START + 11 * M15)
        self.assertEqual(event.original_recovery_pivot_time, START + 13 * M15)
        self.assertEqual(event.recovery_confirmation_time, START + 16 * M15)
        self.assertEqual(event.decision_time, START + 17 * M15)

    def test_bullish_exact_first_knowable_close(self):
        got = self.run_detector(bars(bull_rows()))
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0].direction, "BULLISH_STRUCTURAL_PULLBACK_FAILURE")
        self.assertEqual(got[0].decision_time, START + 17 * M15)
        self.assertEqual(got[0].original_anchor_pivot_time, START + 8 * M15)
        self.assertEqual(got[0].anchor_confirmation_time, START + 11 * M15)
        self.assertEqual(got[0].original_recovery_pivot_time, START + 13 * M15)
        self.assertEqual(got[0].recovery_confirmation_time, START + 16 * M15)

    def test_prefix_invariance_complete_records(self):
        whole = bars()
        full = self.run_detector(whole)
        for n in range(len(whole) + 1):
            self.assertEqual(self.run_detector(whole[:n]),
                             tuple(c for c in full if c.decision_time <= START + n * M15))

    def test_unconfirmed_recovery_has_no_candidate(self):
        self.assertEqual(self.run_detector(bars()[:15]), ())

    def test_no_trigger_has_no_candidate(self):
        altered = list(BEAR)
        altered[16] = (9.2, 9.5, 9, 9.2)
        self.assertEqual(self.run_detector(bars(altered)), ())

    def test_equal_trigger_level_is_not_a_break(self):
        altered = list(BEAR)
        altered[16] = (9, 9.5, 8.5, 9)
        self.assertEqual(self.run_detector(bars(altered)), ())

    def test_same_bar_invalidation_precedes_trigger(self):
        altered = list(BEAR)
        altered[16] = (8, 14, 7.5, 8)
        self.assertEqual(self.run_detector(bars(altered)), ())

    def test_gap_resets_state(self):
        source = list(bars())
        source[16] = ResearchBar("TESTUSDT", M15, START + 17 * M15,
                                 START + 18 * M15, *BEAR[16])
        self.assertEqual(self.run_detector(tuple(source)), ())

    def test_duplicate_and_out_of_order_reset(self):
        source = bars()
        self.assertEqual(self.run_detector(source[:15] + (source[14],) + source[15:]), ())
        self.assertEqual(self.run_detector(source[:15] + (source[13],) + source[15:]), ())

    def test_incomplete_final_bar_never_enters(self):
        source = bars()
        self.assertEqual(detect(source, contract_sha256=CONTRACT,
                                dataset_sha256=DATASET,
                                as_of=source[16].open_time), ())

    def test_invalidation_before_recovery_confirmation(self):
        altered = list(BEAR)
        altered[14] = (9, 14, 8, 9)
        self.assertEqual(self.run_detector(bars(altered)), ())

    def test_recovery_deadline(self):
        delayed = BEAR[:11] + [(8.5, 9, 7, 8.5)] * 13 + BEAR[11:]
        self.assertEqual(self.run_detector(bars(delayed)), ())

    def test_trigger_at_eighth_bar_qualifies_and_ninth_expires(self):
        neutral = [(9.5, 10, 9, 9.5)] * 7
        trigger = (8, 9, 7.5, 8)
        eligible = bars(BEAR[:16] + neutral + [trigger])
        got = self.run_detector(eligible)
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0].decision_time, START + 24 * M15)
        expired = bars(BEAR[:16] + neutral + [neutral[0], trigger])
        self.assertEqual(self.run_detector(expired), ())

    def test_invalid_ohlc_resets_state(self):
        source = list(bars())
        source[15] = ResearchBar("TESTUSDT", M15, source[15].open_time,
                                 source[15].close_time, 8, 7, 6, 8)
        self.assertEqual(self.run_detector(tuple(source)), ())

    def test_per_symbol_isolation(self):
        a, b = bars(symbol="AUSDT"), bars(symbol="BUSDT")
        mixed = tuple(v for pair in zip(a, b) for v in pair)
        got = self.run_detector(mixed)
        self.assertEqual({c.symbol for c in got}, {"AUSDT", "BUSDT"})
        self.assertEqual(len({c.candidate_id for c in got}), 2)

    def test_replay_duplicate_id_and_no_broker_surface(self):
        first = self.run_detector(bars())
        self.assertEqual(first[0].candidate_id, self.run_detector(bars())[0].candidate_id)
        self.assertFalse(hasattr(first[0], "execution_intent"))
        self.assertFalse(hasattr(first[0], "order_id"))
        self.assertEqual(first[0].htf_context_status, "HTF_CONTEXT_UNAVAILABLE")

    def test_detector_runs_when_outbound_socket_is_denied(self):
        with patch("socket.socket", side_effect=AssertionError("network forbidden")):
            self.assertEqual(len(self.run_detector(bars())), 1)

    def test_distinct_simultaneous_events_are_not_suppressed(self):
        a, b = bars(symbol="AUSDT"), bars(symbol="BUSDT")
        got = self.run_detector(tuple(v for pair in zip(a, b) for v in pair))
        self.assertEqual(len(got), 2)
        self.assertEqual(got[0].decision_time, got[1].decision_time)
        self.assertNotEqual(got[0].candidate_id, got[1].candidate_id)

    def test_replay_is_deterministic(self):
        source = bars()
        self.assertEqual(self.run_detector(source), self.run_detector(source))


if __name__ == "__main__":
    unittest.main()
