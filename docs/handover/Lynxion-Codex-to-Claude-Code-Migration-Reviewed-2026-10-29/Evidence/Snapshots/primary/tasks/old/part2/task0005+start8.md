You are now entering Engineering Sprint 6 of the Lynxion-ETS Quantitative R&D Program.

Completed milestones:

- Backtest Engine Certification
- Market Data Domain Layer
- Binance Market Data Collector
- Venue Normalization
- L2 Order Book Reconstruction
- Deterministic Replay Engine

The research platform is now ready for alpha feature development.

Do NOT build a generic feature library.

Do NOT create hundreds of indicators.

We will develop features driven by a specific quantitative hypothesis.

=====================================================

OBJECTIVE

Implement the first Alpha Research Feature Pipeline:

Next Generation Liquidity Sweep (NGLS)

=====================================================

RESEARCH HYPOTHESIS

A liquidity sweep occurs when price temporarily consumes resting liquidity near important market boundaries, followed by absorption and failure to continue.

The strategy hypothesis:

Large liquidity consumption + order flow imbalance + absorption behavior can identify short-term reversal opportunities.

=====================================================

IMPLEMENT ONLY FEATURES REQUIRED FOR THIS HYPOTHESIS

Required features:

1. Order Book Imbalance (OBI)

Calculate:

- bid depth
- ask depth
- imbalance ratio
- multi-level imbalance
- imbalance change velocity


2. Trade Flow Delta

Calculate:

- aggressive buy volume
- aggressive sell volume
- delta
- cumulative delta


3. Liquidity Sweep Detection

Detect:

- previous swing liquidity zones
- liquidity penetration
- volume consumed
- rejection behavior


4. Absorption Detection

Detect:

- high traded volume
- limited price movement
- opposing liquidity response


5. Market Context

Include:

- volatility
- spread
- depth
- regime context


=====================================================

ARCHITECTURE

Follow:

OrderBook State
|
v
Feature Generator
|
v
Feature Snapshot
|
v
Strategy Layer

Features must NOT know about strategies.

=====================================================

TESTING

Validate:

- deterministic replay produces identical features
- no future data usage
- timestamp correctness
- missing data handling
- multi-symbol isolation

=====================================================

DELIVERABLES

Provide:

1. Feature domain models
2. Feature generator implementation
3. Tests
4. Documentation
5. Example generated feature snapshots
6. Research limitations

Do not implement trading rules.

Do not implement entries/exits.

Do not implement execution.

Stop after NGLS Feature Pipeline.