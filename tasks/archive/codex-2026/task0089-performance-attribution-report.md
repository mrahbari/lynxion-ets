# TASK-0089 — TASK 001 Performance Attribution

**Status:** COMPLETE — current edge rejected; TASK 002 decomposition required

## Scope and Cohort Integrity

The canonical `data/trade_journal.csv` was analyzed read-only. Metrics retain only the final
row for each non-empty `trade_id`. The prospective boundary is
`2026-08-13T13:31:42Z`, applied to `entry_timestamp`, because a trade must be admitted to an
OOS cohort using information fixed at entry. The older audit utility applies the boundary to
`exit_timestamp`; that view is not used for the prospective decision here.

The journal stores BingX realized `profit` in `pnl_usdt` and signed `commission` separately in
`fees_usdt`. Cost-adjusted PnL in this report is therefore `pnl_usdt + fees_usdt`.

## Data Quality

- Source rows: 1,768
- Unique final trade IDs: 1,128
- Duplicate rows removed by final-record selection: 640
- Prospective trades admitted by entry time: 418
- Missing required core fields: 0
- Missing confidence/SL/TP: 33 each
- Missing regime: 418 (100%)
- MFE/MAE: unavailable in the canonical journal
- Timeframe: every admitted row is labeled `1m`; no cross-timeframe comparison is possible
- `is_execution_unwind`: false for all admitted rows, including the XMR cascade described
  below, so this field is not sufficient for incident classification.

## Overall Cost-Adjusted Result

| Metric | Result |
| --- | ---: |
| N | 418 |
| Recorded PnL | -248.9557 VST |
| Fees | -7.8472 VST |
| Cost-adjusted PnL | **-256.8029 VST** |
| Expectancy | **-0.6144 VST/trade** |
| Profit factor | **0.2071** |
| Win rate | 31.34% |
| Average win | +0.5119 VST |
| Average loss | -1.1284 VST |
| Payoff ratio | 0.4536 |
| Peak-to-trough equity drawdown | 261.9063 VST |

**Decision: REJECT CURRENT EDGE.** The aggregate cohort is decisively negative after recorded
fees. No capital scaling, production promotion, or threshold tuning is justified.

## Dominant Attribution

### Symbol / duration / exit concentration

- `XMRUSDT`: N=142, cost-adjusted PnL **-261.7112 VST**.
- All 142 XMR records exit through `MARKET`; 132 are BUY and 10 are SELL.
- All use quantity `0.177`; all have unique trade/order references.
- Their entry/exit window is 2026-08-16 through 2026-08-21.
- The `<15m` bucket has N=158, zero wins, and **-266.9354 VST**. XMR explains the dominant
  share of this bucket.
- The existing prospective checkpoint independently identified the initial XMR sequence as
  timeout `MARKET` exits that did not trigger the STOP-only cooldown rule, allowing rapid
  re-entry. The canonical unwind flag nevertheless says false, exposing attribution drift.

This is evidence of execution/risk-control contamination, not permission to declare that
excluding an entire symbol proves an edge.

### Side

| Side | N | Cost-adjusted PnL | Expectancy | PF |
| --- | ---: | ---: | ---: | ---: |
| BUY | 298 | -219.8139 | -0.7376 | 0.1770 |
| SELL | 120 | -36.9891 | -0.3082 | 0.3483 |

Both sides fail; BUY is materially worse and contains most XMR records.

### Strategy

| Strategy | N | Cost-adjusted PnL | Expectancy | PF |
| --- | ---: | ---: | ---: | ---: |
| VWAPReversal | 192 | -157.2374 | -0.8189 | 0.1677 |
| trend_following | 33 | -69.2566 | -2.0987 | 0.0000 |
| MTFTrend | 57 | -19.2669 | -0.3380 | 0.3386 |
| SweepScalper | 63 | -9.9107 | -0.1573 | 0.4853 |
| TrendFollow | 39 | -5.6355 | -0.1445 | 0.4724 |
| MeanReversion | 21 | +1.9667 | +0.0937 | 1.4177 |
| OIFootprint | 13 | +2.5375 | +0.1952 | 2.3236 |

The two positive strategies have N=21 and N=13. Those samples are insufficient to establish
a defensible OOS edge and regime attribution is absent.

### Exit type

| Exit | N | Cost-adjusted PnL | Expectancy | PF |
| --- | ---: | ---: | ---: | ---: |
| MARKET | 152 | -260.5934 | -1.7144 | 0.0101 |
| STOP_MARKET | 162 | -55.3577 | -0.3417 | 0.0664 |
| TAKE_PROFIT_MARKET | 103 | +58.9791 | +0.5726 | 45.7151 |
| LIMIT | 1 | +0.1690 | +0.1690 | n/a |

Exit labels are outcomes, not causal treatments. The strong TP result and weak stop result do
not by themselves prove exit logic is the root cause. MARKET exits require source
classification before any exit-policy change.

### Position size

- `<=25 VST`: N=268, +2.6191 VST, expectancy +0.0098, PF 1.0433.
- `25–100 VST`: N=150, -259.4221 VST, expectancy -1.7295, PF 0.0150.

The larger bucket is almost entirely contaminated by repeated ~74 VST XMR positions. This is
not evidence that smaller sizing itself creates edge.

## Descriptive Counterfactual, Not an Edge Claim

Removing all XMR records leaves N=276, +4.9082 VST cost-adjusted PnL, expectancy roughly
+0.0178 VST/trade, and PF about 1.08. This result is post-hoc, symbol-selected, lacks regime
metadata, and has not passed walk-forward/OOS stability gates. It is recorded only to quantify
incident concentration.

## Missing Required Attribution

Regime, MFE, MAE, reliable market-exit source, entry-condition detail, trailing/breakeven
activation, and funding/slippage are not recoverable from the canonical rows. No values are
invented. TASK 002 must first separate confirmed XMR execution-cascade rows from normal trades
and classify MARKET exit sources before any production strategy change.

## Reproduction

```bash
python scripts/performance_attribution.py \
  --journal data/trade_journal.csv \
  --cohort-start 2026-08-13T13:31:42Z
```
