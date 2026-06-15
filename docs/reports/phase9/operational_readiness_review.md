# Phase 9 — Operational Readiness Review

**Areas covered:** 10 Database integrity · 11 Trade reconciliation · 12 Logging/observability ·
13 Alerting · 14 Circuit breakers · 15 Kill switches · 16 Production config safety ·
17 Secrets management · 18 API key safety · 19 Monitoring coverage · 20 Operational readiness
**Scope:** infrastructure safety only; strategy logic untouched.

Fixes touching the **real-funds order path** or **production secrets** are **[GATED]** (Rule 5 +
org policy: secrets are *flagged, not silently removed*). One safe bug was fixed (H14).

---

## AREA 10 — Database integrity

### C7a — Live trade/position state is in-memory only; total loss on crash — **Critical** (= C7)
- **Measure:** `infrastructure/tracking/trade_tracker.py:14` `self.active_trades: Dict = {}`;
  `:85 del self.active_trades[trade_id]`; module-global singleton `:97`.
  `application/risk_management/enterprise_risk_manager.py:231` `self.positions[symbol]=...`; PnL
  accumulators `:319-320` are in-memory floats. `pending_orders_tracker.py:28` class-level dict.
- **Diagnose:** No durable store of positions/orders/PnL; on crash/restart all open positions,
  pending orders, and running PnL are forgotten, and the duplicate guard resets to empty.
- **Fix [GATED]:** Persist positions/orders/fills to a transactional store (SQLite WAL or Postgres)
  on every transition; load + reconcile on startup (with C8/9.1).
- **Re-evaluate:** Prerequisite for any safe live operation.

### H13 — Non-atomic CSV write in the canonical candle store — **High**
- **Measure:** `infrastructure/data/candle_store.py:29-33` `df.to_csv(path, index=False)` overwrites
  the live file directly (no temp+rename, no fsync). The sync path
  (`infrastructure/data_sync/file_repository_adapter.py:159-174`) *does* temp+validate+`os.replace`,
  so this is an inconsistency, not an inherent limit.
- **Diagnose:** A crash mid-write leaves a truncated/corrupt OHLCV file that feeds bad prices into
  signal generation and SL/TP evaluation.
- **Fix:** Make `CandleStore.save` write to `path + ".tmp"` then `os.replace` (mirror the existing
  helper), ideally `flush()`+`fsync()` before rename. *(Data-pipeline, not funds; not applied this
  pass only because the test suite can't be run in this shell — see "Verification constraints".)*
- **Re-evaluate:** Removes a corruption-on-crash vector for market data.

### M — SQLite opened without WAL / busy-timeout; new connection per call — **Medium**
`infrastructure/results_tracking/results_tracker.py` (`:36,135,231,...`) `sqlite3.connect()` with no
`PRAGMA journal_mode=WAL`, no `timeout`, no `check_same_thread`. Under the heavily-threaded system
this throws `database is locked`. Today only research results are at risk, but the pattern would be
catastrophic if reused for trades. Fix: WAL + `synchronous=NORMAL` + busy timeout + per-thread conn.

### M — No uniqueness/idempotency constraints on records — **Medium**
`results_tracker.py:40-72` tables have only autoincrement PKs (only `combined_runs.run_id` is UNIQUE).
A retried write inserts a duplicate row silently. For a future trade ledger, add unique natural keys
(exchange order/fill id) + `ON CONFLICT`.

### M — Timezone inconsistency across write paths — **Medium**
Mixed naive-UTC vs naive-local stamps: `trade_tracker.py:43 datetime.utcnow()` vs
`enterprise_risk_manager.py:225,328 datetime.now()`; `forensic_logger.py:84` /
`_forensic_broker.py:62,112` `utcnow().isoformat()+"Z"`; `binance_adapter.py:54,73 datetime.now()`.
Corrupts holding-time, ordering, and any time-based reconciliation. Fix: standardize on
`datetime.now(timezone.utc)` everywhere.

### L — `flush_all`/`flushall` exposed on shared Redis client — **Low**
`shared/redis_client.py:33-35` wipes the entire DB; `set()` uses bare `json` with no error handling.
Redis is used only for market-data caching (limited blast radius), but remove/guard `flush_all`.

### L — Atomic-rename helpers don't fsync before replace — **Low**
`file_repository_adapter.py:164-174,364-368` `os.replace` without prior `fsync` — a host crash can
atomically swap in a partial temp file. Add `flush()`+`fsync()` before replace and fsync the dir.

---

## AREA 11 — Trade reconciliation

### C8 — No broker↔local reconciliation exists at all — **Critical**
- **Measure:** repo-wide `reconcil*` hits only `infrastructure/results_tracking/edge_ledger.py`
  (a *math identity* check on backtest stats, not broker truth). `domain/ports/broker_ports.py:36-48`
  exposes `get_balance/get_position/get_all_positions`, but no code diffs them against
  `enterprise_risk_manager.positions` / `trade_tracker.active_trades`. No drift detector, startup
  recovery, or periodic sync of trade state.
- **Diagnose:** Nothing detects divergence between the system's book and the exchange (missed fills,
  exchange-side liquidations, partial fills, late fills, crash-lost state). The system would keep
  trading on a fictional book.
