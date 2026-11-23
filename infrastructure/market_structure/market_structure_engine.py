"""Market Structure Engine: volume profile (POC/VAH/VAL), swing support/resistance and bias.

Standard definitions (E16-U8, 2026-11-23):
  * Volume profile: each bar's volume is spread uniformly over its own high-low range on a
    ``volume_profile_bins`` grid (formerly the whole volume was put in the bin of the CLOSE with 10 bins:
    POC more than 1 ATR away from a 1m-resolution profile in 23 % of 20-hour windows; now 10 %, median
    POC / VAL / VAH error 0.14 / 0.10 / 0.12 ATR on HOLDOUT). Value area = 70 % of volume grown from the
    POC towards the larger neighbouring bin.
  * Support / resistance: the most recent CONFIRMED swing low below / swing high above the last close
    (fractal pivot: lower/higher than ``pivot_bars`` bars on each side; the last ``pivot_bars`` bars cannot
    be confirmed yet). Fallback: lowest low / highest high of the PREVIOUS bars (current bar excluded).
  * Bias: last close vs POC with a buffer of ``bias_atr_buffer`` x ATR (formerly a fixed 0.1 %).
Return keys unchanged (bias, poc, vah, val, support, resistance) plus ``atr`` and ``method``.
"""

from typing import Any, Dict, List, Optional

import numpy as np


