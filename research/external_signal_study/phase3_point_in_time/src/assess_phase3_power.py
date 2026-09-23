"""Pre-verdict clustered power only; suppresses observed case-control effects."""
import csv
import hashlib
import math
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
PRACTICAL_D = 0.40
ISOLATED_BH_ALPHA = 0.10 / len(FEATURES)  # conservative single-discovery BH q=.10 hurdle


def read(path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write(path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(records[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(records)


def quantile(values, q):
    ordered = sorted(values)
    pos = q * (len(ordered) - 1)
    lo = int(pos)
    frac = pos - lo
    return ordered[lo] * (1 - frac) + ordered[min(lo + 1, len(ordered) - 1)] * frac


def clustered_null_means(residuals, groups, seed):
    """Resample whole day or symbol clusters, retaining case family within each."""
    keys = sorted(set(groups))
    members = {key: [i for i, group in enumerate(groups) if group == key] for key in keys}
    rng = random.Random(seed)
    result = []
    for _ in range(ITERATIONS):
        indices = [i for _ in keys for i in members[keys[rng.randrange(len(keys))]]]
        result.append(sum(residuals[i] for i in indices) / len(indices))
    return result


def power_at_delta(null_means, delta):
    critical = quantile([abs(x) for x in null_means], 1 - ISOLATED_BH_ALPHA)
    power = sum(abs(x + delta) > critical for x in null_means) / len(null_means)
    return power, critical


def main():
    assert hashlib.sha256((PHASE / "preregistration/PHASE3_RESEARCH_SPEC.md").read_bytes()).hexdigest() == SPEC_HASH
    rows = read(PHASE / "features/point_in_time_features.csv")
    assert len(rows) == 224
    groups = defaultdict(list)
    for row in rows:
        groups[row["case_id"]].append(row)
    assert len(groups) == 56
    paired = []
    for cid, family in sorted(groups.items()):
        case = [r for r in family if r["record_type"] == "CASE"]
        controls = [r for r in family if r["record_type"] == "CONTROL"]
        assert len(case) == 1 and len(controls) == 3
        paired.append((case[0], controls))
    days = [c["event_time_utc"][:10] for c, _ in paired]
    symbols = [c["symbol"] for c, _ in paired]
    sides = Counter(c["side"] for c, _ in paired)
    breadth = len(set(days)) >= 20 and len(set(symbols)) >= 10 and min(sides.values()) >= 10
    report = []
    for idx, feature in enumerate(FEATURES):
        usable = [(c, controls) for c, controls in paired if c[feature] != "" and all(r[feature] != "" for r in controls)]
        case_count = len(usable)
        if case_count < 2:
            report.append(dict(feature=feature, nominal_cases=56, matched_complete_cases=case_count, case_utc_days=0, case_symbols=0, long_cases=0, short_cases=0, controls_per_case=3, practical_standardized_d=PRACTICAL_D, isolated_bh_alpha=ISOLATED_BH_ALPHA, pooled_robust_scale="", day_cluster_power="", symbol_cluster_power="", conservative_power="", day_95pct_ci_halfwidth_standardized="", symbol_95pct_ci_halfwidth_standardized="", day_isolated_bh_threshold_standardized="", symbol_isolated_bh_threshold_standardized="", power_class="NOT_IDENTIFIABLE"))
            continue
        all_values = [float(r[feature]) for c, controls in usable for r in [c, *controls]]
        med = statistics.median(all_values)
        pooled_scale = 1.4826 * statistics.median(abs(x - med) for x in all_values)
        if pooled_scale <= 0:
            report.append(dict(feature=feature, nominal_cases=56, matched_complete_cases=case_count, case_utc_days=0, case_symbols=0, long_cases=0, short_cases=0, controls_per_case=3, practical_standardized_d=PRACTICAL_D, isolated_bh_alpha=ISOLATED_BH_ALPHA, pooled_robust_scale=0, day_cluster_power="", symbol_cluster_power="", conservative_power="", day_95pct_ci_halfwidth_standardized="", symbol_95pct_ci_halfwidth_standardized="", day_isolated_bh_threshold_standardized="", symbol_isolated_bh_threshold_standardized="", power_class="NOT_IDENTIFIABLE"))
            continue
        differences = [float(c[feature]) - sum(float(r[feature]) for r in controls) / 3 for c, controls in usable]
        # Remove any observed selection effect before power simulation. No effect estimate is output.
        center = statistics.mean(differences)
        residuals = [x - center for x in differences]
        case_days = [c["event_time_utc"][:10] for c, _ in usable]
        case_symbols = [c["symbol"] for c, _ in usable]
        case_sides = Counter(c["side"] for c, _ in usable)
        day_null = clustered_null_means(residuals, case_days, 31005 + idx * 2)
        symbol_null = clustered_null_means(residuals, case_symbols, 31006 + idx * 2)
        delta = PRACTICAL_D * pooled_scale
        day_power, day_critical = power_at_delta(day_null, delta)
        symbol_power, symbol_critical = power_at_delta(symbol_null, delta)
        conservative = min(day_power, symbol_power)
        case_breadth = case_count >= 40 and len(set(case_days)) >= 20 and len(set(case_symbols)) >= 10 and case_sides["LONG"] >= 10 and case_sides["SHORT"] >= 10
        classification = "ADEQUATELY_POWERED" if case_breadth and conservative >= .80 else "MARGINALLY_POWERED" if case_breadth and conservative >= .60 else "UNDERPOWERED"
        day_ci = quantile([abs(x) for x in day_null], .95) / pooled_scale
        symbol_ci = quantile([abs(x) for x in symbol_null], .95) / pooled_scale
        report.append(dict(feature=feature, nominal_cases=56, matched_complete_cases=case_count, case_utc_days=len(set(case_days)), case_symbols=len(set(case_symbols)), long_cases=case_sides["LONG"], short_cases=case_sides["SHORT"], controls_per_case=3, practical_standardized_d=PRACTICAL_D, isolated_bh_alpha=ISOLATED_BH_ALPHA, pooled_robust_scale=format(pooled_scale, ".12g"), day_cluster_power=format(day_power, ".4f"), symbol_cluster_power=format(symbol_power, ".4f"), conservative_power=format(conservative, ".4f"), day_95pct_ci_halfwidth_standardized=format(day_ci, ".4f"), symbol_95pct_ci_halfwidth_standardized=format(symbol_ci, ".4f"), day_isolated_bh_threshold_standardized=format(day_critical / pooled_scale, ".4f"), symbol_isolated_bh_threshold_standardized=format(symbol_critical / pooled_scale, ".4f"), power_class=classification))
    write(PHASE / "diagnostics/power_analysis.csv", report)
    print({r["feature"]: (r["conservative_power"], r["power_class"]) for r in report})


if __name__ == "__main__":
    main()
