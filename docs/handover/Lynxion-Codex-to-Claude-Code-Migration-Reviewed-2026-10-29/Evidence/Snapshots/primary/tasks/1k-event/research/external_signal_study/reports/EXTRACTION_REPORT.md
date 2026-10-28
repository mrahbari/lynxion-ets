# LYNXION EXTERNAL SIGNAL FORENSIC EXTRACTION REPORT

## 1. Scope
This report documents the forensic research-data extraction from external trading-signal archives (`jan-jul/result.json` and `aug/result.json`). In strict accordance with Lynxion forensic research protocols, this task operates in BLIND RESEARCH DATA PREPARATION mode only. No trading strategy discovery, alpha optimization, reverse engineering, profitability ranking, or production modifications were performed.

## 2. Raw Evidence Processed
- **Raw source messages processed**: 2051
- **Screenshots/photos processed & indexed**: 1050
- **OCR and CV feature extraction records**: 1050
- **Stable evidence IDs generated**: `EV-000001` to `EV-002051`

## 3. Collection Limitations
The raw evidence was collected from Telegram channel desktop exports without full API access. Known limitations observed and preserved include: varying message verbosity, informal Persian trading vernacular, screenshot compression artifacts, missing explicit stop levels in favor of percentage risk, and unparented follow-up messages.

## 4. Date Coverage
- **Earliest source timestamp**: `2024-11-17T10:40:19`
- **Latest source timestamp**: `2026-09-17T13:08:17`
- **Target period**: Full Archive

## 5. Extraction Methodology
Extraction followed a deterministic 7-stage blind forensic pipeline:
1. Immutable Evidence Ingestion & SHA-256 Hashing
2. Parallel Optical Character Recognition (Tesseract) & OpenCV Contour/Color Analysis
3. Lexical & Semantic Message Classification into 9 controlled classes
4. Point-in-Time Schema Normalization with strict look-ahead isolation
5. Deterministic Signal <-> Follow-up Reply Tree Graph Linking
6. Rigorous Deterministic Geometry Calculation (applied only when entry, stop, and targets are verifiable positive numbers)
7. Quality Control Verification across 15 automated validation checks.

## 6. Message Classification Counts
Distribution of source messages across controlled categories:
- **SIGNAL**: 312
- **FOLLOW_UP**: 245
- **OUTCOME**: 395
- **MARKET_COMMENTARY**: 390
- **NO_TRADE_COMMENTARY**: 3
- **EDUCATIONAL**: 76
- **REPOST**: 0
- **DUPLICATE**: 0
- **UNKNOWN**: 630

## 7. Unique Signal Count
- **Total unique signals extracted**: `306`

## 8. LONG / SHORT Counts
- **LONG signals**: `169` (55.2%)
- **SHORT signals**: `137` (44.8%)
- **UNKNOWN side**: `0`

## 9. Strategy-Label Counts
Distribution of strategy identifiers identified in source evidence:
- **BombiClub**: `177` (57.8%)
- **1K_EVENT**: `100` (32.7%)
- **TFS**: `18` (5.9%)
- **HMT**: `10` (3.3%)
- **RadarX**: `1` (0.3%)

## 10. Outcome Coverage
Reported trade outcomes resolved from explicit textual and visual evidence:
- **WIN (Full Target / Profit Exit)**: `94`
- **PARTIAL_WIN (TP1/TP2 hit, partial take)**: `49`
- **BREAKEVEN (Risk-free stop at entry)**: `13`
- **LOSS (Stop hit / loss closed)**: `15`
- **OPEN (No final outcome reported)**: `135`
- **UNKNOWN / AMBIGUOUS**: `0`
- **Outcome Resolution Rate**: `55.9%`

## 11. Missing-Data Statistics
Preservation of missing information (`UNKNOWN` used rather than imputed):
- **Signals with entry price `UNKNOWN`**: `165` (53.9%)
- **Signals with stop loss `UNKNOWN`**: `170` (55.6%)
- **Signals with TP1 `UNKNOWN`**: `219` (71.6%)

## 12. Duplicate / Repost Statistics
- **Signals paired with bot alerts / updates**: `6`
- **Exact duplicates identified & lineage preserved**: `0`
- Reposts and updates were appended to existing signal source evidence rather than creating phantom independent trades.

## 13. Signal-Follow-Up Linking Quality
- **HIGH Confidence (Direct Telegram reply tree linkage)**: `175`
- **MEDIUM Confidence (Single unambiguous symbol match within active window)**: `10`
- **LOW / UNRESOLVED (Candidate ambiguity recorded to unresolved queue)**: `121`
- **Total items in unresolved link queue**: `76`

## 14. Timestamp Quality
- **Valid ISO-8601 published timestamps**: `306 / 306` (100.0%)
- **Timestamp ambiguity flags**: `0`

## 15. Price-Field Quality
- **Explicit numeric entry price verified**: `141`
- **Explicit numeric stop loss verified**: `136`
- **Explicit numeric take-profit verified**: `87`
- Deterministic R:R geometry calculated strictly when valid positive numeric entry and SL were present.

## 16. Manual-Review Queue
- **Signals flagged for manual review**: `2`
  - `SIG-000110`: STOP_ABOVE_ENTRY_LONG (BONKUSDT LONG)
  - `SIG-000200`: TP_BELOW_ENTRY_LONG (DOGEUSDT LONG)

## 17. Chronological Gaps
Identified gaps in source archive:
- ARCHIVE_GAP: 2025-03-01 to 2025-04-30 (0 messages in archive)
- ARCHIVE_GAP: 2026-01-01 to 2026-07-28 (0 messages between BombiClub archive and 1K EVENT archive)

## 18. Known Archive-Completeness Concerns
- **Two Major Archive Gaps**: Between March-April 2025 and January-July 2026, no messages were archived by the operator.
- **Implicit Market Entries**: Some setups specify `ورود مارکت` (Market Entry) without explicit dollar prices in the message body.
- **Unresolved Outcomes**: Follow-ups lacking direct reply identifiers and referencing ambiguous tickers were isolated in `unresolved_links.csv` to avoid look-ahead bias.

## 19. Files Generated
- `research/external_signal_study/extracted/signals.csv`
- `research/external_signal_study/extracted/signals.jsonl`
- `research/external_signal_study/extracted/evidence_index.csv`
- `research/external_signal_study/extracted/unresolved_links.csv`
- `research/external_signal_study/extracted/extraction_quality.csv`
- `research/external_signal_study/reports/EXTRACTION_REPORT.md`
- Monthly datasets under `research/external_signal_study/extracted/monthly/`
- Monthly extraction reports under `research/external_signal_study/reports/monthly/`

## 20. Final Dataset-Readiness Verdict
**DATASET_READY_FOR_FORENSIC_REVIEW**