# Phase 6.5 — Edge Coverage Audit

**Date:** 2026-06-11   **Type:** research-coverage audit ONLY. No backtests, no
new signals, no parameter searches, no optimization. Purpose: decide whether
paid-data acquisition is justified or premature, by mapping what Phase-6 actually
tested against the full hypothesis space.

**Headline answer (detail in §7):** We have **NOT exhausted free-data edge
discovery** — we exhausted **one subset** of it (simple single-asset technical +
funding-carry + naive cross-sectional + simple volatility-regime). Multiple major
**free-data** hypothesis classes remain **untested**. **Paid-data acquisition is
premature.**

---

## 1. Hypothesis taxonomy for systematic trading

Organised by the **source of edge** (not by indicator). Eight top-level classes:

- **C1 Time-series / single-asset technical** — trend/momentum, mean-reversion,
  breakout/range, volatility-based, volume/liquidity-derived.
- **C2 Cross-sectional / relative-value** — XS momentum/reversal, factor-sorted
  portfolios (size/liquidity/beta), pairs & cointegration (stat-arb), lead-lag
  networks.
- **C3 Carry / term-structure / positioning** — funding carry, spot-perp **basis**,
  funding **term-structure**, open-interest dynamics, options-implied (skew/VRP).
- **C4 Microstructure / order-flow** — L2 order-book imbalance/absorption/sweeps,
  trade-tape aggressor flow, liquidation cascades, **OHLCV-derived microstructure
  proxies** (Roll spread, Amihud illiquidity, Kyle λ, intrabar shape, gaps).
- **C5 Regime / state-conditional** — volatility regime, trend/range regime via
  HMM/change-point, liquidity regime, cross-asset risk-on/off (conditioners, not
  standalone triggers).
- **C6 Event-driven** — scheduled events (funding settlement, listings, unlocks,
  expiries), shock/overreaction events, calendar/seasonality (time-of-day,
  day-of-week).
- **C7 Fundamental / alternative-data** — on-chain flows, sentiment/news/social,
  macro.
- **C8 Statistical / ML composition** — multi-feature models that **combine many
  weak signals**, nonlinear interactions, ensembles (a method layer over C1–C7).

## 2. Classification of all tested hypotheses

Phase-6 harness batches (signal-level IC, cost-gated):
- batch1: momentum(20,96), reversion(5,20), RSI-reversion, range-revert,
  vol-scaled reversion, volume-spike → **C1**; xs_reversal(20)/xs_momentum(96) → **C2**.
- batch2: rsi/range **extreme** reversion → **C1**; xs_reversal(5) → **C2**.
- batch3–4: funding revert / z / xs (1y then 24-sym 3y) → **C3** (funding carry only).
- batch5: xs reversal(3,9)/momentum(9,30), BTC lead-lag(1) → **C2** (naive).
- batch6: high-vol-regime reversion, low-vol momentum → **C5×C1** (vol regime only).
- step9–10: OOS + cost gate + low-turnover rescue of the C5×C1 lead.

Phase-5 (strategy-level, not clean signal-IC): trend/breakout/scalping/vwap/
liquidity/oi_footprint/sweep/mtf — span **C1** and *named* **C4**, but the C4 ones
ran on stubs/proxies (B12) so C4 was never genuinely tested.

## 3. Coverage matrix

Status ∈ {Tested-Rejected, Tested-Inconclusive, Untested}. "Rejected" = no
tradeable edge after costs; "Inconclusive" = tested only in a naive/limited form.

