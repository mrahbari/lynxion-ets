# Lynxion Leverage Correction Implementation Map

## Contract Touchpoints

- `domain/entities/order.py`: add optional requested leverage for general compatibility; BingX
  derivatives admission makes it mandatory and validated.
- `domain/entities/position.py`: preserve optional authoritative leverage and margin mode. Unknown
  values stay null; they are never replaced with 10x.
- `application/dto/mappers.py` and `application/factories/trading_factories.py`: preserve the new
  fields where input contracts provide them without inventing defaults.
- `application/services/dynamic_risk_service.py`: copy requested leverage when rebuilding a
  risk-adjusted order so risk sizing cannot erase the execution invariant.

## Live Order Creation Touchpoints

- `infrastructure/orchestrators/_auto_detection_execution.py`
- `infrastructure/messaging/event_system.py`

These are the direct runtime constructors found for new live-domain Orders. Each must source the
single validated configured value. Backtest and read-adapter constructors remain compatible and do
not gain exchange behavior.

`BingXBrokerAdapter.place_order` also clones the Order into a formatted temporary Order and must
preserve requested leverage; otherwise a valid upstream value is lost at the final adapter boundary.

## Authoritative BingX Boundary

- `_BingXBroker._assert_entry_admission` is the existing serialized, broker-backed entry boundary.
  Leverage establishment and verification belong inside this lock before the entry request.
- `_execute_order_after_admission` must remain unreachable on any leverage error. Tests should spy
  on it rather than call an exchange.
- `BingXBrokerAdapter.get_all_positions` must parse finite leverage and margin mode from the
  authoritative response into Position. A malformed individual position stays explicitly
  untrusted and must not silently become 10x.
- No leverage/margin API exists in the current adapter. Official BingX API references confirm:
  - `GET /openApi/swap/v2/trade/marginType` queries `marginType`; `POST` on the same path accepts
    `symbol` and `marginType` (`ISOLATED`, `CROSSED`, or `SEPARATE_ISOLATED`).
  - `GET /openApi/swap/v2/trade/leverage` accepts `symbol` and returns `longLeverage`,
    `shortLeverage`, their maxima, and available volume.
  - `POST /openApi/swap/v2/trade/leverage` accepts `symbol`, `side` (`LONG`, `SHORT`, or `BOTH`),
    and integer `leverage`, returning the applied leverage.
  - `GET /openApi/swap/v2/user/positions` returns per-position integer `leverage` and boolean
    `isolated`, providing an independent post-entry/hydration readback.
- The fail-closed sequence can therefore query margin mode, set/query side-specific leverage, and
  verify the authoritative result before the existing order endpoint. VST behavior must still be
  exercised only through mocked failure injection until runtime authorization exists.

Official references: [BingX perpetual swap trade API](https://github.com/BingX-API/api-ai-skills/blob/main/skills/swap-trade/api-reference.md)
and [BingX swap account API](https://github.com/BingX-API/api-ai-skills/blob/main/skills/swap-account/api-reference.md).

## Position Management Touchpoints

- `infrastructure/risk/active_position_manager.py` currently calculates ROE, fee coverage, and
  locked ROE from one constructor default. Replace production calculations with each hydrated
  position's authoritative leverage; missing leverage means observation/error only and no stop
  mutation.
- The canonical singleton is created at import time, so restart tests must prove hydration supplies
  leverage before an evaluation can mutate a stop.
- The 10x alert constants in the two orchestrators are monitoring-only. They should consume the same
  authoritative value in a later minimal follow-up, not expand the core correction.

## Verified Constructor Census

General Order constructors also exist in DTO/factory, risk-adjustment, backtest, and other broker
read adapters. Position constructors exist in DTO/factory, risk manager, other brokers, backtest,
data adapters, and live execution. Optional fields preserve those callers; only BingX derivatives
entry and active-position mutation are fail-closed consumers.

This map is read-only preparation. It makes no code, endpoint, setting, or runtime change.
