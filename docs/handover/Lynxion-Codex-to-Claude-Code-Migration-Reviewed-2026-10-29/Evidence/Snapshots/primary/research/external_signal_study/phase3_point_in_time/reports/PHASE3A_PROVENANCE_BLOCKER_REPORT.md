# Phase 3A-0 — raw-source provenance audit (interim)

**Scope:** provenance and point-in-time eligibility only. No future returns, MFE/MAE, TP/SL, PnL, or fingerprint test was opened. PASS-1/V2, Lynxion production, and frozen cohorts were not modified. This report does **not** freeze a final HMT/TFS cohort.

## Verified inputs and lineage

- The V2 source script points to `/Users/mojtaba.rahbari/Desktop/orders-1k-event`. Both original Telegram exports, the image-feature cache, and photo directories are present. Raw JSON hashes exactly match `v2_run_manifest.md`: `jan-jul/result.json` = `8aad14b76577505c8f1d0e2719d3a51ea1c45c5e6c21370e7cc0450b4c6859cd` (1,484 messages); `aug/result.json` = `5a091af3fe93fcd0965fbaea143a07fec96f968266ba209e98c0b95df7541300` (567 messages); `image_features.json` = `5f488bd2d12ced856631da4f0003e76cf6151f8ba97505d40790547e8bb63c9d`.
- [Upstream inventory](../manifests/upstream_inventory.csv) hashes 1,898 available files: 1,830 raw photos, 3 raw JSON inputs, and 65 PASS-1/V2 files. This is an availability census, **not** a claim that every photo was linked or used in V2; V2 reports 1,050 linked/cached image profiles. The inventory includes source code/reports and original extracted artifacts. Re-running `src/audit_phase3a0.py` reproduces the census and the two audit CSVs.
- The [100-signal audit](../diagnostics/point_in_time_audit.csv) and [164-link lineage](../extracted/signal_evidence_lineage.csv) reconcile every linked EV ID to the 2,051-row V2 manifest and its original raw message timestamp. There are 100 at-signal links, 64 post-signal links, and zero pre-signal links in the existing `source_evidence_ids` field. **42 signals** have one or more later links. These are legitimate follow-up/provenance links, not inherently faulty data.
- Feature quarantine rule: `max_input_timestamp <= signal_timestamp`. Every one of the 64 post-signal links is marked `NO_QUARANTINED` in the lineage file. This is a prospective feature-input prohibition; the provenance links are preserved. The two TFS-disclosure messages are retrospective labels only, never at-signal market features.
- All 100 rows have a timestamp, symbol string, LONG/SHORT side, and at-signal evidence under the V2 first-message anchor. Thus **100/100 pass the minimal structural point-in-time check**; **89/100 have a non-UNKNOWN extracted timeframe**. One of the 11 missing timeframes is recoverable from the raw LDO photo (15m), so a later, explicitly corrected derived table could reach **90/100** on this field. The current unmodified V2 table remains 89/100. Structural eligibility does **not** establish economic validity or correct engine attribution.

## Raw HMT/TFS disclosure and conflicts

The authoritative 1K EVENT Telegram JSON contains message **579** (2026-09-13 21:54:04), explicitly naming LDO; message **580** (21:55:16), replying to 579 with a 15m setup and an LDO/USDT 15m screenshot; message **592** (2026-09-14 15:17:58), SEI 4h context; message **593** (15:19:50), a 15m SEI setup replying to 592; message **594** (15:22:59), replying directly to LDO message 580 and explicitly saying SEI used the same strategy as LDO last night, called TFS; and message **596** (15:25:52), replying to 594 and saying that setups posted in the channel during the past month were HMT except “these last two,” which were TFS. The message/reply chain unambiguously identifies the **Sep 13 LDO and Sep 14 SEI events** as the two exceptions. It does **not** identify the later Sep 16 LDO row as TFS.

The [discrepancy table](../diagnostics/provenance_discrepancies.csv) records ten conflicts and handling decisions. In particular:

