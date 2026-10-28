# Market Data Architecture Specification
**Document ID:** LYNX-SPEC-MD-001  
**Status:** APPROVED FOR R&D  
**Version:** 1.0.0  
**Target Architecture:** Hexagonal (Ports & Adapters)

---

## 1. Executive Summary

This specification outlines the production-grade **Market Data Infrastructure** for the Lynxion Electronic Trading System (ETS). The goal of this platform is to serve as the unified, high-performance, and mathematically trustworthy single source of truth for all market microstructure data.

### Architectural Philosophy
*   **Hexagonal Isolation:** Clean separation between the domain logic (signals, trading, portfolios) and the infrastructure implementations (databases, WebSockets, REST API clients).
*   **Deterministic Reproducibility:** Ensure every tick, trade, order book update, and funding event can be replayed in backtesting with zero lookahead bias and byte-identical results compared to live execution.
*   **Low Latency & High Throughput:** Design for a continuous stream of up to 10,000 messages/sec per symbol, with sub-millisecond local normalization overhead.

---

## 2. Requirements Analysis & Dataset Catalog (Phase 1)

This section systematically analyzes the 24 required core datasets and introduces 3 additional datasets essential for next-generation quantitative alpha generation.

### A. Core Dataset Catalog

#### 1. Binance Futures L2 Order Book
*   **Domain Representation:** `OrderBookL2` (Bids/Asks lists up to 50 levels deep, sequence ID, event timestamp).
*   **Quantitative Utility:** Computes immediate liquidity distribution, support/resistance levels, and order book imbalance.
*   **Frequency / Latency:** Real-time push (100ms updates). Expected latency: $< 120\text{ms}$.
*   **Validation Rules:** High bids must be strictly less than low asks (no crossed books). Prices and sizes must be positive.
*   **Missing Data Handling:** On disconnect, drop active book state and request a full REST snapshot.
*   **Quality Metrics:** Cross-spread checks, update sequence continuity.
*   **Confidence Score:** $1.0$ (direct exchange-signed feed).

#### 2. Incremental Order Book Updates
*   **Domain Representation:** `OrderBookDelta` (Sequence bounds, list of bid/ask price-level updates).
*   **Quantitative Utility:** Essential for maintaining a local L2/L3 order book copy without consuming excessive network bandwidth.
*   **Frequency / Latency:** Real-time push ($100\text{ms}$ or $250\text{ms}$ updates). Expected latency: $< 120\text{ms}$.
*   **Validation Rules:** Sequence numbers must increase monotonically by exactly $1$ (no gaps).
*   **Missing Data Handling:** If a sequence gap is detected, buffer incoming updates and immediately trigger REST snapshot resync.
*   **Quality Metrics:** Packet sequence continuity, update density.
*   **Confidence Score:** $1.0$.

#### 3. Trade Stream
*   **Domain Representation:** `PublicTrade` (Trade ID, price, quantity, timestamp, buyer/seller order ID dummy).
*   **Quantitative Utility:** Volume analysis, momentum signals, and slip modeling.
*   **Frequency / Latency:** Real-time tick-by-tick. Expected latency: $< 30\text{ms}$.
*   **Validation Rules:** Price $> 0$, quantity $> 0$. Timestamp must be within $10$ seconds of local clock on receipt.
*   **Missing Data Handling:** Use REST `/historicalTrades` API to backfill missing gaps upon reconnection.
*   **Quality Metrics:** Sequence continuity of Trade IDs.
*   **Confidence Score:** $1.0$.

#### 4. Aggressor Side
*   **Domain Representation:** `AggressorSide` (Enum: `BUY`, `SELL`).
*   **Quantitative Utility:** Identifies buying vs selling pressure, feeding into Cumulative Volume Delta (CVD) calculations.
*   **Frequency / Latency:** Real-time tick-by-tick (flag on Trade Stream). Expected latency: $< 30\text{ms}$.
*   **Validation Rules:** Must accompany every trade record.
*   **Missing Data Handling:** Infer side via tick-direction algorithm (e.g. Lee-Ready tick test) if explicitly missing.
*   **Quality Metrics:** Ratio of classified trades.
*   **Confidence Score:** $1.0$ (explicitly provided by Binance Futures).

