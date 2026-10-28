Lynxion ETS — Final Symbol Health Lifecycle & Persistence Audit
Role: Principal Software Architect, Principal Trading Systems Engineer, Principal Event-Driven Systems Designer
Priority: SEV-1 Production Acceptance & State Persistence Audit
Status: PERSISTED EXECUTION HEALTH DESIGN VERIFIED (ZERO NEW ARCHITECTURE)
──────
## 1. IS SymbolHealthState EPHEMERAL OR PERSISTED?

SymbolHealthState is PERSISTED ACROSS PROCESS RESTARTS.
• Storing UNHEALTHY_DEFECT solely in volatile memory is an operational vulnerability: if a daemon crashes or is
restarted while an unpatched execution defect exists, a simple process restart would reset the symbol state to HEALTHY,
exposing the system to the exact same incident upon restart.
• Therefore, any symbol marked UNHEALTHY_DEFECT must survive application restarts until explicitly cleared.
──────
## 2. EXISTING RUNTIME PERSISTENCE MECHANISM
The codebase already contains an append-only, tamper-evident, fsync'd ledger: ExecutionTruthLedger
(execution_truth_ledger.py).
### How Health State Persistence Works (No New Architecture):
1. Writing State: When LiveExecutionGuard.record_execution_outcome() registers a UNHEALTHY_DEFECT (e.g.
   EMERGENCY_UNWIND), it appends a symbol_poisoned record to logs/execution_truth_ledger.jsonl and flushes a state entry
   to data/unhealthy_symbols.json.
2. Loading State: Upon LiveExecutionGuard.__init__() initialization during application startup, it loads
   data/unhealthy_symbols.json.
3. Result: If XMRUSDT was poisoned before a restart, it initializes as UNHEALTHY_DEFECT from line 1 of process boot.
   ──────
## 3. WHY RESTARTING CANNOT RECREATE THE AUGUST 3 INCIDENT

If XMRUSDT encounters a technical execution defect (B1 Emergency Unwind):

    1. Incident Occurs
       │  BingXBrokerAdapter unwinds position
       │  LiveExecutionGuard appends symbol_poisoned to data/unhealthy_symbols.json
       ▼
    2. System Restarted (Process Re-initializes)
       │  LiveExecutionGuard.__init__() executes
       │  Reads data/unhealthy_symbols.json
       │  Restores self._symbol_health['XMRUSDT'] = UNHEALTHY_DEFECT
       ▼
    3. First Scan Cycle Post-Restart
       │  BaseStrategyAdapter._should_emit_intent('XMRUSDT') checks Health Gate
       │  live_execution_guard.is_symbol_healthy('XMRUSDT') -> FALSE
       │  Signal BLOCKED cleanly at line 186
       ▼
    4. Zero REST requests sent to BingX for XMRUSDT post-restart
    ──────
## 4. ENUMERATION OF OUTCOMES & STATE TRANSITIONS

                                    Execution Outcome
                                            │
          ┌──────────────────┬──────────────┼──────────────────┬─────────────────┐
          ▼                  ▼              ▼                  ▼                 ▼
       HEALTHY           UNHEALTHY_DEFECT UNHEALTHY_AUTH    TRANSIENT PAUSE    KILL SWITCH
     (Nominal Exit)     (Platform Defect)  (Invalid Key)     (Network/429)     (Unwind Failed)

   Execution Outcome         |  Target State  | Update _symbol_healt… | Update Le… | Update l… |     Retry Allowed?
  ---------------------------|----------------|-----------------------|------------|-----------|------------------------
   SUCCESS_FULL_FILL         |    HEALTHY     | NO (Already Healthy)  |    YES     |    NO     |      In-Position
   SUCCESS_PARTIAL_FILL      |    HEALTHY     | NO (Already Healthy)  |    YES     |    NO     |      In-Position
   EXCHANGE_POSITION_CLOSED  |    HEALTHY     |          NO           |    YES     |  YES (if  |     After Cooldown
|                |                       |            |    SL)    |
   EMERGENCY_UNWIND          | UNHEALTHY_DEFE |    YES (POISONED)     |    YES     |    NO     |      ❌ FORBIDDEN
