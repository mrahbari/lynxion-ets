# Master Blueprint: Alpha Research Platform & Strategic Research Roadmap

> [!IMPORTANT]
> **Executive Summary & New Phase Focus**
> With the engineering architecture, safety spine, and downstream execution pipeline frozen and testnet-validated, this document serves as the **master quantitative blueprint for the next phase: the Alpha Research Platform**. The existing ETS execution engine operates as a downstream execution target, while the Alpha Research Platform drives signal discovery, feature engineering, and statistical validation.

---

## 1. Research Architecture & Lifecycle

The quantitative research lifecycle defines a non-negotiable 10-stage pipeline that every trading hypothesis must pass before receiving capital allocation:

```
[1. Idea Generation] ──► [2. Mathematical Hypothesis] ──► [3. Dataset Acquisition]
                                                                  │
[6. Walk-Forward OOS] ◄── [5. Label Generation] ◄── [4. Feature Engineering]
         │
         ▼
[7. Statistical Significance] ──► [8. Paper Trading Soak] ──► [9. Objective Promotion] ──► [10. Production Allocation]
```

### Stage Breakdown:
1. **Idea Generation**: Formulate market structural intuition (e.g. order book toxicity, funding rate squeeze).
2. **Mathematical Hypothesis**: Express hypothesis as a testable equation ($\mathbb{E}[R_{t+h} \mid X_t] > \text{Costs}$).
3. **Dataset Acquisition**: Ingest clean, un-adjusted, point-in-time historical data.
4. **Feature Engineering**: Compute stationarity-transformed, Z-score normalized predictive features ($X_t$).
5. **Label Generation**: Construct triple-barrier labels (TP target, SL barrier, Time expiration).
6. **Walk-Forward Out-Of-Sample (OOS)**: Evaluate candidate across sequential, non-overlapping time folds.
7. **Statistical Testing**: Run Monte Carlo permutation, bootstrap hypothesis tests ($p < 0.01$).
8. **Paper Trading Soak**: Execute on live testnet feeds for 14 continuous days to measure slippage/latency drift.
9. **Objective Promotion**: Require candidate to pass explicit quantitative hurdles ($PF > 1.3$, Sharpe $> 1.5$).
10. **Production Allocation**: Promote strategy into live risk allocation pipeline under safety guardrails.

---

## 2. Alpha Categories Taxonomy

We enumerate and define 20 distinct quantitative alpha categories for institutional research:

| # | Alpha Category | Theoretical Mechanism | Core Predictive Inputs | Expected Alpha Horizon |
|---|---|---|---|---|
| **1** | **Momentum** | Trend persistence driven by institutional accumulation & behavioral herding. | Relative strength, Donchian channels, EMA slopes. | 1h – 24h |
| **2** | **Mean Reversion** | Overextended price moves returning to structural fair value. | VWAP deviation, Bollinger Bands, RSI. | 5m – 1h |
| **3** | **Trend Following** | Long-term regime expansion capture during macro shifts. | Multi-timeframe trend alignment, ADX. | 4h – 7d |
| **4** | **Breakout** | Expansion from low-volatility consolidation regimes. | ATR contraction ratios, Keltner Channels. | 15m – 4h |
| **5** | **StatArb** | Co-integrated asset pair spread mean-reversion. | Johansen cointegration, Z-score spread. | 15m – 2h |
| **6** | **Cross-Exchange** | Lead-lag catch-up price dispersion across venues. | Cross-exchange price dispersion, tick lead. | $< 1$s (HFT) |
| **7** | **Cross-Asset** | Market leader spillover (e.g. BTC leading altcoins). | Cross-asset return covariance, BTC delta. | 1m – 15m |
| **8** | **Order Flow** | Aggressor trade imbalance and buying/selling pressure. | CVD (Cumulative Volume Delta), trade tape. | 1m – 5m |
| **9** | **Microstructure** | Order book depth dynamics and passive liquidity absorption. | L2/L3 order book imbalance (OBI), VPIN. | Sub-minute |
| **10**| **Options** | Volatility surface mispricing and gamma squeeze hedging. | Implied volatility skew, put-call ratio, GEX. | 1d – 7d |
| **11**| **Funding Rate** | Perpetual swap leverage crowding and short/long squeezes. | 8h funding rate, predicted funding rate. | 8h – 72h |
| **12**| **Liquidations** | Cascading forced liquidation stop runs creating price spikes. | Liquidation burst clusters, open interest drops. | 5m – 1h |
| **13**| **Basis** | Cash-and-carry perpetual to spot spread convergence. | Spot-perp basis, annualised yield. | 1d – 30d |
| **14**| **Volatility** | Volatility clustering and implied-realized volatility dispersion. | GARCH forecasts, historical volatility ratio. | 1h – 24h |
| **15**| **Regime** | Market state transition (trending vs ranging vs crisis). | Hidden Markov Models (HMM), ADX, ATR. | Regime-wide |
| **16**| **Seasonal** | Calendar anomalies (day-of-week, funding settlement hours). | Settlement UTC hour, weekend liquidity. | Hourly / Daily |
| **17**| **Session Effects** | Liquidity expansion during London/NY market overlaps. | Session volume profile, VWAP reset. | Intraday |
| **18**| **News / Sentiment** | Unstructured text sentiment and macro release surprises. | NLP sentiment score, CPI/FOMC releases. | 1m – 4h |
| **19**| **On-chain** | Blockchain network velocity, miner flows, exchange inflows. | Active addresses, exchange netflow. | 1d – 7d |
| **20**| **Machine Learning** | Non-linear feature interactions and pattern classification. | Gradient Boosted Trees (XGBoost), LightGBM. | 5m – 1h |

