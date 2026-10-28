- Always you must cover the rules and requirements that written in ./tasks/task0-force-to-cover.md

Below is a **production-grade Hedge-Fund Prompt + Specification** you can give to any senior engineer, LLM, or internal team to implement **pre-forensic logging** before entering *Hedge Fund Forensic Optimization*.
This is written for **crypto, high-scale, institutional deployment**.

No hype. Only engineering truth.

---

# 🎯 PURPOSE

Implement **Institutional-Grade Decision Traceability Logging** across the entire:

> Watcher → Engine → Fusion → Strategy → Broker

pipeline, so that **every trade can be forensically reconstructed, statistically audited, and optimized**.

This logging layer must make the system:

* Auditable
* Statistically optimizable
* Hyperopt-safe
* Production-scale
* Regime-aware
* Failure-diagnosable

---

# 🧠 CORE PRINCIPLE

> A trade that cannot be fully reconstructed is a liability.

---

# 🔹 GLOBAL LOG RULES

All logs must:

* Be JSON structured
* Include `trace_id` shared across pipeline
* Be strictly append-only
* Be latency-safe
* Never block execution
* Be compressible
* Be stream-friendly (Kafka / ClickHouse / BigQuery ready)

---

# 🔹 GLOBAL FIELDS (All Logs)

```json
{
  "trace_id": "UUID",
  "layer": "WATCHER|ENGINE|FUSION|STRATEGY|BROKER",
  "exchange": "BINANCE",
  "symbol": "BTCUSDT",
  "timestamp": "ISO8601",
  "processing_latency_ms": 1.24,
  "regime_context": "TREND|RANGE|VOLATILE|UNKNOWN"
}
```

**Why:**
Traceability, latency attribution, regime accountability.

---

# 🟦 WATCHER LOG

### Purpose

Prove raw market perception without interpretation.

```json
{
  "layer": "WATCHER",
  "watcher": "TrendMTF",
  "observation_type": "trend_positive",
  "raw_value": 0.0034,
  "confidence": 0.62,
  "timeframe_sources": ["1m","5m","15m"],
  "data_freshness_sec": 1.2,
  "historical_percentile": 0.71
}
```

**Why hedge-fund level:**

| Field                 | Reason                    |
| --------------------- | ------------------------- |
| raw_value             | Prevents abstraction loss |
| timeframe_sources     | MTF accountability        |
| historical_percentile | Context vs history        |
| data_freshness_sec    | Latency bias detection    |

---

# 🟩 ENGINE LOG

### Purpose

Show interpretation logic quality.

```json
{
  "layer": "ENGINE",
  "engine": "TrendEngine",
  "input_observation": "trend_positive",
  "interpreted_signal": "BUY",
  "confidence": 0.58,
  "signal_strength": 0.41,
  "internal_metrics": {
    "slope": 0.0023,
    "atr": 125.34,
    "volatility_score": 0.78
  },
  "historical_engine_accuracy": 0.63
}
```

**Why:**

| Field                      | Reason                          |
| -------------------------- | ------------------------------- |
| signal_strength            | Confidence alone is meaningless |
| historical_engine_accuracy | Learning capability             |
| internal_metrics           | Forensic reproducibility        |

---

# 🟨 FUSION LOG

### Purpose

Explain why engines were trusted or ignored.

```json
{
  "layer": "FUSION",
  "fused_direction": "BUY",
  "confidence": 0.66,
  "contributors": {
    "TrendEngine": 0.32,
    "OrderFlowEngine": 0.21,
    "VolatilityEngine": 0.13
  },
  "correlation_penalty": 0.18,
  "diversity_score": 0.71,
  "rejected_engines": [
    {"engine":"LiquidityEngine","reason":"low_confidence"}
  ],
  "fusion_entropy": 0.42
}
```

**Why:**

| Field               | Reason                   |
| ------------------- | ------------------------ |
| correlation_penalty | Avoid hidden redundancy  |
| diversity_score     | True signal independence |
| fusion_entropy      | Decision stability       |
| rejected_engines    | Accountability           |

---

# 🟧 STRATEGY LOG

### Purpose

Explain decision responsibility.

```json
{
  "layer": "STRATEGY",
  "strategy": "trend_following",
  "decision": "BUY",
  "confidence": 0.64,
  "position_state": "FLAT",
  "suppression_applied": false,
  "risk_profile": {
    "risk_pct": 0.01,
    "max_size": 0.05
  },
  "decision_score_components": {
    "fusion_weight": 0.55,
    "regime_alignment": 0.21,
    "risk_adjustment": -0.12
  }
}
```

**Why:**

| Field                     | Reason              |
| ------------------------- | ------------------- |
| position_state            | Duplicate reasoning |
| suppression_applied       | Overtrade detection |
| decision_score_components | Accountability      |

---

# 🟥 BROKER LOG

### Purpose

Ensure execution reality.

```json
{
  "layer": "BROKER",
  "side": "BUY",
  "price": 43782.5,
  "quantity": 0.18,
  "sl": 43520,
  "tp": 44240,
  "expected_slippage": 0.6,
  "actual_slippage": 0.8,
  "fee": 3.12,
  "latency_ms": 42,
  "order_status_flow": ["NEW","ACCEPTED","FILLED"]
}
```

---

# 🟪 BROKER CLOSE LOG

```json
{
  "layer": "BROKER_CLOSE",
  "exit_reason": "TAKE_PROFIT",
  "pnl": 82.35,
  "roi_pct": 0.0104,
  "holding_seconds": 312,
  "max_favorable_excursion": 0.014,
  "max_adverse_excursion": -0.006
}
```

**Why:**

Allows SL/TP model optimization.

---

# 🧠 CRITICAL: WHERE TO PLACE

| Layer        | Log Type                |
| ------------ | ----------------------- |
| Watcher      | After observation       |
| Engine       | After interpretation    |
| Fusion       | After aggregation       |
| Strategy     | Before execution intent |
| Broker       | After exchange response |
| Broker Close | After position close    |

---

# 🎯 RESULT

After this logging:

You can:

✔ Rebuild every trade
✔ Attribute loss to exact layer
✔ Train ML correctly
✔ Tune fusion statistically
✔ Detect regime misclassification
✔ Detect overconfidence bias
✔ Detect signal instability
✔ Detect execution drag

---

# 🚨 FINAL TRUTH

Without this logging:

> You are trading blind with good architecture.

With this logging:

> You are running a research-grade trading system.

---

# 🔚 NEXT STAGE AFTER THIS

Only after this layer is implemented, you are allowed to enter:

> Hedge Fund Forensic Optimization Phase

Where optimization is based on **proof**, not belief.


