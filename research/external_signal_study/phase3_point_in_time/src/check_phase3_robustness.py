"""Fixed chronological, side and leave-top-symbol-out descriptive checks."""
import csv
import hashlib
import statistics
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
PHASE = ROOT / "research/external_signal_study/phase3_point_in_time"
SPEC_HASH = "96d0f336f9c0e335b61b8d90df81835180647f9c2d85498d210fa1e34c329193"
FEATURES = (
    "F1_directional_4h_return", "F2_range_location_20", "F3_countertrend_pullback_8",
    "F4_compression_ratio", "F5_relative_volume_8", "F9_BTC_directional_4h_return",
)


def read(path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def mean_for(rows, column):
    return statistics.mean(float(r[column]) for r in rows) if rows else None


def main():
    assert hashlib.sha256((PHASE / "preregistration/PHASE3_RESEARCH_SPEC.md").read_bytes()).hexdigest() == SPEC_HASH
    rows = read(PHASE / "diagnostics/paired_feature_differences.csv")
    assert len(rows) == 56
    days = sorted({r["case_day_utc"] for r in rows})
    assert len(days) == 23
    early_days = set(days[:len(days) // 2])
    late_days = set(days[len(days) // 2:])
    counts = Counter(r["symbol"] for r in rows)
    top = sorted(counts, key=lambda symbol: (-counts[symbol], symbol))[0]
    sets = {
        "FULL": rows,
        "CHRONO_EARLY": [r for r in rows if r["case_day_utc"] in early_days],
        "CHRONO_LATE": [r for r in rows if r["case_day_utc"] in late_days],
        "LONG": [r for r in rows if r["side"] == "LONG"],
        "SHORT": [r for r in rows if r["side"] == "SHORT"],
        "LEAVE_TOP_SYMBOL_OUT": [r for r in rows if r["symbol"] != top],
    }
    output = []
    for feature in FEATURES:
        column = feature + "_difference"
        full = mean_for(rows, column)
        for name, subset in sets.items():
            effect = mean_for(subset, column)
            output.append(dict(feature=feature, check=name, case_count=len(subset), utc_days=len({r["case_day_utc"] for r in subset}), symbol_count=len({r["symbol"] for r in subset}), removed_top_symbol=top if name == "LEAVE_TOP_SYMBOL_OUT" else "NONE", paired_mean_difference=format(effect, ".12g") if effect is not None else "", same_sign_as_full="YES" if effect is not None and effect * full > 0 else "NO", full_effect_fraction="" if not full or effect is None else format(effect / full, ".6f")))
    path = PHASE / "diagnostics/robustness_results.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(output[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(output)
    print(f"top_symbol={top} count={counts[top]} early_days={len(early_days)} late_days={len(late_days)}")
    for row in output:
        if row["feature"] == "F4_compression_ratio" and row["check"] != "FULL":
            print(row["check"], row["case_count"], row["same_sign_as_full"], row["full_effect_fraction"])


if __name__ == "__main__":
    main()
