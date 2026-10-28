# TASK: Persistent Trade Research Dataset / Background Trade Feature Collector

## ROLE

Act as a Senior Production Trading Systems Engineer and Quant Data Engineer.

Implement a small, production-grade background data collection task that continuously builds a structured CSV dataset from the platform's real executed trades.

This task is for RESEARCH / ANALYSIS ONLY.

It MUST NOT modify trading decisions, strategy logic, risk management, execution authorization, broker behavior, or order placement behavior.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## PRIMARY OBJECTIVE

Create and continuously maintain:

    data/trade_features.csv

The purpose of this file is to create a clean research dataset containing the information available around every real trade so that we can later analyze:

- Strategy performance
- Entry quality
- Exit quality
- Stop-loss / take-profit quality
- Market regime
- Signal quality
- Confidence calibration
- Symbol-specific performance
- Long vs Short performance
- Volatility conditions
- Whether losing trades share common characteristics
- Whether profitable trades share common characteristics

The dataset must be populated from the platform's EXISTING trade/order records and then continuously updated for all future trades.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## CRITICAL ARCHITECTURAL CONSTRAINTS

### DO NOT redesign the system.

### DO NOT create a new trading abstraction.

### DO NOT create a new execution lifecycle.

### DO NOT create a new strategy manager.

### DO NOT modify the existing execution architecture.

### DO NOT add opportunity IDs, setup IDs, deduplication systems, or new trading state machines.

### DO NOT modify:

- Strategy decision logic
- Strategy adapters' trading behavior
- StrategyManager decision logic
- EnterpriseRiskManager
- LiveExecutionGuard authorization logic
- BrokerExecutionService execution behavior
- Broker adapters
- Order placement logic
- Risk calculations
- SL/TP calculations
- Signal generation

This is strictly a DATA COLLECTION / RESEARCH task.

The collector must observe existing system state/events/records rather than introduce new trading behavior.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## STEP 1 — FORENSICALLY DISCOVER EXISTING TRADE DATA

Before writing code, inspect the existing project.

Find where the system currently records:

1. Executed orders
2. Filled orders
3. Closed trades
4. Entry price
5. Exit price
6. Stop-loss
7. Take-profit
8. Realized PnL
9. Strategy name
10. Symbol
11. Side
12. Execution timestamps
13. ExecutionIntent
14. FusedSignal
15. Risk parameters
16. Confidence
17. Any existing market/strategy features

Search the actual production code and existing data files.

DO NOT assume filenames or schemas.

Use the existing sources of truth wherever possible.

The first goal is to understand:

    Where does the platform already know that a trade happened?

and:

    What information is already available at entry and exit?

Produce a short audit before implementation.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## STEP 2 — RECONSTRUCT EXISTING HISTORICAL TRADES

The collector must first process the trades that have ALREADY been recorded by the platform.

Do NOT only collect future trades.

Search existing:

- order journals
- execution journals
- trade records
- reconciliation records
- broker records
- JSON files
- CSV files
- logs
- database records

Use the actual existing data sources.

For every historical trade that can be reliably reconstructed, create one row in:

    data/trade_features.csv

Do not invent missing values.

If a field cannot be reconstructed reliably:

    leave it empty / NULL

and document the reason.

Never fabricate values from assumptions.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## STEP 3 — DEFINE A STABLE RESEARCH SCHEMA

Create a practical CSV schema.

At minimum include:

### Trade Identity

- trade_id
- order_id
- execution_intent_id (if available)
- timestamp_entry
- timestamp_exit

### Instrument

- symbol
- side
- strategy
- timeframe (if available)

### Execution

- entry_price
- exit_price
- quantity
- notional_value
- fees
- realized_pnl
- pnl_percent
- exit_reason

### Protection

- initial_stop_loss
- initial_take_profit
- risk_distance
- reward_distance
- risk_reward_ratio

### Signal / Decision Context

Capture existing values if they are already available:

- confidence
- regime
- dominant_bias
- strategy_score
- risk_score
- signal_timestamp

### Market Context

Capture existing values if already available:

- ATR
- RSI
- ADX
- EMA values / EMA distance
- volume
- volume_ratio
- volatility
- funding_rate
- open_interest
- spread
- order_flow metrics
- CVD
- OBI

IMPORTANT:

Do NOT create fake calculations merely to fill columns.

If these values are not currently available at the relevant timestamp, leave them empty.

