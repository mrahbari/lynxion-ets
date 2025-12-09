Here is your task rewritten, **organized, clarified, and cleaned**, with improved wording, structure, and actionable steps.
Nothing has been removed — only structured and made developer-ready.

---

# ✅ **WFO Downloader Feature — Clean & Organized Developer Task**

## **🎯 Primary Goal**

Add a **production-grade Downloader / Sync Engine** to the existing project **without breaking or rewriting existing code**, fully compatible with the already implemented WFO logic.

You must:

1. Understand the **current architecture** (Read `README.md` first).
2. Review my requirement list.
3. Check the provided sample (`./tasks/task29-wfo-downloader-sample-code.md`) and compare it with existing project code.
4. Implement only what is missing.
5. Keep the project structure unchanged.
6. Provide full test instructions in a new file: **`WFO-DOWNLOADER-README.md`**.
7. Ensure the system becomes ready for **Backtest + Hyperopt + Walk-Forward Optimization (WFO)**.

> ⚠️ Important: The sample code might be redundant. Do *not* re-implement existing logic. Only fill missing parts.

---

# 📌 **High-Level Requirement Summary**

We need a **real, standard, production-level Downloader / Sync Engine** that can:

### **Data Requirements**

* Work with **25 chosen coins**.
* Download **1-minute timeframe** data reliably.
* Avoid API rate limits (bulk download + local resampling).
* Store raw data in:

```
/data/history/raw/1m/<SYMBOL>.csv
```

* Generate derivative timeframes:

```
5m, 15m, 30m, 1h
```

* Store processed data:

```
/data/processed/5m/<SYMBOL>.csv
/data/processed/15m/<SYMBOL>.csv
...
```

### **Operational Requirements**

* Daily **incremental sync**:

  * Merge new data
  * Deduplicate
  * Sort
* Full refresh **every 6 months**
* Clean, Hexagonal-compatible code
* Fully safe from API rate limits
* Automatically usable by:

  * Backtest Engine
  * Hyperopt
  * Walk-Forward Engine
* Must match the already implemented **auto-retune logic**

---

# 🟦 **Developer Implementation Checklist**

This is the complete roadmap for implementing the feature **in the current architecture**.

---

## **Stage 1 — Downloader Engine**

**Goal:**
Bulk-download 1m data for 25 coins and store it in `/data/raw/1m/`.

**Developer Actions:**

* [ ] Read existing downloader logic in repo.
* [ ] Compare with sample code.
* [ ] Implement missing functions ONLY.
* [ ] Download 1m candles (Binance / Bulk API).
* [ ] Save per-symbol CSV files.
* [ ] Implement daily incremental sync.
* [ ] Implement 6-month full refresh logic.
* [ ] Ensure API-rate-safe behavior (delays, batching, bulk endpoints).

**Output Example:**
`/data/raw/1m/BTCUSDT.csv`

---

## **Stage 2 — Resample Engine**

**Goal:**
Convert 1m CSV files into higher timeframes.

**Developer Actions:**

* [ ] Implement `resample_engine.py` if missing.
* [ ] Use standard OHLC aggregation.
* [ ] Drop NaN.
* [ ] Ensure zero drift (strict alignment).
* [ ] Resample to: `5m, 15m, 30m, 1h`
* [ ] Save to `/data/processed/<tf>/`

---

## **Stage 3 — Market Data Loader**

**Goal:**
Load multi-timeframe data for Backtest, Hyperopt, and WFO.

**Developer Actions:**

* [ ] Implement or verify `data_loader.py`.
* [ ] Add features:

  * `load()`
  * `load_range(start, end)`
  * Gap detection
  * Multi-timeframe merging
* [ ] Return a clean DataFrame ready for strategy engines.

---

## **Stage 4 — Execution Engine**

**Developer Actions:**

* [ ] Validate existing implementation.
* [ ] Ensure compatibility:

  * Open/Close positions
  * Slippage
  * Fee model
  * Multi-symbol support
  * Metrics output (Sharpe, winrate, drawdown)

---

## **Stage 5 — Strategy Engine**

**Developer Actions:**

* [ ] Confirm compatibility with:

  * Trend Engine
  * Momentum Engine
  * Volatility Engine
* [ ] Verify signals:

  * `long_entry`
  * `short_entry`
  * `confidence`

---

## **Stage 6 — Watcher Layer + Multi-Symbol Router**

**Developer Actions:**

* [ ] Ensure Multi-Symbol + Multi-Timeframe signal aggregation
* [ ] Confirm Router → Execution Engine flow
* [ ] Validate Risk Manager:

  * Position sizing
  * Exposure limits

---

## **Stage 7 — Walk-Forward Optimization (WFO) Engine**

**Developer Actions:**

* [ ] Verify:

  * `WindowManager`
  * `HyperoptRunner`
  * `BacktestRunner`
  * `WFOptimizer`
* [ ] Ensure sliding window logic works:

  * Train: 90 steps
  * Test: 30 steps
  * Slide: 30 steps

**Example windows:**

| Iteration | Train   | Test |
| --------- | ------- | ---- |
| 1         | Jan–Mar | Apr  |
| 2         | Feb–Apr | May  |
| 3         | Mar–May | Jun  |

---

# 🧪 **Critical Testing Requirements**

You MUST perform tests after implementation:

### **Downloader Tests**

* 25 coins download
* Incremental sync
* Full refresh
* Rate-limit safety

### **Resampling Tests**

* Correct OHLC values
* No drift
* No NaN in output

### **Loader Tests**

* Load all timeframes
* Check for gaps
* Multi-timeframe merge

### **Execution Engine Tests**

* Simple buy/sell
* PnL correctness
* Max drawdown accuracy

### **WFO Tests**

* 2+ sliding windows
* Hyperopt integration
* Metrics correctness

---

# 📄 **Required Deliverable**

You must create:

## **`WFO-DOWNLOADER-README.md`**

Contents must include:

1. **Overview of downloader logic**
2. **How to run full refresh**
3. **How incremental sync works**
4. **How to generate resampled timeframes**
5. **How to test**

   * downloader
   * resampling
   * loader
   * WFO sample run
6. **Example commands**
7. **Troubleshooting**

---

# 🧱 Architectural Rules (Must Not Break)

* Maintain Hexagonal Architecture
* No tight coupling
* No logic duplication (DRY)
* No rewriting existing modules
* All previous behaviors must remain identical
* No side effects introduced
* All automated tests must pass

---

# ✔️ Final Summary for Developer

You are integrating a **WFO-ready Downloader + Sync Engine** into an already partially built system.

Your responsibilities:

1. Understand the current architecture first
2. Compare my requirements with existing code
3. Only implement missing parts
4. Keep everything Hexagonal-compliant
5. Test the entire system end-to-end
6. Produce a complete `WFO-DOWNLOADER-README.md` guide

This feature must make the system fully ready for:

* Backtesting
* Hyperopt
* Walk-Forward Optimization

Across **25 coins**, **multiple timeframes**, with **production-grade data quality**.

