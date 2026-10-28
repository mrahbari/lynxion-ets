import csv
import hashlib
import json
import socket
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from scripts.opportunity_radar_v1 import build_radar


UTC = timezone.utc
START = datetime(2023, 1, 1, tzinfo=UTC)


class RadarTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.cutoff = START + timedelta(minutes=15 * 128)
        self._panel()

    def _panel(self, gap=None, duplicate=False, invalid=False):
        symbols = {}
        for symbol, step in (("AAA", 1), ("BBB", -1)):
            path = self.root / f"{symbol}.csv"
            with path.open("w", newline="") as out:
                writer = csv.writer(out)
                writer.writerow(("timestamp", "open", "high", "low", "close", "volume"))
                for i in range(128):
                    if symbol == "AAA" and i == gap:
                        continue
                    close = 100 + step * i * 0.1
                    row = (int((START + timedelta(minutes=15 * i)).timestamp()), close, close + 1,
                           close - 1 if not (invalid and symbol == "AAA" and i == 127) else close + 2,
                           close, 10)
                    writer.writerow(row)
                    if duplicate and symbol == "AAA" and i == 127:
                        writer.writerow(row)
            symbols[symbol] = {"sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        (self.root / "manifest.json").write_text(json.dumps({"interval": "15m", "symbols": symbols}))

    def test_rank_and_context_are_separate_and_deterministic(self):
        first = build_radar(self.root, self.cutoff)
        second = build_radar(self.root, self.cutoff)
        self.assertEqual(first, second)
        self.assertEqual(first["classification"], "OBSERVED_COHORT_RANKING_DEVELOPMENT_ONLY")
        self.assertEqual(first["universe_status"], "HISTORICAL_MARKET_WIDE_UNQUALIFIED")
        self.assertEqual(first["ranked_count"], 2)
        self.assertEqual([r["movement_rank_magnitude"] for r in first["rows"]], [2, 1])
        self.assertEqual(first["rows"][0]["htf_context"]["timeframe"], "1h")
        self.assertEqual(first["rows"][0]["htf_context"]["last_confirmed_close"], self.cutoff.isoformat())
        self.assertEqual(first["rows"][0]["ltf_setup"]["status"], "SETUP_UNAVAILABLE")
        self.assertEqual(first["rows"][0]["eligibility"], "OBSERVED_IN_PANEL_TRADABILITY_UNKNOWN")
        self.assertEqual(first["rows"][0]["data_quality"], "VALID")
        self.assertEqual(first["rows"][0]["source_qualification"],
                         "MANIFEST_HASH_MATCHED_DEVELOPMENT_ONLY_NO_RECEIPT")
        self.assertNotIn("order", json.dumps(first).lower())
        canonical = (json.dumps(first, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()
        self.assertEqual(hashlib.sha256(canonical).hexdigest(),
                         "e7397bcf02eb19d1e13e3ae66c13902c3b167c21f6e279c622421be6f365b140")

    def test_future_candle_never_used(self):
        original = build_radar(self.root, self.cutoff)
        with (self.root / "AAA.csv").open("a") as out:
            out.write(f"{int(self.cutoff.timestamp())},999,1000,998,999,10\n")
        manifest = json.loads((self.root / "manifest.json").read_text())
        manifest["symbols"]["AAA"]["sha256"] = hashlib.sha256((self.root / "AAA.csv").read_bytes()).hexdigest()
        (self.root / "manifest.json").write_text(json.dumps(manifest))
        later = build_radar(self.root, self.cutoff)
        for before, after in zip(original["rows"], later["rows"]):
            for field in ("movement_pct_4_closed_m15", "movement_rank_magnitude",
                          "observation_close", "htf_context", "ltf_setup"):
                self.assertEqual(before[field], after[field])

    def test_stale_cutoff_does_not_rank(self):
        result = build_radar(self.root, self.cutoff + timedelta(hours=2))
        self.assertEqual(result["ranked_count"], 0)
        self.assertTrue(all(r["data_quality"] == "STALE" for r in result["rows"]))

    def test_gap_duplicate_and_invalid_ohlc_fail(self):
        for kwargs in ({"gap": 126}, {"duplicate": True}, {"invalid": True}):
            self._panel(**kwargs)
            with self.assertRaises(ValueError):
                build_radar(self.root, self.cutoff)

    def test_bad_manifest_hash_fails(self):
        (self.root / "AAA.csv").write_text("tampered")
        with self.assertRaises(ValueError):
            build_radar(self.root, self.cutoff)

    def test_late_arriving_pre_cutoff_row_after_future_row_is_rejected(self):
        path = self.root / "AAA.csv"
        with path.open("a") as out:
            out.write(f"{int(self.cutoff.timestamp())},100,101,99,100,10\n")
            out.write(f"{int((self.cutoff - timedelta(minutes=15)).timestamp())},100,101,99,100,10\n")
        manifest = json.loads((self.root / "manifest.json").read_text())
        manifest["symbols"]["AAA"]["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        (self.root / "manifest.json").write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, "out-of-order"):
            build_radar(self.root, self.cutoff)

    def test_incomplete_final_bar_is_excluded(self):
        early = self.cutoff - timedelta(minutes=7)
        result = build_radar(self.root, early)
        self.assertEqual(result["rows"][0]["observation_close"],
                         (self.cutoff - timedelta(minutes=15)).isoformat())

    def test_setup_metadata_is_only_at_same_decision_time(self):
        path = self.root / "setup.jsonl"
        path.write_text(json.dumps({"symbol": "AAA", "decision_time": self.cutoff.isoformat(),
                                    "signal_confirmation_time": self.cutoff.isoformat(),
                                    "candidate_id": "fixture", "direction": "BULLISH_STRUCTURAL_PULLBACK_FAILURE",
                                    "dataset_sha256": json.loads((self.root / "manifest.json").read_text())["symbols"]["AAA"]["sha256"],
                                    "contract_sha256": "fixture-contract"}) + "\n")
        result = build_radar(self.root, self.cutoff, path)
        self.assertEqual(result["rows"][0]["ltf_setup"]["events"][0]["candidate_id"], "fixture")
        self.assertEqual(build_radar(self.root, self.cutoff - timedelta(minutes=15), path)["rows"][0]
                         ["ltf_setup"]["status"], "SETUP_UNAVAILABLE")
        path.write_text(json.dumps({"symbol": "AAA", "decision_time": self.cutoff.isoformat(),
                                    "signal_confirmation_time": (self.cutoff + timedelta(minutes=15)).isoformat(),
                                    "candidate_id": "future-confirmed", "direction": "BULLISH_STRUCTURAL_PULLBACK_FAILURE",
                                    "dataset_sha256": json.loads((self.root / "manifest.json").read_text())["symbols"]["AAA"]["sha256"],
                                    "contract_sha256": "fixture-contract"}) + "\n")
        self.assertEqual(build_radar(self.root, self.cutoff, path)["rows"][0]
                         ["ltf_setup"]["status"], "SETUP_UNAVAILABLE")

    def test_replayed_setup_record_is_displayed_once_in_stable_order(self):
        path = self.root / "setup.jsonl"
        source_hash = json.loads((self.root / "manifest.json").read_text())["symbols"]["AAA"]["sha256"]
        base = {"symbol": "AAA", "decision_time": self.cutoff.isoformat(),
                "signal_confirmation_time": self.cutoff.isoformat(),
                "direction": "BULLISH_STRUCTURAL_PULLBACK_FAILURE",
                "dataset_sha256": source_hash, "contract_sha256": "fixture-contract"}
        second = {**base, "candidate_id": "event-b"}
        first = {**base, "candidate_id": "event-a"}
        path.write_text("\n".join(json.dumps(item) for item in (second, first, first)) + "\n")

        events = build_radar(self.root, self.cutoff, path)["rows"][0]["ltf_setup"]["events"]
        self.assertEqual([event["candidate_id"] for event in events], ["event-a", "event-b"])
        path.write_text("\n".join(json.dumps(item) for item in (first, second)) + "\n")
        self.assertEqual(build_radar(self.root, self.cutoff, path)["rows"][0]["ltf_setup"]["events"], events)
        conflict = {**first, "direction": "BEARISH_STRUCTURAL_PULLBACK_FAILURE"}
        path.write_text("\n".join(json.dumps(item) for item in (first, conflict)) + "\n")
        with self.assertRaisesRegex(ValueError, "conflicting setup records"):
            build_radar(self.root, self.cutoff, path)

    def test_networkless(self):
        with patch.object(socket, "socket", side_effect=AssertionError("network forbidden")):
            self.assertEqual(build_radar(self.root, self.cutoff)["ranked_count"], 2)


if __name__ == "__main__":
    unittest.main()