- **Fix [GATED]:** Reconciliation loop — on startup and periodically, pull positions/balances/orders
  from the broker, diff against the persisted local ledger, **halt + alert** on drift beyond tolerance.
- **Re-evaluate:** This is the defining requirement of "safe for real funds"; until present, UNSAFE.

### C8b — `get_order_status` returns hardcoded `FILLED` fallback — **Critical**
- **Measure:** `infrastructure/brokers/adapters/binance_adapter.py:175-180` returns
  `{'status':'FILLED', ...}` "as a fallback" when the order isn't in open orders;
  `infrastructure/execution/live_execution_engine.py:234-237` `get_order_status` always returns
  `"FILLED"`.
- **Diagnose:** A cancelled/rejected/expired order is reported as FILLED — the worst reconciliation
  lie; downstream believes a phantom position exists.
- **Fix [GATED]:** Query the real order-by-id/history endpoint; return the true terminal status +
  filled qty; never default to FILLED.
- **Re-evaluate:** Removes fabricated fill state feeding all downstream logic.

### H — Fills logged with fabricated price/fee/slippage and a fake lifecycle — **High**
`infrastructure/services/broker_execution_service.py:360-373` logs the *requested* price with
`fee=0.0`, `slippage=0.0`, `order_status_lifecycle=['NEW','ACCEPTED','FILLED']` (all hardcoded;
comments admit it). Violates the project's own standards (fees/slippage in PnL). Fix: capture the
broker's fill response (avg price, commission, executed qty, status) and persist those.

---

## AREA 12 — Logging & observability

### C9a — Hardcoded live Telegram bot token + chat id in committed source — **Critical** (= C9)
- **Measure:** `application/configs/schemas/monitoring.py:19-21` — `telegram_bot_update_url`,
  `telegram_bot_token` Field **defaults** contain a live token; `telegram_chat_id` default present.
  Same token hardcoded in `application/configs/_config_extractors.py:288-290` and
  `application/configs/profiles/{dev,staging,live}.py` (~`:292-295`). **Values not reproduced here.**
- **Diagnose:** A real bot credential is checked into the repo (and git history); it survives even if
  `.env` is removed because `getenv(...)` falls back to the hardcoded default.
- **Fix [GATED — flagged, not removed per org policy]:** Owner must **rotate the token**, replace
  defaults with `""`, source from env/secret manager, and purge from git history.
- **Re-evaluate:** Closes a standing credential exposure + notification-channel hijack risk.

### H14 — `shared/sync_logger.py` missing `import os` → file logging crashed — **High — FIXED**
- **Measure:** `sync_logger.py:49-51` use `os.path`/`os.makedirs` but the module imported only
  `json,sys,traceback,datetime,typing,enum`; the `except (OSError, IOError)` at `:55` does **not**
  catch the resulting `NameError`, so it propagated and broke sync-path logging.
- **Diagnose:** Missing stdlib import; silent loss of data-pipeline observability.
- **Fix (APPLIED):** Added `import os`. Verified by byte-compile + isolated execution of the
  file-write branch (creates nested dir + writes JSON line).
- **Re-evaluate:** Sync/downloader logging now writes to file as intended. Safe, behaviour-fixing,
  no funds/secrets impact.

### M — Configured log size/rotation/level not honored — **Medium**
`monitoring.py:23-25` define `log_max_file_size_mb=50`, `log_backup_count=5`, `logging_level`, but
`shared/logger.py:60` hardcodes `RotatingFileHandler(..., maxBytes=1_000_000, backupCount=5)` and
`:35 setLevel(DEBUG)`. Operators tuning via config have no effect. Fix: pass monitoring config into
`create_logger`/`EnhancedLogger`.

