# Lynxion External Signal Temporal Evolution Forensic Review — Data Quality & Integrity Report

**Document**: `V2_DATA_QUALITY_REPORT.md`  
**Review Mode**: Evidence-First Forensic Audit & Re-Review (V2)  
**Safety & Governance Status**: Strict Compliance (Zero Profitability Claims, Immutability Guarantee Enforced)

---

## 1. Data Ingestion Census & Pipeline Lineage

The V2 forensic re-review ingested and cross-reconciled all available raw Telegram export files and multimodal image assets. Full data integrity was established through 100% census reconciliation:

| Data Source | Entity Name | Channel ID | Raw Messages | Service Actions | Total Items | Time Window |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `jan-jul/result.json` | BombiClub | `2276250505` | 1,483 | 1 | 1,484 | 2024-11-17 to 2025-12-29 |
| `aug/result.json` | 1K EVENT 💣 | `3948690389` | 566 | 1 | 567 | 2026-07-29 to 2026-09-17 |
| **Combined Census** | — | — | **2,049** | **2** | **2,051** | **2024-11-17 to 2026-09-17** |

Every raw message was mapped to a unique, immutable evidence identifier (`EV-000001` through `EV-002051`). Timestamp and sequence reconciliation between the raw JSON exports and the PASS-1 index achieved a **100.0% exact match** (2,051 / 2,051 items).

---

## 2. Multimodal Image & Computer Vision Audit

- **Total Linked Screenshots**: 1,050 image files stored under `jan-jul/photos/` and `aug/photos/`.
- **Cached Asset Audit**: `research/external_signal_study/cache/image_features.json` was verified intact (SHA-256: `5f488bd2d12ced85...`).
- **Feature Extraction Metrics**:
  - **Chart Detection**: 1,012 images (96.4%) classified as trading charts.
  - **PnL Card Detection**: 38 images (3.6%) identified as exchange order/PnL outcome cards.
  - **TradingView Position Tool Contour Detection**: 62 images verified with active Long/Short Position Tool green/red bounding boxes.
  - **Horizontal Price Levels**: Present in 98.2% of chart images.
  - **Trendlines**: Present in 31.5% of chart images.
  - **OCR Timeframe Extraction**: Successfully resolved timeframes for 89.0% of 1K_EVENT charts and 47.2% of BombiClub charts.

---

## 3. PASS-1 Baseline Audit & Discrepancies

V2 audited all 306 signals extracted during the PASS-1 baseline. Six discrete discrepancies were formally documented in `research/external_signal_study/temporal_forensic_v2/review/pass1_discrepancies.csv`. Under strict immutability rules, PASS-1 files were **NOT** overwritten or modified; discrepancies are recorded solely in V2:

### 3.1 Discrepancy Summary Table

| ID | Evidence ID | Signal ID | Field Affected | PASS-1 Baseline Value | V2 Audited Finding | Discrepancy Type |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `DISC-001` | `EV-000060` | `SIG-000307` | Signal Detection | `classification=OUTCOME` (omitted from `signals.csv`) | Actionable spot buy signal on SONIC at 0.6 USD, TP1 0.74 USD | `MISSED_SIGNAL` |
| `DISC-002` | `EV-001356` | `SIG-000179` | Decision Origin | Paired with manual setup `EV-001357` as composite signal | Separated into `BOT_ALERT` (RadarX TFS bot alert) and manual follow-up | `BOT_ATTRIBUTION_SPLIT` |
| `DISC-003` | `EV-001392` | `SIG-000185` | Decision Origin | Paired with manual setup `EV-001393` as composite signal | Separated into `BOT_ALERT` (RadarX HMT bot alert) and manual follow-up | `BOT_ATTRIBUTION_SPLIT` |
| `DISC-004` | `EV-001485` ff. | `SIG-000207-306` | Strategy Label | `strategy_label = 1K_EVENT` across all 100 signals | `observed_generation = 1K_EVENT`; underlying engine disclosed as `HMT` / `TFS` | `PROVENANCE_STRATEGY_DISCLOSURE` |
| `DISC-005` | `EV-001485` ff. | `SIG-000207-306` | Position Box Flag | `long_short_position_box_present = False` (0/100) | `long_short_position_box_present = True` for 62 signals verified via OpenCV | `VISUAL_FEATURE_ENRICHMENT` |
| `DISC-006` | `EV-001396` | `NONE` | Decision Origin | `classification=MARKET_COMMENTARY` | `decision_origin = HUMAN_OVERRIDE` (manual veto of bot BTC buy before CPI) | `SEMANTIC_OVERRIDE_CLASSIFICATION` |

