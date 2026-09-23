# F01 — offline intent-to-order risk-sizing verification

Scope: synthetic intents and a capture-only execution service; **no broker call, order placement, VST, production setting change, strategy change, or economic test**. The capture service returns `None` and only retains the pre-broker `Order` object. Isolated tests: `tests/unit/test_f01_offline_intent_sizing.py`.

## Result

**F01_NO_GAP_DYNAMIC_SIZING_PRESERVED**

Under an explicitly selected dynamic risk-manager mode, equal equity ($10,000), equal risk fraction (1%), and price 100, two valid LONG intents with stops 95/90 produced pre-broker quantities 20/10 and notionals $2,000/$1,000. Two equivalent SHORT intents with stops 105/110 produced the same quantities/notionals. The captured `Order.quantity` equals the risk adapter's result. No downstream overwrite occurred in the tested `SignalProcessor._process_execution_intent` route when constraints were nonbinding. Requested leverage 2 was passed through as order metadata, not used to increase quantity.

| Isolated condition | Captured near/far quantity | Interpretation |
|---|---:|---|
| Dynamic, nonbinding limits, LONG | 20 / 10 | Inverse distance preserved |
| Dynamic, nonbinding limits, SHORT | 20 / 10 | Inverse distance preserved |
| `max_position_exposure=$1,000` | 9.9 / 9.9 | 0.99 exposure buffer dominates both |
| `MAX_ORDER_NOTIONAL_AMOUNT=$500` equivalent settings cap | 5 / 5 | Pre-broker order cap dominates both |
| Risk-manager fixed mode, fixed amount $400 | 4 / 4 | Fixed sizing intentionally ignores stop distance |
| Tiny dynamic risk fraction | 0.001 / 0.001 | Event route's hard minimum quantity overrides smaller computed sizes |

## Source trace and boundaries

`ConsolidatedRiskEngineAdapter.calculate_dynamic_size` reads `intent.risk_parameters.limit_price` and `stop_loss`, equity and risk fraction, then calls `EnterpriseRiskManager.calculate_position_size`. Dynamic mode computes risk amount divided by absolute price-to-stop distance (or a larger volatility-normalized denominator) and clips to position/portfolio exposure with a 0.99 buffer. `SignalProcessor._process_execution_intent` then can replace the result with a 0.001 minimum, liquidity-depth cap, or `MAX_ORDER_NOTIONAL_AMOUNT` cap before constructing `Order.quantity` and calling `execute_order`. In the test that final call is a capture-only stub.

The separate `_AutoDetectionExecutionMixin._execute_trade_from_intent` route also invokes the same adapter and passes its quantity to `Order`, but has its own minimum/liquidity handling and no visible local `MAX_ORDER_NOTIONAL_AMOUNT` cap. That route was source-traced, not dynamically exercised end-to-end here because its other admission/execution services are not part of F01's isolated test. Later broker/risk enforcement may further clip/reject; this study does not claim an exchange-executed quantity.

**Configuration caveat / exact responsible sites:** `application/configs/schemas/position_sizing.py` and `application/configs/profiles/live.py` default `fixed_position_size_enabled=True`, but `bootstrap/container.py::_build_risk_engine` constructs `EnterpriseRiskManager()` with its own default `fixed_position_size_enabled=False`. In the tested event route, the settings flag is read only for the exception fallback; normal successful sizing delegates to the risk manager. Thus the settings flag by itself does **not** select fixed mode in that normal route. This is a configuration-wiring discrepancy, not evidence that dynamic sizing is lost. Smallest proposed remediation, subject to separate approval: explicitly pass the selected sizing settings into the container-built risk manager, then add a regression for both modes. Do not silently change which mode production uses.

**Constraint caveats:** The order object's `requested_leverage` is sourced from settings; it does not alter the dynamic formula. The route's 0.001 floor can exceed a very small calculated risk size, so a later risk gate must reject/clip if necessary. `min_position_size`/`max_position_size` settings were not shown to alter this event route's pre-broker quantity directly; exposure/notional and later risk/broker gates are distinct. `MAX_POSITION_EXPOSURE` in this report refers to the risk manager's `max_position_exposure` field, not proof of a particular environment variable binding. None of these caveats authorizes a fix under F01.

Validation: `python -m pytest -q tests/unit/test_f01_offline_intent_sizing.py tests/unit/test_ngdp_dynamic_position_sizing.py tests/unit/test_paper_trading_safety_attribution.py` → **14 passed**. No profitability, backtest, or broker assertion is implied.

خلاصه ساده: وقتی حالت پویا واقعاً در موتور ریسک فعال باشد و سقف‌ها دخالت نکنند، حدضرر دورتر به سفارش کوچک‌تر منجر می‌شود و این اندازه تا شیء سفارش حفظ می‌شود. اما فلگ fixed در تنظیمات فعلی به موتور ریسک وصل نشده و حداقل حجم می‌تواند محاسبه ریسک بسیار کوچک را بالا ببرد. این‌ها برای بررسی/اصلاح جداگانه ثبت شدند؛ در این تسک تغییری در رفتار سیستم ندادیم.