We can later decide which additional features are worth collecting.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## STEP 4 — ENTRY SNAPSHOT VS EXIT DATA

Understand that some information is only known at entry and some only at exit.

The dataset should preserve this distinction.

At ENTRY:

Capture the information that was actually available to the trading system when the trade decision was made.

At EXIT:

Add:

- exit price
- exit timestamp
- realized PnL
- fees
- exit reason
- final trade result

Do NOT use future information to populate an entry feature.

ABSOLUTE REQUIREMENT:

No lookahead bias.

A feature stored as an ENTRY feature must represent information that was available to the system at or before the actual entry decision.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## STEP 5 — CONTINUOUS BACKGROUND COLLECTION

After the historical dataset has been initialized, the collector must continue running in the background.

It should automatically detect newly completed/executed trades and add them to:

    data/trade_features.csv

The collector should run continuously for the lifetime of the trading process.

DO NOT stop the collector automatically.

It should remain active until an explicit operator instruction/configuration tells it to stop.

IMPORTANT:

This background task must NOT block:

- Market data processing
- Strategy evaluation
- Risk management
- Order execution
- Broker communication

The collector must be non-blocking / isolated from the critical execution path.

If the collector fails, trading must NOT fail because of the collector.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## STEP 6 — IDEMPOTENCY IS REQUIRED

The collector must never duplicate the same trade.

Before appending a trade, identify whether it has already been recorded.

Prefer an existing stable identifier such as:

- trade_id
- exchange order ID
- execution ID
- another existing unique execution identifier

Use the strongest existing identifier available.

Do NOT invent a random UUID every time the collector scans the source because that would make deduplication impossible.

The collector must safely survive:

- process restart
- collector restart
- application restart
- repeated scans
- temporary errors

After restart, it must resume without duplicating historical trades.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## STEP 7 — CSV SAFETY

The output file must be:

    data/trade_features.csv

Create the `data` directory if it does not exist.

The CSV must have a stable header.

Do not change column meaning dynamically from row to row.

When new fields are introduced later, handle schema evolution safely.

Use safe file writing.

Do not corrupt the CSV if the process terminates during a write.

If practical within the existing architecture, use:

- atomic write / temporary file replacement
  OR
- a safe append strategy with appropriate locking

Avoid introducing unnecessary infrastructure.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## STEP 8 — HANDLE PARTIALLY KNOWN TRADES

A trade may exist in several states:

1. Order created
2. Order submitted
3. Order filled
4. Position active
5. Position closed

Do not treat every order record as a completed trade.

The research dataset should distinguish actual exchange execution from:

- rejected orders
- locally blocked orders
- failed pre-send validation
- orders that never filled

For the initial dataset, prioritize REAL EXCHANGE EXECUTIONS.

If a position is still open, you may store an incomplete row only if the existing architecture makes this safe and useful.

Otherwise, wait until the trade is closed.

Do not classify an execution failure as a trading loss unless the existing execution records prove that actual exchange exposure occurred.

This distinction is extremely important.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## STEP 9 — EMERGENCY UNWIND / TECHNICAL FAILURE

Preserve technical execution outcomes separately from normal strategy outcomes.

If the system has an actual exchange exposure followed by:

- emergency unwind
- protective-order failure
- technical execution failure
- forced flattening

record it accurately.

Do NOT silently classify it as a normal strategy SL loss.

Use the actual existing execution outcome / exit reason where available.

For example:

    exit_reason = EMERGENCY_UNWIND

rather than:

    exit_reason = STOP_LOSS

if the records prove that this was an emergency unwind.

This dataset is intended to help us separate:

    STRATEGY FAILURE

from:

    EXECUTION / PLATFORM FAILURE

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## STEP 10 — DO NOT MODIFY EXISTING TRADE RECORDS

The collector is read-only with respect to existing trading records.

It may read:

- journals
- logs
- databases
- execution results
- strategy state
- signals

but it must not rewrite or alter the original trading records.

The CSV is a derived research dataset.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## STEP 11 — LOGGING / OBSERVABILITY

Add concise operational logging for the collector.

Examples:

    TRADE_DATA_COLLECTOR: historical scan started
    TRADE_DATA_COLLECTOR: reconstructed N historical trades
    TRADE_DATA_COLLECTOR: new trade recorded: <id>
    TRADE_DATA_COLLECTOR: duplicate skipped: <id>
    TRADE_DATA_COLLECTOR: incomplete trade deferred: <id>
    TRADE_DATA_COLLECTOR: unable to reconstruct feature X for trade Y
    TRADE_DATA_COLLECTOR: collector running

