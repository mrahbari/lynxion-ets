First, Always you must cover the rules and requirements that written in ./tasks/task0-force-to-cover.md

Handle the Findings and Recommendations:

  1. Duplicate Watcher Implementations (High Priority)
   - Issue: Multiple watchers have both regular and "improved" versions:
     - HistoricalCandleWatcherAdapter vs HistoricalCandleWatcherImprovedAdapter
     - MarketPulseWatcher vs MarketPulseWatcherImprovedAdapter
   - Problem: This creates confusion about which version to use and potential maintenance overhead
   - Recommendation: Consolidate into single adaptive watchers that can adjust their behavior based on configuration

  2. CMCScreener Architecture Difference (Medium Priority)
   - Note: CMCScreener inherits from WatcherPort directly, while others inherit from BaseWatcher
   - Assessment: This is intentional since it serves a different purpose (universe screening vs. individual symbol
     analysis)
   - Status: Acceptable design difference

  3. Potential Overlap Between Watchers (Medium Priority)
   - Issue: Some watchers may have overlapping functionality:
     - TrendMTFWatcher and MarketPulseWatcher both analyze trends
     - VolatilityWatcher and LiquidityWatcher both measure market conditions
   - Assessment: While there's some overlap, each serves a distinct analytical purpose
   - Status: Acceptable but could benefit from clearer differentiation

  4. Watcher Count (Low Priority)
   - Note: There are 10+ different watchers which might seem excessive
   - Assessment: Each watcher serves a specific analytical purpose in a comprehensive trading system
   - Status: Appropriate for a sophisticated trading system

  Refactoring Recommendations

  Priority 1: Consolidate Duplicate Implementations

   1 # Instead of having separate regular/improved versions:
   2 # HistoricalCandleWatcherAdapter and HistoricalCandleWatcherImprovedAdapter
   3 # Create a single HistoricalCandleWatcher that adapts based on configuration

  Priority 2: Standardize Configuration Approach
   - All watchers should have consistent configuration patterns
   - Environment variable naming should follow consistent conventions

  Priority 3: Consider Watcher Factory Pattern
   - Implement a factory to create appropriate watcher variants based on configuration
   - This would eliminate the need for multiple nearly identical classes

  Conclusion

  Most watchers serve legitimate purposes in a comprehensive trading system. The main issue is the duplication
  between regular and improved versions, which creates maintenance burden and potential confusion. The core
  functionality of each watcher type is valuable and should be preserved, but the implementation could be
  streamlined.


----



I strongly believe that **watchers and their business logic should live in their own dedicated files**. By that, I mean that **each watcher and its implementation should reside under**
`infrastructure/watchers/adapters`.

However, I see several methods in
`infrastructure/watchers/market_opportunity_watcher.py`
that concern me and raise the question of whether we have **duplicated part of the watchers’ business logic** in this file as well.

For example, methods such as:

* `_discover_volatility_oriented_symbols`
* `_discover_momentum_oriented_symbols`
* `_discover_anomaly_oriented_symbols`
* `_discover_orderflow_oriented_symbols`
* `_discover_liquidity_oriented_symbols`
* `_discover_funding_oriented_symbols`

make me wonder whether we are **re-implementing watcher-specific logic here**, instead of keeping it fully encapsulated inside each watcher.

Could you please help me review this carefully and confirm that this is **not happening**?
I want to ensure that:

* responsibilities are **properly separated**,
* **each watcher owns its own business logic**, and
* no watcher logic is duplicated or leaked into `market_opportunity_watcher.py`.

Thank you in advance for taking a close look at this.


