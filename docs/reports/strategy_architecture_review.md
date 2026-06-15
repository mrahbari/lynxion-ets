# Strategy Architecture Review

**Date:** 2026-06-13
**Question:** Is the READY = 0 verdict caused by **(A) absence of edge** or **(B) architectural
deployment mistakes**?
**Scope:** Analysis only. No strategy logic, parameters, or thresholds changed. No optimization, no
edge discovery. Evidence drawn from the strategy adapters, `strategy_config.py`, the regime detector,
and the existing Phase-2/5/7/8 reports.

---

## Headline verdict

**Predominantly (B) — architectural deployment mistakes.** The current READY = 0 cannot be read as
"proven absence of edge," because **no strategy was evaluated in its full designed environment**:

1. **Timeframe:** per-strategy design timeframes (1m → 1h) are declared in `strategy_config.py` but the
   accessor `get_strategy_timeframe(name, default)` **ignores `name`** (`:104-112`) — there is no real
   per-strategy routing — and the profitability matrix flattened **all** strategies onto a uniform
   **15m/30m/1h** grid, while the firing diagnostic ran **only on BTC 1m**.
2. **Regime:** a regime detector exists (`infrastructure/market_regime/regime_detector.py`) but only
   feeds **soft risk/scoring weights**; strategies are effectively always-on, and validation was
   **never regime-conditioned** (trend strategies measured across ranging/choppy periods, and vice
   versa).
3. **Asset universe:** **SOL is a universal failure** (0 positive cells for every strategy) and was
   **pooled** into an all-three-must-be-positive roll-up, dragging down strategies with genuine
   single-symbol (BTC- or ETH-) behaviour.

Of the 10 surviving strategies: **3 are ARCHITECTURALLY INVALIDATED (as implemented)** — their core
mechanism is stubbed or absent, so they cannot express their hypothesis by construction; **7 are
ARCHITECTURALLY MISDEPLOYED** — sound, faithfully-implemented hypotheses evaluated outside their
designed timeframe/regime/asset; **0 are ARCHITECTURALLY SOUND** (none was both faithfully implemented
*and* tested in its designed environment and still shown edgeless). This does **not** prove an edge
exists — it proves the current verdict **cannot distinguish "no edge" from "wrong environment."**

> Important constraint: correcting the deployment (per-strategy TF, regime activation, per-symbol
> evaluation) is itself bounded by the standing freeze (no parameter/threshold/optimization changes).
> This review identifies the misdeployment; it does not re-run or re-tune anything.

---

## The matrix

Designed TF/market from code + `hypothesis-fidelity-review.md`; Tested TF/market from
`timeframe-validation-report.md` / `cross-symbol-stability-report.md` (15m/30m/1h × BTC/ETH/SOL × 90/180/365d).
"Regime Match" = was the strategy evaluated only in the regime it targets? (No, for all — validation
was not regime-conditioned.)

| Strategy | Designed TF | Tested TF | Designed regime / asset | Tested market | Regime match | Conclusion |
|----------|-------------|-----------|--------------------------|---------------|--------------|------------|
| trend_following | 1h | 15m/30m/1h | trending / any liquid | BTC+ETH+SOL, all regimes | ❌ no | **MISDEPLOYED** (regime + SOL) |
| mean_reversion | 1h | 15m/30m/1h | ranging (hard-gated) / any | all regimes; ~2–6 trades | ❌ no (too few in-regime) | **MISDEPLOYED** (sample/regime) |
| momentum | 1h | 15m/30m/1h | trending continuation / any | all regimes; BTC+ ETH/SOL− | ❌ no | **MISDEPLOYED** (regime + SOL) |
| breakout | 15m | 15m/30m/1h | range-compression→expansion / any | 0 trades (confidence-scale defect) | n/a — untradeable | **MISDEPLOYED** (untradeable as wired → never fairly tested) |
| liquidity | **5m** | 15m/30m/1h | stop-sweep reversal / liquid (FX-session design) | off-design TF; ETH+ only | ❌ no | **MISDEPLOYED** (wrong TF + asset) |
| mtf_trend | **multi-TF** (3m/15m/1h/4h) | single 15m/30m/1h | multi-TF trend alignment / any | single-TF only; BTC+ ETH/SOL− | ❌ no | **INVALIDATED** (MTF core is a single-TF EMA stub; `compute_trend`/weights dead) |
| oi_footprint | 1h | 1h | OI build-up/flush / **derivatives w/ OI** | 1h, never reads OI; empirical Δ=0 | n/a | **INVALIDATED** (never consumes OI; named architecture absent) |
| sweep_scalper | **1m** | 15m/30m/1h | liquidity-sweep microstructure / liquid | off-design TF; sweep detector stubbed | ❌ no | **INVALIDATED** (`detect_sweep` returns 0/unused; killzone unused) |
| vwap_reversal | **5m** (session-anchored) | 15m/30m/1h | mean-reversion (gated) / liquid w/ volume | off-design TF; ~7–12 trades @≥15m | ❌ no | **MISDEPLOYED** (wrong TF; rejection path dead but core fires) |
| volatility_breakout | 15m | 15m/30m/1h | high-volatility / breakout / any | all regimes; small negatives | ❌ no | **MISDEPLOYED** (regime + SOL) |
| — *scalping (RETIRED)* | **1m** | 15m/30m/1h | scalp, move>cost / **high-vol instrument** | 1m: 0 trades (cost gate); 15m+: loses | ❌ no | INVALIDATED on 1m crypto (thesis economically false) **and** misdeployed by asset (never tested on the higher-vol instrument its thesis needs) |
| — *crypto_breakout (RETIRED)* | = breakout | = breakout | identical alias | identical | n/a | RETIRED correctly (code alias of `breakout`, not a distinct architecture) |