class MarketStructureEngine:
    def __init__(self, swing_lookback: int = 20, volume_profile_bins: int = 24, pivot_bars: int = 2,
                 bias_atr_buffer: float = 0.25, method: str = "range"):
        self.method = method                       # "range" (standard) | "legacy_close" (frozen research)
        self._legacy_bins = 10 if method == "legacy_close" and volume_profile_bins == 24 else volume_profile_bins
        self.swing_lookback = swing_lookback
        self.volume_profile_bins = volume_profile_bins
        self.pivot_bars = pivot_bars
        self.bias_atr_buffer = bias_atr_buffer

    # -- volume profile ---------------------------------------------------------------------------
    @staticmethod
    def volume_profile(lows, highs, closes, volumes, bins: int):
        lo, hi = float(min(lows)), float(max(highs))
        if hi <= lo:
            return None
        edges = np.linspace(lo, hi, bins + 1)
        vol = np.zeros(bins)
        width = edges[1] - edges[0]
        for l, h, c, v in zip(lows, highs, closes, volumes):
            v = float(v)
            if v <= 0:
                continue
            l, h = float(l), float(h)
            if h <= l:  # zero-range bar: all volume at its price
                vol[min(bins - 1, max(0, int((float(c) - lo) / width)))] += v
                continue
            overlap = np.clip(np.minimum(edges[1:], h) - np.maximum(edges[:-1], l), 0.0, None)
            total = overlap.sum()
            if total > 0:
                vol += v * overlap / total
        return edges, vol

    @staticmethod
    def value_area(edges, vol, share: float = 0.70):
        k = int(np.argmax(vol))
        lo_i = hi_i = k
        acc, total = vol[k], vol.sum()
        while acc < share * total and (lo_i > 0 or hi_i < len(vol) - 1):
            left = vol[lo_i - 1] if lo_i > 0 else -1.0
            right = vol[hi_i + 1] if hi_i < len(vol) - 1 else -1.0
            if left >= right:
                lo_i -= 1
                acc += left
            else:
                hi_i += 1
                acc += right
        return float((edges[k] + edges[k + 1]) / 2), float(edges[lo_i]), float(edges[hi_i + 1])

    # -- swings -----------------------------------------------------------------------------------
    def _swing_levels(self, highs, lows, price) -> Dict[str, Optional[float]]:
        k, n = self.pivot_bars, len(highs)
        sup = res = None
        for i in range(n - 1 - k, k - 1, -1):   # newest confirmed pivot first
            window_h, window_l = highs[i - k:i + k + 1], lows[i - k:i + k + 1]
            if res is None and highs[i] == max(window_h) and highs[i] > price:
                res = float(highs[i])
            if sup is None and lows[i] == min(window_l) and lows[i] < price:
                sup = float(lows[i])
            if sup is not None and res is not None:
                break
        return {"support": sup, "resistance": res}

    @staticmethod
    def _atr(highs, lows, closes, period: int = 14) -> float:
        if len(closes) < 2:
            return float(highs[-1] - lows[-1]) if highs else 0.0
        tr = [max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1]))
              for i in range(1, len(closes))]
        return float(np.mean(tr[-period:]))

    def calculate_market_structure(self, prices: List[float], highs: List[float],
                                   lows: List[float], volumes: List[float]) -> Dict[str, Any]:
        if self.method == "legacy_close":
            return self._legacy_close_profile(prices, highs, lows, volumes)
        n = len(prices)
        if n < 5:
            current_price = prices[-1] if n > 0 else 0.0
            return {"bias": "NEUTRAL", "poc": current_price, "vah": current_price, "val": current_price,
                    "support": current_price, "resistance": current_price, "atr": 0.0, "method": "insufficient"}

        lookback = min(self.swing_lookback, n)
        c, h, l = list(map(float, prices[-lookback:])), list(map(float, highs[-lookback:])), list(map(float, lows[-lookback:]))
        v = list(map(float, volumes[-lookback:])) if volumes and len(volumes) >= lookback else [1.0] * lookback
        price = c[-1]
        atr = self._atr(h, l, c)

        prof = self.volume_profile(l, h, c, v, self.volume_profile_bins)
        if prof is None or prof[1].sum() <= 0:
            poc = vah = val = price
        else:
            poc, val, vah = self.value_area(*prof)

        swings = self._swing_levels(h, l, price)
        prev_h, prev_l = (h[:-1] or h), (l[:-1] or l)
        support = swings["support"] if swings["support"] is not None else float(min(prev_l))
        resistance = swings["resistance"] if swings["resistance"] is not None else float(max(prev_h))

        buffer = self.bias_atr_buffer * atr if atr > 0 else 0.001 * price
        bias = "LONG" if price > poc + buffer else "SHORT" if price < poc - buffer else "NEUTRAL"
        return {"bias": bias, "poc": poc, "vah": vah, "val": val, "support": support, "resistance": resistance,
                "atr": atr, "method": "range_volume_profile"}

    def _legacy_close_profile(self, prices: List[float], highs: List[float],
                                  lows: List[float], volumes: List[float]) -> Dict[str, Any]:
        """Former algorithm (whole bar volume at its close, 10 bins, 20-bar Donchian S/R incl. current bar,
        0.1 % bias). Kept only for frozen research replays (method='legacy_close')."""
        n = len(prices)
        if n < 5:
            # Guard against insufficient data
            current_price = prices[-1] if n > 0 else 0.0
            return {
                "bias": "NEUTRAL",
                "poc": current_price,
                "vah": current_price,
                "val": current_price,
                "support": current_price,
                "resistance": current_price
            }

        # 1. Swing Highs / Lows (Support / Resistance)
        lookback = min(self.swing_lookback, n)
        recent_highs = highs[-lookback:]
        recent_lows = lows[-lookback:]

        resistance = float(max(recent_highs))
        support = float(min(recent_lows))

        # 2. Volume Profile (POC / VAH / VAL)
        all_prices = prices[-lookback:]
        all_vols = volumes[-lookback:]

        min_price = min(all_prices)
        max_price = max(all_prices)
        price_range = max_price - min_price

        if price_range == 0:
            poc = min_price
            vah = min_price
            val = min_price
        else:
            bin_size = price_range / self._legacy_bins
            bins = [min_price + i * bin_size for i in range(self._legacy_bins + 1)]
            bin_vols = [0.0] * self._legacy_bins

            for p, v in zip(all_prices, all_vols):
                bin_idx = min(int((p - min_price) / bin_size), self._legacy_bins - 1)
                bin_vols[bin_idx] += float(v)

            max_idx = int(np.argmax(bin_vols))
            poc = float(bins[max_idx] + bin_size / 2.0)

            # Value Area (70% volume around POC)
            total_vol = sum(bin_vols)
            target_vol = total_vol * 0.70
            accumulated_vol = bin_vols[max_idx]
            left_idx = max_idx
            right_idx = max_idx

            while accumulated_vol < target_vol and (left_idx > 0 or right_idx < self._legacy_bins - 1):
                left_vol = bin_vols[left_idx - 1] if left_idx > 0 else -1.0
                right_vol = bin_vols[right_idx + 1] if right_idx < self._legacy_bins - 1 else -1.0

                if left_vol >= right_vol:
                    left_idx -= 1
                    accumulated_vol += left_vol
                else:
                    right_idx += 1
                    accumulated_vol += right_vol

            val = float(bins[left_idx])
            vah = float(bins[right_idx + 1])

            # Enforce invariants
            if val > vah:
                val, vah = vah, val
            if not (val <= poc <= vah):
                poc = (val + vah) / 2.0

        # 3. Directional Bias
        current_price = prices[-1]
        threshold = 0.001 * current_price  # 0.1% buffer
        if current_price > poc + threshold:
            bias = "LONG"
        elif current_price < poc - threshold:
            bias = "SHORT"
        else:
            bias = "NEUTRAL"

        return {
            "bias": bias,
            "poc": poc,
            "vah": vah,
            "val": val,
            "support": support,
            "resistance": resistance
        }
