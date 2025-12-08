You want a test script for every watcher to verify that each one works correctly.
All watchers should use BingX by default, but each watcher must be able to use its own broker (Binance, Phemex, MEXC, etc.).
Only CMC Screener must always read from CoinMarketCap.
Each test should print the coins found and the final result so you can debug easily.
Important test scripts should be moved into proper unit tests.

Short Action Plan

Set BingX as the default broker.

Add config support to set a custom broker per watcher.

Keep CMC Screener fixed to CoinMarketCap.

Create a test script for each watcher (print coins + print final result).

Debug each watcher until it works without errors.

Review existing unit tests and add the important test scripts.

Start testing all watchers one by one.

Confirm data flow and consistency at each step.

Validate Watchers

Ensure watchers trigger properly.

Perform full end-to-end testing.