Do not flood production logs every scan cycle.

Use appropriate log levels.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## STEP 12 — FAILURE ISOLATION

The collector must be best-effort and must never become a trading dependency.

If:

- CSV is temporarily unavailable
- a historical record is malformed
- one trade cannot be reconstructed
- one feature is missing
- a source query fails

the trading engine must continue operating.

The collector should log the failure and retry according to a simple existing mechanism.

DO NOT introduce a complex queueing system unless the existing architecture already has one that can be safely reused.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## STEP 13 — VALIDATION

Before declaring the task complete, prove:

1. Historical trades were discovered.
2. Historical trades were reconstructed.
3. `data/trade_features.csv` was created.
4. Row count matches the number of uniquely reconstructed trades.
5. Duplicate trades are not present.
6. Existing trade IDs/order IDs are preserved.
7. Entry timestamps are correct.
8. Exit timestamps are correct.
9. Entry features do not contain future information.
10. Emergency unwinds are distinguishable from normal SL exits where the source data permits.
11. Missing data is represented as NULL/empty rather than invented.
12. Collector survives application restart.
13. Collector continues collecting future trades.
14. Collector failure cannot stop trading.
15. No trading logic was modified.

Run appropriate tests.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## STEP 14 — IMPORTANT: DO NOT OVERENGINEER

This is a data collection task.

Do NOT turn it into:

- a new service architecture
- a new event bus
- a new database
- a new lifecycle manager
- a new strategy abstraction
- a new execution state machine
- a new cache
- a new persistence framework

Prefer the smallest implementation that correctly uses the existing architecture.

One CSV file is the required research artifact.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## STEP 15 — BACKGROUND LIFECYCLE

The collector is a long-running background task.

It should:

1. Initialize.
2. Perform historical backfill.
3. Validate / deduplicate the existing CSV.
4. Start monitoring for new trades.
5. Append new completed trades.
6. Continue indefinitely.
7. Stop ONLY when explicitly instructed by the operator or when the main application is intentionally shutting down.

It must integrate cleanly with the application's existing startup/shutdown mechanism.

Do not create a separate manually managed process if the existing application already has a background-task mechanism.

Reuse the existing mechanism if available.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## STEP 16 — FINAL REPORT

After implementation, report:

### Files Created / Modified

List every file.

### Existing Data Sources Used

List exactly where historical trades came from.

### Historical Backfill

Report:

- number of source records examined
- number of unique real trades reconstructed
- number skipped
- number incomplete
- number of duplicates skipped

DO NOT invent numbers.

### CSV Schema

Show the final columns.

### Background Mechanism

Explain exactly how the collector remains active.

### Future Trade Capture

Explain exactly how a newly executed trade reaches `trade_features.csv`.

### Idempotency

Explain exactly how duplicate trades are prevented.

### Failure Isolation

Prove that collector failure cannot stop trading.

### Tests

Show actual test results.

### Architectural Impact

Explicitly confirm:

- No strategy behavior changed.
- No risk behavior changed.
- No execution authorization behavior changed.
- No broker behavior changed.
- No new trading abstraction was introduced.
- No new opportunity/setup lifecycle was introduced.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## ZERO-TRUST REQUIREMENT

Do not say:

"implemented successfully"

unless you have actually inspected the code and verified the behavior.

For every important conclusion distinguish:

FACT
INFERENCE
UNKNOWN

Do not invent trade statistics.

Do not invent missing market features.

Do not claim that a feature was available at entry unless the source data proves it.

The goal is to produce a trustworthy research dataset, not a cosmetically complete CSV.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## EXECUTION ORDER

Follow this exact order:

1. AUDIT existing trade/order data sources.
2. AUDIT existing background-task mechanisms.
3. AUDIT available entry/exit/strategy/signal data.
4. Report findings and proposed minimal implementation.
5. Implement the collector.
6. Backfill historical trades.
7. Validate the CSV.
8. Start the collector as a persistent background task.
9. Run tests.
10. Report evidence.

Do NOT redesign anything.

Do NOT touch trading logic unless absolutely required to expose an already-existing read-only data source, and if such a change is considered necessary, STOP and report it before modifying it.