#### 5. Open Interest (OI)
*   **Domain Representation:** `OpenInterest` (Symbol, total open positions in base currency, contract quantity, timestamp).
*   **Quantitative Utility:** Gauges market participation and capital inflow.
*   **Frequency / Latency:** Push every $5$ minutes. Expected latency: $< 500\text{ms}$.
*   **Validation Rules:** Value must be $> 0$.
*   **Missing Data Handling:** Forward-fill the last known value (open interest is persistent).
*   **Quality Metrics:** Value stability (no sudden drop $> 99\%$ unless contract expires).
*   **Confidence Score:** $0.95$ (often delayed or aggregated by the exchange).

#### 6. Open Interest Delta
*   **Domain Representation:** `OpenInterestDelta` (Difference between current and previous OI, direction flag).
*   **Quantitative Utility:** Detects short squeezes, long liquidations, or position accumulation.
*   **Frequency / Latency:** Computed every $5$ minutes on OI change. Expected latency: $< 100\text{ms}$ post-calculation.
*   **Validation Rules:** Derived from Open Interest.
*   **Missing Data Handling:** Set to $0.0$ if base OI is missing.
*   **Quality Metrics:** Mean-reverting behavior over long intervals.
*   **Confidence Score:** $0.95$.

#### 7. Funding Rate
*   **Domain Representation:** `FundingRate` (Symbol, current funding rate value, next funding timestamp).
*   **Quantitative Utility:** Dictates holding costs for perpetual positions and pricing differentials.
*   **Frequency / Latency:** Pushed every $8$ hours (or $4$ hours for volatile assets). Expected latency: $< 100\text{ms}$.
*   **Validation Rules:** Clamped between $[-3.0\%, +3.0\%]$.
*   **Missing Data Handling:** Query historical funding endpoints on the REST API.
*   **Quality Metrics:** Static verification against exchange announcements.
*   **Confidence Score:** $1.0$.

#### 8. Funding Rate History
*   **Domain Representation:** `FundingRateHistory` (Symbol, timestamped list of funding rates).
*   **Quantitative Utility:** Strategy backtesting and carry-cost modeling over multi-month runs.
*   **Frequency / Latency:** Batch query/update once per day. Expected latency: N/A.
*   **Validation Rules:** Rates match historical exchange logs.
*   **Missing Data Handling:** Redownload from archive index.
*   **Quality Metrics:** Complete coverage for the strategy's time horizon.
*   **Confidence Score:** $1.0$.

#### 9. Liquidation Feed
*   **Domain Representation:** `LiquidationEvent` (Symbol, side, price, quantity, timestamp).
*   **Quantitative Utility:** High-alpha volatility expansion signals and counter-trend exhaustion triggers.
*   **Frequency / Latency:** Real-time push upon liquidation execution. Expected latency: $< 50\text{ms}$.
*   **Validation Rules:** Execution price must be close to index price.
*   **Missing Data Handling:** Gaps cannot be fully recovered via public streams; estimate missing liquidations using trade stream outliers.
*   **Quality Metrics:** Outlier verification against public aggregators.
*   **Confidence Score:** $0.90$.

#### 10. Mark Price
*   **Domain Representation:** `MarkPrice` (Price value used for margin/liquidation, timestamp).
*   **Quantitative Utility:** Calculates floating PnL, margins, and liquidation distances.
*   **Frequency / Latency:** Real-time push (every $3$ seconds). Expected latency: $< 50\text{ms}$.
*   **Validation Rules:** Price must be between Bid and Ask.
*   **Missing Data Handling:** Interpolate between index price and last known mark price.
*   **Quality Metrics:** Volatility limit relative to spot.
*   **Confidence Score:** $1.0$.

#### 11. Index Price
*   **Domain Representation:** `IndexPrice` (Price based on spot index basket, timestamp).
*   **Quantitative Utility:** Detects futures premium/discount trends.
*   **Frequency / Latency:** Real-time push (every $3$ seconds). Expected latency: $< 50\text{ms}$.
*   **Validation Rules:** Must not deviate from mark price by $> 5\%$ under normal market conditions.
*   **Missing Data Handling:** Compute a spot basket median from alternative exchange feeds.
*   **Quality Metrics:** Deviation from constituent spot prices.
*   **Confidence Score:** $0.98$ (index formula details are exchange-specific).

