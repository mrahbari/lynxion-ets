# Phase 10 — Paper Trading Validation Report

**Date:** 2026-06-12
**Objective:** Validate the real-world behaviour of the full trading system in paper mode, with **no
risk of live capital**, and determine whether there is any emergent profitability or structural
weakness under real execution conditions.
**Constraints honoured:** `paper_trading = TRUE`, `LIVE_TRADING` unset/FALSE throughout. No
strategy, execution-layer, guard, or risk logic was modified (validation only).

**Headline:** ✅ **Capital-safe** (zero live sends, zero real orders) but ⛔ **paper trading is
structurally non-functional on the live path** — every order died at the broker-connect gate *before*
the safety guard, so no order was ever simulated, filled, or priced. **No emergent profitability is
observable, and none can be measured from this path.** This reaffirms READY = 0.

---

## 1. Method

Two complementary runs (a true 24–72h run is impractical in this environment, so the authorised
"equivalent simulated burst window" supplements a bounded real run):

1. **Real production run** — the exact mandated command, paper-forced:
   `BROKER_PAPER_TRADING=true` (LIVE_TRADING unset) →
   `python run_trading_system.py --mode production --auto-detect --comprehensive-logs --symbols BTC/USDT,ETH/USDT,SOL/USDT`,
   bounded to a 6-minute window (~3 min of active trading-loop operation after data warm-up). Log:
   `logs/phase10_real_run.log`.
2. **Equivalent simulated burst** — `scripts/phase10_paper_trading_burst.py` drives the **real**
   `LIVE_EXECUTION_GUARD.authorize_and_send` → Execution Truth Ledger in paper mode at volume
   (72h-equivalent order flow across the 3 live strategies × BTC/ETH/SOL), with a cost-impact model
   built from the system's own parameters (`fee_rate=0.001`, `slippage_factor=0.0005`).

---

## 2. Capital-safety confirmation (primary requirement)

| Control | Result |
|---|---|
| `LIVE_TRADING` | unset / FALSE for the entire exercise |
| Real orders sent to a live exchange | **0** |
| Real orders sent to any exchange (real run) | **0** — all failed at the broker-connect gate |
| Guard route for simulated burst (87 orders) | **100% PAPER**, 0 sent |
| Execution Truth Ledger integrity (burst) | hash-chain verified `ok` over 174 records |

No path placed real capital at risk. ✅

---

## 3. Real production run — results

Active window ≈ 21:10:20 → 21:13:28 (~3 min of loop operation). The system **started cleanly and ran
stably**: all four broker adapters and the historical data provider initialised; strategies
`trend_following`, `mean_reversion`, `volatility_breakout` registered; the full pipeline
(Watcher → Engine → Fusion → Strategy → Aggregator → Broker) came up; **0 tracebacks, 0 crashes**.

| Metric | Value |
|---|---|
| Distinct order attempts (reached execution service) | **30** |
| Orders that succeeded | **0** |
| Failed at `❌ BROKER NOT CONNECTED` | **30 (100%)** → `ORDER PLACEMENT FAILED: invalid order ID: None` |
| Orders that reached the LIVE_EXECUTION_GUARD | **0** (0 `PAPER MODE` / guard lines) |
| Execution Truth Ledger records written by the real run | **0** |
| Strategies that emitted orders | **trend_following only** (mean_reversion, volatility_breakout silent) |
| Symbols | BTC / ETH / SOL (evenly) |
| Kill-switch / circuit-breaker / risk-alert activations | **0** |

A representative order was well-formed — `trend_following` on ETHUSDT, qty sized from the strategy
intent (`requested_position_size=0.0475`, `risk_per_trade=0.02`), with SL `1635.12` / TP `1718.54`
attached — then rejected at the connect gate.

---

## 4. Equivalent simulated burst — results

Driving the real guard + ledger in paper mode (`scripts/phase10_paper_trading_burst.py`):

| Metric | Value |
|---|---|
| Window (equivalent) | 72 h |
| Paper orders | 87 (≈ 29 / day) |
| Route distribution | **PAPER ×87** (100%); 0 TESTNET/LIVE; 0 real sends |
| Ledger records / verify | 174 / `ok` |
| Guard decision latency | avg ≈ 5.2 ms, max ≈ 53.8 ms |

**Cost-impact model** (fees 0.10% + slippage 0.05%, 2% notional sizing on $10k, round-trip):

| Strategy | Orders | Gross notional | Fees | Slippage | Round-trip cost est. |
|---|---|---|---|---|---|
| trend_following | 18 | $3,600 | $3.60 | $1.80 | $10.80 |
| mean_reversion | 42 | $8,400 | $8.40 | $4.20 | $25.20 |
| volatility_breakout | 27 | $5,400 | $5.40 | $2.70 | $16.20 |
| **Total** | **87** | **$17,400** | **$17.40** | **$8.70** | **$52.20 (0.52% of capital / 72h)** |

> The frequencies here are **assumed parameters** for a cost-sensitivity model, not measured live
> rates. They quantify the drag the cost layer would impose; they are not a profitability estimate.

---

## 5. Analysis against the requested dimensions

