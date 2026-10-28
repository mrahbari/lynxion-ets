I see several suspicious and problematic cases in trading and I want you to carefully examine them to solve the problem.
1- Confidence in many trades is 76.%, which shows that the calculation method is wrong.
2- It seems that the trend_following strategy is recording too many trades, which should be back-tested to see where the problem is.
3- Other strategies should be tested carefully one by one. For example, WLDUSDT opened both buy and sell trades with two different strategies. HYPEUSDT opened both buy and sell trades with one strategy, which indicates that they have problems and are not accurate. So:

Monitor each strategy carefully with all the details. Maybe the strategy itself is not wrong and problems arise at different stages.
When you get confirmation that they have an acceptable win rate, go to the next strategy.
See what can be done in the settings and logs to increase the accuracy of the trades.
Make the tasks for each item and handle them. do comprehensive analyse first!



[2026-07-13 21:58] LynxionNotifier: 🚀 WLDUSDT BUY on BINGX

📦 Order Details:
├ Side: 🟩 BUY
├ Symbol: WLDUSDT
├ Exchange: BINGX
├ Quantity: 100.9845998485231
└ Price: 0.3961

⚙️ Execution Details:
├ Strategy: balanced_strategy
├ Regime: stable
├ Confidence: 48.0%
├ Performance Score: 0.518
└ Risk-Adjusted Priority: 0.518

🛡️ Risk Parameters:
├ Stop Loss: 0.388178
└ Take Profit: 0.40798300000000004

🕒 Timestamp: 2026-07-13 20:14:39
🆔 Order ID: 2076757579565895680
[2026-07-13 22:04] LynxionNotifier: 🚀 WLDUSDT SELL on BINGX

📦 Order Details:
├ Side: 🟥 SELL
├ Symbol: WLDUSDT
├ Exchange: BINGX
├ Quantity: 101.26582278481013
└ Price: 0.395

⚙️ Execution Details:
├ Strategy: trend_following
├ Regime: trending
├ Confidence: 56.2%
├ Performance Score: 0.607
└ Risk-Adjusted Priority: 0.607

🛡️ Risk Parameters:
├ Stop Loss: 0.40290000000000004
└ Take Profit: 0.38315

🕒 Timestamp: 2026-07-13 20:14:39
🆔 Order ID: 2076759693553831936

---- 

[2026-07-13 21:43] LynxionNotifier: 🚀 HYPEUSDT BUY on BINGX

📦 Order Details:
├ Side: 🟩 BUY
├ Symbol: HYPEUSDT
├ Exchange: BINGX
├ Quantity: 0.6288616032826576
└ Price: 63.607

⚙️ Execution Details:
├ Strategy: trend_following
├ Regime: trending
├ Confidence: 76.0%
├ Performance Score: 0.821
└ Risk-Adjusted Priority: 0.821

🛡️ Risk Parameters:
├ Stop Loss: 62.33486
└ Take Profit: 65.51521

🕒 Timestamp: 2026-07-13 20:31:36
🆔 Order ID: 2076754307673231360
[2026-07-13 21:43] LynxionNotifier: 🚀 HYPEUSDT SELL on BINGX

📦 Order Details:
├ Side: 🟥 SELL
├ Symbol: HYPEUSDT
├ Exchange: BINGX
├ Quantity: 0.629079185342455
└ Price: 63.585

⚙️ Execution Details:
├ Strategy: trend_following
├ Regime: trending
├ Confidence: 76.0%
├ Performance Score: 0.821
└ Risk-Adjusted Priority: 0.821

🛡️ Risk Parameters:
├ Stop Loss: 64.8567
└ Take Profit: 61.67745

🕒 Timestamp: 2026-07-13 20:14:39
🆔 Order ID: 2076754258318856192