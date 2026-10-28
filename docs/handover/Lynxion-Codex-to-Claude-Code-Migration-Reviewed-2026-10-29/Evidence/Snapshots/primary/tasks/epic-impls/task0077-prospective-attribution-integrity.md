# TASK0077 — Prospective Attribution Integrity

**Status:** IMPLEMENTED — runtime verification pending deployment

## Scope

Preserve SL/TP, confidence, regime, strategy, and risk metadata from intent to
exchange order history without changing trading decisions.

## Acceptance Criteria

- New journal intents contain canonical SL/TP values and decision metadata.
- The journal reference, client order ID, and exchange order ID resolve to the same metadata.
- A completed post-deployment CSV row contains all required attribution fields and finite R metrics.
- No strategy/risk behavior changes.

## Evidence

- Collector and broker metadata propagation implemented.
- Unit coverage is green; live runtime evidence requires the updated service to process a new completed trade.
