# Next Generation Liquidity Sweep (NGLS) Feature Pipeline: Technical Documentation

**Component Path:** `domain/entities/feature.py`, `infrastructure/data/ngls_feature_generator.py`  
**Test Suite:** `tests/unit/test_ngls_feature_pipeline.py`  

---

## 1. Research Hypothesis Context
A liquidity sweep occurs when price temporarily penetrates resting liquidity near historical swing high/low boundaries, followed by aggressive absorption by market makers, leading to a failure to continue and an immediate price rejection/reversal.

The **NGLS Feature Generator** aggregates Level 2 book structures and public trade ticks to compute indicators required to validate this hypothesis:

```
[ Reconstructed L2 Book ] + [ Trade Ticks ]
            |
            v
 +--------------------------------------------------------------------------------+
 |                           NGLS FEATURE GENERATOR                               |
 |                                                                                |
 |  1. OBI (Ratio, Multi-Level, Velocity)                                         |
 |  2. Trade Flow Delta (Rolling Delta, CVD)                                      |
 |  3. Sweep Detection (Range Penetration, Pullback Rejection)                    |
 |  4. Absorption Detection (High Traded Volume + Small Price Range)              |
 |  5. Market Context (Decimal Volatility, Regime Context)                        |
 +--------------------------------------------------------------------------------+
            |
            v
[ FeatureSnapshot.to_dict() ]
```

---

## 2. Feature Calculations & Formulas

### A. Order Book Imbalance (OBI)
*   **Best OBI Ratio (`obi_ratio`):**  
    $$\text{OBI Ratio} = \frac{Q_{\text{bid}} - Q_{\text{ask}}}{Q_{\text{bid}} + Q_{\text{ask}}}$$  
    Calculated at the best bid and ask price levels.
*   **Multi-Level OBI (`obi_multi_level`):**  
    Calculated across the top 5 bids and asks levels to capture deeper resting book imbalances.
*   **OBI Velocity (`obi_velocity`):**  
    $$\text{OBI Velocity} = \frac{\text{OBI Ratio}_t - \text{OBI Ratio}_{t-1}}{dt}$$  
    Where $dt$ is the change in exchange timestamp seconds.

### B. Trade Flow Delta
*   **Net Delta (`delta`):** Aggressive BUY volume minus aggressive SELL volume over a rolling window of the last 20 trades.
*   **Cumulative Delta (`cumulative_delta`):** Continuous sum of BUY (+) and SELL (-) volumes since initialization, representing Cumulative Volume Delta (CVD).

### C. Liquidity Sweep Detection
*   **Mechanism:** Tracks the swing high and low over the last 20 trade ticks. If the latest trade price penetrates this swing high/low, but the reconstructed L2 order book's mid-price pulls back inside the range:
    *   `is_sweep = True`.
    *   `sweep_rejection_ratio` measures the ratio of the mid-price pullback relative to the price penetration.

### D. Absorption Detection
*   **Mechanism:** Triggers when rolling volume over the last 10 trades is high ($>10.0$ units) but the high-to-low price range is narrow ($< 5.0$ USD), signifying a passive seller/buyer absorbing aggressive takers.

### E. Market Context
*   **Volatility:** Rolling standard deviation of the last 20 trade prices calculated with high-precision Decimal arithmetic.
*   **Regime Context:** Categorized as `"HIGH_VOLATILITY"` if volatility exceeds the regime threshold. Otherwise, categorized as `"TRENDING"` if the moving average difference of prices is high, or `"RANGING"` if flat.

---

## 3. Example Generated Feature Snapshot
Below is a serialized JSON example of `FeatureSnapshot.to_dict()`:

```json
{
  "symbol": "BTC-USDT",
  "timestamp": 1700000002000,
  "obi_ratio": "-0.50000000000000000000",
  "obi_multi_level": "-0.41666666666666666667",
  "obi_velocity": "-0.41666666666666666667",
  "buy_volume": "0.0",
  "sell_volume": "0.0",
  "delta": "0.0",
  "cumulative_delta": "3.0",
  "is_sweep": false,
  "sweep_level_price": null,
  "sweep_volume_consumed": "0.0",
  "sweep_rejection_ratio": "0.0",
  "is_absorption": false,
  "absorption_volume": "0.0",
  "absorption_price_range": "0.0",
  "volatility": "0.0",
  "spread": "10.0",
  "depth_total": "10.0",
  "regime_context": "RANGING"
}
```

---

## 4. Research Limitations & Future Extensions
1.  **Fixed Threshold Constraints:** Volatility regime classifications and absorption triggers use static parameters (e.g. volatility $> 15.0$ or range $< 5.0$). For production research, these should be dynamically standardized as Z-scores or rolling ATR (Average True Range) multipliers.
2.  **Sensitivity to Window Sizes:** The swing high/low boundaries are sensitive to the trade tick buffer size. A window of 20 ticks acts as a micro-structural boundary, whereas a 200-tick window would represent macro-liquidity zones. Multiple generators with different windows should be run concurrently for comparative analysis.
3.  **Absence of Order Book Cancelations:** OBI velocity is affected by passive cancelations and additions that do not lead to trades. Future extensions should incorporate order book delta telemetry (measuring cancel/add volume streams).
