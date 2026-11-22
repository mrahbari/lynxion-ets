# Lynxion v2 — Edge Discovery Roadmap (Claude, started 2026-11-22)

Codex-era tasks (task0077–task0457 and older) are archived under `tasks/archive/codex-2026/`.
They are reference only; their negative results tell us where NOT to search
(six majors, 15m–24h horizons, taker execution). v2 starts from a different premise.

## Thesis

Crypto edges that survive costs are most likely **cross-sectional** (ranking hundreds of
symbols against each other), at **hourly-to-weekly horizons** with controlled turnover,
built from **price, volume, funding, basis/premium, OI** on the **full Binance USDT-M universe
including delisted symbols**. Single-symbol, short-horizon taker strategies on BTC/ETH were
exhaustively negative and are out of scope.

## Ground rules (lightweight, but strict where it matters)

1. Data: Binance public archives (`data.binance.vision`), checksum-verified. Execution: BingX.
2. Point-in-time: a bar is usable only after it closes; universe membership uses only past data;
   delisted symbols stay in the sample until delisting (no survivorship bias).
3. Splits — fixed now, before any result:
   - **Development:** 2020-01-01 → 2024-12-31 (all research, walk-forward inside it).
   - **Sealed holdout:** 2025-01-01 → 2026-10-31. Opened **once** per surviving strategy in EPIC-4.
   - **Forward:** live paper on BingX VST after EPIC-4.
4. Costs always on: fee 5 bp/side (taker) + liquidity-bucket slippage + actual funding.
   Stress test at 2x costs.
5. Every backtest run is logged automatically in a trial registry; significance uses the
   Deflated Sharpe Ratio over the *actual* number of trials (multiple-testing control by math,
   not by banning data reuse).
6. A strategy "survives" development only if: DSR p<0.05, positive net Sharpe in ≥ 4/5
   development years, net of 2x costs still positive, no single symbol > 10% of PnL.
7. No hourly checkpoint docs. One short report per finished task in `docs/v2/reports/`.

## EPICs and tasks

| ID | Task | Acceptance | Status |
|---|---|---|---|
| **E0** | **Foundation** | | |
| E0-1 | Archive Codex tasks, new branch `claude/edge-v2` | tasks archived, roadmap written | DONE |
| E0-2 | Retire journal epoch 1 (operator: no open BingX trades) | archive + hashes + disposition, clean journal | DONE |
| E0-3 | Telegram self-test tool | `scripts/telegram_selftest.py` passes | DONE (2026-11-22) |
| E0-4 | Full-universe data lake: 1h klines, funding, premium index | ~923 symbols, checksums OK, manifest | DONE (1.8 GB) |
| E0-5 | Renew BingX VST API keys | signed GET returns code 0 | DONE (account flat) |
| **E1** | **Research harness** | | |
| E1-1 | Panel builder: PIT universe, returns, funding, premium, liquidity buckets | unit tests for lag/alignment | DONE |
| E1-2 | Cross-sectional portfolio backtester (weights → net PnL with fees, slippage, funding, turnover) | hand-computed test cases match | DONE |
| E1-3 | Trial registry + Deflated Sharpe + yearly / symbol-concentration stats | every run logged | DONE |
| E1-4 | Anti-lookahead guards: shuffled-signal null, +1 bar shift test | null Sharpe ≈ 0 | DONE |
| **E2** | **Factor wave 1 (dev period only)** | | |
| E2-1 | Momentum / reversal (1d, 3d, 1w, 4w lookbacks) | report | DONE |
| E2-2 | Funding carry (level, change) | report | DONE |
| E2-3 | Premium/basis level & change | report | DONE |
| E2-4 | Volatility / beta / idiosyncratic vol, liquidity (Amihud), volume shocks | report | DONE |
| E2-5 | Listing-age effects (new listings, pre-delisting) | report | TODO |
| E2-6 | Regime conditioning (BTC trend / market vol) of survivors | report | TODO |
| **E3** | **Combination & ML** | | |
| E3-1 | Multi-factor linear combination of survivors (walk-forward weights) | report | DONE |
| E3-2 | Gradient-boosting cross-sectional ranker (walk-forward, purged) vs linear | report | TODO |
| E3-3 | Turnover / rebalance-frequency optimisation (cost-aware) | report | TODO |
| E3-4 | OI / long-short ratio metrics for liquid subset (download `metrics`) | report | TODO |
| **E4** | **Holdout verdict** | | |
| E4-1 | Freeze final candidates (code hash + params) | frozen file | DONE |
| E4-2 | Open holdout once; verdict EDGE / NO EDGE | report | DONE |
| E4-3 | Capacity & BingX tradability (symbol overlap, min size, fees) | report | DONE |
| **E5** | **Execution on BingX (only if E4 = EDGE)** | | |
| E5-1 | Lean portfolio rebalancer (target weights → orders), rate-limit aware | VST dry run | TODO |
| E5-2 | Telegram trade + daily PnL notifications | message received | TODO |
| E5-3 | Forward paper 60–90 days, tracking error vs backtest | report | TODO |
| E5-4 | Real-capital decision | operator approval | GATED |

## Out of scope (explicitly)

Existing intraday strategies (VWAPReversal, trend_following, …; PF 0.21 on 418 trades),
Codex cohorts C-11/C-33/C-35, microstructure collectors, investor-release track.

## Results log
- 2026-11-22: XS-COMBO-V1 holdout PASS (Binance SR 1.39; BingX SR 0.96). See docs/v2/reports/E2_E4_RESULTS_2026-11-22.md
