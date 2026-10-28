# Phase 15 — Long-History Validation

**Date:** 2026-06-13. Analysis only. **No strategy logic / thresholds / parameters / risk models /
execution code modified.** No profitability assumed or claimed. This file answers the phase question:
**is the remaining uncertainty (READY=0, INCONCLUSIVE=4) caused by insufficient historical coverage, or
by a genuine absence of edge?**

## Method (identical evaluation contract to prior phases, longer data + 4-fold WFO)

- **Symbols** (those with any prior positive/partial-positive behavior): XRP, DOGE, LINK, BTC, ETH.
- **Strategies** (those that showed any positive evidence): trend_following, momentum, oi_footprint,
  mean_reversion, vwap_reversal.
- **Longest available history acquired** (paginated Binance public klines,
  `scripts/fetch_long_history.py`):

| Symbol | 1h history | 5m history (vwap) |
|---|---|---|
| XRP | 2018-05-04 → 2026-06-13 (~8.1y, 71,001 bars) | 2023-06-13 → 2026-06-13 (315,757) |
| DOGE | 2019-07-05 → 2026-06-13 (~6.9y, 60,793) | 2023-06-13 → 2026-06-13 (315,757) |
| LINK | 2019-01-16 → 2026-06-13 (~7.4y, 64,859) | 2023-06-13 → 2026-06-13 (315,757) |
| BTC | 2017-08-17 → 2026-06-13 (~8.8y, 77,205) | 2025-06-11 → 2026-06-11 (105,122) |
| ETH | 2017-08-17 → 2026-06-13 (~8.8y, 77,205) | 2025-06-11 → 2026-06-11 (105,121) |

  This spans the 2018 bear, 2020–21 bull, 2022 bear, 2023–24 recovery and 2025–26 — **multiple full
  market cycles** (vs the ~1,000-bar / ~1-year windows of prior phases).
- **Evaluation:** design-TF only (1h for 4 strategies, 5m for vwap_reversal — via
  `StrategyConfig.get_strategy_timeframe`, unchanged), **per-symbol** (never pooled),
  **regime-conditioned** (expectancy on the strategy's intended regime), **cost-adjusted** (existing
  0.30% round-trip = 2×(0.001 fee + 0.0005 slippage), unchanged), **4-fold sequential walk-forward** on
  in-regime signals. Metric = net forward-return expectancy per actionable signal (signal-quality WITH
  cost), horizon matched to design TF. Harness: `scripts/phase15_long_history_validation.py`. Raw:
  `phase15_results.json`.

## Results — directional strategies (ample sample, decisively negative)

| Strategy | Symbol | in-regime n | net expectancy | win | WFO folds + | all-4-folds + |
|---|---|---:|---:|---:|---:|:--:|
| **trend_following** | XRP | 4,764 | **−0.147%** | 0.38 | 1/4 | ❌ |
| | DOGE | 4,078 | −0.108% | 0.40 | 1/4 | ❌ |
| | LINK | 5,414 | −0.197% | 0.43 | 1/4 | ❌ |
| | BTC | 4,937 | −0.157% | 0.37 | 0/4 | ❌ |
| | ETH | 5,462 | −0.214% | 0.38 | 0/4 | ❌ |
| **momentum** | XRP | 9,198 | **−0.280%** | 0.38 | **0/4** | ❌ |
| | DOGE | 8,389 | −0.272% | 0.39 | 0/4 | ❌ |
| | LINK | 11,434 | −0.301% | 0.42 | 0/4 | ❌ |
| | BTC | 7,964 | −0.301% | 0.37 | 0/4 | ❌ |
| | ETH | 10,283 | −0.224% | 0.39 | 0/4 | ❌ |
| **oi_footprint** | XRP | 4,932 | **−0.190%** | 0.39 | 1/4 | ❌ |
| | DOGE | 4,852 | −0.150% | 0.40 | 1/4 | ❌ |
| | LINK | 5,169 | −0.348% | 0.42 | 0/4 | ❌ |
| | BTC | 5,391 | −0.269% | 0.37 | 0/4 | ❌ |
| | ETH | 5,398 | −0.237% | 0.40 | 0/4 | ❌ |

- **Every directional strategy is negative net of cost on every symbol over multi-year history**, with
  **thousands** of in-regime signals (not a small-sample issue) and win rates 0.37–0.43.
- **No symbol is sign-stable across the 4 walk-forward folds** — at best 1/4 folds positive (a single
  early-cycle window), never all four. The few positive folds are isolated cycle artifacts.
- `oi_footprint` is the as-implemented (volume-spike + momentum) behavior; its named OI mechanism is
  stubbed and **untestable on long history** anyway — real OI history caps at ~30 days (BTC/ETH/SOL
  only). Long coverage cannot rehabilitate it.