---

## 3. Data Acquisition Roadmap

| Dataset | Importance | Estimated Alpha Value | Difficulty | Monthly Cost | Commercial Providers | Free Alternatives |
|---|---|:---:|:---:|:---:|---|---|
| **L2/L3 Order Book Depth** | CRITICAL | **HIGH** | High | $500 – $2,000 | Tardis.dev, Kaiko, Databento | Exchange WebSockets (Live only) |
| **Raw Tick & Trade Tape** | CRITICAL | **HIGH** | Medium | $300 – $1,200 | Tardis.dev, CryptoTick | Binance Vision Zip Dumps |
| **Liquidation Clusters** | HIGH | **HIGH** | Medium | $200 – $800 | Coinglass, CoinAnalyze | Direct Exchange WebSockets |
| **Cross-Venue Sub-Second Feeds** | HIGH | **HIGH** | High | $400 – $1,500 | CoinAPI, Kaiko | Direct Multi-Exchange WebSockets |
| **Funding & Basis History** | MEDIUM | **MEDIUM** | Low | $0 – $300 | Amberdata, CryptoCompare | Exchange Public REST APIs |
| **Options Volatility Surface** | MEDIUM | **MEDIUM** | High | $500 – $1,500 | Amberdata, Laevitas | Deribit API |
| **On-Chain Network Metrics** | LOW | **LOW** | Low | $200 – $800 | Glassnode, CryptoQuant | Dune Analytics |

---

## 4. Reusable Feature Library Taxonomy

The feature library provides standardized, stationarity-transformed quantitative inputs for model training:

```python
# Feature Taxonomy Categories:
1. Price Features        -> Log returns, Garman-Klass volatility, Donchian width ratio.
2. Volume Features       -> Volume Z-score, Relative Volume (RVOL), VWAP distance.
3. Microstructure        -> Order Book Imbalance (OBI), VPIN, Trade Intensity (Z-score).
4. Derivatives           -> Funding Rate Z-score, Annualized Basis, OI Delta % / Volume.
5. Cross-Asset           -> Cross-asset return covariance, BTC lead-lag dispersion.
6. Behavioral           -> Liquidations burst magnitude, Funding capitulation score.
7. Macro / Regime        -> ADX(14) trend regime flag, HMM regime state probability.
```

---

## 5. Quantitative Validation Framework

Every candidate alpha must undergo rigorous multi-stage validation:

1. **Walk-Forward Out-Of-Sample (WFO)**: Minimum 4 sequential, non-overlapping OOS folds. Candidate must be positive in $\ge 3/4$ folds.
2. **Bootstrap Resampling**: 1,000 bootstrap iterations of trade returns to establish a $95\%$ confidence interval for expectancy. The lower bound must be $> 0$.
3. **Monte Carlo Permutation**: Shuffle trade sequence 1,000 times to verify that max drawdown remains within acceptable risk limits ($< 15\%$).
4. **Cross-Symbol Validation**: Candidate must show positive expectancy across at least 2 distinct symbols (e.g. BTC and ETH) to prove it is not a single-coin artifact.
5. **Friction Sensitivity Stress Test**: Evaluate performance under scaled fees ($1.0\text{x}, 1.5\text{x}, 2.0\text{x}$ baseline fee + slippage). Candidate must remain profitable under $1.5\text{x}$ friction.

