Runtime Remediation Implementation (Verified Issues Only)

Implement only the verified runtime defects.

Architecture is frozen.

No redesign.

No new abstractions.

No responsibility changes.

No speculative improvements.

Every modification must preserve the current production architecture.

Issue 1 — PendingOrdersTracker

Status: VERIFIED

Root cause:

PendingOrdersTracker stores an internal order id while BingX removal uses the exchange order id.

Additionally stale entries are never pruned.

Required implementation:

Fix the identifier mismatch.
Ensure add/remove use the same identifier.
Add automatic TTL cleanup before every pending lookup.
Preserve current public API.
Add regression tests proving:
successful removal
stale cleanup
continuous trading after many hours
no duplicate orders
Issue 2 — Confidence

Status:

Root cause VERIFIED.

Implementation NOT VERIFIED.

Do NOT introduce

0.60 + 0.35 * abs(setup.score)

or any other synthetic formula.

Instead:

Trace the origin of confidence.

If the strategy already computes confidence internally,

use that value.

If no confidence exists,

leave runtime behaviour unchanged and expose a TODO explaining that confidence generation belongs to the strategy logic rather than inventing a derived value.

No fabricated confidence formulas are allowed.

Issue 3 — Execution Timestamp

Status: VERIFIED

Replace notification timestamp with the actual execution timestamp.

The timestamp must represent the moment the order was accepted/executed by the broker.

Do not reuse signal timestamps.

Regression test required.

Issue 4 — Telegram Entry Price

Status: VERIFIED

Replace signal price in notifications with the actual exchange fill price.

Use avgPrice when available.

If avgPrice is unavailable,

fallback deterministically and log the reason.

Journal and Telegram must display identical execution prices.

Regression tests required.

Issue 5 — SL/TP Recalibration

Status:

Verified only for strategies that define exits as relative distances.

Before implementation:

Inspect every production strategy.

Classify each strategy as one of:

percentage distance
ATR distance
volatility distance
structure level
liquidity level
support/resistance
swing high/low
fixed price

Only recalibrate strategies whose exits are distance-based.

Do NOT recalibrate strategies using structural price levels.

Generate a compatibility table before applying the patch.

After implementation:

Regression tests must prove:

intended R:R preserved
ATR scaling preserved
no behaviour change for structural exits
Explicitly Reject

Do NOT implement:

strategy redesign
break-even stop
expectancy optimization
signal filtering changes
risk model modifications

Those remain outside the scope.

Deliverables

Provide:

Files modified
Exact code diff
New unit tests
Why each change is safe
Regression impact
Confirmation that architecture and ownership boundaries remain unchanged