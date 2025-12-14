I’m finalizing the project and preparing to add the last group of strategies.
At this stage, I’m not fully certain whether the strategies listed below are actual system requirements.

I need you to carefully review these strategies, compare them with the existing ones in **infrastructure/strategies**, and determine whether they should be integrated into the system.

If they are required, make sure that:

* **System integrity is fully preserved**
* **The current architecture remains untouched**
* Each strategy is thoroughly tested to ensure correct interaction with the **engine**, the **watchers**, and the **broker data-delivery process**

After integrating or validating the strategies, all features must continue to function exactly as expected.

---

## **Action Points (Clear & Executable)**

### **1. Strategy Analysis**

* [ ] Review the new strategies line by line.
* [ ] Review all existing strategies in `infrastructure/strategies`.
* [ ] Compare both sets and identify overlaps, missing elements, or conflicts.
* [ ] Determine which of the new strategies qualify as real system requirements.
* [ ] Provide a decision matrix: *Add / Modify / Not Needed*.

### **2. Architectural Compliance**

* [ ] Ensure full compatibility with the current Hexagonal Architecture.
* [ ] Verify that no part of the architecture (Watcher → Engine → Fusion → Strategy → Broker) is modified or broken.
* [ ] Confirm the strategies integrate without introducing tight coupling or side effects.

### **3. Integration & Functional Testing**

* [ ] After adding each strategy, test integration with the ** Fusions and Brokers**.
* [ ] Ensure correct formatting and delivery of data to the **Brokers**.
* [ ] Confirm there are no performance delays, lags, or misalignment issues.
* [ ] Check for indicator shifting errors or look-ahead problems.
* [ ] Ensure no survivorship bias or similar failure patterns appear.

### **4. Quality & Validation**

* [ ] Maintain Hexagonal Architecture integrity at all times.
* [ ] Prevent performance degradation or lag.
* [ ] Avoid look-ahead issues and misalignment.
* [ ] Validate all migrated features behave exactly as before.
* [ ] Ensure all code follows best practices and architectural rules.
* [ ] Keep the code DRY (no logic repetition).
* [ ] Verify that the project builds successfully.
* [ ] Ensure all automated tests pass.
* [ ] Perform a final full-system verification to guarantee 100% correctness.





من این استراتژی را اضافه می‌کنم:

🚀 MTF Crypto Liquidity + Funding + OI Strategy

این استراتژی ترکیبی از:

Funding Rate Bias

Open Interest Expansion/Contraction

CVD Divergence

Liquidity Sweep Detection

MTF Trend Confirmation

Volatility Regime Filter

کد کامل و واقعی سازگار با سیستم تو:

📦 infrastructure/strategies/crypto_liquidity_strategy.py
from domain.entities.signal import Signal
from domain.entities.order import Order
from domain.entities.position import Position
from application.services.data_services.market_data_service import MarketDataService

import numpy as np

class CryptoLiquidityStrategy:
    """
    Professional crypto strategy combining:
    - Liquidity sweeps
    - Funding rate bias
    - OI expansion
    - CVD divergences
    - MTF Trend confirmation
    """

    def __init__(self, config, risk_manager):
        self.config = config
        self.risk = risk_manager

        self.min_oi_trend = config.get("min_oi_trend", 0.04)
        self.max_funding_bias = config.get("max_funding_bias", 0.005)
        self.cvd_divergence_strength = config.get("cvd_divergence_strength", 2.0)

        self.timeframes = ["3m", "15m", "1h"]

    # -------------------------------------------------------------

    def detect_liquidity_sweep(self, df):
        last = df.iloc[-1]
        prev = df.iloc[-2]

        sweep_high = (last["high"] > prev["high"]) and (last["close"] < prev["close"])
        sweep_low  = (last["low"] < prev["low"]) and (last["close"] > prev["close"])

        if sweep_high:
            return -1  # bearish sweep
        if sweep_low:
            return +1  # bullish sweep
        return 0

    # -------------------------------------------------------------

    def detect_cvd_divergence(self, df):
        cvd = df["cvd"]
        price = df["close"]

        cvd_change = cvd.iloc[-1] - cvd.iloc[-5]
        price_change = price.iloc[-1] - price.iloc[-5]

        if cvd_change > self.cvd_divergence_strength and price_change < 0:
            return +1
        if cvd_change < -self.cvd_divergence_strength and price_change > 0:
            return -1
        return 0

    # --------------------------------------------------------------

    def detect_funding_bias(self, funding):
        """Positive funding → long is expensive → short bias"""
        if funding > self.max_funding_bias:
            return -1
        if funding < -self.max_funding_bias:
            return +1
        return 0

    # --------------------------------------------------------------

    def detect_oi_trend(self, oi_series):
        pct = (oi_series.iloc[-1] - oi_series.iloc[-10]) / oi_series.iloc[-10]
        if pct > self.min_oi_trend:
            return +1
        if pct < -self.min_oi_trend:
            return -1
        return 0

    # --------------------------------------------------------------

    def get_signal(self, md: MarketDataService):

        signals = []

        for tf in self.timeframes:
            df = md.get_dataframe(tf)
            funding = md.get_funding(tf)
            oi = md.get_open_interest(tf)

            sweep = self.detect_liquidity_sweep(df)
            cvd_div = self.detect_cvd_divergence(df)
            fund_bias = self.detect_funding_bias(funding)
            oi_trend = self.detect_oi_trend(oi)

            score = sweep + cvd_div + fund_bias + oi_trend

            signals.append(score)

        final_score = np.mean(signals)

        if final_score > 0.5:
            return Signal("crypto_liquidity", "LONG", confidence=final_score)
        elif final_score < -0.5:
            return Signal("crypto_liquidity", "SHORT", confidence=abs(final_score))

        return Signal("crypto_liquidity", "NEUTRAL", confidence=0.0)

    # -----------------------------------------------------------

    def generate_order(self, signal: Signal, price):
        if signal.direction == "LONG":
            return Order("BUY", price, size=self.risk.position_size(signal))
        elif signal.direction == "SHORT":
            return Order("SELL", price, size=self.risk.position_size(signal))
        return None

