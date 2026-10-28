# LYNXION FORENSIC EXTRACTION REPORT — 2025-12

## 1. Scope
This report documents the forensic research-data extraction from external trading-signal archives (`jan-jul/result.json` and `aug/result.json`). In strict accordance with Lynxion forensic research protocols, this task operates in BLIND RESEARCH DATA PREPARATION mode only. No trading strategy discovery, alpha optimization, reverse engineering, profitability ranking, or production modifications were performed.

## 2. Raw Evidence Processed
- **Raw source messages processed**: 227
- **Screenshots/photos processed & indexed**: 100
- **OCR and CV feature extraction records**: 1050
- **Stable evidence IDs generated**: `EV-000001` to `EV-002051`

## 3. Collection Limitations
The raw evidence was collected from Telegram channel desktop exports without full API access. Known limitations observed and preserved include: varying message verbosity, informal Persian trading vernacular, screenshot compression artifacts, missing explicit stop levels in favor of percentage risk, and unparented follow-up messages.

## 4. Date Coverage
- **Earliest source timestamp**: `2025-12-01T07:12:47`
- **Latest source timestamp**: `2025-12-29T09:32:02`
- **Target period**: 2025-12

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
- **SIGNAL**: 40
- **FOLLOW_UP**: 26
- **OUTCOME**: 37
- **MARKET_COMMENTARY**: 53
- **NO_TRADE_COMMENTARY**: 0
- **EDUCATIONAL**: 2
- **REPOST**: 0
- **DUPLICATE**: 0
- **UNKNOWN**: 69

## 7. Unique Signal Count
- **Total unique signals extracted**: `34`

## 8. LONG / SHORT Counts
- **LONG signals**: `19` (55.9%)
- **SHORT signals**: `15` (44.1%)
- **UNKNOWN side**: `0`

## 9. Strategy-Label Counts
Distribution of strategy identifiers identified in source evidence:
- **TFS**: `18` (52.9%)
- **HMT**: `10` (29.4%)
- **BombiClub**: `5` (14.7%)
- **RadarX**: `1` (2.9%)

## 10. Outcome Coverage
Reported trade outcomes resolved from explicit textual and visual evidence:
- **WIN (Full Target / Profit Exit)**: `9`
- **PARTIAL_WIN (TP1/TP2 hit, partial take)**: `4`
- **BREAKEVEN (Risk-free stop at entry)**: `0`
- **LOSS (Stop hit / loss closed)**: `1`
- **OPEN (No final outcome reported)**: `20`
- **UNKNOWN / AMBIGUOUS**: `0`
- **Outcome Resolution Rate**: `41.2%`

## 11. Missing-Data Statistics
Preservation of missing information (`UNKNOWN` used rather than imputed):
- **Signals with entry price `UNKNOWN`**: `26` (76.5%)
- **Signals with stop loss `UNKNOWN`**: `26` (76.5%)
- **Signals with TP1 `UNKNOWN`**: `26` (76.5%)

## 12. Duplicate / Repost Statistics
- **Signals paired with bot alerts / updates**: `6`
- **Exact duplicates identified & lineage preserved**: `0`
- Reposts and updates were appended to existing signal source evidence rather than creating phantom independent trades.

## 13. Signal-Follow-Up Linking Quality
- **HIGH Confidence (Direct Telegram reply tree linkage)**: `13`
- **MEDIUM Confidence (Single unambiguous symbol match within active window)**: `1`
- **LOW / UNRESOLVED (Candidate ambiguity recorded to unresolved queue)**: `20`
- **Total items in unresolved link queue**: `16`

## 14. Timestamp Quality
- **Valid ISO-8601 published timestamps**: `34 / 34` (100.0%)
- **Timestamp ambiguity flags**: `0`

## 15. Price-Field Quality
- **Explicit numeric entry price verified**: `8`
- **Explicit numeric stop loss verified**: `8`
- **Explicit numeric take-profit verified**: `8`
- Deterministic R:R geometry calculated strictly when valid positive numeric entry and SL were present.

## 16. Manual-Review Queue
- **Signals flagged for manual review**: `1`
  - `SIG-000200`: TP_BELOW_ENTRY_LONG (DOGEUSDT LONG)

## 17. Chronological Gaps
Identified gaps in source archive:
- No intra-month gaps detected exceeding 7 days.

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