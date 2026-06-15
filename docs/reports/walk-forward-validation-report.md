# Walk-Forward (Out-of-Sample) Validation Report

**Date:** 2026-06-12. Tests whether any production strategy's apparent edge **persists
across disjoint out-of-sample time segments** — the prerequisite that distinguishes real
edge from in-sample artifacts. Existing params only (no tuning; the strategies have no
fitted parameters, so walk-forward = temporal-stability across non-overlapping periods).

**Design:** the ~1-year 1h history (most cost-robust TF) split into **4 disjoint ~3-month
OOS segments** — S1 Jun–Sep 2025, S2 Sep–Dec 2025, S3 Dec 2025–Mar 2026, S4 Mar–Jun 2026.
Every strategy run on each segment × BTC/ETH/SOL at 1h = **144 cells** (`wfo_1h.json`).
A strategy is *temporally stable* on a symbol if positive in ≥3 of its traded segments.

## Core result: ZERO temporally-stable (strategy, symbol) pairs

**No strategy is positive across ≥3 of 4 OOS segments on any symbol.** The best any
achieves is **2/4 (a coin-flip)**, with signs alternating segment to segment — the
signature of noise, not edge.

| strategy | symbol | S1 | S2 | S3 | S4 | positive segments |
|---|---|---|---|---|---|---|
| oi_footprint | ETH | **+253** | −37 | −179 | **+212** | 2/4 |
| momentum | BTC | +54 | −312 | +223 | −50 | 2/4 |
| momentum | ETH | +27 | +343 | −85 | −383 | 2/4 |
| trend_following | BTC | +64 | −66 | +4 | −63 | 2/4 |
| trend_following | ETH | +245 | −2 | +6 | −181 | 2/4 |
| scalping | ETH | +41 | −706 | −406 | +61 | 2/4 |
| mtf_trend | BTC | −216 | −192 | −79 | +131 | 1/4 |
| mtf_trend | ETH | +264 | −411 | −355 | −147 | 1/4 |
| oi_footprint | SOL | −125 | +92 | −255 | −126 | 1/4 |
| momentum | SOL | −659 | −324 | −357 | −546 | 0/4 |
| mtf_trend | SOL | −255 | −535 | −591 | −436 | 0/4 |
| scalping | SOL/BTC | … | … | … | … | 0/4 |

## What this proves
- **The nested-window positives were in-sample artifacts.** `oi_footprint` ETH — the
  single best cell in the timeframe matrix (365d +165, GO) — is positive in only 2 of 4
  disjoint OOS quarters (strongly positive in S1 & S4, negative in S2 & S3). Its "edge"
  does not persist; it is period-specific.
- **No strategy clears the bar on any symbol.** Even the most active traders (momentum,
  mtf_trend, trend_following) flip sign across segments.
- **SOL fails out-of-sample too** (0–1/4 everywhere), consistent with the cross-symbol
  finding — it is a universal failure, not a single-period fluke.
- **No directional persistence:** a strategy positive in S1 is as likely negative in S2.

## Conclusion
**Walk-forward validation: FAIL for all 12 strategies.** This is the strongest evidence
in the program: the handful of positive cells seen in the nested-window matrices do **not
survive disjoint out-of-sample testing**. There is no temporally-stable, cross-symbol edge
anywhere in the suite. This independently and conclusively confirms **READY 0 — NOT
DEPLOYABLE**, and removes the "maybe oi_footprint/mtf_trend are close" caveat: they are not.

The verdict in `final-deployment-readiness-report.md` stands, now reinforced by OOS
evidence: the existing strategy suite has **no demonstrable, persistent edge** on any
tested timeframe or symbol, and **must not be deployed**. Future work must gate on
out-of-sample, cross-symbol persistence — a bar none of the current suite approaches.
