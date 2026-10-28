# Phase 6 · Step 9 — OOS Confirmation + Cost Gate (revert_highvol_3)

_The only breadth-backed lead. 24 symbols, 8h bars. OOS = last 30% of each series (untouched by hypothesis selection). Cost gate trades sign(signal) on each high-vol bar, holds 8h. Signal-decoupled cost-adjusted expectancy — no SL/TP ladder or full sim._

## (1) Out-of-sample confirmation (IC@8h)

| segment | mean IC | symbols +IC & sig |
|---|---:|---:|
| in-sample (first 70%) | +0.080 | 21/24 |
| **OOS (last 30%)** | **+0.043** | **4/24** |

❌ **Edge does NOT hold OOS** (mean IC collapses / breadth drops) — the full-sample result was period-dependent.

## (2) Cost gate (OOS, per-trade expectancy)

- **Trades** (high-vol active bars, OOS): 10,880
- **Gross** mean return/trade: **+1.3 bps** (win rate 51.8%)
- **Breakeven round-trip cost:** 1.3 bps
- **Net @ 5 bps:** -3.7 bps · **@ 10 bps:** -8.7 bps · **@ 20 bps:** -18.7 bps

❌ **Does NOT survive realistic costs** — gross edge is smaller than the ~10 bps round-trip cost (Phase-5's cost cliff). Signal-level edge, but not tradeable at 8h turnover.

## Verdict

**REJECTED at the cost gate** — OOS edge weak and net-of-cost expectancy is not positive at realistic 8h-turnover costs. A real signal-level effect that is not tradeable as-is; would need lower turnover (longer hold), a wider-spread-free venue, or larger gross edge.

_No tuning, no curve-fitting. Honest read regardless of outcome._