---

## 6. Objective Promotion Rules

State transitions between research phases are strictly governed by quantitative thresholds:

```
[ Research ] ────► [ Prototype ] ────► [ Candidate ] ────► [ Paper Trading ] ────► [ Production ]
               (1)                 (2)                   (3)                     (4)
```

* **Transition (1) Research $\rightarrow$ Prototype**: Raw signal Spearman Information Coefficient $|\text{IC}| > 0.03$ with $p$-value $< 0.01$.
* **Transition (2) Prototype $\rightarrow$ Candidate**: Cost-adjusted net expectancy $> +0.10\%$ per trade across backtest window; WFO positive folds $\ge 3/4$.
* **Transition (3) Candidate $\rightarrow$ Paper Trading**: Bootstrap 95% CI lower bound $> 0$; Profit Factor $> 1.3$; Max Drawdown $< 12\%$.
* **Transition (4) Paper Trading $\rightarrow$ Production**: 14 continuous days on live testnet with $< 15\%$ slippage drift, $0$ execution errors, and live net expectancy within $1.5 \text{ StdDev}$ of backtest estimate.

---

## 7. Objective Retirement Rules

A production strategy will be automatically decommissioned if any of the following quantitative kill triggers occur:

1. **Expectancy Degradation**: Realized 30-day net expectancy drops below $0.00\%$ (alpha decay).
2. **Drawdown Breach**: Strategy drawdown exceeds $1.5 \times$ its maximum backtest drawdown.
3. **Consecutive Losing Streak**: Strategy experiences $N$ consecutive losing trades exceeding the 99th percentile Monte Carlo threshold.
4. **Execution Drift**: Live slippage exceeds $2.5 \times$ the backtest baseline for 5 consecutive trades.

---

## 8. Prioritized Research Backlog (Top 50 Projects)

Below is the prioritized quantitative research backlog ranked by Expected ROI:

| Rank | Project Name | Research Question | Expected ROI | Required Data | Effort | Risk | Dependencies |
|:---:|:--- |:--- |:---:|:--- |:---:|:---:|:--- |
| **1** | **HFT-Catchup** | Does Binance$\rightarrow$MEXC dispersion predict MEXC 1s price catch-up? | VERY HIGH | Cross-Venue Sub-Second | 2 wks | High | L2 WebSocket Collector |
| **2** | **Liq-Squeeze** | Do liquidation burst clusters reliably predict 15m price bounces? | HIGH | Historical Liquidations | 2 wks | Med | Liquidation Ingestion |
| **3** | **L2-Absorption** | Does passive L2 order book absorption indicate institutional walls? | HIGH | Full L2 Market Depth | 3 wks | High | L2 Depth Pipeline |
| **4** | **VPIN-Toxicity**| Can VPIN toxicity spikes predict impending volatility crashes? | HIGH | Raw Tick Trade Tape | 2 wks | Med | Tick Data Storage |
| **5** | **Fund-Capitulation**| Does extreme negative funding rate predict 72h BTC/ETH reversals? | MEDIUM | 8h Funding Rate History | 1 wk | Low | REST Funding Ingestion |
| **6** | **Perp-Spot-Basis** | Does spot-perp basis divergence predict basis convergence yield? | MEDIUM | Spot & Perp Price Series | 1 wk | Low | Basis Feature Calculation |
| **7** | **Maker-VWAP-Reversion**| Can limit order maker rebates make VWAP 2.0x band entries net positive? | MEDIUM | 5m OHLCV + L2 Depth | 2 wks | Med | Limit Order Execution |
| **8** | **Vol-Expansion-Breakout**| Does ATR ratio $>1.3$ predict sustained 15m trend expansion? | MEDIUM | 15m OHLCV Data | 1 wk | Low | Technical Feature Library |
| **9** | **ADX-Trend-Gating** | Does gating TrendFollow on ADX $>25$ eliminate 70% of chop losses? | MEDIUM | 1h OHLCV Data | 1 wk | Low | Regime Engine Integration |
| **10**| **Multi-Venue-Arb** | Does Coinbase spot lead Binance perp during US session opens? | HIGH | Cross-Venue L2 Depth | 3 wks | High | Multi-Exchange Feed |
| 11 | Order Book Imbalance (OBI) | Does OBI $>0.7$ predict 5-bar forward return direction? | MEDIUM | L2 Top-of-Book Depth | 2 wks | Med | L2 Collector |
| 12 | Time-of-Day Liquidity | Does trading only during London/NY overlap reduce slippage drag? | LOW | 1m OHLCV | 1 wk | Low | Session Filter |
| 13 | Spread Expansion Filter | Does blocking entries when spread $>0.05\%$ prevent toxic fills? | LOW | Top-of-Book Spread | 1 wk | Low | Execution Guard |
| 14 | Cointegrated Pair StatArb| Are BTC/ETH log prices cointegrated for 15m Z-score trading? | MEDIUM | 15m OHLCV Majors | 2 wks | Med | Cointegration Pipeline |
| 15 | Options Vol Skew Signal | Does Deribit 25-delta put-call skew predict spot directional moves? | MEDIUM | Deribit Options Surface | 3 wks | High | Deribit API Ingestion |
| 16 | Dynamic Trail Take Profit| Does structural pivot trailing TP outperform fixed 1.5x R:R targets? | LOW | 15m OHLCV | 1 wk | Low | Setup Engine |
| 17 | Time-Based Expiration | Does force-closing trades after 4h improve portfolio capital velocity?| LOW | 15m OHLCV | 1 wk | Low | Execution Engine |
| 18 | Donchian Breakout Vol | Does Donchian channel breakout with volume $>1.5x$ 20-MA reduce false breaks?| LOW | 15m OHLCV | 1 wk | Low | Feature Library |
| 19 | GARCH Vol Forecasting| Does GARCH(1,1) forecast outperform ATR for stop loss placement? | LOW | 1h OHLCV | 2 wks | Med | Statistical Engine |
| 20 | Hidden Markov Regime | Can 3-state HMM accurately classify trending vs ranging regimes? | MEDIUM | 1h OHLCV | 2 wks | Med | ML Pipeline |
| 21 | Altcoin BTC Beta Lead | Does BTC 1m momentum predict altcoin (SOL/AVAX) 5m momentum? | MEDIUM | 1m OHLCV Universe | 2 wks | Med | Cross-Asset Pipeline |
| 22 | Open Interest Divergence| Does price rise with falling OI indicate weak short-covering? | LOW | 1h OI & OHLCV | 1 wk | Low | OI Data Feed |
| 23 | Passive Maker Scalping| Can 1m maker limit orders capture bid-ask spread net of adverse selection?| HIGH | L2 Depth & Tick Tape | 4 wks | High | HFT Engine |
| 24 | Weekend Liquidity Block| Does blocking execution on weekends improve overall profit factor? | LOW | 1h OHLCV | 1 wk | Low | Session Filter |
| 25 | News Sentiment NLP | Does CryptoPanik sentiment score predict 1h volatility expansion? | LOW | News Sentiment API | 3 wks | High | NLP Pipeline |
| 26 | On-Chain Exchange Flow | Do large exchange BTC inflows predict 24h sell pressure? | LOW | Glassnode On-Chain API | 2 wks | Med | On-chain Feed |
| 27 | XGBoost Signal Fusion | Can XGBoost combine 20 features into a non-linear signal? | MEDIUM | Feature Matrix | 3 wks | High | ML Pipeline |
| 28 | LightGBM Regime Class | Can LightGBM predict 4h market regime with $>65\%$ accuracy? | MEDIUM | Feature Matrix | 3 wks | High | ML Pipeline |
| 29 | Random Forest Entry Filter| Does RF filter out $50\%$ of losing trades without reducing winners?| LOW | Feature Matrix | 2 wks | Med | ML Pipeline |
| 30 | Short Squeeze Predictor | Does OI spike + high funding + price resistance predict squeeze?| MEDIUM | Derivatives Feed | 2 wks | Med | Setup Engine |
| 31 | Basis Yield Curve Carry | Does rolling 3-month futures basis provide stable carry return? | LOW | Futures Curve Data | 2 wks | Low | StatArb Engine |
| 32 | Coinbase Premium Index | Does Coinbase BTC premium predict US institutional buying? | MEDIUM | Coinbase vs Binance Feed| 1 wk | Low | Cross-Exchange Feed |
| 33 | Order Cancellation Rate| Does high cancel-to-fill ratio in L2 book indicate spoofing? | MEDIUM | L2 Order Depth Diff | 3 wks | High | Microstructure Pipeline|
| 34 | Trade Size Clustering | Do institutional block trades ($>\$100\text{k}$) predict trend direction?| MEDIUM | Tick Trade Tape | 2 wks | Med | Tick Pipeline |
| 35 | Triple Barrier Labeling | Does triple barrier labeling improve ML model classification precision?| LOW | Feature Matrix | 2 wks | Low | ML Labeling Engine |
| 36 | Fractional Differentiation| Does fractional differentiation make price stationary while preserving memory?| LOW | OHLCV Series | 1 wk | Low | Feature Library |
| 37 | Kalman Filter Trend | Does Kalman filter produce less lagging trend signals than EMA? | LOW | 1h OHLCV | 1 wk | Low | Feature Library |
| 38 | Hilbert Transform Cycle | Does Hilbert transform accurately identify range cycle turning points?| LOW | 1h OHLCV | 2 wks | Med | Feature Library |
| 39 | Hurst Exponent Filter | Does Hurst exponent ($H > 0.55$) identify true trending regimes?| LOW | 1h OHLCV | 1 wk | Low | Feature Library |
| 40 | Entropy Volatility | Does Shannon entropy of price returns predict volatility breakouts?| LOW | 5m OHLCV | 2 wks | Med | Feature Library |
| 41 | Cross-Asset Correlation Cap| Does capping correlation at $0.7$ reduce portfolio drawdown? | LOW | Portfolio Matrix | 1 wk | Low | Portfolio Engine |
| 42 | Dynamic Risk Scaling | Does scaling risk inversely to 14-day drawdown protect capital? | LOW | Performance History | 1 wk | Low | Risk Engine |
| 43 | Taker Volume Ratio | Does Taker Buy/Sell ratio $>1.5$ predict 15m price increases? | LOW | Taker Volume Feed | 1 wk | Low | Feature Library |
| 44 | Order Book Slope | Does the slope of bid/ask depth curves predict immediate slippage?| LOW | L2 Market Depth | 2 wks | Med | Microstructure Pipeline|
| 45 | Market Impact Model | Does Almgren-Chriss impact modeling optimize execution size? | LOW | Execution Logs | 2 wks | Med | Execution Engine |
| 46 | Funding Rate Settlement Arb| Does price drop systematically 5 mins before 8h funding settlement?| LOW | 1m OHLCV & Funding | 1 wk | Low | Session Filter |
| 47 | Volatility Skew Mean Rev | Does 25-delta put/call skew mean-revert to 30-day average? | LOW | Options Vol Surface | 2 wks | Med | Options Pipeline |
| 48 | Liquidation Heatmap Reversal| Do liquidation heatmap nodes act as price magnetic targets? | MEDIUM | Coinglass Heatmap Data | 2 wks | Med | Liquidation Pipeline |
| 49 | Multi-Exchange Lead Lag Index| Does a 4-exchange weighted price index lead single-venue price?| HIGH | 4-Exchange Tick Feeds | 3 wks | High | Multi-Exchange Feed |
| 50 | Reinforcement Learning Sizing| Can DDPG RL agent optimize position sizing dynamically? | LOW | Feature Matrix & Environment| 4 wks | High | Advanced Research |

---

## 9. Final Strategic Recommendation (6–12 Month Roadmap)

Based on all quantitative evidence gathered across the engineering stabilization and edge discovery phases:

1. **Months 1–3: Data Infrastructure Expansion**: Ingest high-frequency L2/L3 market depth diffs and raw tick trade tapes (Projects 1–4). This provides the necessary microstructure data layer.
2. **Months 4–6: Microstructure & Lead-Lag Alpha Development**: Develop and validate cross-venue sub-second catch-up and liquidation cluster squeeze signals (Projects 1, 2, 10).
3. **Months 7–9: Maker Execution & Passive Routing**: Enhance execution engine to support passive limit order posting with maker fee rebates, eliminating taker fee drag.
4. **Months 10–12: Institutional Paper Soak & Staged Rollout**: Execute 30-day paper trading soak under the new data feeds, promotion rules, and safety spine before minimal live pilot deployment.