| Class | Sub-class | Tested? | Verdict |
|---|---|:--:|---|
| C1 | trend / momentum | ✅ | **Rejected** (IC≈0, multi-horizon) |
| C1 | mean-reversion (RSI/range/extreme/vol-scaled) | ✅ | **Rejected** at signal level |
| C1 | volume-spike | ✅ | **Rejected** |
| C1 | breakout/range, volatility-based | ⚠️ | **Inconclusive** (only via Phase-5 strategies, not clean IC) |
| C1 | calendar / seasonality (time-of-day, day-of-week) | ❌ | **Untested** (free) |
| C1 | OHLCV microstructure proxies (Roll/Amihud/Kyle/intrabar) | ❌ | **Untested** (free) |
| C2 | XS momentum / reversal | ✅ | **Rejected** (naive demean, 24-sym) |
| C2 | lead-lag | ⚠️ | **Inconclusive** (single-lag BTC only) |
| C2 | pairs / cointegration / stat-arb | ❌ | **Untested** (free) |
| C2 | factor-sorted portfolios (size/liquidity/beta) | ❌ | **Untested** (free) |
| C3 | funding carry / reversion | ✅ | **Rejected** (1y + 24-sym 3y) |
| C3 | spot-perp **basis** | ❌ | **Untested** (free — needs spot OHLCV) |
| C3 | funding **term-structure**, OI dynamics | ⚠️ | **Untested/thin** (OI capped 30d) |
| C3 | options-implied (skew / VRP) | ❌ | **Untested** (paid) |
| C4 | L2 order-book (imbalance/absorption/sweep) | ❌ | **Untested** (paid) |
| C4 | trade-tape aggressor flow | ❌ | **Untested** (paid) |
| C4 | liquidation cascades | ❌ | **Untested** (semi-free) |
| C4 | OHLCV microstructure proxies | ❌ | **Untested** (free — also under C1) |
| C5 | volatility regime | ✅ | **Tested** (the lead; real signal, cost-rejected) |
| C5 | HMM / change-point / liquidity / risk-on-off regime | ❌ | **Untested** (free) |
| C6 | scheduled events / overreaction / seasonality | ❌ | **Untested** (free) |
| C7 | on-chain / sentiment / macro | ❌ | **Untested** (paid/specialist) |
| C8 | multi-feature ML signal **combination** | ❌ | **Untested** (free — reuses existing signals) |

**Tally:** Tested-Rejected **6**, Tested-Inconclusive **3**, **Untested 13** (of
which **8 are free-data**, 5 paid/specialist).

## 4. Major untested classes

**Free-data, untested:** spot-perp **basis** (C3); **pairs/cointegration stat-arb**
(C2); **OHLCV microstructure proxies** (C4/C1); **multi-feature ML combination**
(C8); **calendar/seasonality & event-driven** (C1/C6); **advanced regimes** —
HMM/change-point (C5); **factor-sorted portfolios** & **multi-lag lead-lag
networks** (C2); **liquidation cascades** (C4, semi-free).

**Paid-data, untested:** L2 order-book flow (C4), trade-tape (C4), options-implied
/VRP (C3), on-chain (C7), sentiment/news (C7).

## 5. Untested-class estimates

E=effort (L/M/H), magnitude=plausible gross-edge ceiling, turnover, cost-sens
(how exposed to the ~10bps cliff that killed the lead).

| Class | Effort | Data source | Paid? | Edge magnitude | Turnover | Cost-sensitivity |
|---|:--:|---|:--:|---|---|---|
| Spot-perp basis (C3) | M | spot OHLCV (free) + have funding | **No** | low-mod, persistent | **low** | **low** ✅ |
| Pairs / cointegration (C2) | M | have 24-sym 8h | **No** | mod | **low-mod** | **low-mod** ✅ |
| Multi-feature ML combination (C8) | M | already-computed signals | **No** | unknown (combines weak) | tunable | tunable |
| OHLCV microstructure proxies (C4) | M | have OHLCV | **No** | low-mod | high | **high** ⚠️ |
| Calendar / seasonality (C6) | **L** | have OHLCV | **No** | low (decays) | low | low |
| Advanced regimes HMM/CP (C5) | M-H | have OHLCV | **No** | conditioner (×other) | inherits | inherits |
| Factor-sorted portfolios (C2) | M | have OHLCV+OI | **No** | mod | low | low ✅ |
| Lead-lag networks (C2) | M | have 24-sym | **No** | low-mod | high | high ⚠️ |
| Liquidation cascades (C4) | M | liq feed (semi-free) | partial | mod (event) | high | high ⚠️ |
| **L2 order-book flow (C4)** | **H** | vendor L2 | **YES** | mod-high | **very high** | **VERY high** ⛔ |
| **Trade-tape flow (C4)** | **H** | vendor tape | **YES** | mod-high | **very high** | **VERY high** ⛔ |
| Options-implied / VRP (C3) | M-H | options vendor | **YES** | mod, persistent | low-mod | low-mod |
| On-chain (C7) | H | specialist vendor | **YES** | speculative | low | low |
| Sentiment / news (C7) | H | paid feed | **YES** | speculative | high | high |

