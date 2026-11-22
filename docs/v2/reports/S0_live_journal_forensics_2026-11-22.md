# S0 — Live journal forensics (platform strategies, BingX VST, 2026-07-08 → 2026-10-18)

Source: `data/trade_journal.csv` (2,053 closed trades, 87 symbols, all BingX).

## Headline vs decomposition
| Slice | Trades | PnL (USDT) | PF | Win % |
|---|---|---|---|---|
| All trades (the "PF ~0.2" headline) | 2,053 | −15,390 | 0.17 | 38.3 |
| Worst 20 trades | 20 | ≈ −15,700 (102% of total loss) | — | — |
| All except worst 20 | 2,033 | +304 | 1.11 | — |
| Normal size (≤200 USDT notional) | 1,885 | −752 | 0.44 | — |
| Normal size, excluding XMRUSDT | 1,412 | +189 | 1.48 | 52.1 |

By strategy (normal size, no XMR): trend_following 493 trades PF 1.80; VWAPReversal 336 PF 3.25;
OIFootprint 47 PF 3.61; MeanReversion 201 PF 0.67; SweepScalper 124 PF 0.50; MTFTrend 121 PF 0.41.

## Execution-flow defects visible in the journal
1. **Sizing**: median notional 21 USDT, but the 1% tail is ~20,000 USDT (up to ~100,000). These
   oversized trades (July 2026, trend_following, mostly SELL) carry the entire net loss.
2. **Re-entry loop on one symbol**: XMRUSDT has 548 trades (27% of all), entries 0 s apart at minimum,
   median gap 126 s; −3,335 USDT. No per-symbol cooldown/duplicate guard was effective.
3. **Stop protection**: 18 `LIMIT` exits lost −5,247; e.g. UNI SELL held 23.6 h through a +10% move,
   LDO SELL +9.5% — positions ran far beyond the configured stop.
4. **Journal accounting**: 5 trades record −2,034 USDT where price×qty implies −200.

## Interpretation (caveats)
- The PF ~0.2 verdict on the platform strategies was driven by execution/risk defects, not
  (only) by signal quality. After removing defect-driven trades, trend_following and VWAPReversal
  are positive on this sample.
- This filtering is post-hoc (defined by defects, not by outcome) and the sample is small
  (~3 months, ~$21 notional, VST fills). It is a reason to re-test live with a fixed flow,
  **not** evidence of an edge.

## Next (S0, moved first)
Verify/fix in the platform: per-order notional cap, per-symbol duplicate-entry/cooldown guard,
stop placement verification; then run trend_following + VWAPReversal (+ OIFootprint) on VST through
the real platform runner under `.env` limits, isolated from the v2 XS-COMBO book (symbol exclusion).

## Correction (2026-11-22, evening)
1. **"trend_following" was not a strategy label.** All 800 journal rows labelled `trend_following` had no
   strategy metadata: the trade collector used `trend_following` as a default for unattributed orders.
   The "trend_following PF 1.80" figure above is therefore for *unattributed* trades, not the TrendFollow
   strategy. Rows were relabelled `UNATTRIBUTED` (761) and `XS-COMBO-V1` (39 sleeve rebalances on
   2026-11-22); backup in `data/journal_archive/relabel_2026-11-22/`.
2. **Platform strategy results before 2026-11-22 ~18:50 local are not evidence either way**: every live
   strategy priced its entries from one stale, foreign-symbol candle buffer (fix `1f3028a`). The
   VWAPReversal PF 3.25 above is from that period and must not be used for the edge decision.