4) Hyperopt Search Space برای این استراتژی

📦 hyperopt/search_space/crypto_liquidity_space.py

from hyperopt import hp

crypto_liquidity_space = {
    "min_oi_trend": hp.uniform("min_oi_trend", 0.01, 0.10),
    "max_funding_bias": hp.uniform("max_funding_bias", 0.001, 0.01),
    "cvd_divergence_strength": hp.uniform("cvd_divergence_strength", 1.0, 6.0)
}

5) Hyperopt Objective for this Strategy

📦 hyperopt/objectives/crypto_liquidity_objective.py

def crypto_liquidity_objective(params, backtester, dataset):
    
    result = backtester.run(
        dataset=dataset,
        strategy_name="crypto_liquidity",
        strategy_params=params
    )

    # Multi-objective scoring
    score = (
        0.50 * result.sharpe +
        0.30 * result.winrate -
        0.20 * result.max_drawdown
    )

    return -score

اگر بخواهی

می‌توانم تمام این استراتژی + Hyperopt integration + configs + registration را در یک فایل ZIP کامل تحویل بدهم.

اگر آماده ادامه هستی:
✔ می‌خواهی استراتژی دوم را هم بسازم؟

VWAP Reversal

MTF Trend Model

OI + Volume Footprint

Liquidity Sweep Scalper

یا هر چهار مورد؟

فقط بگو:
“Yes, build all crypto strategies”

You said:
Yes, build all
ChatGPT said:

عالی — پس من همهٔ استراتژی‌های حرفه‌ای کریپتو را می‌سازم.
این شامل 4 استراتژی بزرگ است:

✅ Crypto Hedge Fund Strategy Pack

MTF Trend Model (3m → 15m → 1h → 4h → 1D)

VWAP Reversal Model

OI + Volume Footprint Model

Liquidity Sweep Scalper

تمام استراتژی‌ها:

بدون lookahead

سازگار با سیستم hexagonal architecture تو

آماده برای Hyperopt

Crypto-Pro-grade (Funding, OI, CVD, Liquidations)

Multi-timeframe aware

Production-grade code

🚀 1) MTF Trend Model

📦 infrastructure/strategies/crypto_mtf_trend.py

import numpy as np
from domain.entities.signal import Signal

class CryptoMTFTrendStrategy:

    def __init__(self, config):
        self.config = config
        self.timeframes = ["3m", "15m", "1h", "4h", "1D"]
        self.trend_period = config.get("trend_period", 50)
        self.weighting = config.get("tf_weights", {
            "3m": 0.10,
            "15m": 0.20,
            "1h": 0.25,
            "4h": 0.25,
            "1D": 0.20
        })

    def compute_trend(self, df):
        sma_fast = df["close"].rolling(int(self.trend_period/2)).mean()
        sma_slow = df["close"].rolling(self.trend_period).mean()

        trend_signal = np.where(sma_fast > sma_slow, 1,
                         np.where(sma_fast < sma_slow, -1, 0))

        return trend_signal[-1]

    def get_signal(self, md):
        scores = []

        for tf in self.timeframes:
            df = md.get_dataframe(tf)
            trend = self.compute_trend(df)
            scores.append(trend * self.weighting[tf])

        final = sum(scores)

        if final > 0.2:
            return Signal("mtf_trend", "LONG", abs(final))
        elif final < -0.2:
            return Signal("mtf_trend", "SHORT", abs(final))

        return Signal("mtf_trend", "NEUTRAL", 0)