#### 12. Premium Index
*   **Domain Representation:** `PremiumIndex` (Premium percentage, timestamp).
*   **Quantitative Utility:** Predicts upcoming funding rate changes.
*   **Frequency / Latency:** Real-time push (every $3$ seconds). Expected latency: $< 50\text{ms}$.
*   **Validation Rules:** Correlated with basis (futures price - spot price).
*   **Missing Data Handling:** Calculate manually using:
    $$\text{Premium Index} = \frac{\max(0, \text{Impact Bid} - \text{Index Price}) - \max(0, \text{Index Price} - \text{Impact Ask})}{\text{Index Price}}$$
*   **Quality Metrics:** Smoothness index.
*   **Confidence Score:** $0.95$.

#### 13. Volume Profile
*   **Domain Representation:** `VolumeProfile` (Price bins, volume per bin, value area, POC).
*   **Quantitative Utility:** Locates support/resistance shelves and high/low-volume nodes.
*   **Frequency / Latency:** Recalculated every $1$ minute on a rolling window. Expected latency: $< 200\text{ms}$.
*   **Validation Rules:** Total profile volume equals sum of trade volumes in the window.
*   **Missing Data Handling:** Rebuild profile using the raw trade stream.
*   **Quality Metrics:** Bin density coverage.
*   **Confidence Score:** $0.98$.

#### 14. CVD (Cumulative Volume Delta)
*   **Domain Representation:** `CVD` (Cumulative buy volume minus sell volume, timestamp).
*   **Quantitative Utility:** Measures aggressive order flow balance over specific sessions.
*   **Frequency / Latency:** Updated tick-by-tick. Expected latency: $< 10\text{ms}$ post-trade.
*   **Validation Rules:** Cumulative tracker; resets at session open or runs on rolling windows.
*   **Missing Data Handling:** Recalculate from raw trade stream.
*   **Quality Metrics:** Continuous drift checks.
*   **Confidence Score:** $1.0$.

#### 15. Bid/Ask Imbalance
*   **Domain Representation:** `BookImbalance` (Imbalance ratio $[-1.0, +1.0]$, timestamp).
*   **Quantitative Utility:** Pre-trade alpha for micro-price direction.
*   **Frequency / Latency:** Calculated on every L2 update ($100\text{ms}$). Expected latency: $< 5\text{ms}$.
*   **Validation Rules:** Value must range between $[-1.0, 1.0]$.
*   **Missing Data Handling:** Set to $0.0$ if order book is currently disconnected.
*   **Quality Metrics:** Signal variance.
*   **Confidence Score:** $0.98$.

#### 16. Absorption
*   **Domain Representation:** `AbsorptionState` (Price level, absorbed volume, direction, duration).
*   **Quantitative Utility:** Pinpoints icebergs or block orders absorbing aggressive market orders.
*   **Frequency / Latency:** Event-driven. Expected latency: $< 50\text{ms}$ post-trade.
*   **Validation Rules:** Aggressive trades occur at a price level but the price fails to tick through, with book size replenished.
*   **Missing Data Handling:** Non-recoverable if order book updates are missed; mark state as "Unknown" for that window.
*   **Quality Metrics:** Replenishment ratio.
*   **Confidence Score:** $0.85$ (requires heuristics).

#### 17. Iceberg Detection
*   **Domain Representation:** `IcebergOrder` (Price, estimated total size, visible size, executed size).
*   **Quantitative Utility:** Avoids executing orders into large hidden walls.
*   **Frequency / Latency:** Event-driven. Expected latency: $< 100\text{ms}$ post-match.
*   **Validation Rules:** Total executed size at level exceeds the original visible size on the book.
*   **Missing Data Handling:** Heuristics based on order matching logs.
*   **Quality Metrics:** Detection accuracy compared to execution fill reports.
*   **Confidence Score:** $0.80$.

#### 18. Session Statistics
*   **Domain Representation:** `SessionStats` (High, low, open, close, volume, VWAP, session start).
*   **Quantitative Utility:** Strategic anchoring of support/resistance bands.
*   **Frequency / Latency:** Updates every $1$ minute. Expected latency: $< 10\text{ms}$.
*   **Validation Rules:** High $\ge$ Low, Open/Close fall within High/Low bounds.
*   **Missing Data Handling:** Recompute from trade database.
*   **Quality Metrics:** Completeness checks.
*   **Confidence Score:** $1.0$.

