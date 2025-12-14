I want to improve my cmc_screener.py based on the following description, check and make it better if needed. 
after enhancment, do the comperhensise test to make sure all is functioning well.
becarful about overfit issues. 





the filters — perfect for implementation, documentation, prompt engineering, and deeper analysis.

---

# ✅ **Detailed Filters for Detecting High-Potential Coins (Growth & Crash)**

### *For Implementation, Algorithm Design, or Prompt Usage*

Below is the full list of filters you should use when evaluating cryptocurrencies for **strong upward potential** or **heavy downward risk**.
These filters are based on proven market behavior, liquidity requirements, volatility patterns, and common pump-and-dump indicators.

---

# 📌 **1. Filters to EXCLUDE Stablecoins**

Stablecoins must be removed because they do not exhibit meaningful volatility.

### **A) Tag-based filter**

Remove any coin that contains:

* `"stablecoin"`
* `"asset-backed-stablecoin"`
* `"algorithmic-stablecoin"`

### **B) Price-based filter**

Remove any coin whose price stays near $1:

```
If 0.95 < price < 1.05 → exclude
```

### **C) Known stablecoins to blacklist**

USDT, USDC, BUSD, DAI, TUSD, FRAX, PYUSD, GUSD, USDD, EURT, etc.

---

# 📌 **2. Filters for High-Growth Potential Coins (Explosive Upward Moves)**

A coin is considered **high-growth potential** if it meets *multiple* strong indicators of bullish momentum and speculative activity.

### **A) Price Momentum**

```
percent_change_24h > 15%
```

Why: explosive coins typically show early acceleration.

Optional stronger filter:

```
percent_change_1h > 1.5%
```

---

### **B) High Trading Volume (Very Important)**

```
volume_24h > 5,000,000 USD
```

This removes fake pumps with low liquidity.

Premium filter:

```
volume_change_24h > 25%
```

---

### **C) Market Capitalization (Smaller = Faster Moves)**

```
market_cap < 1,000,000,000   # mid caps & small caps
```

Small caps move fastest, mid caps are stable grower candidates.

Optional advanced filter:

```
market_cap > 10,000,000      # removes junk microcaps
```

---

### **D) Volatility**

```
high_24h - low_24h >= 6%
```

High volatility = speculative opportunity.

---

### **E) Liquidity Health Check**

```
volume_24h / market_cap ≥ 0.08
```

8%+ is a sign of active speculation.

---

### **F) Trend Confirmation**

Use moving averages:

```
price > MA20  
MA20 > MA50  
```

This confirms short-term bullish trend.

---

# 📌 **3. Filters for High Crash Potential (Coins Likely to Drop Hard)**

A coin is considered **high crash risk** if it shows strong downward momentum combined with significant trading activity.

### **A) Price Collapse**

```
percent_change_24h < -15%
```

Optional stronger filter:

```
percent_change_1h < -2%
```

---

### **B) High Volume (Real Crash vs Fake Drop)**

```
volume_24h > 2,000,000 USD
```

High volume ensures the drop is legit, not random noise.

---

### **C) Negative Trend Validation**

```
price < MA20  
MA20 < MA50
```

---

### **D) Liquidity Panic Indicator**

```
volume_change_24h > 20%
```

Sharp increase in sell volume.

---

### **E) Extreme Volatility**

```
(high_24h - low_24h) / price > 0.07
```

---

# 📌 **4. Optional Additional Filters (Advanced)**

### **A) Social Sentiment Indicators**

* Positive sentiment → growth
* Negative sentiment → crash

### **B) On-Chain Activity Trends**

* Increase in active addresses → growth
* Sharp decline → crash

### **C) Whale Activity**

* Whale buying → growth
* Whale selling → crash

(If you want, I can add APIs for these.)

---

# 📌 **Full Prompt (English Template for ChatGPT or LLM Tools)**

Here is your final **ready-to-use prompt**:

---

## **📌 PROMPT: “Crypto High Potential Coin Analyzer”**

**You are an expert crypto market analyst.
Analyze the provided coin data using the following strict filters:**

### **1. Exclude Stablecoins**

* Remove any coin tagged as “stablecoin”
* Remove coins priced between 0.95 and 1.05 USD
* Remove known stablecoins such as USDT, USDC, BUSD, DAI, etc.

---

### **2. Identify High-Growth Potential Coins (Bullish Candidates)**

Select coins that match multiple of these:

* 24h price change > 15%
* 24h volume > 5M USD
* Market cap < 1B
* 24h volatility ≥ 6%
* Volume-to-market-cap ≥ 0.08
* Uptrend: price > MA20 and MA20 > MA50

Return them as:
`"High Growth Potential Coins": [...]`

---

### **3. Identify High Crash Potential Coins (Bearish Candidates)**

Select coins that match multiple of these:

* 24h price change < –15%
* 24h volume > 2M USD
* Downtrend: price < MA20 and MA20 < MA50
* Volume spike: 24h volume change > 20%
* Volatility > 7%

Return them as:
`"High Crash Potential Coins": [...]`

---

### **4. For each coin, return:**

* Name
* Symbol
* Price
* % change (1h, 24h, 7d)
* Market cap
* 24h volume
* Reason why it passed the filters





Review existing unit tests and add the important test scripts.

Start testing all watchers one by one.

Confirm data flow and consistency at each step.

Validate Watchers

Ensure watchers trigger properly.

Perform full end-to-end testing.