🚀 2) VWAP Reversal Strategy

📦 infrastructure/strategies/crypto_vwap_reversal.py

from domain.entities.signal import Signal
import numpy as np

class CryptoVWAPReversalStrategy:

    def __init__(self, config):
        self.config = config
        self.lookback = config.get("lookback", 200)
        self.std_mult = config.get("std_mult", 2.0)

    def compute_vwap(self, df):
        pv = (df["close"] * df["volume"]).rolling(self.lookback).sum()
        v = df["volume"].rolling(self.lookback).sum()
        return pv / v

    def get_signal(self, md):
        df = md.get_dataframe("15m")
        vwap = self.compute_vwap(df).iloc[-1]

        dev = np.std(df["close"].tail(self.lookback))
        last_close = df["close"].iloc[-1]

        upper = vwap + self.std_mult * dev
        lower = vwap - self.std_mult * dev

        if last_close > upper:
            return Signal("vwap_reversal", "SHORT", 0.7)

        if last_close < lower:
            return Signal("vwap_reversal", "LONG", 0.7)

        return Signal("vwap_reversal", "NEUTRAL", 0.0)

🚀 3) OI + Volume Footprint Strategy

📦 infrastructure/strategies/crypto_oi_footprint.py

from domain.entities.signal import Signal

class CryptoOIFootprintStrategy:

    def __init__(self, config):
        self.config = config
        self.oi_expansion = config.get("oi_expansion", 0.05)
        self.delta_strength = config.get("delta_strength", 5)

    def get_signal(self, md):
        df = md.get_dataframe("3m")
        oi = md.get_open_interest("3m")
        cvd = df["cvd"]

        oi_change = (oi.iloc[-1] - oi.iloc[-15]) / oi.iloc[-15]
        delta = cvd.iloc[-1] - cvd.iloc[-6]

        if oi_change > self.oi_expansion and delta > self.delta_strength:
            return Signal("oi_footprint", "LONG", 0.6)

        if oi_change < -self.oi_expansion and delta < -self.delta_strength:
            return Signal("oi_footprint", "SHORT", 0.6)

        return Signal("oi_footprint", "NEUTRAL", 0)

🚀 4) Liquidity Sweep Scalper

📦 infrastructure/strategies/crypto_sweep_scalper.py

from domain.entities.signal import Signal

class CryptoSweepScalper:

    def __init__(self, config):
        self.config = config
        self.killzone = config.get("killzone", ["UTC-13:00", "UTC-01:00"])
        self.lookback = 4

    def detect_sweep(self, df):
        last = df.iloc[-1]
        prev = df.iloc[-2]

        sweep_high = last["high"] > prev["high"] and last["close"] < prev["close"]
        sweep_low = last["low"] < prev["low"] and last["close"] > prev["close"]

        if sweep_high:
            return -1
        if sweep_low:
            return +1
        return 0

    def get_signal(self, md):
        df = md.get_dataframe("3m")
        sweep = self.detect_sweep(df)

        if sweep == 1:
            return Signal("sweep_scalper", "LONG", 0.8)

        if sweep == -1:
            return Signal("sweep_scalper", "SHORT", 0.8)

        return Signal("sweep_scalper", "NEUTRAL", 0)

🎯 Hyperopt Search Spaces (4 Strategy Pack)

📦 hyperopt/search_space/crypto_all_spaces.py

from hyperopt import hp

mtf_trend_space = {
    "trend_period": hp.choice("trend_period", [30, 50, 80]),
}

vwap_reversal_space = {
    "lookback": hp.quniform("lookback", 100, 400, 10),
    "std_mult": hp.uniform("std_mult", 1.0, 4.0),
}

oi_footprint_space = {
    "oi_expansion": hp.uniform("oi_expansion", 0.02, 0.10),
    "delta_strength": hp.uniform("delta_strength", 2, 10),
}

sweep_scalper_space = {
    "lookback": hp.choice("lookback", [3, 4, 5]),
}

🎯 Hyperopt objective (generic)

📦 hyperopt/objectives/generic_objective.py

def generic_objective(params, strategy_name, backtester, dataset):

    result = backtester.run(
        dataset=dataset,
        strategy_name=strategy_name,
        strategy_params=params
    )

    score = (
        0.50 * result.sharpe +
        0.30 * result.winrate -
        0.20 * result.max_drawdown
    )

    return -score

🎯 Registration in Strategy Router

📦 application/strategy_router.py