you can find many beneficial data inside the data/live_order_journal.json. 

----


# TASK: Production Trade Dataset Collector & Continuous Trade Journal

## Role

Act as a Senior Production Trading Systems Engineer.

Your task is NOT to redesign the trading architecture, strategy engine, execution pipeline, or risk system.

We need a reliable dataset of actual executed trades so that the trading strategy and execution quality can be analyzed later from real production/paper-trading data.

Keep the implementation minimal and aligned with the existing architecture.

---

# 1. PRIMARY OBJECTIVE

Create/repair a persistent CSV trade dataset under:

    data/

Use the existing trade records currently available in the system to populate the CSV.

Then keep the CSV updated automatically for every NEW completed/executed trade from this point forward.

This must run as a background task/service and continue running until explicitly stopped by the operator.

Do NOT create a new trading subsystem.

Do NOT introduce a new architecture, abstraction layer, database, event bus, lifecycle manager, opportunity manager, or analytics framework.

Use the existing trade/execution/reconciliation information already available in the codebase.

---

# 2. FIRST: AUDIT BEFORE MODIFYING

Before writing code:

1. Locate the existing trade journal / trade history / execution records.
2. Locate how completed trades are currently detected.
3. Locate the existing files under data/.
4. Locate any existing CSV trade collector/exporter.
5. Determine whether a background task already exists that can safely host this functionality.
6. Determine the authoritative source for:
  - entry fill
  - exit fill
  - quantity
  - realized PnL
  - fees
  - SL
  - TP
  - exit reason
  - strategy
  - symbol
  - side
  - timestamps

Do not assume the signal price is the actual entry price.

Do not assume a local order record is the final exchange truth if broker reconciliation already provides authoritative information.

Before changing anything, report:

FACT:
- what already exists
- where trade information comes from
- how completed trades are currently detected
- what information is available

UNKNOWN:
- fields that cannot currently be obtained reliably

Do not invent missing values.

---

# 3. EXISTING HISTORICAL TRADES

Read the trades that have already been recorded by the current system.

Populate the CSV with all historical completed trades that can be reliably reconstructed.

The collector must be:

- idempotent
- restart-safe
- duplicate-safe

If the process restarts, it must NOT duplicate previously exported trades.

If the CSV already contains a trade, do not append it again.

Use the strongest existing unique trade/order identifier available.

Do not create a fake identifier unless absolutely necessary.

---

# 4. CSV LOCATION

Store the dataset under:

    data/

Use a clear production-oriented name such as:

    data/trade_journal.csv

Before creating a new file, check whether an existing CSV already serves this purpose.

If an appropriate existing CSV exists, prefer extending/fixing it instead of creating another competing trade file.

We want ONE canonical trade-analysis CSV.

---

# 5. REQUIRED DATA

Capture the following fields whenever the system already has them.

Core fields:

- trade_id
- symbol
- strategy
- side
- entry_timestamp
- exit_timestamp
- entry_price
- exit_price
- quantity
- pnl_usdt
- fees_usdt
- exit_reason

Execution/risk fields:

- actual_fill_price
- initial_stop_loss
- initial_take_profit
- risk_usdt
- r_multiple

Signal/context fields, ONLY if already available:

- confidence
- regime
- timeframe
- signal_direction

Derived fields may include:

- duration_seconds
- sl_distance_pct
- tp_distance_pct

Do NOT fabricate any of these values.

If a value is genuinely unavailable:

    UNKNOWN

or an empty value is acceptable, depending on the existing CSV convention.

Do NOT infer exchange fill price from signal price.

Do NOT infer exit reason from PnL alone.

Do NOT infer SL/TP from strategy defaults if the actual order parameters are available elsewhere.

---

# 6. VERY IMPORTANT: ACTUAL EXECUTION TRUTH

For every trade distinguish between:

A. Signal price
B. Intent price
C. Submitted order price
D. Actual exchange fill price

For trade analysis we care about the actual execution.

Therefore:

    entry_price = actual exchange entry fill

whenever available.

Likewise:

    exit_price = actual exchange exit fill

whenever available.

If the trade was closed through reconciliation, use the authoritative exchange/reconciliation information already used by the platform.

---

# 7. EXIT REASON

Preserve the actual reason when available.

Use the existing terminology from the platform.

Examples may include:

- TP
- SL
- RISK_EXIT
- EMERGENCY_UNWIND
- MANUAL
- LIQUIDATION
- EXCHANGE_REJECT
- UNKNOWN

