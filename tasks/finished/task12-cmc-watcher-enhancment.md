

# ✅ **Improved & Clarified Task Description (Final Version)**

I want to **improve and enhance** the file:

```
infrastructure/watchers/adapters/cmc_screener.py
```

Your job is to:

1. **Refactor the CMC screener logic**
2. **Integrate the detailed filters below** (growth, crash, and stablecoin exclusion)
3. **Optimize the pipeline to avoid overfitting**
4. **Perform comprehensive testing** to ensure full functionality and data consistency

After the enhancement, perform an **end-to-end validation** of the entire watcher system.

---

# 📌 **Filtering Logic to Implement in `cmc_screener.py`**

Use the following complete, production-ready filtering rules to detect:

* **High-Growth Potential Coins**
* **High Crash Risk Coins**
* **And exclude all stablecoins**

These filters are based on market behavior, liquidity requirements, volatility patterns, and pump-and-dump detection models.

---

# 🔹 **1. Stablecoin Exclusion Filters**

Stablecoins must be completely removed from the dataset.

### **A) Tag-based stablecoin filter**

Exclude coins that contain tags such as:

* `stablecoin`
* `asset-backed-stablecoin`
* `algorithmic-stablecoin`

### **B) Price-based stablecoin filter**

Exclude any coin priced around $1:

```
0.95 < price < 1.05 → exclude
```

### **C) Known stablecoin blacklist**

Exclude well-known stablecoins:
USDT, USDC, BUSD, DAI, TUSD, FRAX, PYUSD, GUSD, USDD, EURT, etc.

---

# 🔹 **2. Filters for High-Growth Potential Coins**

A coin qualifies as **high-growth potential** when it meets multiple bullish and speculative indicators.

### **A) Price Momentum**

```
percent_change_24h > 15%
```

(Optional):

```
percent_change_1h > 1.5%
```

### **B) High Trading Volume**

```
volume_24h > 5,000,000
```

(Optional):

```
volume_change_24h > 25%
```

### **C) Market Capitalization**

```
market_cap < 1,000,000,000
```

(Optional):

```
market_cap > 10,000,000
```

### **D) Volatility**

```
high_24h - low_24h >= 6%
```

### **E) Liquidity Health**

```
volume_24h / market_cap >= 0.08
```

### **F) Trend Confirmation (MA)**

```
price > MA20
MA20 > MA50
```

---

# 🔹 **3. Filters for High Crash Potential Coins**

A coin qualifies as **high-risk / crash candidate** when strong downward momentum and high-volume sell-offs appear.

### **A) Price Collapse**

```
percent_change_24h < -15%
```

(Optional):

```
percent_change_1h < -2%
```

### **B) High Volume Confirmation**

```
volume_24h > 2,000,000
```

### **C) Negative Trend (MA)**

```
price < MA20
MA20 < MA50
```

### **D) Liquidity Panic**

```
volume_change_24h > 20%
```

### **E) High Volatility**

```
(high_24h - low_24h) / price > 0.07
```

---

# 🔹 **4. (Optional) Advanced Filters**

If needed:

* Social sentiment analysis
* On-chain activity trends
* Whale activity detection

---

# 📌 **5. Output Requirements (Refactored Script Must Provide)**

For each selected coin, return:

* Name
* Symbol
* Price
* % change (1h, 24h, 7d)
* Market cap
* 24h volume
* **Exact reasons why the coin passed the filters**

---

# 📌 **6. Testing Requirements (Very Important)**

After refactoring `cmc_screener.py`, run a full test cycle:

### **A) Review existing unit tests**

* Update or fix failing tests
* Add missing tests for each new filter condition

### **B) Add new tests**

Examples:

* Stablecoin exclusion test
* High-growth detection test
* Crash-risk detection test
* Trend filter (MA20/MA50) test
* Liquidity ratio test
* Solana/Polygon tokens passing/ failing scenarios

### **C) Validate all watchers, one by one**

* Confirm watchers trigger correctly
* Confirm adapters pass correct data
* Confirm scoring logic produces consistent output

### **D) Full End-to-End Test**

* From CMC API → watcher → adapter → filters → final output
* Inspect the entire pipeline for accuracy
* Make sure no overfitting behavior happens (filters should generalize)

---

# ✔ **This version clearly states:**

* You are improving `cmc_screener.py`
* You are applying the detailed filters
* You are avoiding overfitting
* You are performing complete testing
* You will validate watchers and data flow end-to-end


