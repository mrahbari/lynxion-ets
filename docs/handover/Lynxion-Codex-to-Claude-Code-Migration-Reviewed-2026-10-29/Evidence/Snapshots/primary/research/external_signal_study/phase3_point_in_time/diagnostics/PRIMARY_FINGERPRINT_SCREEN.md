# Phase 3A primary six-feature screen — interim, not a verdict

Frozen preregistration: `b9ec946` / SHA-256 `96d0f336f9c0e335b61b8d90df81835180647f9c2d85498d210fa1e34c329193`. This screen uses only the six frozen pre-signal features, 56 matched interval-HMT cases, and their 168 Family-A controls. It does **not** inspect Telegram outcomes, future market returns, profitability, or trade execution.

`src/test_primary_fingerprint.py` computes one paired case-minus-mean-of-three-controls difference per case, a 10,000-replicate UTC-day-cluster bootstrap confidence interval, a 10,000-draw UTC-day-cluster sign-flip p-value (seed `31004 + feature_index`), and Benjamini–Hochberg q-values across six tests. Controls are not counted as independent N. [Machine-readable primary results](./primary_fingerprint_comparisons.csv) and [paired differences](./paired_feature_differences.csv) preserve the reproducible details.

| Feature | Robust-standardized difference d | BH q | Frozen q<=.10 AND abs(d)>=.40 screen |
| --- | ---: | ---: | --- |
| F1 directional 4h return | +0.322 | .630 | FAIL |
| F2 20-bar range location | +0.220 | .254 | FAIL |
| F3 8-bar countertrend pullback | +0.001 | .996 | FAIL |
| F4 compression ratio | +0.476 | .163 | FAIL |
| F5 relative volume | +0.379 | .630 | FAIL |
| F9 BTC directional 4h return | +0.298 | .630 | FAIL |

**No feature passes the preregistered primary q-and-effect screen.** F4's unadjusted day-cluster p≈.027 and positive day-bootstrap interval are *not* a valid fingerprint claim: q≈.163 exceeds the frozen .10 hurdle, and F4's conservative power to detect d=.40 was only ≈41%. We must not relabel it as edge or tune thresholds/features around it. Five of six dimensions were underpowered and F2 only marginally powered in the pre-verdict analysis. Therefore this screen cannot support `PHASE3A_NO_DEFENSIBLE_FINGERPRINT`; absent later prespecified corroboration, the scientifically honest status remains `INCONCLUSIVE_DATA_LIMITED`.

**Robustness specification issue discovered without using outcomes:** M3 adds “same weekday” to Family-A's same ISO week and same four-hour UTC block while also excluding controls within ±6 hours of the case signal. Any same-week, same-weekday, same-block timestamp is <4 hours from the case; therefore M3 has **zero eligible controls by construction**. Mark M3 `NOT_IDENTIFIABLE` in this run; do not relax the exclusion after seeing this screen. M2 names a 30-day BTC volatility tercile but does not freeze an exact volatility estimator/tercile mapping, so no result-dependent formula may be invented now. M2 is pending a separately disclosed append-only amendment if it remains scientifically justified; it cannot be used to rescue or veto the current screen by discretionary definition. These limits must be carried into the final verdict.

Next bounded work: run the still-identifiable frozen chronological, side, leave-symbol-out, and valid placebo checks. If none overturn the current screen, close Phase 3A as underpowered/inconclusive rather than launching an unbounded redesign or Phase 3B. A fresh study could define feasible M2/M3 and a new unopened boundary; it cannot retroactively confirm this opened sample.

**خلاصهٔ ساده:** هیچ‌یک از شش معیار از دروازهٔ ازپیش‌تعیین‌شده عبور نکرد. یک عدد ظاهراً امیدوارکننده در فشردگی بازار بعد از اصلاح چندآزمونی کافی نیست و توان آماری‌اش هم کم است؛ پس هنوز نه edge پیدا شده و نه می‌توان با قطعیت گفت الگویی وجود ندارد.
