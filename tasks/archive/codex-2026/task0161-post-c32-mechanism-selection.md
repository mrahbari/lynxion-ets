# TASK-0161 — Post-C32 Mechanism Selection

**Status:** COMPLETE

## Objective

Select one genuinely new, point-in-time mechanism after C-32 became data-blocked, without changing
its venue/timestamp contract or recombining opened historical outcomes.

## Decision

Admit a **prospective Binance forced-liquidation exhaustion** mechanism for preregistration. The
official public USD-M all-market liquidation stream emits event time, trade time, symbol, side,
average price, original/final quantity, status, and the UM/CM discriminator. It needs no account or
broker path and supplies the causal event identity missing from the earlier archive feasibility
study.

This mechanism is distinct from C-27: C-27 inferred aggressor exhaustion from ordinary aggregate
trades, while the new direction uses exchange-labelled forced-liquidation orders. Its economic
claim is that an exceptional, completed cluster of forced selling or buying temporarily exhausts
one side and creates a multi-hour reversal capable of clearing conservative futures friction.

## Source Constraint

The official stream is censored: for each symbol it publishes only the latest liquidation order
within each 1,000-ms interval. Any candidate must treat the feed as a snapshot measure, never as
complete liquidation volume or count, and must retain `st=1` USD-M observations only.

Official reference:
`https://developers.binance.com/docs/derivatives/usds-margined-futures/websocket-market-streams/All-Market-Liquidation-Order-Streams`

## Next Unit

TASK-0162 must preregister C-33 before any stream connection or conditional outcome. It must freeze
the prospective boundary, exact event aggregation and censoring interpretation, public price and
funding alignment, one direction, execution horizon, costs, missing-stream heartbeat rules,
minimum samples, temporal folds, clustered uncertainty, breadth, concentration, drawdown, and
stress gates. No historical backfill, authentication, order, broker, or runtime path is permitted.

## Result

One independent prospective direction is admitted for preregistration only. No endpoint was
connected, no observation or outcome was opened, and no edge is claimed.