### M — Forensic log uses non-rotating `FileHandler` → unbounded growth — **Medium**
`infrastructure/logging/forensic_logger.py:50 logging.FileHandler(log_file)`, enabled by default,
logs a JSON record per decision/observation/broker event — can fill the disk and down the process.
Fix: rotation **with high retention** (forensic = audit trail; choose retention deliberately — this
is why it was *documented*, not auto-changed).

### M — No secret redaction in logs — **Medium**
`shared/logger.py` / `sync_logger.py` do no masking; `multi_broker_service.py:376-385,409` log full
`order`/broker context at INFO and `.env` sets `LOG_LEVEL=DEBUG`. A config object carrying
`api_key` would be written in plaintext under `logs/`. Fix: redaction filter for
`api_key|secret|token|passphrase|password`; default prod level to INFO.

### L — Critical conditions logged at INFO/WARNING, not ERROR/CRITICAL — **Low**
`shared/logger.py:469-477 log_risk_alert` uses `info(...)`; orchestrator breaches log at `warning`.
Level-based paging would miss them. Fix: emit risk breaches / breaker trips at `error`/`critical`.

**Positives:** `log_paths.py` anchors logs to project root; `MessageBusAdapter` propagates callback
errors (vs the legacy `event_bus.py:42` silent `print`); correlation-ID plumbing exists
(`logger.py:136-148`); no secret *values* found in log *messages*.

---

## AREA 13 — Alerting

### H8a — Risk alerts notify only; never halt/flatten — **High** (= C2 enforcement gap)
`production_trading_orchestrator.py:144-167` sends an alert on breach and continues; `RiskAlertService`
is purely a notifier. Fix [GATED]: on `critical` breach, trigger halt/flatten in addition to alerting.

### H8b — `RiskAlertService.run_alert_monitor` fed empty placeholder data — **High**
`infrastructure/services/risk_alerts.py:148-171` loops on `trade_log={}`, `equity_curve={}`,
`asset_performance={}` ("Placeholder data") — a no-op that can never fire. Fix: wire to real
repositories or delete so the orchestrator loop is the single source.

### M — Notification services constructed with empty credentials in the live orchestrator — **Medium**
`production_trading_orchestrator.py:66-74` builds `EmailNotificationService()` /
`TelegramNotificationService()` with no args (empty-string defaults, `risk_alerts.py:26-28,62-64`);
sends fail and are caught/logged (`:55,83`). Critical alerts silently fail to deliver. Fix: inject
credentials from settings; escalate/health-metric on send failure.

---

## AREA 14 — Circuit breakers

### C3a — `CircuitBreaker` is decorative — zero usages in order/broker/data path — **Critical** (= C3)
- **Measure:** `shared/circuit_breaker.py` implements a correct CLOSED/OPEN/HALF_OPEN breaker, but a
  repo-wide search finds **no** broker call, data fetch, or order submission wrapped with it; the
  global `circuit_breaker_manager` registers no breakers. *(First-hand: grep over
  `infrastructure/orchestrators|execution|services|brokers` → no `CircuitBreaker` references.)*
- **Diagnose:** On broker failures / rate-limit storms / stale data, nothing fails fast; the live
  loops catch-log-sleep-retry forever (`production_trading_orchestrator.py:261`,
  `live_execution_engine.py:96`), hammering a failing broker and trading on stale data.
- **Fix [GATED]:** Wrap broker `place_order/cancel_order/get_position` and data fetches with the
  breaker; on OPEN, block new orders + alert. Add a **data-staleness** breaker (none exists).
- **Re-evaluate:** Adds fail-fast + automatic protection to the live path.

### M — CMC circuit-breaker thresholds configured but no breaker object exists — **Medium**
`application/configs/schemas/data.py:44-45` define `cmc_circuit_breaker_*` but no breaker is
instantiated for the CMC client. Instantiate one or drop the config.

---

## AREA 15 — Kill switches

### C3b — No kill switch wired into the live loop (backtest/validation only) — **Critical** (= C3)
- **Measure:** `infrastructure/risk/strategy_kill_switch.py:38 StrategyKillSwitchEngine` is real but
  built **from backtest results** (`bootstrap/container.py:312-316 create_kill_switch_from_backtest_results`)
  and resolved only by `interface/cli/comprehensive_validation.py:126` /
  `extended_horizon_validation.py:109` → `application/use_cases/_validate_portfolio_flows.py:298`.
  The production orchestrator (`container.py:478-489`) injects **no** kill switch. *(First-hand grep
  confirmed: no `kill_switch` reference in orchestrators/execution/services.)*