Do NOT invent a new exit-reason taxonomy unless the existing system has no usable classification.

For an emergency unwind, distinguish it from a normal strategy loss.

This is important because we must later separate:

    genuine strategy losses

from:

    execution/infrastructure failures.

---

# 8. EMERGENCY UNWIND / FAILED EXECUTION

Do NOT automatically classify every failed order as a trade.

Only include it as an executed trade when actual exchange exposure occurred.

Use the existing execution/reconciliation evidence.

For example:

- Local validation failure → not a trade
- Risk rejection before send → not a trade
- Exchange rejection before fill → not a trade
- Network timeout with unknown exchange state → do not prematurely classify as a trade
- Main order filled + emergency unwind → actual exposure occurred and must be represented appropriately

Do not change execution behavior as part of this task.

This task is DATA COLLECTION ONLY.

---

# 9. BACKGROUND OPERATION

The collector must continue processing new completed trades automatically.

Requirements:

- run in the background using the simplest existing mechanism available
- survive normal application operation
- do not block trading
- do not add meaningful latency to order execution
- do not interfere with BrokerExecutionService
- do not interfere with LiveExecutionGuard
- do not interfere with StrategyManager
- do not modify strategy decisions
- do not modify risk decisions
- do not modify order placement

It should observe/read existing state rather than becoming part of the critical execution path.

If an existing background scheduler/task mechanism exists, use it.

Do NOT create a new scheduler framework.

---

# 10. CONTINUOUS APPEND BEHAVIOR

For every newly completed trade:

1. Detect it using the existing authoritative source.
2. Check whether its trade_id already exists in the CSV.
3. If not, append exactly one row.
4. Flush/persist safely.
5. Log that the trade was recorded.

Example:

    TRADE_JOURNAL: recorded completed trade XMRUSDT / <trade_id>

If the trade is already present:

    TRADE_JOURNAL: duplicate ignored <trade_id>

Do not continuously rewrite the entire CSV unnecessarily.

---

# 11. DATA INTEGRITY

The collector must never:

- modify existing historical rows silently
- duplicate trades
- overwrite actual exchange prices with signal prices
- invent missing fields
- classify rejected orders as completed trades
- change trading decisions
- modify risk parameters
- modify execution authorization
- modify strategy logic

If a previously recorded trade later receives additional authoritative information, handle that only if the existing architecture already supports safe updates.

Otherwise preserve the original row and report the limitation.

---

# 12. MANUAL DATA

Some information may NOT currently exist in the platform.

Do not create fake automation for unavailable information.

At the end of the implementation, produce a short report:

## AUTOMATICALLY AVAILABLE

List every field the system can reliably populate.

## NOT CURRENTLY AVAILABLE

List every field that cannot reliably be populated.

## POTENTIALLY MANUAL

List fields where manual TradingView/chart annotation may eventually provide useful research data.

The goal is to minimize manual work.

Do NOT require me to manually draw 100 trades unless absolutely necessary.

---

# 13. IMPORTANT RESEARCH FIELDS

The eventual purpose of this dataset is to determine whether losses are caused by:

1. genuine strategy failure
2. bad entry
3. bad stop placement
4. bad take-profit placement
5. slippage/execution quality
6. exchange-specific behavior
7. repeated-entry/re-entry defects
8. infrastructure/execution defects
9. other unknown causes

Therefore preserve raw factual execution data.

Do NOT add subjective labels such as "bad trade" or "good trade".

Those classifications will be performed later during research.

---

# 14. VALIDATION

After implementation:

1. Run the collector against existing historical trades.
2. Report:
  - number of trades discovered
  - number exported
  - number skipped as duplicates
  - number with missing fields
3. Inspect at least several historical rows manually.
4. Verify that:
  - entry price is actual fill where available
  - exit price is actual fill where available
  - PnL matches authoritative trade data
  - no duplicate trade IDs exist
5. Start the background collector.
6. Verify that a newly completed trade is detected and appended.
7. Restart the process and verify that the same trade is NOT duplicated.

---

# 15. SCOPE CONTROL

This is critical.

DO NOT:

- redesign architecture
- introduce Opportunity IDs
- introduce Setup Lifecycle Managers
- introduce new execution gates
- introduce new strategy abstractions
- introduce a database
- introduce a message bus
- modify LiveExecutionGuard behavior
- modify BrokerExecutionService behavior
- modify StrategyManager behavior
- modify strategy entry/exit logic
- modify risk logic
- modify broker execution logic

