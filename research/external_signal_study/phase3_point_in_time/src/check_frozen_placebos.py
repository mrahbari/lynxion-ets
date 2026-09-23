"""Frozen Phase 3A clock-shift negative controls; uses no outcomes or future features."""
import hashlib
import json
import statistics
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from build_family_a_controls import (DATA, EXCLUSION_SECONDS, PHASE, SPEC_HASH,
                                     has_full_lookback, load_open_times, read_csv,
                                     utc_epoch, utc_text, write_csv)
from build_point_in_time_features import FEATURES, calculate, load_bars

DAY = 86400
BAR = 900


def week_start(epoch):
    dt = datetime.fromtimestamp(epoch, timezone.utc)
    return int((dt.replace(hour=0, minute=0, second=0, microsecond=0)
                - timedelta(days=dt.weekday())).timestamp())


def shifted(epoch, days):
    start = week_start(epoch)
    slot = (epoch - start) // BAR
    return start + ((slot + days * 96) % (7 * 96)) * BAR


def main():
    assert hashlib.sha256((PHASE / "preregistration/PHASE3_RESEARCH_SPEC.md").read_bytes()).hexdigest() == SPEC_HASH
    manifest = json.loads((PHASE / "manifests/phase3_proxy_source_manifest.json").read_text())
    cases = {r["signal_id"]: r for r in read_csv(PHASE / "extracted/phase3_cases.csv")}
    matched = sorted({r["case_id"] for r in read_csv(PHASE / "controls/matched_controls.csv")})
    primary = {r["feature"]: r for r in read_csv(PHASE / "diagnostics/primary_fingerprint_comparisons.csv")}
    assert len(matched) == 56 and len(primary) == 6
    signals = defaultdict(list)
    for row in cases.values():
        signals[row["symbol"]].append(utc_epoch(row["signal_timestamp_utc"]))
    opens = {s: load_open_times(DATA / f"{s}.csv", item["sha256"])
             for s, item in manifest["symbols"].items() if item["status"] == "COMPLETE_VALIDATED"}
    panels = {s: load_bars(s, manifest["symbols"][s]["sha256"]) for s in opens}
    assert "BTCUSDT" in opens
    eligible = defaultdict(dict)
    audit = []
    for cid in matched:
        case = cases[cid]
        symbol = case["symbol"]
        original = utc_epoch(case["signal_timestamp_utc"])
        for days, seed in ((1, 31001), (2, 31002), (3, 31003)):
            t = shifted(original, days)
            reason = "ELIGIBLE"
            if t == original or week_start(t) != week_start(original) or t // 14400 % 6 != original // 14400 % 6:
                reason = "SHIFT_OR_BLOCK_MISMATCH"
            elif any(abs(t - x) <= EXCLUSION_SECONDS for x in signals[symbol]):
                reason = "SIGNAL_EXCLUSION"
            elif not has_full_lookback(t, opens[symbol]) or not has_full_lookback(t, opens["BTCUSDT"]):
                reason = "MISSING_PRE_T_LOOKBACK"
            controls = []
            if reason == "ELIGIBLE":
                for control_t in range(week_start(t), week_start(t) + 7 * DAY, BAR):
                    if (control_t // 14400) % 6 != (t // 14400) % 6 or control_t == t:
                        continue
                    if any(abs(control_t - x) <= EXCLUSION_SECONDS for x in signals[symbol]):
                        continue
                    if not has_full_lookback(control_t, opens[symbol]) or not has_full_lookback(control_t, opens["BTCUSDT"]):
                        continue
                    digest = hashlib.sha256(f"phase3a-placebo-v1|{seed}|{cid}|{utc_text(control_t)}".encode()).hexdigest()
                    controls.append((digest, control_t))
                chosen, dates = [], set()
                for digest, control_t in sorted(controls):
                    date = utc_text(control_t)[:10]
                    if date not in dates:
                        chosen.append((digest, control_t))
                        dates.add(date)
                    if len(chosen) == 3:
                        break
                if len(chosen) < 2:
                    reason = "FEWER_THAN_TWO_CONTROLS"
                else:
                    eligible[cid][days] = (t, chosen)
            audit.append(dict(case_id=cid, shift_days=days, seed=seed, original_time_utc=utc_text(original),
                              placebo_time_utc=utc_text(t), candidate_controls=len(controls),
                              selected_controls=len(chosen) if reason in ("ELIGIBLE", "FEWER_THAN_TWO_CONTROLS") else 0,
                              status=reason, retained_for_comparison="PENDING"))
    retained = {cid for cid, shifts in eligible.items() if len(shifts) >= 2}
    for row in audit:
        row["retained_for_comparison"] = "YES" if row["case_id"] in retained and row["status"] == "ELIGIBLE" else "NO"
    pairs = []
    for cid in sorted(retained):
        case = cases[cid]
        for days, (t, controls) in sorted(eligible[cid].items()):
            case_values, availability = calculate(panels[case["symbol"]], panels["BTCUSDT"], t, case["side"])
            assert all(x is not None and x <= t for x in availability.values())
            control_values = []
            for _, control_t in controls:
                values, times = calculate(panels[case["symbol"]], panels["BTCUSDT"], control_t, case["side"])
                assert all(x is not None and x <= control_t for x in times.values())
                control_values.append(values)
            for feature in FEATURES:
                assert case_values[feature] is not None and all(x[feature] is not None for x in control_values)
                pairs.append(dict(case_id=cid, shift_days=days, feature=feature, placebo_day_utc=utc_text(t)[:10],
                                  placebo_time_utc=utc_text(t), control_count=len(controls),
                                  max_input_close_utc=utc_text(max(availability.values())),
                                  paired_difference=format(case_values[feature] - statistics.mean(x[feature] for x in control_values), ".15g")))
    results = []
    for days in (1, 2, 3):
        for feature in FEATURES:
            subset = [r for r in pairs if r["shift_days"] == days and r["feature"] == feature]
            scale = float(primary[feature]["pooled_robust_scale"])
            d = statistics.mean(float(r["paired_difference"]) for r in subset) / scale if subset else None
            real_d = float(primary[feature]["standardized_effect_d"])
            results.append(dict(shift_days=days, seed=31000 + days, feature=feature,
                                retained_case_count=len(subset), independent_utc_days=len({r["placebo_day_utc"] for r in subset}),
                                placebo_standardized_d="" if d is None else format(d, ".6f"),
                                primary_standardized_d=format(real_d, ".6f"),
                                magnitude_matches_or_exceeds_primary="UNKNOWN" if d is None else ("YES" if abs(d) >= abs(real_d) else "NO")))
    write_csv(PHASE / "diagnostics/placebo_shift_audit.csv", audit, list(audit[0]))
    write_csv(PHASE / "diagnostics/placebo_paired_differences.csv", pairs, list(pairs[0]))
    write_csv(PHASE / "diagnostics/placebo_comparisons.csv", results, list(results[0]))
    print(json.dumps({"nominal_cases": len(matched), "cases_with_at_least_two_valid_shifts": len(retained),
                      "valid_shift_counts": {str(i): sum(r["shift_days"] == i and r["retained_for_comparison"] == "YES" for r in audit) for i in (1, 2, 3)},
                      "f4": [r for r in results if r["feature"] == "F4_compression_ratio"]}, sort_keys=True))


if __name__ == "__main__":
    main()
