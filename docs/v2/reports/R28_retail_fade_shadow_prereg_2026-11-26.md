# R28 — Prospective shadow of XS-COMBO-V1 + retail-fade factor (pre-registered 2026-11-26)

**Why.** E44: fading crowded retail accounts was strong in 2024–26 (V1 + F_RETAIL +12.4 %/yr, 7/7 phases) but not in
2020–23. History cannot settle it, so the decision is taken on new data only.

**Shadow (no trading, no effect on the live sleeve).**
- At every live weekly rebalance, the rebalancer also computes the V1 + F_RETAIL target book. It uses the same live
  panel and universe, plus Binance's all-account long/short ratio.
- F_RETAIL is −mean(log ratio) over the last 3 completed daily values, from `/futures/data/globalLongShortAccountRatio`,
  period 1d. Names without a ratio are not eligible in the shadow.
- The target weights are written to `data/v2_live/shadow_r28/<date>.json` next to the live targets
  (`data/v2_live/targets/<date>.json`).
- Errors are logged and never stop or change the rebalance.

**Evaluation (fixed now).**
- For each week k between consecutive rebalances, compute the model net return of both target books:
  Binance daily close-to-close, real funding, `lib.backtest` cost model on the turnover from the previous week's target.
- Use the paired weekly difference: shadow minus live.

**Decision.**
- Taken at 12 weekly rebalances or 2027-03-01, whichever comes first. No earlier decision, no definition change.
- **CANDIDATE:** mean weekly difference > 0, t ≥ 2.0 on the weekly differences, and ≥ 8 of 12 weeks positive.
  Adoption into the live strategy remains an operator decision.
- **Otherwise:** R28 closed, V1 unchanged.

## Amendment 2026-11-26 (before any shadow data existed; operator focus decision)

**Change.** The shadow is computed **every day**, not only on the live rebalance day.
- Each day, the daily job builds the live panel and writes both the V1 target book and the V1 + F_RETAIL target book to
  `data/v2_live/shadow_r28/<date>.json`.
- Day D serves the weekly phase "D mod 7". This gives 7 paired phases per week.

**Why.**
- E38 showed the weekly rebalance phase alone moves the holdout Sharpe between 0.50 and 1.77.
- A single-phase comparison would mostly measure phase luck.
- It also gives 7× more paired observations.

**Evaluation.**
- For each phase k and week w, compute the 7-day model net return of both books from day D = phase-k rebalance day:
  same daily close-to-close, real funding, `lib.backtest` cost model on the turnover vs the previous target of that phase.
- The weekly difference is averaged over the 7 phases. The t-test runs on these weekly phase-averaged differences.

**Decision.** Unchanged: 12 weeks or 2027-03-01.
- **CANDIDATE:** mean > 0, t ≥ 2, and ≥ 8 of 12 weeks positive.