## Results — selective strategies (frequency-starved even at multi-year scale)

| Strategy | Symbol | bars | signals_total | **in-regime n** | net expectancy |
|---|---|---:|---:|---:|---:|
| **mean_reversion** | XRP | 71,001 | 44 | **3** | −4.48% |
| (1h) | DOGE | 60,793 | 37 | 9 | −0.27% |
| | LINK | 64,859 | 29 | 1 | −2.80% |
| | BTC | 77,205 | 36 | 6 | −0.97% |
| | ETH | 77,205 | 47 | 5 | +0.04% |
| **vwap_reversal** | XRP | 315,757 | 22 | **3** | −0.50% |
| (5m) | DOGE | 315,757 | 18 | **0** | — |
| | LINK | 315,757 | 35 | **0** | — |
| | BTC | 105,122 | 75 | 8 | −0.79% |
| | ETH | 105,121 | 24 | 1 | −1.52% |

- **mean_reversion fires ~37–47 times in 60,000–77,000 bars** (~0.06% of bars), and only **1–9** of those
  land in its intended `ranging` regime. **vwap_reversal fires 18–75 times in up to 315,757 bars**, with
  **0–8** in-regime (DOGE/LINK: literally zero in-regime signals over 3 years of 5-minute data).
- This is **decisive**: their inconclusiveness is **NOT a data-coverage problem.** Multiplying the data
  by 60×–300× did not produce a measurable in-regime sample. The cause is **intrinsic selectivity** in
  the strategy logic (which is frozen and was not touched) — more history cannot fix it.

## 1-year vs full-history: the verdict is the same (1 year suffices here)

A 1-year window (most-recent 8,760 1h bars) gives the **same conclusion** as the full 7–9 years — both
uniformly negative and fold-unstable. The two views agree, which is itself the proof that **coverage is
not the binding constraint**:

| Strategy / symbol | 1-yr expectancy | 1-yr WFO | full-history expectancy | full WFO |
|---|---:|---:|---:|---:|
| trend_following / XRP | −0.103% | 1/4 | −0.147% | 1/4 |
| trend_following / DOGE | −0.250% | 1/4 | −0.108% | 1/4 |
| trend_following / LINK | −0.456% | 0/4 | −0.197% | 1/4 |
| trend_following / BTC | −0.215% | 0/4 | −0.157% | 0/4 |
| trend_following / ETH | −0.288% | 0/4 | −0.214% | 0/4 |
| momentum / XRP | −0.190% | 0/4 | −0.280% | 0/4 |
| momentum / (DOGE,LINK,BTC,ETH) | −0.26 to −0.36% | 0/4 | −0.22 to −0.30% | 0/4 |
| oi_footprint / XRP | −0.190% | 0/4 | −0.190% | 1/4 |
| oi_footprint / (DOGE,LINK,BTC,ETH) | −0.20 to −0.48% | 0–1/4 | −0.15 to −0.35% | 0–1/4 |

**Reading:** every cell is negative in both views; no sign flips between 1-year and multi-year. The v2
"positives" did **not** come from a 1-year window — they came from an even shorter ~42-day / ~1,000-bar
slice. They are already absent at 1-year scale. **So 1 year is enough to reach the INVALIDATED verdict;
the multi-year run confirms it and, importantly, directly answers the phase's coverage question** — more
history does not change the result. (Contrast with Phase-14 funding, where a 1-year window *did* create a
false positive — there the conclusion was sign-sensitive to window; here it is not.)

## The phase question — answered

> Is the remaining uncertainty caused by insufficient historical coverage rather than absence of edge?

**No.** Long history resolves the question in two distinct ways:

1. **Directional strategies (trend_following, momentum, oi_footprint): the uncertainty was the
   *episodic positives*, and longer history shows they are absence-of-edge, not under-coverage.** With
   thousands of in-regime signals over 7–9 years they are uniformly negative and walk-forward-unstable.
   The XRP/DOGE/LINK positives that prior phases flagged "pending longer data" **collapse** (detailed in
   `xrp_doge_link_repeatability.md`).
2. **Selective strategies (mean_reversion, vwap_reversal): the uncertainty was *insufficient in-regime
   sample*, and longer history shows that scarcity is structural, not a coverage gap.** Even 60k–315k
   bars yield 0–9 in-regime signals — so they remain unjudgeable, but now for a *known* reason
   (intrinsic rarity) that additional data is proven not to cure.

**Conclusion: insufficient historical coverage is NOT the cause of READY=0.** Reclassification →
`strategy_reclassification_v3.md`; replacement assessment → `replacement_eligibility_review.md`;
overall verdict → `final_phase15_verdict.md`.
