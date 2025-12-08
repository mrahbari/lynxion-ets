Review the following files:

* `infrastructure/watchers/adapters/cmc_screener.py`
* `infrastructure/watchers/adapters/cmc_watcher_adapter.py`
* `infrastructure/watchers/adapters/enhanced_cmc_watcher.py`

The goal is to **merge the logic into one fully featured file**, ideally named:

**`infrastructure/watchers/adapters/cmc_screener.py`**

This consolidated module should handle all required functionality in a clean, scalable, and maintainable way.

### **Potential Improvements to Add in the Unified Screener**

1. **API Rate Limiting Management**
   Implement logic to prevent exceeding CoinMarketCap API rate limits.

2. **Caching Mechanism**
   Cache API responses to reduce redundant network calls and improve performance.

3. **More Sophisticated Analysis**
   Improve price-growth and price-decline detection with better algorithms.

4. **Improved Volume Spike Detection**
   Enhance the logic for identifying unusual trading volume behavior.

5. **Time-based Analysis**
   Support additional timeframes (e.g., 5m, 15m, 1h, 4h, 24h) to make the system more suitable for crypto scalping.

---

### **Action Points**

* [ ] Review the three existing watcher/screener files.
* [ ] Identify duplicated, overlapping, and unique features.
* [ ] Merge all required functionality into a single file: `cmc_screener.py`.
* [ ] Implement API rate limiting controls (e.g., backoff, queueing, sleep).
* [ ] Add caching (in-memory or Redis depending on your architecture).
* [ ] Refactor analysis logic to support more accurate trend detection.
* [ ] Upgrade volume spike detection with dynamic thresholds or statistical methods.
* [ ] Add multi-timeframe analysis support for scalping strategies.
* [ ] Test end-to-end functionality to ensure nothing breaks after consolidation.