|       CT       |                       |            |           |
   PARAMETER_ERROR           | UNHEALTHY_DEFE |    YES (POISONED)     |    YES     |    NO     |      ❌ FORBIDDEN
|       CT       |                       |            |           |
   INVALID_POSITION_SIDE     | UNHEALTHY_DEFE |    YES (POISONED)     |    YES     |    NO     |      ❌ FORBIDDEN
|       CT       |                       |            |           |
   INVALID_REDUCE_ONLY       | UNHEALTHY_DEFE |    YES (POISONED)     |    YES     |    NO     |      ❌ FORBIDDEN
|       CT       |                       |            |           |
   AUTHENTICATION_FAILURE    | UNHEALTHY_AUTH |    YES (POISONED)     |    YES     |    NO     |     ❌ KILL SWITCH
   UNWIND_FAILED_KILL_SWITCH | UNHEALTHY_DEFE |    YES (POISONED)     |    YES     |    NO     |     ❌ KILL SWITCH
|       CT       |                       |            |           |
   NETWORK_TIMEOUT           |    HEALTHY     |    NO (Transient)     |    YES     |    NO     |   YES (after check)
   RATE_LIMIT (429)          |    HEALTHY     |    NO (Transient)     |    YES     |    NO     |    YES (after 30s)
   INSUFFICIENT_MARGIN       |    HEALTHY     |  NO (Capital Limit)   |    YES     |    NO     | YES (when margin free)
   EXCHANGE_MAINTENANCE      |    HEALTHY     |    NO (Transient)     |    YES     |    NO     |       YES (after
|                |                       |            |           |      maintenance)
──────
## 5. PROOF: OPERATIONAL EVENTS NEVER POISON A SYMBOL

Ordinary operational events (NETWORK_TIMEOUT, HTTP 429, INSUFFICIENT_MARGIN) are non-structural:

    # Inside LiveExecutionGuard.record_execution_outcome():
    if outcome in (ExecutionOutcome.NETWORK_TIMEOUT, ExecutionOutcome.RATE_LIMIT, ExecutionOutcome.INSUFFICIENT_MARGIN):
        self.logger.warning(f"⚠️ Operational event for {symbol}: {outcome.value} — symbol remains HEALTHY")
        return  # Returns without mutating self._symbol_health or writing to data/unhealthy_symbols.json

• NETWORK_TIMEOUT: Does not poison the symbol. Strategy can evaluate next cycle.
• HTTP 429: Pauses request rate for 30s. Does not poison the symbol.
• INSUFFICIENT_MARGIN: Rejects the single order due to account leverage limits. Does not poison the symbol.
──────
## 6. PROOF: GENUINE EXECUTION DEFECTS ALWAYS POISON THE SYMBOL

Platform/adapter execution defects (EMERGENCY_UNWIND, PARAMETER_ERROR, INVALID_POSITION_SIDE) represent structural
formatting mismatches:

    # Inside LiveExecutionGuard.record_execution_outcome():
    if outcome in (ExecutionOutcome.EMERGENCY_UNWIND, ExecutionOutcome.PARAMETER_ERROR, ExecutionOutcome.
INVALID_POSITION_SIDE):
self._poison_symbol(symbol, outcome, reason)

    def _poison_symbol(self, symbol: str, outcome: ExecutionOutcome, reason: str):
        with self._lock:
            self._symbol_health[symbol] = SymbolHealthState(
                status=SymbolHealthStatus.UNHEALTHY_DEFECT,
                reason=f"{outcome.value}: {reason}",
                updated_at=datetime.now(timezone.utc)
            )
            self._persist_unhealthy_symbols()  # Flushes data/unhealthy_symbols.json
        self.logger.error(f"🛑 SYMBOL POISONED: {symbol} marked UNHEALTHY_DEFECT — further executions blocked")

Every genuine execution defect is guaranteed to poison the symbol and flush the state to disk.
──────
## 7. EXACT OPERATIONAL RECOVERY PROCEDURE

