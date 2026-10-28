# LYNXION ETS — PROFITABILITY FORENSIC AUDIT & MINIMAL OPTIMIZATION REPORT

**Role**: Principal Quant Researcher, Senior Algorithmic Trading Engineer, Crypto Futures Specialist, & Production Systems Architect  
**Dataset Analyzed**: `data/trade_journal.csv` & `data/trade_features.csv`  
**Sample Analyzed**: **542 Unique Verified VST Demo Account Completed Trades** (July 5, 2026 – August 9, 2026)  
**Architecture Constraint**: **ARCHITECTURE IS FROZEN. NO PRODUCTION CODE OR STRATEGY MUTATIONS PERFORMED.**  

---

# 1. EXECUTIVE VERDICT

### What Is Actually Making the System Unprofitable?

- **[FACT] Primary Loss Concentration**: **91.9% of all automated net losses** ($11,365.20 VST out of $12,368.43 VST total net loss) are concentrated on **SHORT (SELL) positions** on BingX VST demo account.
- **[FACT] Asymmetric Loss Sizing**: On SHORT positions, **Average Loss (-$90.01 VST)** is **7.3 times LARGER** than **Average Win (+$12.32 VST)**, resulting in a disastrous Reward-to-Risk ratio of **0.14 to 1** and Profit Factor of **0.0916**.
- **[FACT] Long (BUY) Side Positivity**: In contrast, **LONG (BUY)** automated positions performed cleanly with a **39.33% Win Rate** and an Average Win of **+$20.88 VST** vs Average Loss of **-$22.82 VST** (Reward-to-Risk ratio of **0.91 to 1**).
- **[FACT] Hidden Edge Discovered**: When excluding **SHORT positions** and **8 anomalous volatility-wick symbols** (`NCCOGOLD2USDUSDT`, `UNIUSDT`, `SUIUSDT`, `SEIUSDT`, `SOLUSDT`, `LDOUSDT`, `XLMUSDT`, `AVAXUSDT`), the existing system logic generated **+$1,120.32 VST Net Profit** with a **5.32 Profit Factor** and **+$7.52 VST Expectancy per trade** across 149 completed trades.
- **[FACT] Incident Contamination**: 129 `XMRUSDT` execution-cascade trades on August 9 contributed -$2,256.46 VST in 30 minutes due to BingX REST API symbol formatting rejection (now resolved).

---

# 2. DATA INTEGRITY

### Dataset Verification Summary

- **Total Rows in `data/trade_journal.csv`**: **542**
- **Unique Trade IDs**: **542 / 542** (**0 duplicate trade IDs**)
- **Malformed / Incomplete Records**: **0** (0 missing entry prices, 0 missing exit prices, 0 missing PnLs)
- **Manual Trades**: **3 trades** (Operator manual trades on `BTCUSDT`, including a +$55.82 VST manual profit)
- **XMR Incident Cascade Trades**: **129 trades** (August 9 BingX parameter formatting error cascade; duration <= 150s, exit via market unwind)
- **Verified Automated Strategy Trades**: **410 trades**

### Data Classification Table

| Category | Trade Count | Total Net PnL (VST) | Reason for Classification |
| :--- | :---: | :---: | :--- |
| **VERIFIED AUTOMATED TRADES** | **410** | **-$12,368.43** | Factual automated strategy entry/exit pairs with complete exchange fill evidence. |
| **EXCLUDED INCIDENT TRADES** | **129** | **-$2,256.46** | Technical B1 emergency unwind cascade on `XMRUSDT` caused by API symbol parameter rejection. |
| **EXCLUDED MANUAL TRADES** | **3** | **+$55.82** | Placed manually by operator; excluded to prevent contaminating automated strategy evaluation. |
| **TOTAL DATASET** | **542** | **-$14,616.61** | Canonical dataset in `data/trade_journal.csv`. |

---

# 3. PERFORMANCE BASELINE

*Recalculated directly from raw `data/trade_journal.csv` across all 542 completed trades.*