## 6. Ranked roadmap

**ROI rank = (edge magnitude × cost-tolerance × confidence) ÷ effort.** Cost-
tolerance is weighted heavily — the binding constraint all along has been the
~10bps cliff, which punishes high-turnover ideas.

### A. Untested FREE-data classes (do these first)
1. **Spot-perp basis (C3)** — persistent, **low-turnover, low cost-sensitivity**;
   data is free (spot OHLCV) and funding already on hand. Best risk-adjusted next test.
2. **Pairs / cointegration stat-arb (C2)** — classic crypto edge, low-moderate
   turnover, free; the proper version of the (naive, rejected) cross-sectional test.
3. **Multi-feature ML combination (C8)** — cheap (reuses already-computed signals);
   weak individual ICs *may* combine into a tradeable signal at controllable turnover.
4. **Factor-sorted portfolios (C2)** — low-turnover relative-value, free.
5. **Advanced regimes — HMM/change-point (C5)** — as conditioners to revisit C1/C2/C3
   (our only real signal was regime-conditional; better regime detection may matter).
6. **Calendar/seasonality & event-driven (C6)** — low effort; likely small but cheap
   to rule in/out.
7. OHLCV microstructure proxies / lead-lag networks / liquidation (C4/C2) — higher
   turnover ⇒ higher cost-sensitivity ⇒ lower priority despite being free.

### B. Untested PAID-data classes (only after A)
1. **Options-implied / VRP (C3)** — paid but **low-turnover, cost-tolerant**; the most
   defensible paid class given the cost constraint.
2. **L2 order-book flow (C4)** / **Trade-tape (C4)** — highest raw-edge reputation
   BUT **very high turnover + very high cost-sensitivity** → ironically the class
   *most* exposed to the exact cliff that killed our free-data lead. Expensive data +
   storage + engineering to chase the hardest-to-monetise edge.
3. On-chain (C7), Sentiment/news (C7) — speculative, specialist/paid.

## 7. The decisive answer

> **Have we exhausted free-data edge discovery, or only the currently explored
> free-data hypotheses?**

**Only the currently explored subset.** Phase-6 rigorously tested **C1 (technical),
funding-carry within C3, naive C2, and vol-regime within C5** — and correctly found
no tradeable edge there. But it never touched **spot-perp basis, cointegration/
stat-arb, OHLCV microstructure proxies, ML signal-combination, advanced regimes,
factor portfolios, seasonality/event** — **all free-data**. Coverage is roughly
**6 rejected / 3 inconclusive / 13 untested (8 free)**. The space is far from
exhausted.

**Is paid-data acquisition justified yet? No — premature.** Two reasons:
1. **8 free-data classes remain untested**, several (basis, stat-arb, factor,
   options-VRP-analogues) with *better* cost profiles than anything tested so far.
2. **The expensive paid class (L2/tape microstructure) is the WORST fit for the
   binding constraint.** Our edge has been killed by transaction costs, and L2/tape
   signals are the **highest-turnover, most cost-sensitive** of all — paying for the
   data most likely to die on the same cliff. The cost-tolerant paid class
   (options-implied/VRP) is the only one worth considering, and only after the free
   low-turnover classes (A1–A4) are tested.

**Recommendation:** proceed with **free-data roadmap A**, prioritising the
**low-turnover, cost-tolerant** classes (basis, cointegration, factor portfolios,
ML combination) — they directly target the cost constraint that has bound every
result. Revisit paid data **only** if A is exhausted, and then start with
**options-implied/VRP**, not L2/tape.

_Audit only — no backtests, signals, searches, or optimization were performed._
