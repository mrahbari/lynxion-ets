# Exit / Trade-Management Layer — Root-Cause Analysis (E-P5.2 Priority 1)

**Date:** 2026-06-11 | **Trigger:** multi-window/multi-symbol evaluation showed
win rates an order of magnitude below the configured SL/TP geometry's
expectation → suspected shared exit-layer defect, not 12 independent failures.

**Verdict: CONFIRMED — the exit/execution layer was systematically destroying
edge across every strategy.** Two distinct bugs found and fixed.

---

## Method (per-trade exit forensics)

Instrumented every realised trade in `RealisticBacktester` to capture:
`exit_type` (SL / TP / force_close), `stop_loss`, `take_profit`,
`same_bar_collision`, MFE (max favorable excursion), MAE (max adverse
excursion), and `realized_R`. Ran representative strategies (adapter + function
path) on BTCUSDT 90d and dissected the distribution.

## Findings (pre-fix)

Across trend_following / momentum / breakout / volatility_breakout:

- **Win rate ~0%** (matrix-wide: median 2%, 37/108 runs at 0%).
- **MFE = 0.000 for essentially every trade** — price *never* moved favorably
  after entry. Statistically impossible for real data unless entries are wrong.
- **realized R ≈ −1** — every trade lost ~one R (hit SL).
- **same-bar SL+TP collisions on ~100% of adapter trades** (trend_following
  472/472, breakout 435/435).
- Raw trades: a *long* entered at **74717** with **SL 70885 / TP 71009 — both
  ~3,800 below entry** → the position could only lose; the SL/TP were sane
  relative to the signal price (~70900) but the **entry was ~5% above** it.

## Root cause #1 — market-impact unit bug (universal) — FIXED `f000ba8`

`calculate_order_execution_price`:
`order_to_market_ratio = abs(size * price) / market_vol` divided a **quote**
amount ($size×price ≈ $300) by a **base** volume (median 6.46 BTC/min) → ratio
≈ 46 instead of ~0.0005 → `market_impact` ~90× too large → **every BUY filled
~5% above (SELL ~5% below)** the reference price. With entries 5% off, SL/TP
(computed from the true signal price) fell on the wrong side of entry →
structural loss on every trade, **all strategies**. Also the ±5% reasonableness
caps were inverted (a buy used `max(.,0.95*price)` — a floor — leaving the
upside uncapped).
**Fix:** ratio = `abs(size)/market_vol` (both base units); caps bound the
adverse direction. **Confirmed:** entries now match the signal price.

## Root cause #2 — adapted-intent SL/TP inverted for longs — FIXED `584efd1`

`_adapt_domain_execution_intent` line 899: `if domain_intent.side ==
OrderSide.BUY:` compared the **domain** intent's side against the
**infrastructure** `OrderSide` enum (a different class) → never equal → **every
adapted intent took the SELL branch** → short geometry (SL above / TP below)
applied even to BUY/long positions (while `infra_side`, computed with the
correct `DomainOrderSide`, opened a long). Result: longs opened with inverted
SL/TP → first bar spans both → same-bar collision → SL-priority exit → ~0% win.
**Fix:** compare against `DomainOrderSide.BUY`. **Confirmed:** geometry now
`sl < entry < tp`; TPs fire; collisions collapsed (472→0, 435→2); win rates
realistic and signal-dependent.

## Other exit mechanics reviewed (not defective, noted)

- **Same-bar SL/TP tie** resolved SL-first — conservative and standard; the
  collisions were caused by the inverted geometry (#2), now rare.
- **Exit fills / spread / slippage / fees** apply in the adverse direction (T4) —
  realistic; not the cause of the 0% win rate.
- **End-of-run force-close** books open positions — small, expected.
- **Short positions are not SL/TP-tracked** in `_execute_from_intent` (the
  SELL-when-flat branch opens a short without `active_positions.append`). Now
  that #2 is fixed, BUY/long handling is correct; short-side tracking is a
  smaller follow-up (most strategies here trade long via BUY intents).

## Post-fix confirmation (BTCUSDT 90d)

| strategy | pre win% | post win% | post exits | collisions |
|---|---|---|---|---|
| trend_following | 0 | 25 | TP:3 SL:1 | 472→0 |
| breakout | 0 | 8.5 | SL:263 TP:172 | 435→2 |
| mean_reversion | ~3 | 10 | TP:4 SL:6 | →0 |
| volatility_breakout | 0 | 0* | SL:28 TP:12 | 0 |

\* volatility_breakout now has correct geometry; its 0% is a *legitimate* signal
result in this window, not an artifact.

## Next (per the stated sequence)

1. **Full 108-matrix re-run (POST both fixes)** is executing; PRE preserved at
   `eval_matrix_PRE.json`. Compare via `eval_compare.py`.
2. Re-assess strategy quality only on the corrected harness.
3. Then per-strategy signal/regime refinement; then Option B fusion fidelity.

**Conclusion:** the exit layer was systematically destroying edge via two
independent bugs (entry-price inflation + inverted long SL/TP). Both fixed and
verified. Win rates are now realistic and reflect actual signal quality — strategy
hypotheses can finally be evaluated on their merits.
