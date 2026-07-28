"""1H Market Structure Engine analyzing swing structures, S/R, volume profile, and directional bias."""

from typing import Dict, List, Any
import numpy as np


class MarketStructureEngine:
    """
    1H Market Structure Engine.
    Responsible for identifying key S/R zones, swing structures, Volume Profiles, and directional bias.
    """

    def __init__(self, swing_lookback: int = 20, volume_profile_bins: int = 10):
        self.swing_lookback = swing_lookback
        self.volume_profile_bins = volume_profile_bins

    def calculate_market_structure(self, prices: List[float], highs: List[float],
                                  lows: List[float], volumes: List[float]) -> Dict[str, Any]:
        """
        Calculate support, resistance, Volume Profile (POC/VAH/VAL), and directional bias from series data.
        """
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
            bin_size = price_range / self.volume_profile_bins
            bins = [min_price + i * bin_size for i in range(self.volume_profile_bins + 1)]
            bin_vols = [0.0] * self.volume_profile_bins

            for p, v in zip(all_prices, all_vols):
                bin_idx = min(int((p - min_price) / bin_size), self.volume_profile_bins - 1)
                bin_vols[bin_idx] += float(v)

            max_idx = int(np.argmax(bin_vols))
            poc = float(bins[max_idx] + bin_size / 2.0)

            # Value Area (70% volume around POC)
            total_vol = sum(bin_vols)
            target_vol = total_vol * 0.70
            accumulated_vol = bin_vols[max_idx]
            left_idx = max_idx
            right_idx = max_idx

            while accumulated_vol < target_vol and (left_idx > 0 or right_idx < self.volume_profile_bins - 1):
                left_vol = bin_vols[left_idx - 1] if left_idx > 0 else -1.0
                right_vol = bin_vols[right_idx + 1] if right_idx < self.volume_profile_bins - 1 else -1.0

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
