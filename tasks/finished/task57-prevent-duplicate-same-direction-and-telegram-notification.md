
Recently I added a feature to Prevent Duplicate Same-Direction Trades per Symbol but after that I didn't have any successful order placement. 
1- check the logs "./logs/*" and fix the issues of order placement. You can find the flag in .env file "PREVENT_SAME_DIRECTION_TRADE_PER_SYMBOL=true" for tracking the implementations. 

2- Telegram notification. I've seen you implemented a test script for telegram notifications. the good point is, related credential is in .env file which I added here as well. 
check why the notifications is not working yet and fix it. 

3- Find the reason and resolve the issues of getting stuck with USDCUSDT order! it's strange and this coin must be excluded from watcher flow  

##############################
# TELEGRAM BOT CONFIGURATION
##############################
TELEGRAM_BOT_NAME=@LynxionNotifierBot
TELEGRAM_BOT_URL=t.me/LynxionNotifierBot
TELEGRAM_BOT_UPDATE_URL=https://api.telegram.org/bot8324444752:AAGoubuQSgXp6lhQGCxcOtGT6hLg3kTgWbY/getUpdates
TELEGRAM_BOT_TOKEN=8324444752:AAGoubuQSgXp6lhQGCxcOtGT6hLg3kTgWbY
TELEGRAM_CHAT_ID=71819811
TELEGRAM_NOTIFICATIONS_ENABLED=true    # Enable Telegram notifications for order placements (true/false)



---

### 🧩 Task: Prevent Duplicate Same-Direction Trades per Symbol

**Description**
Add a configurable safeguard to prevent opening multiple **active positions in the same direction** (BUY/LONG or SELL/SHORT) for the **same trading symbol**.

When a position for a symbol is already active in a given direction, the system must **not open another trade in that same direction** for that symbol.

**Configuration**

* Introduce a new configuration flag (e.g. `prevent_same_direction_trade_per_symbol`)
* **Default value:** `true`
* When enabled:

  * If there is an **active position** for a symbol in a given direction, any new execution intent with the **same symbol and same direction** must be skipped or rejected.
* When disabled:

  * The system behaves as before and allows multiple same-direction trades on the same symbol.

**Acceptance Criteria**

* The check applies only to **active positions** (open, not closed).
* Opposite-direction trades (e.g. opening a SHORT when a LONG is active) are **not blocked**.
* The behavior is fully controlled via configuration.
* The system logs a clear message when a trade is skipped due to this rule.

**Rationale**
This prevents over-exposure and unintended position stacking on the same symbol while keeping the behavior flexible via configuration.






## Extra Critical Rules Implemented

### **1. Architectural Compliance**

* [ ] Ensure full compatibility with the current Hexagonal Architecture.
* [ ] Verify that no part of the architecture (Watcher → Engine → Fusion → Strategy → Broker) is modified or broken.
* [ ] Confirm the strategies integrate without introducing tight coupling or side effects.
* [ ] Confirm and place orders on bingx, so that we have SUCCESSFUL ORDERS PLACED ON BINGX VST BROKER.

### **2. Integration & Functional Testing**
* [ ] Confirm there are no performance delays, lags, or misalignment issues.
* [ ] Check for indicator shifting errors or look-ahead problems.
* [ ] Ensure no survivorship bias or similar failure patterns appear.

### **3. Quality & Validation**
* [ ] Maintain Hexagonal Architecture integrity at all times.
* [ ] Better architecture: Each component now has a single responsibility. SOLID principals must be followed for coding!
* [ ] Prevent performance degradation or lag.
* [ ] Avoid look-ahead issues and misalignment.
* [ ] Validate all migrated features behave exactly as before.
* [ ] Ensure all code follows best practices and architectural rules.
* [ ] Keep the code DRY (no logic repetition).
* [ ] Verify that the project builds successfully.
* [ ] Ensure all automated tests pass.
* [ ] Perform a final full-system verification to guarantee 100% correctness.
* [ ] The system must be fully functional and able to order placement via mentioned flow (Watcher → Engine → Fusion → Strategy → Broker)