- **Diagnose:** No runtime mechanism to disable a malfunctioning strategy or halt trading; only
  `Ctrl-C`/SIGTERM, which doesn't flatten positions (`stop_system` just flips a flag).
- **Fix [GATED]:** Inject a runtime kill-switch + halt flag into the orchestrator and order path;
  gate `execute_order` on it; add an operator-triggerable flat-all/halt entry point (requires the
  working cancel/status from H5).
- **Re-evaluate:** Provides the missing emergency stop for live operation.

### H10 — Safety flags advertised as enabled but have no runtime consumer — **High**
`application/configs/schemas/safety.py:11,13,18` `circuit_breaker_enabled` / `emergency_stop_enabled`
/ `kill_switch_enabled` default `True` (live profile `:160-169`), but **no code branches on them**.
Operators reading the live profile will believe controls are active when they are inert. Fix: wire
the flags to real enforcement, or remove them; add a startup assertion that fails if a flag is on but
no enforcer is bound.

---

## AREA 16 — Production configuration safety

### C10a — `BINGX_ORDER_PLACEMENT_ENABLED` defaults to **True** — **Critical** (= C10)
`application/configs/_config_extractors.py:25
get_bool_env_var('BINGX_ORDER_PLACEMENT_ENABLED', True)`; `.env` does not set it → resolves True;
`DEFAULT_BROKER=bingx`. Consumed at `multi_broker_service.py:362-375` to route real orders. The safe
default for live order placement must be **False**. Fix [GATED]: default False; explicit env opt-in.

### C10b — `paper_trading` flag is dead code — **Critical** (= C10)
`application/configs/schemas/broker.py:15 paper_trading=True` (default), set per profile, but **no
execution-path reads it** (verified: only config/profile/schema references). The order path
(`multi_broker_service.place_order`, `:426`) never checks it. Fix [GATED]: enforce `paper_trading`
(and a `dry_run`) as a hard gate in `place_order` — simulate + return a synthetic id, never call the
broker.

### C10c — Binance adapter ignores `testnet`; always live endpoint — **Critical** (= C10)
`multi_broker_service.py:74-82` computes `binance_config['testnet']` but constructs
`BinanceBrokerAdapter(api_key, secret_key)` without passing it; `binance_adapter.py:13-16` →
`RestClient` with hardcoded `base_url="https://api.binance.com"`. `BINANCE_TESTNET` is silently
discarded. Fix [GATED]: thread `testnet` into the adapter/`RestClient` and select the testnet base
URL, or fail fast if Binance testnet is requested but unsupported.

### M — `enabled_brokers` not enforced at the routing gate — **Medium**
`.env` enables only bingx, but `live.py:47` lists all four with `*_order_placement_enabled=True`
(`:33,37,41`); routing keys off the per-broker flag, not `enabled_brokers`. A "disabled" broker can
still place orders. Fix: gate routing on `enabled_brokers ∩ *_order_placement_enabled`.

---

## AREA 17 / 18 — Secrets & API key safety

### C9b — Real broker/CMC/Telegram secrets committed in tracked `.env.example` — **Critical** (= C9)
- **Measure:** `.env.example` is **tracked** (confirmed `git ls-files .env.example`) and its values
  are **populated** (confirmed non-empty, values not reproduced): `BINGX/BINANCE/MEXC/PHEMEX
  _API_KEY/_SECRET_KEY` (and BingX passphrase), `CMC_API_KEY`, `TELEGRAM_BOT_TOKEN`
  (`.env.example:7-32`). An `.example` must contain placeholders only.
- **Diagnose:** Anyone with repo access (or any leak) obtains live trading keys for four exchanges +
  CMC + the Telegram token. If keys carry trade/withdraw scope, this is direct fund-loss exposure.
- **Fix [GATED — flagged, not removed per org policy]:** Treat all as **compromised → rotate/revoke
  immediately** on all venues; replace every value in `.env.example` with placeholders; purge from
  git history (filter-repo/BFG).
- **Re-evaluate:** Required before any live run regardless of other fixes.

