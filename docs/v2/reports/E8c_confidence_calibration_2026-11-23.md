# E8c — Is watcher "confidence" informative? (layer-2 input, 2026-11-23)

DEV window 2026-07..08 only, 8 perps, Fusion-rule side, 4h forward return, by confidence quintile.
Data: `E8c_confidence_calibration.csv`.

| Watcher | Confidence range | Share above live Fusion threshold | Quintile 1 → 5 (bp, 4h) |
|---|---|---|---|
| market_pulse | 0.20–0.52 | 0% (threshold 0.60) | +4.5, +5.8, +1.7, −1.7, **−9.5** |
| historical_candle | 0.25–0.39 | 0% (threshold 0.60) | +4.2, +0.9, +5.1, +5.8, −0.1 |
| anomaly_ml | 0.15–0.98 | 32% (threshold 0.70) | −2.9, −1.0, −7.7, −4.6, **−14.4** |
| trend_mtf | 0–0.60 | 40% (threshold 0.55) | too few directional samples |
| volatility | 0.20–0.95 | 12% (threshold 0.55) | regime role, no side |

## Conclusion for layer 2 (Fusion)
- Reported confidences are uncalibrated heuristics; where they vary, higher confidence is *worse* (market_pulse,
  anomaly_ml). The fixed thresholds can never be met by market_pulse/historical_candle.
- Lowering the thresholds would admit signals that E8b showed carry no edge. **Decision: the Fusion filter is left
  as is** — "no direction" is the correct output while no watcher has edge. Revisit only for a watcher that passes
  an out-of-sample test, with a threshold set on DEV data from its own confidence distribution.