Unless a tiny change is absolutely required solely to expose already-existing authoritative trade information to the collector.

Prefer the smallest possible implementation.

---

# 16. OUTPUT

When finished, provide:

### IMPLEMENTED

Exact files changed and why.

### CSV

Exact path of the canonical CSV.

### SCHEMA

Final CSV columns.

### HISTORICAL IMPORT

How many existing trades were imported.

### CONTINUOUS COLLECTION

How new completed trades are detected and appended.

### DATA QUALITY

Which fields are authoritative and which are unavailable.

### MANUAL WORK REQUIRED

Only list information that genuinely cannot currently be obtained automatically.

### VALIDATION EVIDENCE

Provide concrete evidence that:
- historical trades were imported
- duplicates are prevented
- a new trade can be recorded
- restart does not duplicate trades

Do not claim success without evidence.

Use:

FACT / INFERENCE / UNKNOWN

where appropriate.

---

## FINAL PRINCIPLE

We are building a clean factual dataset for later quantitative research.

The collector must observe the trading system, not change how the trading system trades.

Keep it simple.
Keep the architecture frozen.
Use existing sources of truth.
Do not invent data.
Do not over-engineer.

---

# CRITICAL FOLLOW-UP TASK
# Trade Journal Data Integrity Audit — DO NOT ANALYZE STRATEGY YET

We now have:

    data/trade_journal.csv

The current CSV contains 303 records and 31 columns.

Before making any trading-strategy conclusions, perform a forensic audit of the dataset and the collector that produced it.

IMPORTANT:
The CSV currently contains many records where:

- status = FILLED
- exit_reason is populated
- but entry_price is NULL
- exit_price is NULL
- actual_fill_price is NULL
- pnl_usdt is NULL
- fees_usdt is NULL
- SL/TP are NULL

Therefore DO NOT assume these are completed trades.

The purpose of this task is to determine exactly what each row represents.

---

## 1. CLASSIFY THE CURRENT 303 RECORDS

For every record determine whether it represents:

A. Completed trade
B. Entry order only
C. Exit order only
D. Open position
E. Emergency unwind
F. Rejected order
G. Pending/unknown execution
H. Other

Do not infer based only on `status` or `exit_reason`.

Trace the actual source of each record in the codebase.

---

## 2. FIND THE AUTHORITATIVE TRADE SOURCE

Trace:

- where the entry order is created
- where exchange fill information is stored
- where position state is updated
- where exit orders are detected
- where realized PnL is obtained
- where fees are obtained
- where SL/TP parameters are stored
- where BrokerReconciliationService detects a completed position
- where StrategyManager.record_trade_result() is called

Identify the authoritative source for a COMPLETED TRADE.

The CSV must represent completed trades, not merely order records.

---

## 3. DO NOT FABRICATE DATA

Never populate:

entry_price
exit_price
actual_fill_price
pnl_usdt
fees_usdt
SL
TP

from guesses.

Do not use:

signal price as fill price
intent price as fill price
current market price as exit price
strategy default SL/TP as actual SL/TP

unless the code proves that value was actually submitted/executed.

---

## 4. REPAIR THE COLLECTOR

Modify only the trade-journal collector.

Do not modify:

- strategy logic
- strategy adapters
- StrategyManager behavior
- risk logic
- LiveExecutionGuard
- BrokerExecutionService
- broker execution behavior
- order placement
- trading decisions

The collector must consume existing authoritative execution/reconciliation information.

---

## 5. CANONICAL ROW SEMANTICS

One CSV row should represent ONE COMPLETED TRADE.

A completed trade requires sufficient evidence that:

1. An entry exposure occurred on the exchange.
2. The position was subsequently closed.
3. The entry and exit can be associated with the same trade/position.
4. Realized PnL can be obtained when available.

Do not create a completed-trade row merely because an order has:

    status = FILLED

An entry order being FILLED does not mean the trade is complete.

---

## 6. ORDER-TO-TRADE RECONSTRUCTION

Determine how the current system can associate:

ENTRY:

    entry order
    actual fill price
    filled quantity
    entry timestamp

with:

EXIT:

    exit order
    actual fill price
    exit timestamp
    realized PnL
    fees
    exit reason

Use existing IDs and reconciliation information where available.