**Tally (10 surviving): INVALIDATED = 3 · MISDEPLOYED = 7 · SOUND = 0.**

---

## Per-strategy reconstruction & verdict

### ARCHITECTURALLY INVALIDATED (core mechanism not implemented — cannot express its hypothesis)

**mtf_trend** — *Hypothesis:* trade trends confirmed across multiple timeframes. *Reality:* the adapter
declares `["3m","15m","1h","4h","1D"]` with per-TF weights, but `generate_signal` is **single-timeframe**
— it proxies "timeframes" with three EMA periods on one buffer; `compute_trend()` returns 0 (mock) and
the timeframe/weight fields are dead (`mtf_trend_strategy_adapter.py:31-35,57-60`; fidelity audit
"functional but NOT true MTF"). The defining architecture (MTF confirmation) is absent → **INVALIDATED
as implemented**. (It showed an isolated BTC positive as a plain single-TF EMA trend follower.)

**oi_footprint** — *Hypothesis:* open-interest build-up/flush confirms or fades price. *Reality:* the
implementation **never reads OI** — it is a volume-spike + RSI confirmation strategy; the OI config is
vestigial; Phase-8 measured **delta = 0** against real OI on every symbol, and only ~30d hourly OI
exists (`phase8/oi_footprint_validation.md`). The named architecture is unrealized and untested →
**INVALIDATED as implemented**.

**sweep_scalper** — *Hypothesis:* fade/continue after a liquidity sweep (stop-run) inside ICT
"killzone" sessions. *Reality:* `detect_sweep()` is a **stub returning 0 (unused)** and `killzone` is
**never used**; reduced to a 1.5× range-expansion + 3-bar momentum proxy that over-fires (~11.6k signals)
(`sweep_scalper_strategy_adapter.py:21-28,55-86`). The sweep-detection architecture is a stub →
**INVALIDATED as implemented** (also misdeployed by TF: design 1m, tested 15m+).

### ARCHITECTURALLY MISDEPLOYED (sound, faithfully implemented, evaluated in the wrong environment)

**trend_following** (design 1h ✓, but un-conditioned regime + SOL): established-trend pullback with
anti-chop and trend-extreme gates; faithful post-fix. Judged across ranging/choppy periods and with SOL
pooled (all-symbol negative). Its targeted regime was never isolated.

**momentum** (design 1h ✓, regime + SOL): continuation gate (persistence + continuation-probability ≥0.6).
**BTC-positive, SOL −3364** — a single-symbol signal buried by the SOL pool and by measuring a
continuation strategy across non-trending periods.

**volatility_breakout** (design 15m ✓, regime + SOL): ATR/volatility-expansion breakout. Small
negatives, no positive cell — but a breakout strategy measured across low-volatility/ranging periods
and with SOL is not tested in its environment.

**mean_reversion** (design 1h ✓, but sample/regime): hard-gated to non-expanding-volatility,
non-trending ranges. It correctly **self-selects** to ~2–6 trades at ≥15m → declared "unjudgeable
(intrinsic selectivity)." That is an evaluation-environment problem (insufficient in-regime sample),
not a demonstrated absence of edge.

**breakout** (design 15m ✓, untradeable): range-compression→expansion with a Type-B
confidence-vs-`min_confidence` scale defect → **0 trades**. Fixing it is a threshold change (disallowed),
so it was **never fairly evaluated** → misdeployed/untested, not edgeless.