| Issue | Resolution from authority order |
| --- | --- |
| Report `EV-002075`–`EV-002080` | These IDs do not exist in the V2 manifest, which ends at `EV-002051`. Raw messages 591/592/593/594/596 correspond to `EV-002020/21/22/23/24`. This is a report/manual-review reference-numbering error; it does not imply missing raw messages. |
| Review `SIG-000297/298` = LDO/SEI | The actual rows are ETH/ZEC on Sep 11. The relevant rows are `SIG-000300` (Sep 13 LDO event, incorrectly extracted as `LOO`) and `SIG-000301` (Sep 14 SEI). These are manually authored review signal-ID errors, with an additional genuine LDO symbol/timeframe extraction defect in `SIG-000300`. |
| Direct vs interval HMT | No individual 1K_EVENT HMT engine label is present at event time. The raw operator statement supports **retrospective interval-level** HMT attribution only. “Past month” lacks an exact date/time start. Earlier August and post-Sep-14 events must not be swept into HMT. |
| SEI event anchor | V2 anchors `SIG-000301` at the 4h context message 592; the 15m setup arrived in message 593, 112 seconds later. Using 593 as a feature at 592 would leak future information. Event-time choice must be explicitly frozen at preregistration; the 3A-0 audit uses the conservative earlier anchor. |
| Position management / discretion | V2 narrative channel policy, semantic prose tags, and row-level matrix rates describe different constructs. Neither implies that each signal carried that rule. Do not silently convert these into row features. |

## Attribution feasibility, not a frozen cohort

- `STRICT_HMT_COHORT`: **0** directly/high-confidence per-event HMT labels in these 100 rows. This is a source-documentation limit, not evidence that HMT made no signals.
- `EXPANDED_HMT_COHORT`: a **conservative provisional pool of 64 events** from 2026-08-16 00:00 through immediately before the Sep 13 LDO event, excluding both TFS exceptions. The Aug 16 cutoff is deliberately inside any ordinary interpretation of “past month” at Sep 14; the exact start remains a sensitivity/definition issue to freeze before evaluation. Of these, 59 have non-UNKNOWN V2 timeframe. This is interval-level retrospective attribution, **not direct engine proof** and **not a final cohort**.
- `TFS_EXPLORATORY_COHORT`: exactly **2 verified retrospective exceptions**, `SIG-000300` (LDO; V2 symbol/timeframe need derived correction) and `SIG-000301` (SEI; event-anchor ambiguity documented). Not an inference about later LDO or later signals.
- `UNKNOWN_ENGINE_COHORT`: the remaining **34** rows under this conservative partition. This includes earlier-August and post-disclosure events; no engine is imputed from surrounding rows or report prose.

## PRELIMINARY identifiability and power

The maximal nominal 1K_EVENT sample is 100 (89 with V2 timeframes; 90 only after explicit raw-derived correction). A conservative HMT interval offers at most 64 nominal events/59 with V2 timeframe; TFS offers 2 and is unsuitable for a separate effect test. Multiple signals on the same market day, symbol, or common market move are not independent. Matched controls would not multiply the independent sample. Effective N, variance, class balance, image availability, and matched-control availability remain **UNKNOWN** until a protocol defines clustering and data requirements. As an optimistic orientation only, a single paired standardized mean difference would require roughly `2.8/sqrt(N_eff)`: 0.28 at an impossible best-case independent N=100, 0.35 at N=64, and 0.40 at N=50, before multiple-testing or market-data losses. This is **not** a formal power claim and no economic outcome was examined.

## Decision and next boundary

Raw files required from the operator: **none**. The raw statement/reply chain resolves the mistaken EV/SIG references and identifies the two TFS exceptions. The LDO symbol/timeframe extraction error and SEI time-anchor ambiguity are explicitly identified and can be corrected or conservatively specified in a **new derived preregistration**, without touching PASS-1/V2. Final preregistration can safely be drafted **only if** it freezes the derived correction, event-time policy, conservative HMT interval (including boundary sensitivity), UNKNOWN bucket, and post-signal quarantine *before* opening any outcome/market-return data. This report itself does not take that next step and does not authorize a fingerprint test.

**Final interim status:** `PHASE3A_PROVENANCE_RESOLVED_READY_FOR_PREREGISTRATION`