#### 19. VWAP (Volume Weighted Average Price)
*   **Domain Representation:** `VWAP` (VWAP price value, standard deviation bands, timestamp).
*   **Quantitative Utility:** Mean-reversion boundaries and institutional execution benchmark.
*   **Frequency / Latency:** Calculated on every new trade. Expected latency: $< 5\text{ms}$.
*   **Validation Rules:** Must lie within session High and Low.
*   **Missing Data Handling:** Recompute using trade stream database.
*   **Quality Metrics:** Real-time standard deviation variance.
*   **Confidence Score:** $1.0$.

#### 20. TWAP (Time Weighted Average Price)
*   **Domain Representation:** `TWAP` (TWAP price value, window length, timestamp).
*   **Quantitative Utility:** Baseline execution benchmark for execution algorithms.
*   **Frequency / Latency:** Computed every $1$ minute. Expected latency: $< 10\text{ms}$.
*   **Validation Rules:** Placed within close range of mean market price.
*   **Missing Data Handling:** Rebuild using historical close prices.
*   **Quality Metrics:** Time-interval consistency.
*   **Confidence Score:** $1.0$.

#### 21. Realized Volatility
*   **Domain Representation:** `RealizedVolatility` (Value, window size, calculation method).
*   **Quantitative Utility:** Dynamically adjusts risk exposure and SL/TP distances.
*   **Frequency / Latency:** Computed every $1$ minute on $5\text{m}$ log-return rolling windows. Expected latency: $< 20\text{ms}$.
*   **Validation Rules:** Must be $\ge 0.0$.
*   **Missing Data Handling:** Fall back to historical close price standard deviation if ticks are missing.
*   **Quality Metrics:** Stationarity check.
*   **Confidence Score:** $0.98$.

#### 22. ATR (Average True Range)
*   **Domain Representation:** `ATR` (Value, period, timestamp).
*   **Quantitative Utility:** Measures asset volatility to calculate stop-loss boundaries.
*   **Frequency / Latency:** Calculated at candle closes (1m, 5m, 1h). Expected latency: $< 50\text{ms}$.
*   **Validation Rules:** Must be $> 0$.
*   **Missing Data Handling:** Calculate using adjacent candles; forward-fill if necessary.
*   **Quality Metrics:** Smoothness check.
*   **Confidence Score:** $1.0$.

#### 23. Correlation Matrix
*   **Domain Representation:** `CorrelationMatrix` (2D matrix of rolling correlation coefficients).
*   **Quantitative Utility:** Dynamically hedges portfolios and prevents over-allocation to correlated assets.
*   **Frequency / Latency:** Computed hourly over daily windows. Expected latency: $< 1\text{sec}$.
*   **Validation Rules:** Values must fall strictly between $[-1.0, 1.0]$. Diagonal values must equal $1.0$.
*   **Missing Data Handling:** Exclude assets with $> 5\%$ missing data in the target window.
*   **Quality Metrics:** Matrix positive semi-definiteness check.
*   **Confidence Score:** $0.95$.

---

### B. Additional High-Alpha Datasets

To enhance predictive alpha and execution quality, we include three additional datasets:

#### 24. Order Flow Toxicity (VPIN - Volume Imbalance Probability of Toxicity)
*   **Domain Representation:** `VPIN` (Value $[0.0, 1.0]$, volume bucket index, timestamp).
*   **Quantitative Utility:** Measures the probability that market makers are trading against informed traders. Triggers stop-trading limits during toxic flow events.
*   **Frequency / Latency:** Recalculated on completion of every volume bucket. Expected latency: $< 100\text{ms}$.
*   **Validation Rules:** Must fall between $[0.0, 1.0]$.
*   **Missing Data Handling:** Interpolate across adjacent volume buckets.
*   **Quality Metrics:** Predictive correlation with short-term volatility spikes.
*   **Confidence Score:** $0.90$.

