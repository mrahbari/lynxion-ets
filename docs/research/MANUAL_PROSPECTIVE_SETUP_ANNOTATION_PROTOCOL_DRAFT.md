# Manual prospective setup annotation — design draft, inactive

Status: **INDEPENDENT_LEAD / NOT_YET_TESTED**. This document is a schema and governance design only. It does not define a qualifying setup, activate observation, label outcomes, or authorize an Edge study. Microstructure Pilot-2 remains the sole primary measurement program.

## Activation prerequisites (not yet met)

Before the first observation, a separate, committed and hashed protocol must freeze the venue, point-in-time symbol universe, exact candidate inclusion rule, observer, scheduled UTC sessions, source/screenshot capture method, clock semantics, missing-data treatment, and rule for missed or interrupted sessions. The rule must be executable without knowing any later price or trade result. A complete candidate denominator must be logged, including candidates the operator declines to trade. Outcomes, analysis plan, costs, minimum independent sample and confirmation cohort require their own preregistration and operator scientific decision before labeling/testing. **No collection starts under this draft.**

## Separate append-only record types

| Record | Fields to preserve at creation | Integrity rule |
|---|---|---|
| Session | protocol ID/hash; observer; venue/source; UTC planned start/stop; universe snapshot/reference; acquisition clock; start/end actuality; interruptions and reasons | Created before looking for candidates. Keep cancelled and empty sessions. |
| Candidate observation | unique candidate ID and session ID; observed UTC and local receipt time; symbol/contract; point-in-time rank reference if applicable; raw market/participation/setup-state references; screenshot/raw path and SHA-256; exact contemporaneous human reasoning; trade/no-trade intent; missing fields and provenance | Write once before later outcome information. No hindsight edits; append a correction with author, time, original hash and reason. Retain rejected candidates. |
| Disposition | candidate ID; contemporaneous decision (`TRADE`, `NO_TRADE`, `FAILED_SETUP`, `NO_FILL` or pending); decision time; contemporaneous reason; order/fill reference only if a separately authorized trading workflow exists | Absence of a trade is not absence of a candidate. This draft does not authorize orders or authenticated access. |
| Later outcome label | candidate ID; label time; source/provenance; frozen labeling-rule ID; label including `WINNER`, `LOSER`, `NO_MOVE`, `UNRESOLVED/CENSORED` where applicable | Stored separately after the frozen outcome protocol, never written back into the original observation or reasoning. These labels do not automatically imply economic PnL. |

Each append should have an immutable raw representation, content hash, stable candidate/session key, previous-record hash or equivalent tamper-evident manifest, and UTC write time. Screenshot evidence should retain original bytes and hashes. Missing, invalid, and no-screenshot observations remain in the denominator with explicit flags; do not delete inconvenient entries. Access to later labels should be separated from observation capture when feasible.

## Bias controls and open design choices

The future inclusion rule must cover **all** eligible opportunities within each frozen window, not only visually appealing examples. Preserve winners, losers, no-trades, failed setups, no-fills, no-moves, missing-data cases, and unresolved/censored records. Record candidate clustering by UTC day, symbol and common market episode; do not count screenshot count as independent sample size. Hold any training/exploratory cohort apart from an unopened confirmation cohort.

The exact setup, threshold, rank definition, venue, timeframe, windows, sample floor, outcome, economic cost model and hypothesis remain **UNKNOWN / UNSELECTED**. Choosing or activating them is a later scientific decision, not a mechanical continuation of this schema.
