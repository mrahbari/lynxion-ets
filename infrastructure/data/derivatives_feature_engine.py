"""Pure, deterministic feature engine for derivatives metrics."""

import math
from typing import Dict, List, Optional, Any
from domain.value_objects import Symbol, ExchangeTimestamp
from domain.entities.market_data import FundingRate, OpenInterest
from domain.entities.feature import DerivativesFeatureVector


class DerivativesFeatureEngine:
    """Pure, deterministic feature engine for derivatives metrics."""

    @staticmethod
    def compute_vector(
        symbol: Symbol,
        timestamp: ExchangeTimestamp,
        funding_rates: List[FundingRate],
        open_interests: List[OpenInterest],
        ohlcv_records: Optional[List[Dict[str, Any]]] = None,
    ) -> DerivativesFeatureVector:
        """Compute point-in-time DerivativesFeatureVector at target timestamp T."""
        t_target = timestamp.millis

        # Point-in-Time Filtering: strictly <= T
        f_hist = [f for f in funding_rates if f.timestamp.millis <= t_target]
        oi_hist = [o for o in open_interests if o.timestamp.millis <= t_target]

        ohlcv_hist = None
        if ohlcv_records is not None:
            ohlcv_hist = [c for c in ohlcv_records if c["timestamp"] <= t_target]

        # 1. funding_annualized (1 observation)
        funding_annualized = None
        if len(f_hist) >= 1:
            funding_annualized = float(f_hist[-1].rate) * 3.0 * 365.0 * 100.0

        # 2. funding_sma_24h (3 observations = 24h)
        funding_sma_24h = None
        if len(f_hist) >= 3:
            funding_sma_24h = sum(float(r.rate) for r in f_hist[-3:]) / 3.0

        # 3. oi_change_1h_pct (2 observations = 1h change)
        oi_change_1h_pct = None
        if len(oi_hist) >= 2:
            prev_oi = float(oi_hist[-2].value.value)
            curr_oi = float(oi_hist[-1].value.value)
            if prev_oi > 0:
                oi_change_1h_pct = (curr_oi - prev_oi) / prev_oi
            else:
                oi_change_1h_pct = 0.0

        # 4. oi_to_volume_ratio_24h (requires 24h OHLCV volume)
        oi_to_volume_ratio_24h = None
        if len(oi_hist) >= 1 and ohlcv_hist is not None and len(ohlcv_hist) >= 24:
            vol_sum = sum(float(c["volume"]) for c in ohlcv_hist[-24:])
            curr_oi_val = (
                float(oi_hist[-1].value_quote.amount)
                if oi_hist[-1].value_quote is not None
                else float(oi_hist[-1].value.value)
            )
            if vol_sum > 0:
                oi_to_volume_ratio_24h = curr_oi_val / vol_sum
            else:
                oi_to_volume_ratio_24h = 0.0

        # 5. funding_zscore_30d (90 observations = 30d)
        funding_zscore_30d = None
        if len(f_hist) >= 90:
            f_vals_90 = [float(r.rate) for r in f_hist[-90:]]
            mean_90 = sum(f_vals_90) / 90.0
            var_90 = sum((x - mean_90) ** 2 for x in f_vals_90) / 90.0
            std_90 = math.sqrt(var_90)
            if std_90 > 0:
                funding_zscore_30d = (f_vals_90[-1] - mean_90) / std_90
            else:
                funding_zscore_30d = 0.0

        # 6. funding_percentile_90d (270 observations = 90d)
        funding_percentile_90d = None
        if len(f_hist) >= 270:
            f_vals_270 = [float(r.rate) for r in f_hist[-270:]]
            curr_rate = f_vals_270[-1]
            rank_count = sum(1 for r in f_vals_270 if r <= curr_rate)
            funding_percentile_90d = rank_count / 270.0

        # 7. oi_zscore_14d (336 observations = 14d)
        oi_zscore_14d = None
        if len(oi_hist) >= 336:
            oi_vals_336 = [float(o.value.value) for o in oi_hist[-336:]]
            mean_336 = sum(oi_vals_336) / 336.0
            var_336 = sum((x - mean_336) ** 2 for x in oi_vals_336) / 336.0
            std_336 = math.sqrt(var_336)
            if std_336 > 0:
                oi_zscore_14d = (oi_vals_336[-1] - mean_336) / std_336
            else:
                oi_zscore_14d = 0.0

        # 8. price_oi_divergence_score (requires 24h OHLCV and 24h OI)
        price_oi_divergence_score = None
        if ohlcv_hist is not None and len(ohlcv_hist) >= 24 and len(oi_hist) >= 24:
            p_prev = float(ohlcv_hist[-24]["close"])
            p_curr = float(ohlcv_hist[-1]["close"])
            oi_prev = float(oi_hist[-24].value.value)
            oi_curr = float(oi_hist[-1].value.value)

            if p_prev > 0 and oi_prev > 0:
                ret_p = (p_curr - p_prev) / p_prev
                ret_oi = (oi_curr - oi_prev) / oi_prev
                sign_p = 1.0 if ret_p > 0 else (-1.0 if ret_p < 0 else 0.0)
                sign_oi = 1.0 if ret_oi > 0 else (-1.0 if ret_oi < 0 else 0.0)
                score_val = sign_p * sign_oi * min(abs(ret_p - ret_oi) * 10.0, 3.0)
                price_oi_divergence_score = round(score_val, 4)

        # 9. funding_capitulation_gate (requires 30d Z-score)
        funding_capitulation_gate = None
        if funding_zscore_30d is not None and len(f_hist) >= 90:
            curr_r = float(f_hist[-1].rate)
            if curr_r <= -0.0005 and funding_zscore_30d <= -2.0:
                funding_capitulation_gate = 1  # Long Capitulation Reversal Trigger
            elif curr_r >= 0.0008 and funding_zscore_30d >= 2.0:
                funding_capitulation_gate = -1  # Short Capitulation Reversal Trigger
            else:
                funding_capitulation_gate = 0

        # 10. oi_liquidation_vulnerability_index (requires 24h OHLCV and 14d OI Z-score)
        oi_liquidation_vulnerability_index = None
        if (
            ohlcv_hist is not None
            and len(ohlcv_hist) >= 24
            and oi_zscore_14d is not None
            and len(f_hist) >= 1
        ):
            log_returns = []
            for i in range(1, len(ohlcv_hist[-24:])):
                c_prev = float(ohlcv_hist[-24 + i - 1]["close"])
                c_curr = float(ohlcv_hist[-24 + i]["close"])
                if c_prev > 0 and c_curr > 0:
                    log_returns.append(math.log(c_curr / c_prev))

            vol_24h = 0.0
            if len(log_returns) > 1:
                mean_vol = sum(log_returns) / len(log_returns)
                var_vol = sum((x - mean_vol) ** 2 for x in log_returns) / len(log_returns)
                vol_24h = math.sqrt(var_vol)

            ret_p_24h = (
                (float(ohlcv_hist[-1]["close"]) - float(ohlcv_hist[-24]["close"]))
                / float(ohlcv_hist[-24]["close"])
            ) if float(ohlcv_hist[-24]["close"]) > 0 else 0.0
            curr_r = float(f_hist[-1].rate)

            condition_factor = 1.5 if (curr_r * ret_p_24h) < 0 else 1.0
            raw_lvi = vol_24h * 100.0 * max(oi_zscore_14d, 0.0) * condition_factor
            oi_liquidation_vulnerability_index = min(max(round(raw_lvi, 2), 0.0), 100.0)

        # Warmup Check: requires 270 funding periods (90d) and 336 OI periods (14d)
        is_warmed_up = (len(f_hist) >= 270) and (len(oi_hist) >= 336)

        return DerivativesFeatureVector(
            symbol=symbol,
            timestamp=timestamp,
            is_warmed_up=is_warmed_up,
            funding_annualized=funding_annualized,
            funding_sma_24h=funding_sma_24h,
            oi_change_1h_pct=oi_change_1h_pct,
            oi_to_volume_ratio_24h=oi_to_volume_ratio_24h,
            funding_zscore_30d=funding_zscore_30d,
            funding_percentile_90d=funding_percentile_90d,
            oi_zscore_14d=oi_zscore_14d,
            price_oi_divergence_score=price_oi_divergence_score,
            funding_capitulation_gate=funding_capitulation_gate,
            oi_liquidation_vulnerability_index=oi_liquidation_vulnerability_index,
        )