#### 25. Liquidations Heatmap (Liquidity Density)
*   **Domain Representation:** `LiquidityDensity` (Map of price levels to accumulated historical liquidation volumes).
*   **Quantitative Utility:** Identifies "liquidity pools" where stop-losses cluster, acting as price attractors.
*   **Frequency / Latency:** Maintained in memory, updated on every liquidation event. Expected latency: $< 50\text{ms}$.
*   **Validation Rules:** Liquidation values must decay over time (half-life of 24-48 hours) to reflect order changes.
*   **Missing Data Handling:** Backfill with historical liquidation logs.
*   **Quality Metrics:** Density map stability.
*   **Confidence Score:** $0.85$.

#### 26. Correlated Asset Lead-Lag Lagged Covariance
*   **Domain Representation:** `LeadLagOffset` (Offset in milliseconds, correlation coefficient, timestamp).
*   **Quantitative Utility:** Exploits lead-lag relationships (e.g. BTC spot leading altcoin futures).
*   **Frequency / Latency:** Computed every $10$ seconds on sub-second ticks. Expected latency: $< 500\text{ms}$.
*   **Validation Rules:** Coefficient $\in [-1.0, 1.0]$.
*   **Missing Data Handling:** Set to zero correlation during high network jitter or data dropouts.
*   **Quality Metrics:** Lead-lag coefficient significance score.
*   **Confidence Score:** $0.80$.

---

## 3. Data Architecture (Phase 2)

The market data platform adheres to Hexagonal Architecture patterns, keeping exchange-specific connections outside the domain core.

```
       +-------------------------------------------------------------------+
       |                       INFRASTRUCTURE LAYER                        |
       |                                                                   |
       |  +--------------------+                   +--------------------+  |
       |  | Exchange WebSocket |                   |  TimescaleDB /     |  |
       |  | Adapter            |                   |  QuestDB Adapter   |  |
       |  +---------+----------+                   +---------+----------+  |
       |            |                                        |             |
       +------------|----------------------------------------|-------------+
                    |                                        |
       +------------|----------------------------------------|-------------+
       |            v                                        v             |
       |  +--------------------+                   +--------------------+  |
       |  | MarketCollectorPort|                   | MarketStoragePort  |  |
       |  +---------+----------+                   +---------+----------+  |
       |            |                                        ^             |
       |            |          +------------------+          |             |
       |            +--------->|  Domain Engine   |----------+             |
       |                       |  (Market Data    |                        |
       |                       |   Core Domain)   |                        |
       |                       +--------+---------+                        |
       |                                |                                  |
       |                                v                                  |
       |                       +------------------+                        |
       |                       |  FeatureGenPort  |                        |
       |                       +--------+---------+                        |
       |                                |                                  |
       |                                v                                  |
       |                       +------------------+                        |
       |                       |   StrategyPort   |                        |
       |                       +------------------+                        |
       |                                                                   |
       |                        DOMAIN CORE LAYER                          |
       +-------------------------------------------------------------------+
```

### Component Specifications

*   **Adapters:**
    *   *BinanceWebsocketAdapter:* Establishes connections to Binance USD-M Futures WebSocket API (`wss://fstream.binance.com`).
    *   *DatabaseStorageAdapter:* Implements write pipelines to TimescaleDB/QuestDB.
*   **Collectors:**
    *   *MarketDataCollector:* Manages connection state, processes incoming JSON messages, filters keep-alives, and normalizes payloads into domain entities.
*   **Stream Processors:**
    *   *OrderBookBuilder:* Reconstructs local L2 books using REST snapshots and incremental diff streams. Runs on dedicated process threads to prevent event loop blockages.
    *   *TickAggregator:* Groups tick trades into rolling time/volume buckets.
*   **Replay Engine:**
    *   Reads historical data from QuestDB. It injects ticks sequentially into the backtest runner, maintaining identical function calls to the live pipeline.
*   **Caching Topology:**
    *   *Redis L2 Order Book Cache:* Stores the latest 50 levels of bids/asks for rapid access by execution routers.
*   **Timestamp Normalization:**
    *   Every data point carries three timestamps:
        1.  `exchange_time`: Clock time recorded by the exchange server.
        2.  `local_ingest_time`: Clock time when the packet entered our gateway.
        3.  `normalized_time`: Synchronized database insertion time.
    *   Backtesting and feature calculations use `exchange_time` to prevent network jitter bias.
