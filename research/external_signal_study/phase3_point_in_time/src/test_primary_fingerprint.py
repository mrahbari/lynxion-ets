"""Frozen six-feature Family-A selection comparison; no market outcomes."""
import csv
import hashlib
import random
import statistics
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
PHASE = ROOT / "research/external_signal_study/phase3_point_in_time"
SPEC_HASH = "96d0f336f9c0e335b61b8d90df81835180647f9c2d85498d210fa1e34c329193"
FEATURES = (
    "F1_directional_4h_return", "F2_range_location_20", "F3_countertrend_pullback_8",
    "F4_compression_ratio", "F5_relative_volume_8", "F9_BTC_directional_4h_return",
)
ITERATIONS = 10_000


def read(path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def quantile(values, q):
    data = sorted(values)
    pos = q * (len(data) - 1)
    lo = int(pos)
    return data[lo] * (1 - pos + lo) + data[min(lo + 1, len(data) - 1)] * (pos - lo)


def bh_qvalues(p_values):
    ranks = sorted(range(len(p_values)), key=lambda i: p_values[i])
    out = [1.0] * len(p_values)
    best = 1.0
    for rank in range(len(ranks), 0, -1):
        i = ranks[rank - 1]
        best = min(best, p_values[i] * len(p_values) / rank)
        out[i] = best
    return out


def infer(values, days, seed):
    observed = statistics.mean(values)
    by_day = defaultdict(list)
    for day, value in zip(days, values):
        by_day[day].append(value)
    clusters = [by_day[x] for x in sorted(by_day)]
    rng = random.Random(seed)
    boot, extremes = [], 0
    for _ in range(ITERATIONS):
        sample = [v for _ in clusters for v in clusters[rng.randrange(len(clusters))]]
        boot.append(statistics.mean(sample))
        signed = []
        for cluster in clusters:
            sign = -1 if rng.randrange(2) else 1
            signed.extend(v * sign for v in cluster)
        if abs(statistics.mean(signed)) >= abs(observed):
            extremes += 1
    return observed, quantile(boot, .025), quantile(boot, .975), (extremes + 1) / (ITERATIONS + 1)


def main():
    assert hashlib.sha256((PHASE / "preregistration/PHASE3_RESEARCH_SPEC.md").read_bytes()).hexdigest() == SPEC_HASH
    table = read(PHASE / "features/point_in_time_features.csv")
    power = {r["feature"]: r for r in read(PHASE / "diagnostics/power_analysis.csv")}
    assert len(table) == 224 and len(power) == 6
    family = defaultdict(list)
    for r in table:
        assert r["leakage_check"] == "PASS"
        family[r["case_id"]].append(r)
    assert len(family) == 56
    paired = []
    for cid, rows in sorted(family.items()):
        case = [r for r in rows if r["record_type"] == "CASE"]
        controls = [r for r in rows if r["record_type"] == "CONTROL"]
        assert len(case) == 1 and len(controls) == 3
        row = dict(case_id=cid, symbol=case[0]["symbol"], side=case[0]["side"], case_time_utc=case[0]["event_time_utc"], case_day_utc=case[0]["event_time_utc"][:10])
        for feature in FEATURES:
            row[feature + "_difference"] = float(case[0][feature]) - statistics.mean(float(c[feature]) for c in controls)
        paired.append(row)
    write(PHASE / "diagnostics/paired_feature_differences.csv", paired)
    result = []
    for index, feature in enumerate(FEATURES):
        vals = [r[feature + "_difference"] for r in paired]
        days = [r["case_day_utc"] for r in paired]
        effect, lo, hi, p = infer(vals, days, 31004 + index)
        robust_scale = float(power[feature]["pooled_robust_scale"])
        result.append(dict(feature=feature, case_count=len(vals), independent_day_clusters=len(set(days)), symbol_count=len({r["symbol"] for r in paired}), long_cases=sum(r["side"] == "LONG" for r in paired), short_cases=sum(r["side"] == "SHORT" for r in paired), paired_mean_difference=format(effect, ".12g"), pooled_robust_scale=format(robust_scale, ".12g"), standardized_effect_d=format(effect / robust_scale, ".6f"), day_bootstrap_ci95_low=format(lo, ".12g"), day_bootstrap_ci95_high=format(hi, ".12g"), day_cluster_sign_flip_p=format(p, ".6f"), bh_q="", power_class=power[feature]["power_class"], primary_screen="PENDING_ROBUSTNESS"))
    q = bh_qvalues([float(r["day_cluster_sign_flip_p"]) for r in result])
    for r, q_value in zip(result, q):
        r["bh_q"] = format(q_value, ".6f")
        r["primary_screen"] = "PASSES_Q_AND_D_ONLY" if q_value <= .10 and abs(float(r["standardized_effect_d"])) >= .40 else "FAILS_Q_OR_D"
    write(PHASE / "diagnostics/primary_fingerprint_comparisons.csv", result)
    print({r["feature"]: (r["standardized_effect_d"], r["bh_q"], r["primary_screen"]) for r in result})


if __name__ == "__main__":
    main()
