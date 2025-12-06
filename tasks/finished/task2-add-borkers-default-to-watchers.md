I need watchers to fetch data from different brokers and send the results to the next step (the engines).
Default broker should be BingX, but some watchers must be able to use Binance, Phemex, or MEXC as well.

Action plan:

Add a new config option for selecting the broker.

Update all brokers to read this value from the config.

Allow each watcher to specify which broker it should use.

Set BingX as the default if no broker is specified.

Confirm data flow and consistency at each step.

Validate Watchers

Ensure watchers trigger properly.

Perform full end-to-end testing.