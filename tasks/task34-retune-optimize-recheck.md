At the moment, my **resync** process, which includes various items, is working correctly:
```bash
python runner_resync.py --all
```

However, the issue is that for **retune**, I need a **1-day timeframe**.

I want my **retune** process to have the same capabilities as **resync**:

```bash
python runner_retune.py --strategy crypto_breakout --symbols BTCUSDT --evals 50 --days 90
```

1. For the coins listed in `.env` under `WFO_COINS`, use the downloader to download **1-day timeframe data for 6 months** (`--days 180`).
2. It’s better if the downloaded data is stored in the directory:
   `data/history/processed/1d`
3. Then I want to make sure that **after downloading, the retune process is actually executed correctly**.
4. If no symbol name is provided when calling the **retune** command, it should **download and tune all symbols**.
5. Make sure that **hyperopt is working correctly**.
6. Finally, give me a **comprehensive instruction** on how I can **professionally use retune, walk-forward, and optimized backtesting**. I still don’t fully understand how I should use them.
7. I think it would be good to **add the 1-day timeframe to the resync processed timeframes as well**. It will probably be useful for backtesting.

---


### **1. Architectural Compliance**

* [ ] Ensure full compatibility with the current Hexagonal Architecture.
* [ ] Verify that no part of the architecture (Watcher → Engine → Fusion → Strategy → Broker) is modified or broken.
* [ ] Confirm the strategies integrate without introducing tight coupling or side effects.

### **2. Integration & Functional Testing**
* [ ] Confirm there are no performance delays, lags, or misalignment issues.
* [ ] Check for indicator shifting errors or look-ahead problems.
* [ ] Ensure no survivorship bias or similar failure patterns appear.

### **3. Quality & Validation**
* [ ] Maintain Hexagonal Architecture integrity at all times.
* [ ] Prevent performance degradation or lag.
* [ ] Avoid look-ahead issues and misalignment.
* [ ] Validate all migrated features behave exactly as before.
* [ ] Ensure all code follows best practices and architectural rules.
* [ ] Keep the code DRY (no logic repetition).
* [ ] Verify that the project builds successfully.
* [ ] Ensure all automated tests pass.
* [ ] Perform a final full-system verification to guarantee 100% correctness.
