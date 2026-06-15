# E4 — Final Closure Plan (design only, NO code)

Controlled migration-closure plan for E4 (Domain Model Unification). **No code changes,
no implementation, no refactor, no commit.** Builds on the broker-boundary discovery and
the contract-design decisions.

## Status entering closure
- E4.T1 (entity merge) ✅ committed `a05904c`
- E4.T2 (delete shadow model + dead cluster) ✅ committed `8fb26bb`
- E4.T3 (remove pandas from domain) ✅ committed `69f74c7`
- E4.T4 Phase 1B (pure DTOs + mapper choke point) ✅ + Phase 2A (ingestion wiring) ✅ — committed `766d154`
- Broker/execution layer: **legacy, untouched, intentionally so.**
- Contract decisions (D1–D4): defined, **not implemented.**

---

## 1. Symbol policy — FINAL DECISION: **strict canonical inbound via `to_symbol()`; exchange-aware OUTBOUND only**

- **Inbound (raw → domain):** one canonical `Symbol` form system-wide — `to_symbol()` strips
  whitespace + separators (`-`/`/`/`_`) + uppercases → no-dash canonical (`BTCUSDT`).
- **Outbound (domain → exchange API):** stays exchange-specific via `SymbolFormatHelper`
  (`BTC/USDT`, etc.) — unchanged.

**Justification (trading correctness):** symbol *identity* must be consistent for position/
order matching (`pos.symbol == query_symbol`, approval lists, caches). Divergent inbound
forms (`BTC-USDT` vs `BTCUSDT`) are a correctness hazard. Strict canonical inbound
**subsumes bingx's `replace("-","")`** — `to_symbol("BTC-USDT") → BTCUSDT` reproduces bingx's
current value, so there is **no bingx regression and no per-adapter exception**. The
exchange-aware concern is real but belongs to *outbound* formatting, which is already
separated. (Rejected: keeping exchange-specific inbound normalization — it perpetuates the
divergence E4 exists to remove.)

> Implementation caveat (when executed as its own step): enhancing `to_symbol()` changes its
> normalization. It does **not** change the committed ingestion *output* (those row dicts
> carry no symbol field), but it is a behavior change to the mapper primitive and must be
> parity-checked against every current caller before landing.

## 2. Safe migration strategy — staged rollout (the deferred-execution playbook)

Order is foundation-first, then ascending risk; **bingx last**. Each adapter sits behind
`BrokerPort`, so each step is **independently revertable (one file)**.

| # | Target | Risk | Expected behavioral change | Rollback safety |
|---|--------|------|----------------------------|-----------------|
| 0a | `to_symbol()` separator-normalization (D2) | **MED** | canonical no-dash everywhere; bingx parity preserved; affects symbol identity globally | revert `mappers.py` (1 file); pre/post symbol-set parity test |
| 0b | extend `OrderDTO`+`order_to_domain` (D1) | **LOW** | additive only (optional fields); no behavior until Order sites migrate | revert `order_dto.py`/`mappers.py`; domain untouched |
| 1 | `broker_manager.py` | **LOW** | **none — no-op** (pure delegator, no construction) | n/a |
| 2 | `multi_broker_service.py` (symbol-validation sites → `to_symbol`) | **MED** | symbol approval/availability now uses canonical normalization; could change which symbols pass the approved-list gate | revert 1 file; verify approved-symbol set unchanged |
| 3 | `binance_adapter.py` | **MED** | `Balance.*` float→`Decimal`; `Order.price` float→`Money`; `stop_price`/`time_in_force` preserved via extended DTO; `asset.upper()` retained | revert 1 file; golden snapshot of `get_balance`/`get_open_orders` |
| 4 | `mexc_adapter.py` | **MED** | same pattern as binance | revert 1 file; golden snapshot |
| 5 | `phemex_adapter.py` | **HIGH** | corrects latent bug: `Position.side` str→enum, `entry_price`/`pnl` float→`Money`; `/1e8` scaling preserved; **type-correcting behavior change** | revert 1 file; explicit before/after position-read review |
| 6 | `bingx_adapter.py` (**LAST**) | **HIGH** | `Balance` `Money`→`Decimal`; `Position` qty float→`Decimal` (fixes latent `Decimal×float`); dash handling now via canonical `to_symbol`; most complex adapter (SL/TP, conditional orders) | revert 1 file; full position/order/balance golden review |

## 3. Order / Balance / Position migration policy → **DEFER all three (do NOT migrate now)**

- **Now:** none. These are live trading-read paths; migrating them is the high-risk work
  above and requires D1 (DTO extension), D2 (symbol policy), and a **consumer audit** first.