---

## 4. Archive Gaps & Temporal Censoring Analysis

The longitudinal analysis reveals two massive temporal hiatuses in the provided archive where zero messages were recorded:

```
2024-11      2025-02   2025-05                     2025-12   2026-07         2026-09
  [ Early Bombi ]       [ Standardized BombiClub ]  [ RadarX ]       [ 1K_EVENT ]
  ==============| GAP 1 |==========================|=========| GAP 2 |===========>
                70 days                              213 days
               (Mar-Apr 25)                         (Jan-Jul 26)
```

### 4.1 Gap 1: Spring 2025 Hiatus (70 Calendar Days)
- **Bounds**: 2025-02-20 (`EV-000062`) to 2025-05-01 (`EV-000063`).
- **Nature**: Complete cessation of Telegram channel activity in the provided export.
- **Impact**: Preceded the immediate adoption of the rigid 5-line template in May 2025.

### 4.2 Gap 2: Winter/Spring 2026 Hiatus (213 Calendar Days)
- **Bounds**: 2025-12-29 (`EV-001484`) to 2026-07-29 (`EV-001485`).
- **Nature**: The BombiClub export terminates on December 29, 2025. The 1K_EVENT export begins on July 29, 2026.
- **Impact**: It is empirically impossible to determine whether the system was suspended, tested privately, or operated in another channel during this 7-month window.

---

## 5. Outcome Reporting Asymmetry & Censoring Bias

A critical data quality finding is the severe asymmetry in outcome reporting by the channel author:
- **Winning Trade Celebration**: Target achievements (TP1, TP2, TP3) are aggressively announced with celebratory phrases (`بررررکت`, `فول تارگت`, `دیدید چطور شکار کردیم`).
- **Losing Trade Omission**: Trades that move against the entry frequently receive zero follow-up messages, expiring silently into subsequent market commentary.
- **Survivorship Bias**: As a result, computing raw win rates from Telegram outcome messages produces a heavily inflated, invalid metric.
- **Governance Requirement**: Under V2 protocol, outcome status is recorded strictly for provenance auditing; **win-rate claims and profitability rankings are strictly FORBIDDEN**.

---

## 6. PASS-1 Immutability Verification

Before publishing V2, all PASS-1 baseline artifacts were audited via SHA-256 cryptographic hashing. Zero bytes were modified:

- `extracted/signals.csv`: `ba4bc3ad4ce5ddb774494c1bdc388a959bd507fb5ff932befb592ceeffa86bdb` (MATCH)
- `extracted/signals.jsonl`: `628c2584c0485a30ed20e6f075d5c1b6e117aa2f3e50ea48eb1d3bd50a2a1071` (MATCH)
- `extracted/evidence_index.csv`: `3c915ac845e3174f0485ff301f4aae4b815d3b3efc4fb121302005a7a599775b` (MATCH)
- `extracted/extraction_quality.csv`: `9b2778ff87c47528ef3d629db35d574f3600ac07fe93f4b6e09be528b6a44f45` (MATCH)
- `extracted/unresolved_links.csv`: `e8be807f6926e407e6fff4807f2cf50e6464247341fa18da4c9239f263a9e664` (MATCH)
- `reports/EXTRACTION_REPORT.md`: `696cab356f8a76bbc1c04dbe9f2c057431687d8bc54eb649ce2ee20cb2110218` (MATCH)

All V2 artifacts are isolated under `research/external_signal_study/temporal_forensic_v2/`.