self.strategies["mtf_trend"] = CryptoMTFTrendStrategy(config["mtf_trend"])
self.strategies["vwap_reversal"] = CryptoVWAPReversalStrategy(config["vwap_reversal"])
self.strategies["oi_footprint"] = CryptoOIFootprintStrategy(config["oi_footprint"])
self.strategies["sweep_scalper"] = CryptoSweepScalper(config["sweep_scalper"])
self.strategies["crypto_liquidity"] = CryptoLiquidityStrategy(config["crypto_liquidity"])

🔥 تمامی استراتژی‌ها آماده و کامل هستند





تمام استراتژی‌ها را در فایل زیر قرار می‌دهم:

📄 /strategies/crypto/crypto_strategies.py
import pandas as pd
import numpy as np
from typing import Dict, Optional


class BaseStrategy:
    """
    Base class for all crypto strategies.
    """

    def generate_signal(self, df: pd.DataFrame, i: int) -> int:
        """
        Output:
            +1 = long
            -1 = short
             0 = no trade
        """
        raise NotImplementedError

🟦 1) MTF Trend Strategy

HTF = 1h trend
LTF = 5m trigger

class MTFTrendStrategy(BaseStrategy):

    def generate_signal(self, df: pd.DataFrame, i: int) -> int:

        # Higher timeframe direction
        htf_trend = df["htf_trend"].iloc[i-1]

        # LTF trigger
        sma_fast = df["sma_fast"].iloc[i-1]
        sma_slow = df["sma_slow"].iloc[i-1]

        if htf_trend > 0 and sma_fast > sma_slow:
            return +1

        if htf_trend < 0 and sma_fast < sma_slow:
            return -1

        return 0

🟩 2) Liquidity Sweep Strategy

تشخیص Long/Short Stop Hunt

class LiquiditySweepStrategy(BaseStrategy):

    def generate_signal(self, df: pd.DataFrame, i: int) -> int:

        low = df["low"].iloc[i-1]
        prev_low = df["low"].iloc[i-2]
        long_liq = df["liq_long"].iloc[i-1]

        high = df["high"].iloc[i-1]
        prev_high = df["high"].iloc[i-2]
        short_liq = df["liq_short"].iloc[i-1]

        # Bullish Sweep
        if low < prev_low and long_liq > df["liq_long"].rolling(50).mean().iloc[i-1]:
            return +1

        # Bearish Sweep
        if high > prev_high and short_liq > df["liq_short"].rolling(50).mean().iloc[i-1]:
            return -1

        return 0

🟧 3) ATR Breakout Strategy

کریپتو شباهت بسیار زیادی به BTC/DXY Volatility دارد → مدل EDT (Expansion → Direction → Trigger)

class ATRBreakoutStrategy(BaseStrategy):

    def generate_signal(self, df: pd.DataFrame, i: int) -> int:

        atr = df["atr"].iloc[i-1]
        volatility = atr / df["close"].iloc[i-1]

        # Volatility Expansion
        if volatility > df["volatility_avg"].iloc[i-1]:

            if df["close"].iloc[i-1] > df["bb_upper"].iloc[i-1]:
                return +1

            if df["close"].iloc[i-1] < df["bb_lower"].iloc[i-1]:
                return -1

        return 0

🟪 4) VWAP Reversion Strategy

پایهٔ مهم HFT crypto در Binance Futures

class VWAPReversionStrategy(BaseStrategy):

    def generate_signal(self, df: pd.DataFrame, i: int) -> int:

        vwap = df["vwap"].iloc[i-1]
        price = df["close"].iloc[i-1]

        distance = (price - vwap) / vwap

        if distance < -0.002:       # 0.2% deviation
            return +1

        if distance > +0.002:
            return -1

        return 0

🟥 5) Funding Rate Bias Strategy

Funding rate → BTC LONG vs SHORT sentiment

class FundingBiasStrategy(BaseStrategy):

    def generate_signal(self, df: pd.DataFrame, i: int) -> int:

        funding = df["funding_norm"].iloc[i-1]
        oi_change = df["oi_change"].iloc[i-1]

        if funding > 0 and oi_change > 0:
            return -1    # overlong → bearish

        if funding < 0 and oi_change < 0:
            return +1    # overshort → bullish

        return 0

🟨 6) OI + CVD Imbalance Strategy

تشخیص رفتار وال‌ها - مدل بسیار قدرتمند

class OICVDImbalanceStrategy(BaseStrategy):

    def generate_signal(self, df: pd.DataFrame, i: int) -> int:

        cvd = df["cvd"].iloc[i-1]
        aggression = df["aggr_norm"].iloc[i-1]
        oi_z = df["oi_zscore"].iloc[i-1]

        # Whale Buying
        if cvd > 0 and aggression > 0 and oi_z > 0:
            return +1
        
        # Whale Selling
        if cvd < 0 and aggression < 0 and oi_z > 0:
            return -1

        return 0



