First, Always you must cover the rules and requirements that written in ./tasks/task0-force-to-cover.md
- Why we need to check .csv file for order placements and many issues like this! 
- why system needs to check it for production! it's not backtest!!!!!
- Check my observations that I shared below as a sample of logs!


There are lots of strange issues which i confused! so track a symbol like  NEOUSDT and find out what happened?
- check the ./logs/* deeply as well
- remember, we still have problem with order placement!

---

Right now we have a few problems.

One is that we already have a downloader, so we need to do unification. In the first step, review these files and give me a solution that prevents registering duplicate symbols in multiple places.

The following downloaders can use the list of approved symbols:

* `runner_history_download.py`
* `runner_multitimeframe_update.py`
* `runner_historical_data_sync.py`

Don’t forget that in the next step, for backtesting, we must also use only these registered symbols from a single source.

The current format that must be used everywhere—and which we already have—is:

```
data/history/raw/1m/SOL-USDT.csv
```

Processed 1m symbols are persisted in different paths:

```
data/history/processed/5m/SOL-USDT.csv
data/history/processed/15m/SOL-USDT.csv
data/history/processed/30m/SOL-USDT.csv
data/history/processed/1h/SOL-USDT.csv
data/history/processed/4h/SOL-USDT.csv
data/history/processed/1d/SOL-USDT.csv
```

Be sure to carefully review the current implementations.

Finally, if the system for any reason needs 1-minute historical data, it should use this address:
CSV_DATA_PATH=./data/history/raw/1m