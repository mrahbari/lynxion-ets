# Phase 15 — XRP / DOGE / LINK Repeatability

**Date:** 2026-06-13. Analysis only; no logic/threshold/param changes; no profitability claim. Focused
question (Task 5): **do the XRP / DOGE / LINK positives observed in prior phases persist across
multi-year history, or collapse?**

## What prior phases actually claimed

Phase 12 / reclassification-v2 found the *only* positives in the entire suite were XRP-clustered (with
weaker DOGE/LINK echoes), and explicitly labelled them **"INCONCLUSIVE-episodic, back-loaded,
high-drawdown, pending longer data"** — never reclassified upward. Specifically (on ~1,000-bar / short
windows):

| Strategy | v2 positive claim | flagged |
|---|---|---|
| trend_following | XRP/DOGE positive in 3/4, 2/4 folds (front folds negative) | episodic, high-DD |
| momentum | XRP **+0.39%** (one fold −0.52, −32% DD, back-loaded) | episodic |
| oi_footprint | XRP **+0.38% (4/4 folds)**, DOGE +0.09, LINK +0.04 | back-loaded, sub-50% win |

These were the strongest "maybe there's something on alts" signals in the program. Phase 15 tests them on
**7–9 years** instead of weeks.

## What multi-year history shows: COLLAPSE

| Strategy | Symbol | v2 (short window) | **Phase-15 (full history)** | verdict |
|---|---|---|---|---|
| trend_following | XRP | + in 3/4 folds | **−0.147%**, 1/4 folds, win 0.38 (n=4,764) | collapsed |
| trend_following | DOGE | + in 2/4 folds | **−0.108%**, 1/4 folds (n=4,078) | collapsed |
| trend_following | LINK | weak + | **−0.197%**, 1/4 folds (n=5,414) | collapsed |
| momentum | XRP | **+0.39%** | **−0.280%**, **0/4** folds, win 0.38 (n=9,198) | collapsed |
| momentum | DOGE | (echo) | −0.272%, 0/4 (n=8,389) | collapsed |
| momentum | LINK | (echo) | −0.301%, 0/4 (n=11,434) | collapsed |
| oi_footprint | XRP | **+0.38% (4/4)** | **−0.190%**, 1/4 folds (n=4,932) | collapsed |
| oi_footprint | DOGE | +0.09% | −0.150%, 1/4 (n=4,852) | collapsed |
| oi_footprint | LINK | +0.04% | −0.348%, 0/4 (n=5,169) | collapsed |

**Every** XRP/DOGE/LINK positive from prior phases turns **negative** over full history, with much larger
samples (4k–11k in-regime signals) and walk-forward stability of at best 1/4 folds (never all four).

## Why the prior positives appeared — and why they were not edge

- **They were single-window, back-loaded cycle artifacts.** The v2 fold pattern ("front folds negative,
  back folds positive") was the tell: the positives lived in one favourable late-window regime
  (the 2025 alt move on the ~1,000-bar slice). Phase 15's 4-fold walk-forward over 7–9 years shows the
  positive fold is **isolated** — e.g. trend_following XRP fold-expectancies
  `[−0.0019, −0.0010, −0.0044, +0.0009]`: only the last fold is positive, and barely.
- **Win rates are 0.37–0.43 throughout** — these are not high-hit strategies that cost is merely eroding;
  they are directionally wrong more often than right on these symbols over the long run.
- **The collapse is consistent across all three alts and both majors** — i.e. it is not "XRP is
  special," it is "the short window was special."

## They collapse already at 1-year scale (not just multi-year)

The collapse does **not** require multi-year data. Re-running the directional strategies on the
**most-recent 1 year** gives the same negative, fold-unstable result (trend_following XRP −0.103%,
momentum XRP −0.190%, oi_footprint XRP −0.190% — all 0–1/4 folds; see `long_history_validation.md`). The
v2 positives originated from an even shorter **~42-day / ~1,000-bar** slice, not a full year. So the alt
positives are gone the moment the window widens to a year, and remain gone across 7–9 years. **One year
is sufficient to disprove them**; the long history simply removes any residual doubt.

## Direct answer

**The XRP / DOGE / LINK positives do not persist — they collapse, already at 1-year scale and across
multi-year history.** They were
episodic, window-dependent artifacts, exactly as the v2 "pending longer data" flag suspected. There is
**no repeatable, cost-adjusted, walk-forward-stable edge** on XRP, DOGE, or LINK for any of the five
re-tested strategies. This removes the last open "maybe there's an alt-symbol edge" question from the
program: the answer is no.