Examples:

- order_id
- client_order_id
- position information
- exchange trade/fill IDs
- reconciliation records
- existing journal records

Do not introduce a new trade lifecycle architecture.

---

## 7. EMERGENCY UNWIND

Treat emergency unwind separately.

If:

    main order FILLED
    +
    protective SL/TP failed
    +
    emergency unwind executed

then this represents REAL exchange exposure.

It should NOT be silently discarded.

However, distinguish it from a normal strategy trade.

Use:

    is_execution_unwind = True

when the existing execution evidence proves that this occurred.

Do not classify it as a normal strategy SL.

Do not modify strategy metrics from the collector.

---

## 8. CURRENT CSV

Audit the existing 303 rows and report:

- how many are genuine completed trades
- how many are entry/order records
- how many are incomplete
- how many are duplicates
- how many are emergency unwinds
- how many cannot currently be reconstructed

Do not delete historical data silently.

If the current CSV is semantically wrong, preserve it as evidence and create the corrected canonical dataset only after documenting the decision.

Prefer:

    data/trade_journal.csv

as the canonical final file.

Do not create multiple competing CSVs unless absolutely necessary.

---

## 9. REQUIRED COMPLETED-TRADE FIELDS

For genuine completed trades populate, when authoritative data exists:

trade_id
symbol
strategy
side
entry_timestamp
exit_timestamp
entry_price
exit_price
quantity
pnl_usdt
fees_usdt
exit_reason
initial_stop_loss
initial_take_profit
confidence
regime
timeframe
signal_direction
duration_seconds
sl_distance_pct
tp_distance_pct
exchange
is_execution_unwind
status

Additional IDs may be retained:

order_id
order_ref
client_order_id

---

## 10. DATA QUALITY RULE

A completed trade with:

    entry_price = NULL
    exit_price = NULL
    pnl_usdt = NULL

must NOT be presented as a complete trade.

It should be classified as incomplete/order-level data.

---

## 11. CONTINUOUS COLLECTION

After fixing the collector:

For every NEW completed trade:

1. reconstruct the trade from authoritative existing sources
2. verify exchange exposure occurred
3. verify the position closed
4. obtain actual entry/exit fills
5. obtain realized PnL when available
6. append exactly one row
7. prevent duplicates
8. continue running in background

The collector must remain observational and must not affect trading.

---

## 12. VALIDATION

After implementation:

A. Reprocess the existing records.

B. Show a summary such as:

    Total source records: X
    Completed trades: X
    Entry-only records: X
    Incomplete: X
    Emergency unwinds: X
    Duplicates: X
    Unknown: X

C. Show 5 representative completed trades with:

    symbol
    entry price
    exit price
    PnL
    SL
    TP
    exit reason
    duration

D. Verify no completed trade has NULL entry_price/exit_price unless the exchange genuinely does not provide it.

E. Verify restart safety.

F. Verify a newly completed trade is captured exactly once.

---

# 13. STOP CONDITION

Do NOT proceed to strategy optimization.

Do NOT analyze the 25% win rate.

Do NOT modify trading logic.

First establish that:

    data/trade_journal.csv

is a trustworthy representation of actual completed trades.

Only after that should we use the dataset for strategy/execution research.

---

# FINAL REPORT

Return:

1. ROOT CAUSE of the current bad CSV semantics
2. AUTHORITATIVE source of completed trade truth
3. EXACT files modified
4. Number of valid completed trades recovered
5. Number of incomplete/order records
6. Number of emergency unwinds
7. Final CSV schema
8. Evidence that actual exchange fill prices are being used
9. Evidence that realized PnL is being used
10. Evidence that duplicates are prevented
11. Any information that still requires manual investigation

Use:

FACT
INFERENCE
UNKNOWN

Do not claim anything is fixed without code/evidence.


---

# NEXT TASK — FORENSIC TRADE QUALITY ANALYSIS
# DO NOT MODIFY TRADING LOGIC

We now have 61 verified completed trades.

Current measured baseline:

- Trades: 61
- Wins: 15
- Losses: 46
- Win Rate: 24.59%
- Net PnL: -$27.22
- Fees: -$7.60
- Average Win: +$3.90
- Average Loss: -$1.57
- Profit Factor: 0.8114

Do NOT modify any strategy, execution, risk, broker, or guard code.

The purpose of this task is forensic analysis only.

---

