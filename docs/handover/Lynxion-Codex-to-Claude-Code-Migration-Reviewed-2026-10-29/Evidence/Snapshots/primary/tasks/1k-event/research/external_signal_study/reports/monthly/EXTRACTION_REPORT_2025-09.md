# LYNXION FORENSIC EXTRACTION REPORT — 2025-09

## 1. Scope
This report documents the forensic research-data extraction from external trading-signal archives (`jan-jul/result.json` and `aug/result.json`). In strict accordance with Lynxion forensic research protocols, this task operates in BLIND RESEARCH DATA PREPARATION mode only. No trading strategy discovery, alpha optimization, reverse engineering, profitability ranking, or production modifications were performed.

## 2. Raw Evidence Processed
- **Raw source messages processed**: 297
- **Screenshots/photos processed & indexed**: 146
- **OCR and CV feature extraction records**: 1050
- **Stable evidence IDs generated**: `EV-000001` to `EV-002051`

## 3. Collection Limitations
The raw evidence was collected from Telegram channel desktop exports without full API access. Known limitations observed and preserved include: varying message verbosity, informal Persian trading vernacular, screenshot compression artifacts, missing explicit stop levels in favor of percentage risk, and unparented follow-up messages.

## 4. Date Coverage
- **Earliest source timestamp**: `2025-09-01T06:39:51`
- **Latest source timestamp**: `2025-09-30T19:37:33`
- **Target period**: 2025-09

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
- **SIGNAL**: 34
- **FOLLOW_UP**: 53
- **OUTCOME**: 73
- **MARKET_COMMENTARY**: 47
- **NO_TRADE_COMMENTARY**: 0
- **EDUCATIONAL**: 2
- **REPOST**: 0
- **DUPLICATE**: 0
- **UNKNOWN**: 88

## 7. Unique Signal Count
- **Total unique signals extracted**: `34`

## 8. LONG / SHORT Counts
- **LONG signals**: `22` (64.7%)
- **SHORT signals**: `12` (35.3%)
- **UNKNOWN side**: `0`

## 9. Strategy-Label Counts
Distribution of strategy identifiers identified in source evidence:
- **BombiClub**: `34` (100.0%)

## 10. Outcome Coverage
Reported trade outcomes resolved from explicit textual and visual evidence:
- **WIN (Full Target / Profit Exit)**: `14`
- **PARTIAL_WIN (TP1/TP2 hit, partial take)**: `11`
- **BREAKEVEN (Risk-free stop at entry)**: `0`
- **LOSS (Stop hit / loss closed)**: `0`
- **OPEN (No final outcome reported)**: `9`
- **UNKNOWN / AMBIGUOUS**: `0`
- **Outcome Resolution Rate**: `73.5%`

## 11. Missing-Data Statistics
Preservation of missing information (`UNKNOWN` used rather than imputed):
- **Signals with entry price `UNKNOWN`**: `4` (11.8%)
- **Signals with stop loss `UNKNOWN`**: `4` (11.8%)
- **Signals with TP1 `UNKNOWN`**: `31` (91.2%)

## 12. Duplicate / Repost Statistics
- **Signals paired with bot alerts / updates**: `6`
- **Exact duplicates identified & lineage preserved**: `0`
- Reposts and updates were appended to existing signal source evidence rather than creating phantom independent trades.

## 13. Signal-Follow-Up Linking Quality
- **HIGH Confidence (Direct Telegram reply tree linkage)**: `26`
- **MEDIUM Confidence (Single unambiguous symbol match within active window)**: `2`
- **LOW / UNRESOLVED (Candidate ambiguity recorded to unresolved queue)**: `6`
- **Total items in unresolved link queue**: `18`

## 14. Timestamp Quality
- **Valid ISO-8601 published timestamps**: `34 / 34` (100.0%)
- **Timestamp ambiguity flags**: `0`

## 15. Price-Field Quality
- **Explicit numeric entry price verified**: `30`
- **Explicit numeric stop loss verified**: `30`
- **Explicit numeric take-profit verified**: `3`
- Deterministic R:R geometry calculated strictly when valid positive numeric entry and SL were present.

## 16. Manual-Review Queue
- **Signals flagged for manual review**: `1`
  - `SIG-000110`: STOP_ABOVE_ENTRY_LONG (BONKUSDT LONG)

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