- **Safest order of operations (within the deferred rollout), per adapter:**
  **Symbol → Balance → Order (after D1) → Position (last).**
  - Symbol: lowest (canonical, parity via D2).
  - Balance: float→`Decimal` (entity contract); audit consumers doing float math on
    `Balance.total/available/reserved`.
  - Order: only after `OrderDTO` extension + audit of `Order.price` float→`Money` consumers.
  - Position: last; corrects phemex/bingx latent type bugs (currency via `Symbol.quote_asset()`).

## 4. Contract stability rule — MUST NOT change during E4 finalization

Frozen for the duration of E4 closure (other code may now depend on the committed layer):
- **DTO schema** of the committed layer — frozen. The only permitted change is the *additive*
  `OrderDTO` extension (D1), and only when that step is separately executed (not during
  closure).
- **Money model (D3 hybrid)** — fixed: primitives at the seam, `Decimal`/`Money` in domain
  via mappers. No `__post_init__` coercion added to domain entities.
- **`to_symbol()` behavior** — frozen until D2 is executed as its own reviewed step (it
  affects committed ingestion semantics).
- **Mapper public API** (`to_symbol`/`to_money`/`to_percentage`/`to_decimal` + `*_to_domain`)
  — stable signatures.
- **Domain entities** — no field/shape changes (E4.T1 model is canonical and frozen).
- **Ingestion wiring** (`csv_history_loader`, `data_downloader_adapter`) — no further change
  during closure.

## 5. Validation strategy (per migration step, when the deferred work runs)

**Pre-migration checkpoint (per adapter):**
- Capture a golden snapshot: for representative raw payloads, record the *types and values*
  of `get_balance` / `get_open_orders` / `get_positions` outputs.
- Consumer audit: `grep` for `.price`, `.total`, `.available`, `.quantity`, `.entry_price`,
  `.side` on broker-returned objects to find float/enum assumptions that a type change breaks.

**Post-migration checkpoint:**
- Re-run golden snapshot → assert value parity; any type change (float→`Decimal`/`Money`,
  str→enum) must be **explicitly listed** as an intended delta (esp. phemex/bingx bug fixes).
- Structural greps: no direct `Balance(`/`Order(`/`Position(`/`Symbol(` from raw dict remain
  in the migrated adapter (must route through mappers).
- `py_compile` repo-wide; `container.resolve_all()` + the suite **in a proper venv**
  (numpy/pandas/pydantic/pytest present — NOT runnable in the current deps-light interpreter).

**Standing invariants (must stay green throughout):**
- `grep -rn "import pandas" domain/` == 0 (E4.T3).
- `grep -rn "shared.types" .` == 0 (E4.T2).
- `mypy-strict` on `domain/` + `application/` — the ultimate enforcement, **pending E6.T4**
  (no mypy config exists yet).

**Rollback:** every step is a single-file revert behind `BrokerPort`; no cross-file coupling
in the migration set; `to_symbol`/DTO steps are revertable in `application/dto/`.

## 6. FINAL RECOMMENDATION → **STOP AND DEFER THE E4 EXECUTION/BROKER LAYER TO E5**
### (equivalently: PARTIAL COMPLETION — the ingestion boundary is E4's final delivered scope)

**Close E4 now.** Its core objective (P6 — one canonical domain model, pandas-free domain,
VO enforcement *introduced* at the boundary via the DTO/mapper choke point) is **achieved
and committed** (T1–T3 + DTO layer + ingestion wiring). 

**Defer the broker/execution VO enforcement to E5** (where broker/CLI/interface work lives),
executed via the staged playbook in §2 using the D1–D4 contract decisions as its spec.

**Why not full completion now:** the broker/execution migration is multiple HIGH-risk edits
to **live order/balance/position** code, blocked on a DTO contract extension (D1), a global
`to_symbol` change (D2), latent-bug corrections (phemex/bingx), and a consumer audit. Cramming
that into "closure" trades trading correctness for schedule — the opposite of production-safe.
Deferring keeps E4 a clean, shippable baseline and gives the risky work its own gated home.

**Concrete closure actions (no code):**
- Mark E4 **COMPLETE at the ingestion boundary**; record broker/execution VO enforcement as a
  carried-forward E5 item with this plan as its spec.
- Carry the open enforcement of the `mypy-strict` acceptance clause to **E6.T4**.
- (Optional, your call) commit the three E4.T4 design/discovery docs for provenance.

---
**DO NOT IMPLEMENT.** Design/architecture only — no code, no wiring, no commit.