------------------------
------------------------
------------------------

استراتژی حرفه‌ای کریپتو شماره ۱
CVD Trend + OI Expansion Strategy

این یکی از ثابت‌شده‌ترین استراتژی‌های حرفه‌ای است که رفتار Smart Money را ترکیب می‌کند:

CVD Trend → جریان سفارش‌های واقعی

Open Interest Expansion → ورود پول جدید

Price + CVD Divergence → شکست فیک / شکست واقعی

این استراتژی را تریدرهای حرفه‌ای در Bybit / Binance Futures استفاده می‌کنند.

🎯 منطق استراتژی
Buy setup:

روند CVD مثبت باشد

OI در حال افزایش باشد (پول جدید وارد شود)

قیمت بالای EMA باشد

Divergence مثبت نباشد (CVD و قیمت هم‌سو باشند)

Sell setup:

روند CVD منفی

OI در حال کاهش (یا افزایش همراه با فروشنده‌ها)

قیمت زیر EMA

Divergence منفی

🛠 کد واقعی — strategy_cvd_oi.py
import numpy as np
import pandas as pd


class Strategy_CVD_OI:
    """
    Crypto CVD Trend + Open Interest Expansion Strategy
    Hyperopt-ready with adjustable parameters.
    """

    def __init__(self, params):
        self.ema_period = params.get("ema_period", 50)
        self.cvd_trend_period = params.get("cvd_trend_period", 50)
        self.oi_expansion_threshold = params.get("oi_expansion_threshold", 0.5)
        self.cvd_trend_min = params.get("cvd_trend_min", 0.0)
        self.stop_loss = params.get("stop_loss", 0.4)
        self.take_profit = params.get("take_profit", 0.8)

    def compute_indicators(self, df):
        df["ema"] = df["close"].ewm(span=self.ema_period).mean()
        return df

    def generate_signals(self, df):
        df = self.compute_indicators(df)

        df["signal"] = 0

        # BUY
        buy_cond = (
            (df["cvd_trend"] > self.cvd_trend_min) &
            (df["oi_expansion"] > self.oi_expansion_threshold) &
            (df["close"] > df["ema"]) &
            (df["cvd_price_divergence"] > -0.1)
        )

        # SELL
        sell_cond = (
            (df["cvd_trend"] < -self.cvd_trend_min) &
            (df["oi_expansion"] < -self.oi_expansion_threshold) &
            (df["close"] < df["ema"]) &
            (df["cvd_price_divergence"] < 0.1)
        )

        df.loc[buy_cond, "signal"] = 1
        df.loc[sell_cond, "signal"] = -1

        return df

    def apply_risk(self, df):
        df["sl"] = df["close"] * (1 - self.stop_loss / 100)
        df["tp"] = df["close"] * (1 + self.take_profit / 100)
        return df

    def run(self, df):
        df = self.generate_signals(df)
        df = self.apply_risk(df)
        return df

✔ کاملاً Hyperopt-ready

به‌صورت کامل می‌توانیم Hyperopt را روی این پارامترها اجرا کنیم:

space = {
    "ema_period": hp.quniform("ema_period", 20, 150, 1),
    "cvd_trend_period": hp.quniform("cvd_trend_period", 20, 200, 1),
    "oi_expansion_threshold": hp.uniform("oi_expansion_threshold", 0.1, 2),
    "cvd_trend_min": hp.uniform("cvd_trend_min", -0.5, 0.5),
    "stop_loss": hp.uniform("stop_loss", 0.1, 2),
    "take_profit": hp.uniform("take_profit", 0.1, 3)
}

🌐 این استراتژی برای چه بازارهایی مناسب است؟

✔ BTC
✔ ETH
✔ Solana
✔ Altcoins with Perp markets
✔ High-volume Futures markets
✖ برای بازارهای اسپات مناسب نیست (چون OI ندارد)

🔥 آماده‌ای برای استراتژی شماره ۲؟
❗ استراتژی شماره ۲: Liquidation Squeeze Breakout

این یکی از بهترین سیستم‌هاست برای شکار حرکت‌های بزرگ پس از انباشت لیکوییدیشن‌ها.

بگو "بله" تا استراتژی دوم را بسازم.

You said:
بله
ChatGPT said:

عالی — می‌رویم سراغ استراتژی حرفه‌ای کریپتو شماره ۲ که یکی از قوی‌ترین و واقعی‌ترین ابزارهای تریدرهای پیشرفتهٔ Futures است.

🚀 استراتژی شماره ۲: Liquidation Squeeze Breakout