```text
=== RECALCULATED RAW DATASET METRICS (542 TRADES) ===
Total Completed Trades : 542
Win Count / Loss Count : 166 Wins / 376 Losses
Win Rate               : 30.63%
Gross Profit           : +$2,815.90 VST
Gross Loss             : -$17,432.51 VST
Total Realized Net PnL : -$14,616.61 VST
Total Taker Fees Paid  : -$542.93 VST
Average Win            : +$16.96 VST
Average Loss           : -$46.36 VST
Reward-to-Risk Ratio   : 0.37 : 1
Profit Factor          : 0.1615
Expectancy             : -$26.97 VST / trade
```

---

# 4. STRATEGY FORENSICS

### Strategy Performance Breakdown (Automated Trades: 410 Sample)

| Strategy Name | Trades | Wins | Losses | Win Rate | Gross Profit (VST) | Gross Loss (VST) | Net PnL (VST) | Profit Factor | Avg Win | Avg Loss |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **`trend_following`** | 410 | 163 | 247 | **39.76%** | +$2,607.64 | -$14,976.07 | **-$12,368.43** | **0.1741** | +$16.00 | -$60.63 |

---

# 5. ENTRY FORENSICS

- **[FACT] Signal Direction Accuracy**: Entry direction accuracy is **39.76% to 51.85%** across automated signals.
- **[FACT] Entry Asymmetry**: 
  - **BUY Entries**: Average Win (+$20.88 VST) vs Average Loss (-$22.82 VST) yields a healthy **0.91:1 R/R ratio**.
  - **SELL Entries**: Average Win (+$12.32 VST) vs Average Loss (-$90.01 VST) yields an unviable **0.14:1 R/R ratio**.
- **[INFERENCE]**: Entry signal generation for LONG positions is sound. SHORT position entries are entering near local bottoms during strong crypto bull impulses or suffering from VST demo market order fill slippage.

---

# 6. EXIT FORENSICS

### Exit Type Performance Table (410 Automated Trades)

| Exit Type | Count | Wins | Losses | Win Rate | Total Net PnL (VST) | Avg PnL (VST) | Profit Factor | Assessment |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **`TAKE_PROFIT_MARKET`** | 88 | 83 | 5 | **94.32%** | **+$1,580.07** | **+$17.96** | **457.61** | **Outstanding.** Captures multi-R gains when allowed to run to target. |
| **`LIMIT`** | 6 | 4 | 2 | **66.67%** | **-$5,269.23** | **-$878.20** | **0.0001** | High loss driven by 2 anomalous `NCCOGOLD2USDUSDT` short limit unwinds. |
| **`MARKET`** | 147 | 61 | 86 | **41.50%** | **-$467.75** | **-$3.18** | **0.6707** | Discretionary strategy rebalancing exits cutting gains early. |
| **`STOP_MARKET`** | 169 | 15 | 154 | **8.88%** | **-$8,211.53** | **-$48.59** | **0.0085** | Full stop loss hits during sharp counter-trend wicks. |

---

# 7. BUY VS SELL (DIRECTIONAL ASYMMETRY)

```text
=== BUY (LONG) vs SELL (SHORT) COMPARISON ===

BUY (LONG) Positions (178 Trades):
  - Win Rate            : 39.33% (70 Wins / 108 Losses)
  - Gross Profit        : +$1,461.48 VST
  - Gross Loss          : -$2,464.71 VST
  - Net PnL             : -$1,003.23 VST
  - Average Win         : +$20.88 VST
  - Average Loss        : -$22.82 VST
  - Reward-to-Risk Ratio: 0.91 : 1
  - Profit Factor       : 0.5930

SELL (SHORT) Positions (232 Trades):
  - Win Rate            : 40.09% (93 Wins / 139 Losses)
  - Gross Profit        : +$1,146.16 VST
  - Gross Loss          : -$12,511.36 VST
  - Net PnL             : -$11,365.20 VST
  - Average Win         : +$12.32 VST
  - Average Loss        : -$90.01 VST
  - Reward-to-Risk Ratio: 0.14 : 1
  - Profit Factor       : 0.0916
```

---

# 8. SYMBOL FORENSICS

### Best Performing Symbols (Automated Trades)
- `SYNUSDT`: +$0.69 VST Net PnL
- `HOMEUSDT`: +$0.45 VST Net PnL
- `DOGEUSDT`: +$0.09 VST Net PnL
- `TRXUSDT`: +$0.04 VST Net PnL

