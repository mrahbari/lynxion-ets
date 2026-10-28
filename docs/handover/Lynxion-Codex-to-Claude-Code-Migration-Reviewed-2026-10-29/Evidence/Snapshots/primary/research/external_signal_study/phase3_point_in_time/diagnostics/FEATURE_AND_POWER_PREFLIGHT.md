# Phase 3A frozen-feature and pre-verdict power checkpoint

**Status:** FEATURE_INTEGRITY_PASS / POWER_LIMITED / NO_FINGERPRINT_VERDICT. Preregistration SHA-256 `96d0f336f9c0e335b61b8d90df81835180647f9c2d85498d210fa1e34c329193` (commit `b9ec946`). This checkpoint has **not** evaluated observed case-control effect directions, p/q-values, placebos, forward returns, or economic performance.

`src/build_point_in_time_features.py` computed exactly the six prespecified pre-T variables for the 56 matched interval-HMT cases and 168 Family-A controls. [Feature table](../features/point_in_time_features.csv) contains 224 records, source-file hashes, each feature's latest input-close timestamp, and an overall leakage assertion. [Dictionary](../features/feature_dictionary.csv) contains fixed formulas and lookback requirements; [missingness report](./missingness_report.csv) shows **zero missing values** for all six features in those 224 records. An independent synthetic check changed a future bar after T by an extreme amount and confirmed all six feature values stayed unchanged. Every recorded input close is `<=` its own case/control time. CSV source hashes were rechecked against the committed public-source manifest.

For the pre-analysis [power table](./power_analysis.csv), each case is paired with the mean of its three controls; the controls are never treated as independent case observations. The power script centers those paired differences before simulation and writes **no observed effect estimate**. It resamples whole UTC-day clusters and whole symbol clusters separately (10,000 fixed-seed replicates each), adds the frozen practically meaningful `d=0.40` shift in pooled robust-scale units, and conservatively uses the lower of the two power estimates. It uses the isolated-discovery Benjamini–Hochberg q=.10 threshold (`alpha=.10/6`) rather than an unadjusted p=.05 threshold. Approximate null 95% CI half-widths and FDR hurdle widths are recorded. These are simulation-based planning estimates; separate day/symbol resamples do not model every possible two-way dependence, so adequacy must not be overstated.

| Frozen feature | Conservative estimated power to detect d=.40 | Preregistered class |
| --- | ---: | --- |
| F1 directional 4h return | 12.65% | UNDERPOWERED |
| F2 20-bar range location | 70.57% | MARGINALLY_POWERED |
| F3 8-bar countertrend pullback | 15.27% | UNDERPOWERED |
| F4 compression ratio | 40.75% | UNDERPOWERED |
| F5 relative volume | 6.26% | UNDERPOWERED |
| F9 BTC directional 4h return | 8.23% | UNDERPOWERED |

Breadth minima are met at this stage—56 matched cases, 23 UTC days, 22 symbols, 25 LONG and 31 SHORT—but **none** of the six reaches the frozen >=80% adequacy threshold after the conservative clustering/FDR hurdle. This does **not** say the selection fingerprint is absent. Even a non-significant primary test cannot yield `PHASE3A_NO_DEFENSIBLE_FINGERPRINT` under the frozen null-result rule. Later testing may still report a positive, stable candidate if all acceptance conditions pass; otherwise the correct overall category is likely `PHASE3A_INCONCLUSIVE_DATA_LIMITED`.

Next bounded action: execute the prespecified case/control differences, day-cluster uncertainty, BH correction, chronological/symbol/side robustness, M2/M3 matching sensitivity, and placebos without changing the six features or controls. Report any candidate as *selection information only*, not executable edge. Do not begin Phase 3B economic outcomes. The exact sibling market venue, true opportunity universe, and two source-unverified symbols (`ALUSDT`, `XAUUSD`) remain limitations.

**خلاصهٔ ساده:** داده‌های قبل از سیگنال درست و کامل محاسبه شدند، اما تعداد رویدادهای واقعاً مستقل برای ردکردن بیشتر فرضیه‌ها کافی نیست. فعلاً نه نشانهٔ سود داریم و نه حق داریم نتیجه بگیریم «هیچ الگوی انتخابی وجود ندارد».