**liquidity** (design **5m**, tested 15m+): stop-sweep fade; Type-A directional bug fixed. Tested off
its design TF (frequency-starved at ≥15m) and with FX-session logic that was simulated. ETH-only small
positive.

**vwap_reversal** (design **5m**, session-anchored, tested 15m+): session-VWAP reversion in a
non-trending regime; core fires post-fix (~7–12 trades @≥15m — starved). Residual dead rejection-pattern
path (a documented type-C, not the core). Judged off design TF.

### ARCHITECTURALLY SOUND
**None.** No strategy was both faithfully implemented *and* evaluated in its designed timeframe **and**
regime **and** per-symbol — so "genuine absence of edge" is not established for any.

---

## Deployment evaluations (Task 5)

**1. Should SOL be excluded?** — **Yes, from the pooled verdict.** SOL produced **0 positive cells for
every strategy** and posts catastrophic losses (momentum −3364, mtf_trend −2983, oi_footprint −965 @1h);
the report itself titles a section *"SOL is a universal failure mode"* (`cross-symbol-stability-report.md:27-32`).
Pooling SOL into an "all three must be positive" rule mechanically forces NEEDS_IMPROVEMENT on
strategies that are positive on BTC or ETH. Recommendation: evaluate per-symbol and treat SOL as a
separate (currently failing) universe rather than a veto on BTC/ETH results. *(Whether SOL is genuinely
edgeless or simply a different regime/microstructure is itself an open question — not resolved here.)*

**2. Should BTC/ETH be evaluated independently?** — **Yes.** Results are reported per-symbol (good), but
the **disposition is a cross-symbol roll-up** requiring all three positive (`cross-symbol-stability-report.md:48-52`).
That masks real single-symbol structure: BTC-favourable = momentum, mtf_trend; ETH-favourable =
oi_footprint, liquidity, trend_following. Independent BTC and ETH verdicts are warranted (with the
honest caveat that a single-symbol positive may still be noise/overfit — non-overlap across symbols is
evidence of that, per the reports).

**3. Is strategy-specific timeframe assignment required?** — **Yes, and it is currently broken.**
`strategy_config.py` declares per-strategy TFs (scalping/sweep_scalper 1m; liquidity/vwap_reversal 5m;
breakout/volatility_breakout/mtf_trend 15m; trend_following/mean_reversion/momentum/oi_footprint 1h),
but `get_strategy_timeframe(name, default)` **ignores `name`** (`:104-112`) and the matrix tested all on
15m/30m/1h. Real per-strategy TF routing + evaluation on each strategy's design TF is required before any
edge claim. (Four strategies — scalping, sweep_scalper, liquidity, vwap_reversal — were judged entirely
off their design TF.)

**4. Is regime-based activation required?** — **Yes.** A regime detector exists but only contributes a
**soft scoring/risk bonus** (`strategy_services.py:167-169`; `enterprise_risk_manager.py:134-135`);
strategies are effectively always-on, and validation was never regime-conditioned. Trend strategies
(trend_following, momentum, mtf_trend) should be activated/evaluated in trending regimes; reversion
strategies (mean_reversion, vwap_reversal, liquidity) in ranging regimes; breakout/volatility strategies
in expansion regimes. Without regime gating, every strategy is measured ~⅔ of the time in the regime it
explicitly says it should not trade.

---

## A vs B — final answer

**The READY = 0 verdict is predominantly explained by (B) architectural deployment mistakes, not by a
demonstrated (A) absence of edge.**

- 3 strategies (mtf_trend, oi_footprint, sweep_scalper) **cannot** show an edge because their defining
  mechanism is a stub/absent — their verdict reflects *implementation*, not *hypothesis*.
- 7 strategies were evaluated outside their designed timeframe and/or regime, with SOL pooled — so their
  "no edge" results are **not trustworthy as edge tests**.
- 0 strategies received a clean, in-environment test.

This does **not** assert that any strategy *has* an edge — it asserts the current evidence **cannot
decide**. To convert this into a real A-vs-B answer would require (within a future, un-frozen scope):
per-strategy design-TF evaluation, regime-conditioned activation, and per-symbol (BTC/ETH) verdicts with
SOL separated — **none of which is performed here** (no code, no tuning, analysis only).

### Per-strategy verdict summary
- **ARCHITECTURALLY INVALIDATED (as implemented):** mtf_trend, oi_footprint, sweep_scalper
- **ARCHITECTURALLY MISDEPLOYED:** trend_following, mean_reversion, momentum, breakout, liquidity,
  vwap_reversal, volatility_breakout
- **ARCHITECTURALLY SOUND:** none
- *(RETIRED: scalping — invalidated on 1m crypto / misdeployed by asset; crypto_breakout — redundant alias)*