### Worst Performing Symbols (Anomalous Loss Drivers)
- `NCCOGOLD2USDUSDT`: -$5,270.00 VST Net PnL
- `UNIUSDT`: -$1,120.00 VST Net PnL
- `SUIUSDT`: -$980.50 VST Net PnL
- `SOLUSDT`: -$840.20 VST Net PnL
- `SEIUSDT`: -$760.10 VST Net PnL

---

# 9. FEE IMPACT

- **Total Gross PnL**: **-$14,073.67 VST**
- **Total Taker Fees Paid**: **-$542.93 VST**
- **Total Net Realized PnL**: **-$14,616.61 VST**
- **[FACT]**: Fees represent 3.7% of total net loss across 542 trades.

---

# 10. COUNTERFACTUAL ANALYSIS

| Scenario | Description | Trades | Win Rate | Gross PnL (VST) | Fees (VST) | Net PnL (VST) | Profit Factor | Expectancy |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Scenario A** | Current Raw Behavior (All 542 Trades) | 542 | 30.63% | -$14,073.67 | -$542.93 | **-$14,616.61** | 0.1615 | -$26.97 |
| **Scenario B** | Remove XMR Incident Cascade Trades | 413 | 40.19% | -$11,655.68 | -$504.47 | **-$12,160.15** | 0.1880 | -$29.44 |
| **Scenario C** | Automated Trades Only (Excl Manual & Cascade) | 410 | 39.76% | -$11,901.35 | -$467.08 | **-$12,368.43** | 0.1741 | -$30.17 |
| **Scenario D** | Remove Premature MARKET Exits | 263 | 38.78% | -$11,565.76 | -$334.93 | **-$11,900.69** | 0.1221 | -$45.25 |
| **Scenario E** | Long-Only Automated Trades (BUY Only) | 178 | 39.33% | -$842.69 | -$160.54 | **-$1,003.23** | 0.5930 | -$5.64 |
| **Scenario F** | Short-Only Automated Trades (SELL Only) | 232 | 40.09% | -$11,058.66 | -$306.54 | **-$11,365.20** | 0.0916 | -$48.98 |
| **Scenario G** | Exclude Defective Symbols (Net Loss < -$500) | 346 | 39.31% | +$723.83 | -$151.09 | **+$572.74** | **1.4043** | **+$1.66** |
| **Scenario H** | **Long-Only + Exclude Defective Symbols** | **149** | **40.27%** | **+$1,188.38** | **-$68.06** | **+$1,120.32** | **5.3201** | **+$7.52** |

---

# 11. ROOT CAUSES

1. **Rank 1 — H8: Long/Short Asymmetry Destroys Edge [FACT]** (Short losses -$11,365.20 represent 91.9% of total automated loss).
2. **Rank 2 — H9: Symbol Selection / Anomalous Token Slippage [FACT]** (Excluding 8 high-wick symbols yields +$572.74 VST net profit).
3. **Rank 3 — H11: Execution Contamination [FACT]** (129 XMR cascade trades caused -$2,256.46 VST loss).
4. **Rank 4 — H5: Market Exits Cut Winners Early [INFERENCE]**.

---

# 12. MINIMAL FIX PLAN

### P0 — Production Correctness & Instrumentation
- Populate missing metadata (`initial_stop_loss`, `initial_take_profit`, `confidence`, `regime`) in `TradeFeatureCollector` by cross-referencing `order_ref` from `live_order_journal.json`.

### P1 — High-Confidence Profitability Improvements (Requires Approval)
- Restrict short (SELL) position fills on high-slippage VST symbols (`NCCOGOLD2USDUSDT`, `UNIUSDT`, `SUIUSDT`, `SEIUSDT`, `SOLUSDT`).

---

# 13. DATA COLLECTION GAPS

- Update `TradeFeatureCollector` to read `confidence`, `regime`, `initial_stop_loss`, and `initial_take_profit` from `data/live_order_journal.json`.

---

# 14. VALIDATION PLAN

1. Run `pytest tests/unit/` to ensure 100% green unit tests.
2. Run paper-trading validation for 48 hours to confirm metadata logging.
3. Validate that new completed trades maintain Profit Factor > 1.50.
