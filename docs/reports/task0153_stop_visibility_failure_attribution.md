# TASK-0153 Stop Visibility Failure Attribution — Source Evidence Unit

## Verdict

`PARTIAL_ATTRIBUTION`

## Facts

- Placement uses Swap V2 `POST /openApi/swap/v2/trade/order` with `STOP_MARKET`, `stopPrice`,
  `positionSide`, `closePosition=true`, and `workingType=MARK_PRICE`.
- Any response with `code == 0` is returned as `success=true`; a missing nested `orderId` does not
  invalidate acceptance.
- Visibility uses Swap V2 `GET /openApi/swap/v2/trade/openOrders`, then matches order type, side,
  position side, and stop-price tolerance. It does not correlate the placement `order_id`.
- `get_pending_orders` returns the same empty list for a genuinely empty order book, nonzero API
  response, malformed success payload, and caught transport/parser exception.
- The frozen event snapshot contains repeated accepted-but-not-visible outcomes for every recorded
  ADA attempt. NEAR contains both explicit price rejection and accepted-but-not-visible outcomes;
  these are separate causal paths. BNB, DOGE, PROM, TRX, and XRP each have observed verified paths.

## Confirmed Observability Defects

1. `success=true` is not identity-complete because `order_id=None` is admitted.
2. A failed pending-order query is observationally indistinguishable from a successful empty query.
3. Visibility can match an order without any exchange order ID and cannot prove it is the order
   returned by the corresponding placement.

Disconnected tests reproduce all three source semantics without network or broker calls.

## Unknown

The existing evidence cannot distinguish whether ADA/NEAR failures are caused by exchange
non-persistence, query errors, schema variation, wrong account/product visibility, or a genuine
absence after acceptance. Therefore the exchange-side root cause is not confirmed.

## Next Boundary

A separate minimal implementation task may require non-empty placement identity, preserve pending-
query status/error evidence, and verify by returned order ID before attribute fallback. It must not
change stop thresholds, retry counts, timing, or account settings, and runtime activation remains a
separate approval gate.