### H12 — `.env` defaults to `ENVIRONMENT=production` with live keys present — **High**
`.env:42 ENVIRONMENT=production`, `:40 DEFAULT_BROKER=bingx`, live creds populated (`.env` is
correctly gitignored — `.gitignore:18 /.env` — so not a leak, but a live-config landmine: an
accidental `--mode production` uses real creds with no testnet/paper guard, see C10). Fix: default
working `.env`/`.env.example` to `dev`; require an explicit, loud opt-in for production.

### M — No env-only secret invariant — **Medium**
`profiles/live.py:21-46` uses `${...}` placeholders for broker keys (good) but hardcodes the Telegram
token in the same file (C9). Make all secret fields env-only with empty defaults; add a lint/test
that fails on any non-empty literal default for a secret-named field.

---

## AREA 19 — Monitoring coverage

### C1-ref — No order-path risk gate (`is_trading_allowed` never called) — **Critical**
See risk_engine_review C1: `broker_execution_service.py:716-717` removed `_validate_order_risk`;
`is_trading_allowed` (`enterprise_risk_manager.py:354`) has no live caller; `risk_engine` not injected.

### H9 — No heartbeat/liveness; loops self-heal silently; dead threads undetected — **High**
- **Measure:** `heartbeat_interval` configured (`monitoring.py:14`, live `:289`=10s) but **no code
  emits or checks a heartbeat**. Main/background loops catch all exceptions and `sleep`+continue
  forever (`production_trading_orchestrator.py:261-263`, `live_execution_engine.py:96-98`,
  `_risk_monitoring_loop:170-172`). Background services are daemon threads (`:98-110`); if one dies,
  nothing detects/restarts it.
- **Diagnose:** A wedged or partially-dead system (e.g. risk thread exits, data fetch returns empty
  every cycle) is undetectable externally and keeps "running" without oversight.
- **Fix [GATED]:** Emit a heartbeat per loop/thread on `heartbeat_interval`; add a watchdog that
  alerts/halts on stale heartbeat; restart or fail-loudly on dead threads.
- **Re-evaluate:** Gives a supervisor a liveness signal to act on.

### H — "Production" path runs random sample data through a stub executor — **High**
`application/use_cases/run_live_trading.py:25-42` `sample_data_fetcher` generates random OHLCV;
`live_execution_engine._execute_trades` (`:138-154`) is empty; `BrokerAPIService.place_order`
(`:220-226`) returns a fake id. The wired "production" loop does not actually trade or monitor real
state. Fix: replace the sample fetcher with the real provider, implement `_execute_trades` against
the real broker, then re-audit before going live.

### M — Metrics collector in-memory, unbounded, not exported — **Medium**
`shared/metrics.py` stores every metric in an unbounded in-process dict (`:36-47`), no exporter
(Prometheus/StatsD/push), lost on restart; `get_aggregated_metric` recomputes over the full list.
Fix: ring-buffer + an exporter.

---

## AREA 20 — Operational readiness

### H — No startup validation / fail-fast (silent unsafe fallbacks) — **High** (= C10)
`bootstrap/lifecycle.py:15-32` builds + yields with **no** preflight that, in live/production,
testnet/paper guards are consistent, keys are present/non-placeholder, and order placement is
intentionally enabled. `EnvLoader` defaults missing keys to "safe-looking" but unsafe values (C10);
`environments.py:46-47` silently defaults to DEV but `.env` overrides to production. Fix [GATED]:
add a composition-root preflight that **aborts loudly** if `environment ∈ {LIVE, PRODUCTION}` and any
of {testnet consistent with intent, keys present & non-placeholder, `paper_trading` explicitly False,
order placement explicitly enabled} is not satisfied.

### L — No documented release/deploy process; weak prod/dev separation — **Low/Medium**
No deploy/release runbook (only `docs/old/`); environment selection hinges on
`LYNXION_ENV`/`ENVIRONMENT` with a silent DEV fallback and a committed `.env` saying production. Fix:
add a deploy runbook (required env vars, testnet→live promotion checklist, key-rotation steps); make
production selection explicit and logged at startup. See `production_release_checklist.md`.

---

## Verification constraints (disclosure)
The full pytest suite could **not** be run in this shell: the project venv is Windows-targeted
(`.venv/Scripts/python.exe` fails under WSL bash interop) and the system `python3` lacks the
scientific deps (`numpy`). Therefore only the single trivially-safe stdlib fix (H14) was applied and
verified (byte-compile + isolated logic). All other Critical/High remediations are **specified** and
**gated** for owner application + test run, consistent with Rule 7 (regression safety) and the org
policy ("run linting and tests before marking a task complete").
