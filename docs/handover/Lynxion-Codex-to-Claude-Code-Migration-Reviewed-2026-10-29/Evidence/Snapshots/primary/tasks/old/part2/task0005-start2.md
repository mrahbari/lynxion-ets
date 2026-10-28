You are now entering Execution Phase 2 of the Lynxion-ETS Quantitative R&D Program.

The Backtest Engine has successfully passed certification.

The research platform is now considered mathematically trustworthy.

No further work should be performed on the backtesting engine unless a critical defect is discovered.

=====================================================================
MISSION
=====================================================================

Build the production-grade Market Data Infrastructure required for next-generation quantitative trading strategies.

This infrastructure will become the single source of truth for all market microstructure data used by research, backtesting, optimization, and live trading.

Design for long-term scalability, maintainability, and scientific reproducibility.

Preserve the existing Hexagonal Architecture.

Watcher
→ Engine
→ Fusion
→ Strategy
→ Broker

Do not introduce architectural shortcuts.

=====================================================================
PHASE 1 — REQUIREMENTS ANALYSIS
=====================================================================

Determine every market dataset required for the approved research roadmap.

At minimum evaluate:

- Binance Futures L2 Order Book
- Incremental Order Book Updates
- Trade Stream
- Aggressor Side
- Open Interest
- Open Interest Delta
- Funding Rate
- Funding Rate History
- Liquidation Feed
- Mark Price
- Index Price
- Premium Index
- Volume Profile
- CVD (Cumulative Volume Delta)
- Bid/Ask Imbalance
- Absorption
- Iceberg Detection
- Session Statistics
- VWAP
- TWAP
- Realized Volatility
- ATR
- Correlation Matrix

Identify any additional datasets that would materially improve quantitative research.

=====================================================================
PHASE 2 — DATA ARCHITECTURE
=====================================================================

Design a production-grade market data platform.

Define:

- adapters
- collectors
- stream processors
- storage layer
- replay engine
- caching
- synchronization
- timestamp normalization
- gap recovery
- reconnect strategy
- historical storage
- feature generation

Ensure all datasets can be replayed deterministically during backtests.

=====================================================================
PHASE 3 — DATABASE DESIGN
=====================================================================

Design an efficient storage model.

Include:

- schema
- indexing
- partitioning
- compression
- retention
- archival
- replay optimization

Optimize for:

- high write throughput
- low latency
- years of historical storage
- deterministic replay

=====================================================================
PHASE 4 — FEATURE ENGINEERING
=====================================================================

Design reusable feature generators.

Examples:

- CVD
- Order Book Imbalance
- Delta Volume
- Sweep Detection
- Absorption Detection
- Liquidity Heatmap
- Volume Profile
- Session Metrics
- VWAP Bands
- Rolling Volatility

Features must be reusable across multiple strategies.

=====================================================================
PHASE 5 — VALIDATION
=====================================================================

For every dataset define:

- source
- update frequency
- expected latency
- validation rules
- missing-data handling
- quality metrics
- confidence score

=====================================================================
PHASE 6 — IMPLEMENTATION ROADMAP
=====================================================================

Break implementation into small milestones.

Each milestone must:

- be independently deployable
- include tests
- include validation
- include documentation
- preserve architecture

Do NOT implement everything at once.

=====================================================================
PHASE 7 — FINAL DELIVERABLE
=====================================================================

Produce a complete Market Data Architecture Specification.

The document should include:

- architecture diagrams (text form)
- component responsibilities
- data flow
- storage design
- interfaces
- APIs
- event contracts
- implementation order
- risks
- estimated complexity
- expected quantitative impact

This specification should be detailed enough that multiple engineers can implement it independently while maintaining architectural consistency.

Do not begin implementation.

Produce the complete architecture and implementation blueprint first.