### Trade frequency per strategy
- **Real run:** only `trend_following` produced orders — and it **re-emitted the same ETHUSDT order
  repeatedly** (~30 attempts in ~3 min). Because every order failed pre-guard, the duplicate-
  prevention tracker (which only registers *placed* orders) never engaged, producing a tight
  retry-on-failure loop. mean_reversion and volatility_breakout emitted nothing in the window.
- **Simulated burst:** parametric (6/14/9 signals/day) — used only for the cost model.

### Cost impact simulation
Modeled at **0.52% of capital per 72h** at the assumed flow (table above). This is the structural
drag any strategy must overcome; with the Phase-5 finding of no out-of-sample edge, this cost is
pure loss. Real realized cost could not be measured (no fills occurred — see below).

### Win / loss distribution
**Not available.** No order was filled (real run: all rejected at connect; burst: paper orders are
synthetic with no fill/exit simulation). The live/paper path contains **no fill or PnL engine**
(`LiveExecutionEngine._execute_trades` is a stub — Phase-9 audit). For profitability evidence, the
authoritative source remains the Phase-5 backtest matrix: **0 / 108 cells profitable, 0 GO**.

### Slippage behaviour
Only **modeled** (0.05% parameter), never **realized** — no fills means no measured slippage. The
forensic path also hardcodes `slippage=0.0` (Phase-9 audit finding), so even a filled paper order
would not record true slippage.

### Risk engine behaviour under real flow
Confirmed from both the real run and the ledger: the portfolio **risk engine is not on the order
path**. Order sizing came from the strategy intent (`requested_position_size`), not from
`EnterpriseRiskManager`; every ledger `decision` record carries
`risk_engine: {"status": "not_wired_into_order_path"}`. No exposure/drawdown gate executed.

### Kill switch / circuit breaker activation frequency
**0** activations in both runs. In paper mode there is no realized PnL to breach the drawdown
threshold (so the orchestrator never engages the kill switch) and no guard-level send failures to
trip the breaker (orders died before the guard). Their correctness is established separately by the
Phase-9 concurrency validation (2,400-order chaos: 85 kill engagements, breaker trips, 0 leaked
sends).

---

## 6. Structural weaknesses found

| # | Severity | Finding |
|---|---|---|
| S1 | **High** | **Broker-connect gate precedes the guard.** With no valid (testnet) credentials the adapters never connect, so 100% of orders are rejected at `BROKER NOT CONNECTED` *before* the guard — **paper simulation never runs on the live path.** Paper trading as wired cannot exercise the guard/ledger or produce simulated fills. |
| S2 | **High** | **No fill / PnL / slippage engine on the live/paper path** (`_execute_trades` stub). Profitability, win/loss, and realized slippage are structurally unmeasurable from live/paper operation. |
| S3 | **Medium** | **Order/signal spamming on failure.** `trend_following` re-emitted the same order ~10×/min; failed orders never register as pending, so duplicate-prevention does not damp the retry loop. |
| S4 | **Medium** | **Single-strategy dominance.** Only 1 of 3 live strategies emitted orders in the window; signal coverage across strategies is uneven. |
| S5 | **Low/Med** | **Risk engine absent from the flow** (re-confirmation of Phase-9 C1): sizing and admission control are not governed by the portfolio risk engine. |

None were modified (execution/guard/risk frozen); all are recorded for the backlog.

---

## 7. Emergent profitability verdict

**No emergent profitability — and none is measurable from the live/paper path.**

- The real run produced **0 executed trades** (connect gate) and the paper path has **no PnL engine**,
  so profitability cannot arise or be observed here.
- Where profitability *was* measurable — the Phase-5 offline backtest matrix — the result was
  **0/108 profitable, 0 GO**, and the strategy program is frozen (READY = 0, no edge).
- The only economically certain quantity is **cost** (~0.52%/72h modeled), which is pure drag absent
  an edge.

**Conclusion:** Phase 10 confirms the system is **capital-safe in paper mode** (the Phase-9 guard
holds; zero live exposure) but **not capable of demonstrating profitability**, both because no
deployable edge exists and because the live/paper execution path is structurally incomplete
(S1/S2). The verdict from Phases 5–8 stands: **no strategy is deployable.**

---

## 8. Recommendations (backlog — NOT executed; layers frozen)

1. **Make paper mode bypass the broker-connect gate** (or connect a paper/testnet stub) so paper
   orders reach the guard and exercise the full path (S1).
2. **Add a paper fill/PnL simulator** (fills at modeled price + fee + slippage, with exits) so
   win/loss and realized cost become measurable in paper mode (S2).
3. **Dampen failed-order retries** / register intent before send so duplicate-prevention applies to
   failures too (S3).
4. Re-run a true 24–72h paper window once S1/S2 land, then re-assess emergent behaviour.

These are deferred items for a future, un-frozen execution-layer phase.

---

## 9. Artifacts

- `logs/phase10_real_run.log` — full real-run log (30 order attempts, all connect-gated).
- `scripts/phase10_paper_trading_burst.py` — equivalent-burst harness (re-runnable).
- Simulated-burst ledger: `/tmp/phase10_sim_ledger.jsonl` (hash-chain verified).
- Reproduce burst: `.venv/bin/python scripts/phase10_paper_trading_burst.py`