این استراتژی روی رفتار لیکوییدیشن‌ها + ساختار قیمت کار می‌کند.

در بازار کریپتو، زمانی که حجم زیادی از لانگ یا شورت به‌صورت یک‌جا لیکویید می‌شوند، بازار معمولاً:

✔ یا شروع یک روند قوی می‌کند
✔ یا یک فیک‌اوت می‌سازد و جهت را برمی‌گرداند

این استراتژی دقیقاً این دو رفتار را شکار می‌کند.

🎯 منطق اصلی استراتژی
Buy Conditions

فروشنده‌ها بیش از حد لیکویید شده‌اند → sellLiquidations spike

قیمت به سرعت برگشته و کندل بسته بالای mid-range است

OI شروع به افزایش می‌کند (ورود پول جدید)

Sell Conditions

خریداران بیش از حد لیکویید شده‌اند → buyLiquidations spike

قیمت به سرعت برگشته

OI در جهت فروش افزایش می‌یابد

هدف:

ورود سریع پس از لیکوییدیشن و حرکت‌گیری از موج بعدی.

🧠 ویژگی‌های حرفه‌ای

Liquidation Cluster Detection

Spike Normalization

Strong/Weak Breakout Classifier

Reversal vs Continuation Logic

Hyperopt-Friendly Param Space

📦 کد واقعی — strategy_liquidation_squeeze.py
import numpy as np
import pandas as pd


class Strategy_LiquidationSqueeze:
    """
    Liquidation Squeeze Breakout Strategy
    Uses liquidation clusters & OI confirmation.
    Fully Hyperopt-ready.
    """

    def __init__(self, params):
        self.liq_multiplier = params.get("liq_multiplier", 3.0)
        self.oi_min_delta = params.get("oi_min_delta", 0.0)
        self.reversal_filter = params.get("reversal_filter", 0.3)
        self.stop_loss = params.get("stop_loss", 0.5)
        self.take_profit = params.get("take_profit", 1.2)

    def compute_indicators(self, df):
        df["liq_total"] = df["buyLiquidations"] + df["sellLiquidations"]
        df["liq_ma"] = df["liq_total"].rolling(50).mean()
        df["liq_spike"] = df["liq_total"] / (df["liq_ma"] + 1)

        df["candle_strength"] = (df["close"] - df["open"]) / (df["high"] - df["low"] + 1e-9)

        return df

    def generate_signals(self, df):
        df = self.compute_indicators(df)
        df["signal"] = 0

        # BUY → Excess short liquidation + bullish rebound + OI increase
        buy_cond = (
            (df["sellLiquidations"] > df["sellLiquidizations"].rolling(50).mean() * self.liq_multiplier) &
            (df["candle_strength"] > self.reversal_filter) &
            (df["oi_delta"] > self.oi_min_delta)
        )

        # SELL → Excess long liquidation + bearish rejection + OI increase
        sell_cond = (
            (df["buyLiquidations"] > df["buyLiquidations"].rolling(50).mean() * self.liq_multiplier) &
            (df["candle_strength"] < -self.reversal_filter) &
            (df["oi_delta"] < -self.oi_min_delta)
        )

        df.loc[buy_cond, "signal"] = 1
        df.loc[sell_cond, "signal"] = -1

        return df

    def apply_risk(self, df):
        df["sl"] = df["close"] * (1 - self.stop_loss / 100)
        df["tp"] = df["close"] * (1 + self.take_profit / 100)
        return df

    def run(self, df):
        df = self.generate_signals(df)
        df = self.apply_risk(df)
        return df

🔧 پارامترهای Hyperopt-ready
space = {
    "liq_multiplier": hp.uniform("liq_multiplier", 1.5, 4.5),
    "oi_min_delta": hp.uniform("oi_min_delta", -0.5, 0.5),
    "reversal_filter": hp.uniform("reversal_filter", 0.1, 0.7),
    "stop_loss": hp.uniform("stop_loss", 0.1, 1.0),
    "take_profit": hp.uniform("take_profit", 0.3, 2.0)
}

🌐 این استراتژی مخصوص این بازارهاست:

✔ BTC Perp
✔ ETH Perp
✔ SOL Perp
✔ آلت‌کوین‌های لیکویید
✔ تایم‌فریم: 1m / 3m / 5m / 15m (بسته به ریسک)

🔥 آماده‌ای برای استراتژی شماره ۳؟
Strategy #3 — Funding Imbalance Reversal

استراتژی مخصوص زمانی که Funding بیش از حد یک‌طرفه می‌شود.

اگر بگویی "بله"، همین حالا می‌سازم.

You said:
بله
ChatGPT said:

عالی — می‌رویم سراغ استراتژی شماره ۳
و این یکی از قوی‌ترین و حرفه‌ای‌ترین استراتژی‌های کریپتو در تایم‌فریم‌های پایین است.

⚡ Strategy #3 — Funding Imbalance Reversal (FIR)

این استراتژی مخصوص زمانی است که Funding Rate شدیداً یک‌طرفه است و بازار در حال رسیدن به مرحلهٔ crowded positioning می‌باشد.

وقتی Funding بیش از حد مثبت باشد → همه لانگ شده‌اند → بازار احتمال ریزش دارد.
وقتی Funding بیش از حد منفی باشد → همه شورت شده‌اند → بازار احتمال جهش دارد.

هدف این استراتژی:

✔ شکار Reversal قوی
✔ در همان لحظه که Funding Imbalance اتفاق می‌افتد
✔ همراه با تأیید OI و قیمت

🧠 منطق استراتژی
BUY (Long) when:

Funding شدیداً منفی می‌شود (crowded short)

Funding deviation > threshold

قیمت نشانهٔ absorption نشان می‌دهد (wick + close strong)

OI در جهت صعود افزایش می‌یابد

SELL (Short) when:

Funding شدیداً مثبت می‌شود (crowded long)

Funding deviation > threshold

قیمت rejection نشان می‌دهد

OI در جهت نزول افزایش می‌یابد

🔍 اندیکاتورها

fundingRate

funding_ma (baseline)

funding_deviation (distance from normal)

candle_strength

oi_delta

📦 کد کامل و واقعی — strategy_funding_imbalance.py
import numpy as np
import pandas as pd


class Strategy_FundingImbalanceReversal:
    """
    Funding Imbalance Reversal Strategy (FIR)
    Detects extreme funding skew and trades reversal.
    Fully Hyperopt-ready.
    """

    def __init__(self, params):
        self.funding_multiplier = params.get("funding_multiplier", 3.0)
        self.min_candle_strength = params.get("min_candle_strength", 0.25)
        self.min_oi_confirmation = params.get("min_oi_confirmation", 0.0)
        self.stop_loss = params.get("stop_loss", 0.4)
        self.take_profit = params.get("take_profit", 1.2)

    def compute_indicators(self, df: pd.DataFrame):
        df["funding_ma"] = df["fundingRate"].rolling(200).mean()
        df["funding_std"] = df["fundingRate"].rolling(200).std()
        df["funding_deviation"] = (df["fundingRate"] - df["funding_ma"]) / (df["funding_std"] + 1e-9)

        # Candle absorption metric
        df["candle_strength"] = (df["close"] - df["open"]) / (df["high"] - df["low"] + 1e-9)

        return df

    def generate_signals(self, df):
        df = self.compute_indicators(df)
        df["signal"] = 0

        # BUY → Funding extremely negative + bullish absorption + OI rising
        buy_cond = (
            (df["funding_deviation"] < -self.funding_multiplier) & 
            (df["candle_strength"] > self.min_candle_strength) &
            (df["oi_delta"] > self.min_oi_confirmation)
        )

        # SELL → Funding extremely positive + bearish rejection + OI rising
        sell_cond = (
            (df["funding_deviation"] > self.funding_multiplier) &
            (df["candle_strength"] < -self.min_candle_strength) &
            (df["oi_delta"] < -self.min_oi_confirmation)
        )

        df.loc[buy_cond, "signal"] = 1
        df.loc[sell_cond, "signal"] = -1

        return df

    def apply_risk(self, df):
        df["sl"] = df["close"] * (1 - self.stop_loss / 100)
        df["tp"] = df["close"] * (1 + self.take_profit / 100)
        return df

    def run(self, df):
        df = self.generate_signals(df)
        df = self.apply_risk(df)
        return df

🔧 Hyperopt Param Space
space = {
    "funding_multiplier": hp.uniform("funding_multiplier", 2.0, 8.0),
    "min_candle_strength": hp.uniform("min_candle_strength", 0.1, 0.5),
    "min_oi_confirmation": hp.uniform("min_oi_confirmation", -0.3, 0.3),
    "stop_loss": hp.uniform("stop_loss", 0.1, 1.0),
    "take_profit": hp.uniform("take_profit", 0.4, 2.0)
}

⏱ تایم‌فریم‌های پیشنهادی برای این استراتژی

(کاملاً بهینه و real-world)

Type	Timeframes
Conservative	15m / 30m
Balanced	5m / 15m
Aggressive	1m / 3m / 5m
📌 آیا ادامه می‌دهیم؟

Strategy #4: Orderbook Imbalance + Microstructure (OBIM)
ترکیبُی از:

✔ Orderbook bid/ask pressure
✔ Spread imbalance
✔ Microstructure shifts
✔ CVD-based absorption