*   **Gap Recovery & Reconnection:**
    *   *Heartbeat Monitor:* Disconnects and reconnects if no ping is received for $5$ seconds.
    *   *REST Backfiller:* Queries missing trade ranges on reconnect using sequence ranges before resuming live subscriptions.

---

## 4. Database Design & Schema (Phase 3)

We select **TimescaleDB** (PostgreSQL extension) as the primary storage engine due to its SQL flexibility, strong write throughput, and hypertable partitioning.

### Schema Specifications

#### Hypertables

```sql
-- 1. Tick Trades Hypertable
CREATE TABLE futures_trades (
    timestamp TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(12) NOT NULL,
    trade_id BIGINT NOT NULL,
    price DOUBLE PRECISION NOT NULL,
    quantity DOUBLE PRECISION NOT NULL,
    aggressor_side VARCHAR(4) NOT NULL, -- 'BUY' or 'SELL'
    exchange_time TIMESTAMPTZ NOT NULL
);
SELECT create_hypertable('futures_trades', 'timestamp', partitioning_column => 'symbol', number_partitions => 4);

-- 2. L2 Order Book Snapshots Hypertable (Top 20 Levels)
CREATE TABLE order_book_l2 (
    timestamp TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(12) NOT NULL,
    sequence_id BIGINT NOT NULL,
    bids_price DOUBLE PRECISION[] NOT NULL,
    bids_qty DOUBLE PRECISION[] NOT NULL,
    asks_price DOUBLE PRECISION[] NOT NULL,
    asks_qty DOUBLE PRECISION[] NOT NULL
);
SELECT create_hypertable('order_book_l2', 'timestamp', partitioning_column => 'symbol', number_partitions => 4);

-- 3. Market State Variables Hypertable
CREATE TABLE market_state (
    timestamp TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(12) NOT NULL,
    open_interest DOUBLE PRECISION NOT NULL,
    funding_rate DOUBLE PRECISION NOT NULL,
    mark_price DOUBLE PRECISION NOT NULL,
    index_price DOUBLE PRECISION NOT NULL
);
SELECT create_hypertable('market_state', 'timestamp', partitioning_column => 'symbol', number_partitions => 4);
```

### Partitioning & Compression
*   **Partition Interval:** 1 day (daily hypertables).
*   **Compression:** Compression enabled after 7 days, segmenting by `symbol` and sorting by `timestamp DESC`.
*   **Retention Policy:** Keep raw ticks for 90 days. Compress and store hourly rollups for up to 3 years. Archives are exported to Parquet format on AWS S3/GCS.

---

## 5. Feature Engineering Specification (Phase 4)

Feature generators implement `FeatureGeneratorPort`. They run on tick data and output derived signals.

### Core Feature Formulations

*   **Cumulative Volume Delta (CVD):**
    $$CVD_t = CVD_{t-1} + \sum (V_{buy} - V_{sell})$$
*   **Order Book Imbalance (OBI):**
    $$OBI_t = \frac{\sum_{i=1}^{k} Q_{bid, i} - \sum_{i=1}^{k} Q_{ask, i}}{\sum_{i=1}^{k} Q_{bid, i} + \sum_{i=1}^{k} Q_{ask, i}}$$
    where $k = 5$ depth levels.
*   **Delta Volume:**
    Net volume difference over a rolling time window $\Delta t$.
*   **Sweep Detection:**
    Triggers when a single trade order clears $\ge 3$ consecutive price levels on the order book within $< 10\text{ms}$.
*   **Absorption Detection:**
    High trade volume matched with low price movement:
    $$\text{Volume} > \mu_V + 2\sigma_V \quad \text{AND} \quad \text{Price Spread} < \mu_S - 1\sigma_S$$

---

## 6. Data Validation & Quality Metrics (Phase 5)

To maintain data integrity and prevent garbage-in garbage-out biases during backtests, every inbound data stream passes through the validation gateway.

