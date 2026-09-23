# Phase 3A run manifest — control-matching checkpoint

- Research mode: blind point-in-time selection fingerprint; no outcomes, returns after event, profitability, or production actions.
- Frozen preregistration: commit `b9ec946`, SHA-256 `96d0f336f9c0e335b61b8d90df81835180647f9c2d85498d210fa1e34c329193`.
- Provenance audit: commit `6e59c31`; derived case/engine table: `e41815c`.
- Public Binance USDT-perpetual 15m proxy source: `phase3_proxy_source_manifest.json`, collector/report commit `5bc424c`; local OHLCV CSVs are ignored/reconstructable and are not included in Git.
- Primary event anchor: V2 first signal message; 64 interval-HMT cases, 58 nominal HMT quantitative cases after known-timeframe/1w exclusions.
- Family-A checkpoint: 56 matched cases, 168 selected controls, 23 case UTC days, 22 case symbols, 25 LONG/31 SHORT. `ALUSDT` and `XAUUSD` are unavailable from the verified proxy source and remain visible in diagnostics.
- Availability: 224 case/control audit records show `max_input_close_time <= event/control T`; no market values were used to choose controls.
- Upstream PASS-1 `signals.csv` SHA-256: `ba4bc3ad4ce5ddb774494c1bdc388a959bd507fb5ff932befb592ceeffa86bdb` (unchanged).
- Upstream V2 `temporal_signals.csv` SHA-256: `97a2da637e9758fb0b370892f6f5dc4a41d9e1dd97f3e5ade7459213b60acc8f` (unchanged).
- Upstream V2 `v2_evidence_manifest.csv` SHA-256: `a2087a7ae44128588fb80466f4834845b13c3a1a00e1b09dd8a9472fd6da6224` (unchanged).
- Original private `aug/result.json` SHA-256: `5a091af3fe93fcd0965fbaea143a07fec96f968266ba209e98c0b95df7541300` (unchanged). Original `jan-jul` and `aug` folders are never staged/committed.
- Next gate: compute the six frozen pre-T features, feature-family missingness, clustered power/precision, then case/control fingerprint test only if data quality permits. No economic outcome analysis or Phase 3B.