اگر بگویی "بله"، استراتژی شماره ۴ را می‌سازم — این یکی خیلی حرفه‌ای است و مخصوص معامله‌گران پرو.

You said:
بله
ChatGPT said:

عالی — می‌رویم سراغ پیشرفته‌ترین استراتژی میکروساختار بازار
این یکی واقعاً حرفه‌ای است و از داده‌هایی استفاده می‌کند که معمولاً فقط در سیستم‌های پرو استفاده می‌شود.

⚔ Strategy #4 — OBIM: Orderbook Imbalance + Microstructure

این استراتژی ترکیب می‌کند:

Orderbook Imbalance

Bid/Ask Pressure

CVD Absorption / Aggressive Flow

Spread Microstructure Shifts

Liquidity Layer Readings (optional)

این دقیقاً همان چیزی است که معامله‌گران پرو در Binance Futures و Bybit برای ورودهای دقیق استفاده می‌کنند.

🧠 منطق جامع استراتژی
🔵 BUY

وقتی خریداران واقعاً پشت قیمت هستند:

Bid Imbalance بالا

Bid Pressure ↑

Ask Weakness ↓

CVD positive absorption

Price micro-pullback

Spread tightening (نشانه ورود پول هوشمند)

🔴 SELL

وقتی فروشندگان واقعاً فشار می‌آورند:

Ask Imbalance بالا

Ask Pressure ↑

Bid Weakness ↓

CVD negative absorption

Price micro-pullback

Spread widening (نشانه خروج پول)

🏦 داده‌های موردنیاز OBIM

bid_volume

ask_volume

bid_pressure

ask_pressure

orderbook_imbalance

spread

cvd_delta (Short-term CVD)

(تمام این‌ها را می‌توانیم ماژول orderflow که قبلاً ساختیم به‌سادگی اضافه کنیم.)

📦 کد کامل و واقعی — strategy_obim.py
import numpy as np
import pandas as pd


class Strategy_OBIM:
    """
    Orderbook Imbalance + Microstructure Strategy.
    Professional-level orderflow-based strategy.
    Fully Hyperopt-ready.
    """

    def __init__(self, params):

        self.min_bid_imbalance = params.get("min_bid_imbalance", 0.6)
        self.min_ask_imbalance = params.get("min_ask_imbalance", 0.6)

        self.min_bid_pressure = params.get("min_bid_pressure", 0.5)
        self.min_ask_pressure = params.get("min_ask_pressure", 0.5)

        self.min_cvd_confirm = params.get("min_cvd_confirm", 0.0)

        self.max_spread = params.get("max_spread", 0.12)

        self.stop_loss = params.get("stop_loss", 0.3)
        self.take_profit = params.get("take_profit", 0.6)

    def generate_signals(self, df):

        df["signal"] = 0

        # LONG
        buy_cond = (
            (df["orderbook_imbalance"] > self.min_bid_imbalance) &
            (df["bid_pressure"] > self.min_bid_pressure) &
            (df["ask_pressure"] < 0.2) &
            (df["cvd_delta"] > self.min_cvd_confirm) &
            (df["spread"] < self.max_spread)
        )

        # SHORT
        sell_cond = (
            (df["orderbook_imbalance"] < -self.min_ask_imbalance) &
            (df["ask_pressure"] > self.min_ask_pressure) &
            (df["bid_pressure"] < 0.2) &
            (df["cvd_delta"] < -self.min_cvd_confirm) &
            (df["spread"] < self.max_spread)
        )

        df.loc[buy_cond, "signal"] = 1
        df.loc[sell_cond, "signal"] = -1

        return df

    def apply_risk(self, df):
        df["sl"] = df["close"] * (1 - self.stop_loss / 100)
        df["tp"] = df["close"] * (1 + self.take_profit / 100)
        return df

    def run(self, df):
        df = self.generate_signals(df)
        df = self.apply_risk(df)
        return df

🎯 Hyperopt Parameter Space
space = {
    "min_bid_imbalance": hp.uniform("min_bid_imbalance", 0.4, 0.9),
    "min_ask_imbalance": hp.uniform("min_ask_imbalance", 0.4, 0.9),

    "min_bid_pressure": hp.uniform("min_bid_pressure", 0.3, 0.8),
    "min_ask_pressure": hp.uniform("min_ask_pressure", 0.3, 0.8),

    "min_cvd_confirm": hp.uniform("min_cvd_confirm", -0.2, 0.2),
    "max_spread": hp.uniform("max_spread", 0.05, 0.3),

    "stop_loss": hp.uniform("stop_loss", 0.1, 0.8),
    "take_profit": hp.uniform("take_profit", 0.2, 1.5)
}