```
       [Raw Websocket/Rest Packet]
                   |
                   v
         [Schema Validation]  ----> FAIL ----> [Reject Packet & Log Alert]
                   |
                   v
      [Microstructure Boundary Checks]
        - Price/Size > 0
        - Spread > 0          ----> FAIL ----> [Increment Bad Packet Counter]
        - Timestamps sane
                   |
                   v
     [Statistical Outlier Filtering]
        - Price drift check   ----> FAIL ----> [Flag anomalous data]
                   |
                   v
        [Data Integrity Engine]
        - Check for sequence gaps
        - If gap detected     ----> YES  ----> [Trigger Gap Recovery REST request]
                   |
                   v
          [Database Insert]
```

### Gap Detection & Recovery Rules
*   **Trade Gaps:** If a received trade ID increases by $> 1$ relative to the previous ID, initiate REST query for the missing sequence range.
*   **Order Book Gaps:** If update ID bounds are not contiguous, immediately clear the local order book cache and fetch a new full snapshot.

---

## 7. Implementation Roadmap & Milestones (Phase 6)

We break down development into five independent milestones:

```mermaid
gantt
    title Market Data Infrastructure Roadmap
    dateFormat  YYYY-MM-DD
    section Core Infrastructure
    Milestone 0: Ports & Domain Models      :active, m0, 2026-07-15, 7d
    Milestone 1: Websocket Collectors       :        m1, after m0, 10d
    section Processing & Storage
    Milestone 2: Stream Processors          :        m2, after m1, 12d
    Milestone 3: Database & Partitioning    :        m3, after m2, 10d
    section Analytics & Replay
    Milestone 4: Feature Gen & Replay       :        m4, after m3, 14d
```

### Milestone Specifications

*   **Milestone 0: Core Domain Models & Ports Definition**
    *   *Deliverables:* Establish core value objects, entities, and ports in Python (`domain/entities/market_data.py` and `domain/ports/data_ports.py`).
    *   *Validation:* Unit tests verifying entity instantiations.

*   **Milestone 1: WebSocket Collectors & Reconnection Engines**
    *   *Deliverables:* Build exchange connections for Binance Futures feeds.
    *   *Validation:* Mock socket disconnect tests proving gap recovery and auto-reconnections under 3 seconds.

*   **Milestone 2: Stream Processor & Order Book Builder**
    *   *Deliverables:* Order book L2 depth reconstruction thread pool.
    *   *Validation:* Run against recorded raw PCAP updates, ensuring zero crossed books and correct snapshot alignment.

*   **Milestone 3: Time-Series Database Integration & Partitioning**
    *   *Deliverables:* Set up TimescaleDB storage adapters and hypertable partitioning scripts.
    *   *Validation:* Stress testing with 20,000 writes/sec to verify low storage footprint and correct daily partition creation.

*   **Milestone 4: Feature Generator Engine & Backtest Replay Engine**
    *   *Deliverables:* Out-of-the-box feature generators (CVD, OBI) and deterministic backtest replay connectors.
    *   *Validation:* Replay the same historical day twice; verify that generated feature arrays are identical to the last decimal place.

---

## 8. Expected Impact, Risks & Mitigations

### A. Estimated Complexity
*   **Core Collectors & Storage:** Medium (standard network programming, database configuration).
*   **Stateful L2 Book Builder:** High (requires sub-millisecond thread safety and lock-free queue patterns).
*   **Lead-Lag & VPIN Features:** High (mathematical optimization required to prevent latency lag).

### B. Expected Quantitative Impact
*   **Reduced Slippage Overstatement:** Real L2 order book profiles allow the backtester to fill large orders realistically instead of relying on flat spread estimates.
*   **Advanced Alpha Signals:** CVD, Imbalances, and VPIN features enable development of order flow strategies that predict short-term price movements.
*   **Confidence in Backtesting:** Deterministic replay prevents backtest overfitting, ensuring backtest performance matches live trading results.

### C. Risks & Mitigations

| Risk | Impact | Mitigation Strategy |
| :--- | :--- | :--- |
| **Binance API Rate Limits** | High | Distribute IP footprint for REST recovery requests; use private WebSocket endpoints where possible. |
| **High Memory Usage on L2 Books** | Medium | Limit active memory representation to 50 levels; purge older snapshots from Redis caches periodically. |
| **Database Disk Out-Of-Space** | High | Enforce daily data compression and move historical records older than 7 days to S3/GCS. |