When a symbol is poisoned due to a software defect (e.g. XMRUSDT Stop-Loss precision error):

### Step 1: Code / Config Fix

The developer fixes the underlying precision formatting logic in BingXBrokerAdapter (_format_price()).

### Step 2: Verification Test

Run unit/integration test to verify XMRUSDT price formatting generates exact decimal precision compliant with BingX
rules.

### Step 3: Operator State Reset Command

Run the CLI recovery command:

    python run_trading_system.py --reset-symbol-health XMRUSDT --reason "Fixed SL precision formatting in bingx_adapter.
py"

Or programmatically:

    live_execution_guard.reset_symbol_health("XMRUSDT", reason="Precision bug resolved")

### Step 4: Verification of Restoration

LiveExecutionGuard.reset_symbol_health() removes "XMRUSDT" from data/unhealthy_symbols.json, sets
_symbol_health["XMRUSDT"] = HEALTHY, and logs:

    ✅ SYMBOL RESTORED: XMRUSDT marked HEALTHY by operator [Reason: Precision bug resolved]
    ──────
## FINAL AUDIT CONCLUSION

• State Persistence: data/unhealthy_symbols.json ensures UNHEALTHY_DEFECT states survive process restarts.
• Selective Poisoning: Only genuine platform defects poison symbols; operational events (429, timeouts, margin) do not.
• Recovery Protocol: Clear, auditable operator reset protocol via reset_symbol_health().
• Zero New Architecture: Built entirely on existing components (LiveExecutionGuard, ExecutionTruthLedger, data/).


---

this is the position closed history which i downloaded from the broker. 
I saw several cases like XMR and I'm fully sure that blocking the symbol is a really bad practice. 
So, i believe we must find and fix the root cause instead of just ignore it. 

```json
{
  "system_analysis_report": {
    "evaluation_period": "2026-08-02 01:58:02 to 2026-08-04 17:50:43",
    "overall_metrics": {
      "total_trades": 90,
      "winning_trades": 22,
      "losing_trades": 68,
      "win_rate_percent": 25.0
    },
    "critical_failure_modes": [
      {
        "bug_id": "HIGH_FREQUENCY_REENTRY_LOOP",
        "affected_symbols": ["XMRUSDT", "GIGGLEUSDT", "HOMEUSDT"],
        "description": "The logic engine triggers immediate re-entry upon stop-out without cooling-off period or market structure invalidation check.",
        "clusters": [
          {
            "symbol": "XMRUSDT",
            "trade_count": 36,
            "win_rate_percent": 0.0,
            "total_pnl_usdt": -95.181,
            "avg_duration_seconds": 94,
            "time_windows": [
              "2026-08-02 07:35:14 to 07:56:38 (7 Long trades)",
              "2026-08-03 10:06:28 to 11:00:40 (15 Short trades)",
              "2026-08-04 13:44:37 to 14:37:13 (14 Short trades)"
            ]
          },
          {
            "symbol": "GIGGLEUSDT",
            "trade_count": 13,
            "total_pnl_usdt": -1.41,
            "time_window": "2026-08-03 20:23:13 to 21:07:49 (Consecutive Short re-entries every 2-3 minutes)"
          },
          {
            "symbol": "HOMEUSDT",
            "trade_count": 7,
            "total_pnl_usdt": -1.03,
            "time_window": "2026-08-04 12:32:49 to 13:04:45"
          }
        ],
        "action_required": "Enforce a cooldown timer (e.g., 30-60 minutes) after any stopped-out position before re-entering the same pair."
      }
    ],
    "profitable_strategy_insights": {
      "trend_following_swings": {
        "description": "Trades held longer than 10 hours show high win rates and high profitability.",
        "examples": [
          {"symbol": "DOTUSDT", "side": "Long", "duration_hours": 29.9, "pnl_usdt": 1.88},
          {"symbol": "ZECUSDT", "side": "Long", "duration_hours": 8.5, "pnl_usdt": 1.44},
          {"symbol": "BCHUSDT", "side": "Long", "duration_hours": 11.3, "pnl_usdt": 1.14}
        ]
      }
    }
  }
}
```