## 1. DO NOT ASSUME THAT EXCLUDING ALL XMRUSDT IS VALID

The current report claims:

"XMRUSDT produced 33 trades with -$131.18 and excluding XMRUSDT makes the remaining system profitable."

This must be verified.

Classify every XMRUSDT trade into:

A. Confirmed execution-cascade trade
B. Confirmed normal strategy trade
C. Unknown

Use execution evidence, order IDs, timestamps, emergency-unwind flags,
and the August 9 incident evidence.

Do NOT classify an entire symbol as an incident merely because the symbol
was affected by the incident.

Report:

XMR total:
- genuine trades
- cascade trades
- unknown

Then calculate:

1. All trades
2. Excluding ONLY confirmed cascade trades
3. Excluding ALL XMR trades

These are three different scenarios.

---

# 2. MARKET EXIT FORENSICS

The report says 62.3% of trades exited through MARKET orders.

Do NOT conclude that this is harmful yet.

For every MARKET exit determine the actual source:

- strategy
- risk engine
- broker protection
- emergency unwind
- timeout
- regime logic
- manual
- unknown

Then calculate separately:

- count
- win rate
- average PnL
- total PnL
- average duration

for each exit source.

The objective is to answer:

"Who is actually closing these trades?"

---

# 3. EXIT TYPE PERFORMANCE

Create a table:

Exit Type | Count | Win Rate | Avg PnL | Total PnL | Profit Factor

At minimum distinguish:

- TAKE_PROFIT
- STOP_LOSS
- MARKET_EXIT
- EMERGENCY_UNWIND
- UNKNOWN

Do not merge technically different exit mechanisms.

---

# 4. STRATEGY PERFORMANCE

Break down the 61 trades by:

- strategy
- symbol
- side

For each calculate:

- trades
- wins
- losses
- win rate
- gross profit
- gross loss
- net PnL
- profit factor
- average win
- average loss

Do not optimize anything.

We need to determine whether losses are concentrated in:

- one strategy
- one symbol
- one side
- one execution condition

---

# 5. SL / TP QUALITY

For every trade where actual initial SL and TP are available calculate:

- entry → SL distance %
- entry → TP distance %
- realized R multiple
- whether TP was reached before exit
- whether SL was reached before exit

Do NOT infer intrabar TP/SL hits unless the available data proves it.

If candle-level data is required but unavailable, mark:

UNKNOWN

---

# 6. FEE IMPACT

Separate:

Gross PnL
Fees
Net PnL

Calculate:

Fee / Gross Profit
Fee / Gross Loss
Fee / Absolute Net PnL

Do not state that fees caused the losses unless the numbers support it.

---

# 7. TRADE SIZE

Group trades by notional size.

Determine whether the small position sizes ($4–$21 according to the current report)
are materially damaging expectancy because of fees.

Report actual numbers.

---

# 8. MOST IMPORTANT QUESTION

Determine which of these is currently the strongest evidence:

A. Strategy signal quality problem
B. Exit-management problem
C. Risk/SL/TP problem
D. Execution quality problem
E. Fee/position-size problem
F. Incident contamination
G. Insufficient sample size
H. Combination

Rank them based ONLY on available evidence.

Use:

FACT
INFERENCE
UNKNOWN

---

# 9. STATISTICAL CAUTION

61 trades are enough for an initial diagnostic baseline.

They are NOT enough to declare that a strategy has durable statistical edge.

Do not claim:

"the strategy is profitable"

based only on removing XMR.

Do not claim:

"the strategy is unprofitable"

as a statistically final conclusion either.

Use:

"current observed sample is unprofitable."

---

# 10. OUTPUT

Produce:

## A. EXECUTIVE SUMMARY

Maximum 10 bullets.

## B. XMR FORENSICS

Cascade vs genuine strategy trades.

## C. EXIT FORENSICS

Who is generating MARKET exits.

## D. STRATEGY BREAKDOWN

## E. SYMBOL BREAKDOWN

## F. SL/TP ANALYSIS

## G. FEE ANALYSIS

## H. TRADE SIZE ANALYSIS

## I. ROOT-CAUSE RANKING

Rank A-H above.

## J. WHAT WE SHOULD NOT CHANGE YET

Explicitly list conclusions that are not sufficiently supported.

## K. NEXT DATA REQUIREMENT

State exactly what additional data is required before changing strategy logic.

DO NOT modify production trading code.