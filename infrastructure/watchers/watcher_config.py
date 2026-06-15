"""
Standardized Configuration for Watchers
Provides consistent access to configuration through the Configs system
"""
from typing import Union


class WatcherConfig:
    """
    Standardized configuration class for all watchers.
    Provides consistent environment variable naming and default values.
    """

    # Common watcher settings
    @staticmethod
    def get_watcher_enabled(settings, watcher_name: str) -> bool:
        """Get if a watcher is enabled"""
        # Map watcher names to config attributes
        config_map = {
            'market_pulse': lambda: settings.watcher.market_pulse_watcher_enabled if settings.watcher and hasattr(settings.watcher, 'market_pulse_watcher_enabled') else True,
            'volatility': lambda: settings.watcher.volatility_watcher_enabled if settings.watcher and hasattr(settings.watcher, 'volatility_watcher_enabled') else True,
            'trend_mtf': lambda: settings.watcher.trend_mtf_watcher_enabled if settings.watcher and hasattr(settings.watcher, 'trend_mtf_watcher_enabled') else True,
            'anomaly_ml': lambda: settings.watcher.anomaly_ml_watcher_enabled if settings.watcher and hasattr(settings.watcher, 'anomaly_ml_watcher_enabled') else True,
            'orderflow_ws': lambda: settings.watcher.orderflow_ws_watcher_enabled if settings.watcher and hasattr(settings.watcher, 'orderflow_ws_watcher_enabled') else True,
            'cmc_screener': lambda: settings.watcher.cmc_screener_enabled if settings.watcher and hasattr(settings.watcher, 'cmc_screener_enabled') else True,
            'funding_rate': lambda: settings.watcher.funding_rate_watcher_enabled if settings.watcher and hasattr(settings.watcher, 'funding_rate_watcher_enabled') else True,
            'liquidity': lambda: settings.watcher.liquidity_watcher_enabled if settings.watcher and hasattr(settings.watcher, 'liquidity_watcher_enabled') else True,
            'historical_candle': lambda: settings.watcher.historical_candle_watcher_enabled if settings.watcher and hasattr(settings.watcher, 'historical_candle_watcher_enabled') else True,
            'tick': lambda: settings.watcher.tick_watcher_enabled if settings.watcher and hasattr(settings.watcher, 'tick_watcher_enabled') else False,
        }

        if watcher_name.lower() in config_map:
            return config_map[watcher_name.lower()]()
        else:
            # Default to True if watcher name is not recognized
            return True

    @staticmethod
    def get_watcher_lookback(settings, watcher_name: str, default: int = 20) -> int:
        """Get lookback period for a watcher"""
        # Map watcher names to config attributes
        config_map = {
            'market_pulse': lambda: settings.watcher.market_pulse_lookback_period if settings.watcher and hasattr(settings.watcher, 'market_pulse_lookback_period') else default,
            'volatility': lambda: settings.watcher.volatility_lookback_period if settings.watcher and hasattr(settings.watcher, 'volatility_lookback_period') else default,
            'trend_mtf': lambda: settings.watcher.trend_mtf_lookback_period if settings.watcher and hasattr(settings.watcher, 'trend_mtf_lookback_period') else default,
            'anomaly_ml': lambda: settings.watcher.anomaly_ml_lookback_period if settings.watcher and hasattr(settings.watcher, 'anomaly_ml_lookback_period') else default,
            'orderflow_ws': lambda: settings.watcher.orderflow_ws_lookback_period if settings.watcher and hasattr(settings.watcher, 'orderflow_ws_lookback_period') else default,
            'cmc_screener': lambda: settings.watcher.cmc_screener_lookback_period if settings.watcher and hasattr(settings.watcher, 'cmc_screener_lookback_period') else default,
            'funding_rate': lambda: settings.watcher.funding_rate_lookback_period if settings.watcher and hasattr(settings.watcher, 'funding_rate_lookback_period') else default,
            'liquidity': lambda: settings.watcher.liquidity_lookback_period if settings.watcher and hasattr(settings.watcher, 'liquidity_lookback_period') else default,
            'historical_candle': lambda: settings.watcher.historical_candle_lookback_period if settings.watcher and hasattr(settings.watcher, 'historical_candle_lookback_period') else default,
            'tick': lambda: settings.watcher.tick_lookback_period if settings.watcher and hasattr(settings.watcher, 'tick_lookback_period') else default,
        }

        if watcher_name.lower() in config_map:
            return config_map[watcher_name.lower()]()
        else:
            # Default to provided default if watcher name is not recognized
            return default

    @staticmethod
    def get_watcher_min_confidence(settings, watcher_name: str = None, default: float = 0.05) -> float:
        """Get minimum confidence threshold for a watcher"""
        if watcher_name:
            # Map specific watcher names to config attributes
            config_map = {
                'market_pulse': lambda: settings.watcher.market_pulse_min_confidence_threshold if settings.watcher and hasattr(settings.watcher, 'market_pulse_min_confidence_threshold') else default,
                'volatility': lambda: settings.watcher.volatility_min_confidence_threshold if settings.watcher and hasattr(settings.watcher, 'volatility_min_confidence_threshold') else default,
                'trend_mtf': lambda: settings.watcher.trend_mtf_min_confidence_threshold if settings.watcher and hasattr(settings.watcher, 'trend_mtf_min_confidence_threshold') else default,
                'anomaly_ml': lambda: settings.watcher.anomaly_ml_min_confidence_threshold if settings.watcher and hasattr(settings.watcher, 'anomaly_ml_min_confidence_threshold') else default,
                'orderflow_ws': lambda: settings.watcher.orderflow_ws_min_confidence_threshold if settings.watcher and hasattr(settings.watcher, 'orderflow_ws_min_confidence_threshold') else default,
                'cmc_screener': lambda: settings.watcher.cmc_screener_min_confidence_threshold if settings.watcher and hasattr(settings.watcher, 'cmc_screener_min_confidence_threshold') else default,
                'funding_rate': lambda: settings.watcher.funding_rate_min_confidence_threshold if settings.watcher and hasattr(settings.watcher, 'funding_rate_min_confidence_threshold') else default,
                'liquidity': lambda: settings.watcher.liquidity_min_confidence_threshold if settings.watcher and hasattr(settings.watcher, 'liquidity_min_confidence_threshold') else default,
                'historical_candle': lambda: settings.watcher.historical_candle_min_confidence_threshold if settings.watcher and hasattr(settings.watcher, 'historical_candle_min_confidence_threshold') else default,
                'tick': lambda: settings.watcher.tick_min_confidence_threshold if settings.watcher and hasattr(settings.watcher, 'tick_min_confidence_threshold') else default,
            }

            if watcher_name.lower() in config_map:
                return config_map[watcher_name.lower()]()
            else:
                return default
        else:
            # Use general watcher min confidence threshold
            return settings.watcher.min_confidence_threshold if settings.watcher and hasattr(settings.watcher, 'min_confidence_threshold') else default

    @staticmethod
    def get_watcher_max_confidence(settings, watcher_name: str = None, default: float = 0.95) -> float:
        """Get maximum confidence threshold for a watcher"""
        if watcher_name:
            # Map specific watcher names to config attributes
            config_map = {
                'market_pulse': lambda: settings.watcher.market_pulse_max_confidence_threshold if settings.watcher and hasattr(settings.watcher, 'market_pulse_max_confidence_threshold') else default,
                'volatility': lambda: settings.watcher.volatility_max_confidence_threshold if settings.watcher and hasattr(settings.watcher, 'volatility_max_confidence_threshold') else default,
                'trend_mtf': lambda: settings.watcher.trend_mtf_max_confidence_threshold if settings.watcher and hasattr(settings.watcher, 'trend_mtf_max_confidence_threshold') else default,
                'anomaly_ml': lambda: settings.watcher.anomaly_ml_max_confidence_threshold if settings.watcher and hasattr(settings.watcher, 'anomaly_ml_max_confidence_threshold') else default,
                'orderflow_ws': lambda: settings.watcher.orderflow_ws_max_confidence_threshold if settings.watcher and hasattr(settings.watcher, 'orderflow_ws_max_confidence_threshold') else default,
                'cmc_screener': lambda: settings.watcher.cmc_screener_max_confidence_threshold if settings.watcher and hasattr(settings.watcher, 'cmc_screener_max_confidence_threshold') else default,
                'funding_rate': lambda: settings.watcher.funding_rate_max_confidence_threshold if settings.watcher and hasattr(settings.watcher, 'funding_rate_max_confidence_threshold') else default,
                'liquidity': lambda: settings.watcher.liquidity_max_confidence_threshold if settings.watcher and hasattr(settings.watcher, 'liquidity_max_confidence_threshold') else default,
                'historical_candle': lambda: settings.watcher.historical_candle_max_confidence_threshold if settings.watcher and hasattr(settings.watcher, 'historical_candle_max_confidence_threshold') else default,
                'tick': lambda: settings.watcher.tick_max_confidence_threshold if settings.watcher and hasattr(settings.watcher, 'tick_max_confidence_threshold') else default,
            }

            if watcher_name.lower() in config_map:
                return config_map[watcher_name.lower()]()
            else:
                # Use general watcher max confidence threshold
                return settings.watcher.max_confidence_cap if settings.watcher and hasattr(settings.watcher, 'max_confidence_cap') else default
        else:
            # Use general watcher max confidence threshold
            return settings.watcher.max_confidence_cap if settings.watcher and hasattr(settings.watcher, 'max_confidence_cap') else default

    @staticmethod
    def get_watcher_adaptive_sensitivity(settings, watcher_name: str) -> bool:
        """Get if a watcher should use adaptive sensitivity"""
        # Map specific watcher names to config attributes
        config_map = {
            'market_pulse': lambda: settings.watcher.market_pulse_adaptive_sensitivity if settings.watcher and hasattr(settings.watcher, 'market_pulse_adaptive_sensitivity') else False,
            'volatility': lambda: settings.watcher.volatility_adaptive_sensitivity if settings.watcher and hasattr(settings.watcher, 'volatility_adaptive_sensitivity') else False,
            'trend_mtf': lambda: settings.watcher.trend_mtf_adaptive_sensitivity if settings.watcher and hasattr(settings.watcher, 'trend_mtf_adaptive_sensitivity') else False,
            'anomaly_ml': lambda: settings.watcher.anomaly_ml_adaptive_sensitivity if settings.watcher and hasattr(settings.watcher, 'anomaly_ml_adaptive_sensitivity') else False,
            'orderflow_ws': lambda: settings.watcher.orderflow_ws_adaptive_sensitivity if settings.watcher and hasattr(settings.watcher, 'orderflow_ws_adaptive_sensitivity') else False,
            'cmc_screener': lambda: settings.watcher.cmc_screener_adaptive_sensitivity if settings.watcher and hasattr(settings.watcher, 'cmc_screener_adaptive_sensitivity') else False,
            'funding_rate': lambda: settings.watcher.funding_rate_adaptive_sensitivity if settings.watcher and hasattr(settings.watcher, 'funding_rate_adaptive_sensitivity') else False,
            'liquidity': lambda: settings.watcher.liquidity_adaptive_sensitivity if settings.watcher and hasattr(settings.watcher, 'liquidity_adaptive_sensitivity') else False,
            'historical_candle': lambda: settings.watcher.historical_candle_adaptive_sensitivity if settings.watcher and hasattr(settings.watcher, 'historical_candle_adaptive_sensitivity') else False,
            'tick': lambda: settings.watcher.tick_adaptive_sensitivity if settings.watcher and hasattr(settings.watcher, 'tick_adaptive_sensitivity') else False,
        }

        if watcher_name.lower() in config_map:
            return config_map[watcher_name.lower()]()
        else:
            # Default to False if watcher name is not recognized
            return False

    @staticmethod
    def get_watcher_target_broker(settings, watcher_name: str, default: str = 'binance') -> str:
        """Get target broker for a watcher"""
        # Map specific watcher names to config attributes
        config_map = {
            'market_pulse': lambda: settings.watcher.target_broker_market_pulse if settings.watcher and hasattr(settings.watcher, 'target_broker_market_pulse') else default,
            'volatility': lambda: settings.watcher.target_broker_volatility if settings.watcher and hasattr(settings.watcher, 'target_broker_volatility') else default,
            'trend_mtf': lambda: settings.watcher.target_broker_trend_mtf if settings.watcher and hasattr(settings.watcher, 'target_broker_trend_mtf') else default,
            'anomaly_ml': lambda: settings.watcher.target_broker_anomaly_ml if settings.watcher and hasattr(settings.watcher, 'target_broker_anomaly_ml') else default,
            'orderflow_ws': lambda: settings.watcher.target_broker_orderflow_ws if settings.watcher and hasattr(settings.watcher, 'target_broker_orderflow_ws') else default,
            'funding_rate': lambda: settings.watcher.target_broker_funding_rate if settings.watcher and hasattr(settings.watcher, 'target_broker_funding_rate') else default,
            'liquidity': lambda: settings.watcher.target_broker_liquidity if settings.watcher and hasattr(settings.watcher, 'target_broker_liquidity') else default,
            'historical_candle': lambda: settings.watcher.target_broker_historical_candle if settings.watcher and hasattr(settings.watcher, 'target_broker_historical_candle') else default,
            'tick': lambda: settings.watcher.target_broker_tick_watcher if settings.watcher and hasattr(settings.watcher, 'target_broker_tick_watcher') else default,
        }

        if watcher_name.lower() in config_map:
            return config_map[watcher_name.lower()]()
        else:
            # Use general target broker if watcher name is not recognized
            return default

    @staticmethod
    def get_watcher_pattern_weight(settings, watcher_name: str = None, default: float = 0.4) -> float:
        """Get pattern weight for a watcher"""
        if watcher_name:
            # Map specific watcher names to config attributes
            config_map = {
                'market_pulse': lambda: settings.watcher.market_pulse_pattern_weight if settings.watcher and hasattr(settings.watcher, 'market_pulse_pattern_weight') else default,
                'volatility': lambda: settings.watcher.volatility_pattern_weight if settings.watcher and hasattr(settings.watcher, 'volatility_pattern_weight') else default,
                'trend_mtf': lambda: settings.watcher.trend_mtf_pattern_weight if settings.watcher and hasattr(settings.watcher, 'trend_mtf_pattern_weight') else default,
                'anomaly_ml': lambda: settings.watcher.anomaly_ml_pattern_weight if settings.watcher and hasattr(settings.watcher, 'anomaly_ml_pattern_weight') else default,
                'orderflow_ws': lambda: settings.watcher.orderflow_ws_pattern_weight if settings.watcher and hasattr(settings.watcher, 'orderflow_ws_pattern_weight') else default,
                'cmc_screener': lambda: settings.watcher.cmc_screener_pattern_weight if settings.watcher and hasattr(settings.watcher, 'cmc_screener_pattern_weight') else default,
                'funding_rate': lambda: settings.watcher.funding_rate_pattern_weight if settings.watcher and hasattr(settings.watcher, 'funding_rate_pattern_weight') else default,
                'liquidity': lambda: settings.watcher.liquidity_pattern_weight if settings.watcher and hasattr(settings.watcher, 'liquidity_pattern_weight') else default,
                'historical_candle': lambda: settings.watcher.historical_candle_pattern_weight if settings.watcher and hasattr(settings.watcher, 'historical_candle_pattern_weight') else default,
                'tick': lambda: settings.watcher.tick_pattern_weight if settings.watcher and hasattr(settings.watcher, 'tick_pattern_weight') else default,
            }

            if watcher_name.lower() in config_map:
                return config_map[watcher_name.lower()]()
            else:
                return default
        else:
            # Use general watcher pattern weight
            return settings.watcher.pattern_weight if settings.watcher and hasattr(settings.watcher, 'pattern_weight') else default

    @staticmethod
    def get_watcher_momentum_weight(settings, watcher_name: str = None, default: float = 0.3) -> float:
        """Get momentum weight for a watcher"""
        if watcher_name:
            # Map specific watcher names to config attributes
            config_map = {
                'market_pulse': lambda: settings.watcher.market_pulse_momentum_weight if settings.watcher and hasattr(settings.watcher, 'market_pulse_momentum_weight') else default,
                'volatility': lambda: settings.watcher.volatility_momentum_weight if settings.watcher and hasattr(settings.watcher, 'volatility_momentum_weight') else default,
                'trend_mtf': lambda: settings.watcher.trend_mtf_momentum_weight if settings.watcher and hasattr(settings.watcher, 'trend_mtf_momentum_weight') else default,
                'anomaly_ml': lambda: settings.watcher.anomaly_ml_momentum_weight if settings.watcher and hasattr(settings.watcher, 'anomaly_ml_momentum_weight') else default,
                'orderflow_ws': lambda: settings.watcher.orderflow_ws_momentum_weight if settings.watcher and hasattr(settings.watcher, 'orderflow_ws_momentum_weight') else default,
                'cmc_screener': lambda: settings.watcher.cmc_screener_momentum_weight if settings.watcher and hasattr(settings.watcher, 'cmc_screener_momentum_weight') else default,
                'funding_rate': lambda: settings.watcher.funding_rate_momentum_weight if settings.watcher and hasattr(settings.watcher, 'funding_rate_momentum_weight') else default,
                'liquidity': lambda: settings.watcher.liquidity_momentum_weight if settings.watcher and hasattr(settings.watcher, 'liquidity_momentum_weight') else default,
                'historical_candle': lambda: settings.watcher.historical_candle_momentum_weight if settings.watcher and hasattr(settings.watcher, 'historical_candle_momentum_weight') else default,
                'tick': lambda: settings.watcher.tick_momentum_weight if settings.watcher and hasattr(settings.watcher, 'tick_momentum_weight') else default,
            }

            if watcher_name.lower() in config_map:
                return config_map[watcher_name.lower()]()
            else:
                return default
        else:
            # Use general watcher momentum weight
            return settings.watcher.momentum_weight if settings.watcher and hasattr(settings.watcher, 'momentum_weight') else default

    @staticmethod
    def get_watcher_volatility_boost(settings, watcher_name: str, boost_type: str = 'normal', default: float = 0.1) -> float:
        """Get volatility boost for a watcher"""
        if watcher_name:
            # Map specific watcher names and boost types to config attributes
            if boost_type.lower() == 'high':
                config_map = {
                    'market_pulse': lambda: settings.watcher.market_pulse_high_volatility_boost if settings.watcher and hasattr(settings.watcher, 'market_pulse_high_volatility_boost') else default,
                    'volatility': lambda: settings.watcher.volatility_high_volatility_boost if settings.watcher and hasattr(settings.watcher, 'volatility_high_volatility_boost') else default,
                    'trend_mtf': lambda: settings.watcher.trend_mtf_high_volatility_boost if settings.watcher and hasattr(settings.watcher, 'trend_mtf_high_volatility_boost') else default,
                    'anomaly_ml': lambda: settings.watcher.anomaly_ml_high_volatility_boost if settings.watcher and hasattr(settings.watcher, 'anomaly_ml_high_volatility_boost') else default,
                    'orderflow_ws': lambda: settings.watcher.orderflow_ws_high_volatility_boost if settings.watcher and hasattr(settings.watcher, 'orderflow_ws_high_volatility_boost') else default,
                    'cmc_screener': lambda: settings.watcher.cmc_screener_high_volatility_boost if settings.watcher and hasattr(settings.watcher, 'cmc_screener_high_volatility_boost') else default,
                    'funding_rate': lambda: settings.watcher.funding_rate_high_volatility_boost if settings.watcher and hasattr(settings.watcher, 'funding_rate_high_volatility_boost') else default,
                    'liquidity': lambda: settings.watcher.liquidity_high_volatility_boost if settings.watcher and hasattr(settings.watcher, 'liquidity_high_volatility_boost') else default,
                    'historical_candle': lambda: settings.watcher.historical_candle_high_volatility_boost if settings.watcher and hasattr(settings.watcher, 'historical_candle_high_volatility_boost') else default,
                    'tick': lambda: settings.watcher.tick_high_volatility_boost if settings.watcher and hasattr(settings.watcher, 'tick_high_volatility_boost') else default,
                }
            elif boost_type.lower() == 'low':
                config_map = {
                    'market_pulse': lambda: settings.watcher.market_pulse_low_volatility_boost if settings.watcher and hasattr(settings.watcher, 'market_pulse_low_volatility_boost') else default,
                    'volatility': lambda: settings.watcher.volatility_low_volatility_boost if settings.watcher and hasattr(settings.watcher, 'volatility_low_volatility_boost') else default,
                    'trend_mtf': lambda: settings.watcher.trend_mtf_low_volatility_boost if settings.watcher and hasattr(settings.watcher, 'trend_mtf_low_volatility_boost') else default,
                    'anomaly_ml': lambda: settings.watcher.anomaly_ml_low_volatility_boost if settings.watcher and hasattr(settings.watcher, 'anomaly_ml_low_volatility_boost') else default,
                    'orderflow_ws': lambda: settings.watcher.orderflow_ws_low_volatility_boost if settings.watcher and hasattr(settings.watcher, 'orderflow_ws_low_volatility_boost') else default,
                    'cmc_screener': lambda: settings.watcher.cmc_screener_low_volatility_boost if settings.watcher and hasattr(settings.watcher, 'cmc_screener_low_volatility_boost') else default,
                    'funding_rate': lambda: settings.watcher.funding_rate_low_volatility_boost if settings.watcher and hasattr(settings.watcher, 'funding_rate_low_volatility_boost') else default,
                    'liquidity': lambda: settings.watcher.liquidity_low_volatility_boost if settings.watcher and hasattr(settings.watcher, 'liquidity_low_volatility_boost') else default,
                    'historical_candle': lambda: settings.watcher.historical_candle_low_volatility_boost if settings.watcher and hasattr(settings.watcher, 'historical_candle_low_volatility_boost') else default,
                    'tick': lambda: settings.watcher.tick_low_volatility_boost if settings.watcher and hasattr(settings.watcher, 'tick_low_volatility_boost') else default,
                }
            else:  # normal
                config_map = {
                    'market_pulse': lambda: settings.watcher.market_pulse_normal_volatility_boost if settings.watcher and hasattr(settings.watcher, 'market_pulse_normal_volatility_boost') else default,
                    'volatility': lambda: settings.watcher.volatility_normal_volatility_boost if settings.watcher and hasattr(settings.watcher, 'volatility_normal_volatility_boost') else default,
                    'trend_mtf': lambda: settings.watcher.trend_mtf_normal_volatility_boost if settings.watcher and hasattr(settings.watcher, 'trend_mtf_normal_volatility_boost') else default,
                    'anomaly_ml': lambda: settings.watcher.anomaly_ml_normal_volatility_boost if settings.watcher and hasattr(settings.watcher, 'anomaly_ml_normal_volatility_boost') else default,
                    'orderflow_ws': lambda: settings.watcher.orderflow_ws_normal_volatility_boost if settings.watcher and hasattr(settings.watcher, 'orderflow_ws_normal_volatility_boost') else default,
                    'cmc_screener': lambda: settings.watcher.cmc_screener_normal_volatility_boost if settings.watcher and hasattr(settings.watcher, 'cmc_screener_normal_volatility_boost') else default,
                    'funding_rate': lambda: settings.watcher.funding_rate_normal_volatility_boost if settings.watcher and hasattr(settings.watcher, 'funding_rate_normal_volatility_boost') else default,
                    'liquidity': lambda: settings.watcher.liquidity_normal_volatility_boost if settings.watcher and hasattr(settings.watcher, 'liquidity_normal_volatility_boost') else default,
                    'historical_candle': lambda: settings.watcher.historical_candle_normal_volatility_boost if settings.watcher and hasattr(settings.watcher, 'historical_candle_normal_volatility_boost') else default,
                    'tick': lambda: settings.watcher.tick_normal_volatility_boost if settings.watcher and hasattr(settings.watcher, 'tick_normal_volatility_boost') else default,
                }

            if watcher_name.lower() in config_map:
                return config_map[watcher_name.lower()]()
            else:
                return default
        else:
            # Use general watcher volatility boost
            if boost_type.lower() == 'high':
                return settings.watcher.high_volatility_boost if settings.watcher and hasattr(settings.watcher, 'high_volatility_boost') else default
            elif boost_type.lower() == 'low':
                return settings.watcher.low_volatility_boost if settings.watcher and hasattr(settings.watcher, 'low_volatility_boost') else default
            else:
                return settings.watcher.normal_volatility_boost if settings.watcher and hasattr(settings.watcher, 'normal_volatility_boost') else default

    @staticmethod
    def get_watcher_momentum_lookback(settings, watcher_name: str = None, default: int = 10) -> int:
        """Get momentum lookback period for a watcher"""
        if watcher_name:
            # Map specific watcher names to config attributes
            config_map = {
                'market_pulse': lambda: settings.watcher.market_pulse_momentum_lookback_period if settings.watcher and hasattr(settings.watcher, 'market_pulse_momentum_lookback_period') else default,
                'volatility': lambda: settings.watcher.volatility_momentum_lookback_period if settings.watcher and hasattr(settings.watcher, 'volatility_momentum_lookback_period') else default,
                'trend_mtf': lambda: settings.watcher.trend_mtf_momentum_lookback_period if settings.watcher and hasattr(settings.watcher, 'trend_mtf_momentum_lookback_period') else default,
                'anomaly_ml': lambda: settings.watcher.anomaly_ml_momentum_lookback_period if settings.watcher and hasattr(settings.watcher, 'anomaly_ml_momentum_lookback_period') else default,
                'orderflow_ws': lambda: settings.watcher.orderflow_ws_momentum_lookback_period if settings.watcher and hasattr(settings.watcher, 'orderflow_ws_momentum_lookback_period') else default,
                'cmc_screener': lambda: settings.watcher.cmc_screener_momentum_lookback_period if settings.watcher and hasattr(settings.watcher, 'cmc_screener_momentum_lookback_period') else default,
                'funding_rate': lambda: settings.watcher.funding_rate_momentum_lookback_period if settings.watcher and hasattr(settings.watcher, 'funding_rate_momentum_lookback_period') else default,
                'liquidity': lambda: settings.watcher.liquidity_momentum_lookback_period if settings.watcher and hasattr(settings.watcher, 'liquidity_momentum_lookback_period') else default,
                'historical_candle': lambda: settings.watcher.historical_candle_momentum_lookback_period if settings.watcher and hasattr(settings.watcher, 'historical_candle_momentum_lookback_period') else default,
                'tick': lambda: settings.watcher.tick_momentum_lookback_period if settings.watcher and hasattr(settings.watcher, 'tick_momentum_lookback_period') else default,
            }

            if watcher_name.lower() in config_map:
                return config_map[watcher_name.lower()]()
            else:
                return default
        else:
            # Use general watcher momentum lookback
            return settings.watcher.momentum_lookback_period if settings.watcher and hasattr(settings.watcher, 'momentum_lookback_period') else default

    @staticmethod
    def get_watcher_momentum_sensitivity(settings, watcher_name: str = None, default: float = 10.0) -> float:
        """Get momentum sensitivity factor for a watcher"""
        if watcher_name:
            # Map specific watcher names to config attributes
            config_map = {
                'market_pulse': lambda: settings.watcher.market_pulse_momentum_sensitivity_factor if settings.watcher and hasattr(settings.watcher, 'market_pulse_momentum_sensitivity_factor') else default,
                'volatility': lambda: settings.watcher.volatility_momentum_sensitivity_factor if settings.watcher and hasattr(settings.watcher, 'volatility_momentum_sensitivity_factor') else default,
                'trend_mtf': lambda: settings.watcher.trend_mtf_momentum_sensitivity_factor if settings.watcher and hasattr(settings.watcher, 'trend_mtf_momentum_sensitivity_factor') else default,
                'anomaly_ml': lambda: settings.watcher.anomaly_ml_momentum_sensitivity_factor if settings.watcher and hasattr(settings.watcher, 'anomaly_ml_momentum_sensitivity_factor') else default,
                'orderflow_ws': lambda: settings.watcher.orderflow_ws_momentum_sensitivity_factor if settings.watcher and hasattr(settings.watcher, 'orderflow_ws_momentum_sensitivity_factor') else default,
                'cmc_screener': lambda: settings.watcher.cmc_screener_momentum_sensitivity_factor if settings.watcher and hasattr(settings.watcher, 'cmc_screener_momentum_sensitivity_factor') else default,
                'funding_rate': lambda: settings.watcher.funding_rate_momentum_sensitivity_factor if settings.watcher and hasattr(settings.watcher, 'funding_rate_momentum_sensitivity_factor') else default,
                'liquidity': lambda: settings.watcher.liquidity_momentum_sensitivity_factor if settings.watcher and hasattr(settings.watcher, 'liquidity_momentum_sensitivity_factor') else default,
                'historical_candle': lambda: settings.watcher.historical_candle_momentum_sensitivity_factor if settings.watcher and hasattr(settings.watcher, 'historical_candle_momentum_sensitivity_factor') else default,
                'tick': lambda: settings.watcher.tick_momentum_sensitivity_factor if settings.watcher and hasattr(settings.watcher, 'tick_momentum_sensitivity_factor') else default,
            }

            if watcher_name.lower() in config_map:
                return config_map[watcher_name.lower()]()
            else:
                return default
        else:
            # Use general watcher momentum sensitivity
            return settings.watcher.momentum_sensitivity_factor if settings.watcher and hasattr(settings.watcher, 'momentum_sensitivity_factor') else default


# Convenience functions for specific watchers
def get_historical_candle_config(settings) -> dict:
    """Get configuration for HistoricalCandleWatcher"""
    return {
        'enabled': WatcherConfig.get_watcher_enabled(settings, 'HISTORICAL_CANDLE'),
        'lookback': WatcherConfig.get_watcher_lookback(settings, 'HISTORICAL_CANDLE', 50),
        'min_confidence': WatcherConfig.get_watcher_min_confidence(settings, 'HISTORICAL_CANDLE', 0.05),
        'max_confidence': WatcherConfig.get_watcher_max_confidence(settings, 'HISTORICAL_CANDLE', 0.95),
        'adaptive_sensitivity': WatcherConfig.get_watcher_adaptive_sensitivity(settings, 'HISTORICAL_CANDLE'),
        'pattern_weight': WatcherConfig.get_watcher_pattern_weight(settings, 'HISTORICAL_CANDLE', 0.4),
        'momentum_weight': WatcherConfig.get_watcher_momentum_weight(settings, 'HISTORICAL_CANDLE', 0.3),
        'high_volatility_boost': WatcherConfig.get_watcher_volatility_boost(settings, 'HISTORICAL_CANDLE', 'HIGH', 0.2),
        'low_volatility_boost': WatcherConfig.get_watcher_volatility_boost(settings, 'HISTORICAL_CANDLE', 'LOW', 0.05),
        'normal_volatility_boost': WatcherConfig.get_watcher_volatility_boost(settings, 'HISTORICAL_CANDLE', 'NORMAL', 0.1),
        'momentum_lookback': WatcherConfig.get_watcher_momentum_lookback(settings, 'HISTORICAL_CANDLE', 10),
        'momentum_sensitivity': WatcherConfig.get_watcher_momentum_sensitivity(settings, 'HISTORICAL_CANDLE', 10.0),
    }


def get_market_pulse_config(settings) -> dict:
    """Get configuration for MarketPulseWatcher"""
    return {
        'enabled': WatcherConfig.get_watcher_enabled(settings, 'MARKET_PULSE'),
        'lookback': WatcherConfig.get_watcher_lookback(settings, 'MARKET_PULSE', 20),
        'min_confidence': WatcherConfig.get_watcher_min_confidence(settings, 'MARKET_PULSE', 0.05),
        'max_confidence': WatcherConfig.get_watcher_max_confidence(settings, 'MARKET_PULSE', 0.95),
        'adaptive_sensitivity': WatcherConfig.get_watcher_adaptive_sensitivity(settings, 'MARKET_PULSE'),
    }


def get_volatility_config(settings) -> dict:
    """Get configuration for VolatilityWatcher"""
    return {
        'enabled': WatcherConfig.get_watcher_enabled(settings, 'VOLATILITY'),
        'lookback': WatcherConfig.get_watcher_lookback(settings, 'VOLATILITY', 20),
        'min_confidence': WatcherConfig.get_watcher_min_confidence(settings, 'VOLATILITY', 0.05),
    }


def get_trend_mtf_config(settings) -> dict:
    """Get configuration for TrendMTFWatcher"""
    return {
        'enabled': WatcherConfig.get_watcher_enabled(settings, 'TREND_MTF'),
        'short_period': settings.watcher.trend_mtf_short_period if settings.watcher and hasattr(settings.watcher, 'trend_mtf_short_period') else 5,
        'medium_period': settings.watcher.trend_mtf_medium_period if settings.watcher and hasattr(settings.watcher, 'trend_mtf_medium_period') else 15,
        'long_period': settings.watcher.trend_mtf_long_period if settings.watcher and hasattr(settings.watcher, 'trend_mtf_long_period') else 30,
        'min_confidence': WatcherConfig.get_watcher_min_confidence(settings, 'TREND_MTF', 0.05),
    }


def get_anomaly_ml_config(settings) -> dict:
    """Get configuration for AnomalyMLWatcher"""
    return {
        'enabled': WatcherConfig.get_watcher_enabled(settings, 'ANOMALY_ML'),
        'lookback': WatcherConfig.get_watcher_lookback(settings, 'ANOMALY_ML', 50),
        'contamination': settings.watcher.anomaly_ml_contamination if settings.watcher and hasattr(settings.watcher, 'anomaly_ml_contamination') else 0.1,
        'min_confidence': WatcherConfig.get_watcher_min_confidence(settings, 'ANOMALY_ML', 0.05),
    }


def get_orderflow_ws_config(settings) -> dict:
    """Get configuration for OrderFlowWSWatcher"""
    return {
        'enabled': WatcherConfig.get_watcher_enabled(settings, 'ORDERFLOW_WS'),
        'lookback': WatcherConfig.get_watcher_lookback(settings, 'ORDERFLOW_WS', 100),
        'min_confidence': WatcherConfig.get_watcher_min_confidence(settings, 'ORDERFLOW_WS', 0.05),
    }


def get_funding_rate_config(settings) -> dict:
    """Get configuration for FundingRateWatcher"""
    return {
        'enabled': WatcherConfig.get_watcher_enabled(settings, 'FUNDING_RATE'),
        'lookback': WatcherConfig.get_watcher_lookback(settings, 'FUNDING_RATE', 24),
        'min_confidence': WatcherConfig.get_watcher_min_confidence(settings, 'FUNDING_RATE', 0.05),
    }


def get_liquidity_config(settings) -> dict:
    """Get configuration for LiquidityWatcher"""
    return {
        'enabled': WatcherConfig.get_watcher_enabled(settings, 'LIQUIDITY'),
        'lookback': WatcherConfig.get_watcher_lookback(settings, 'LIQUIDITY', 20),
        'min_confidence': WatcherConfig.get_watcher_min_confidence(settings, 'LIQUIDITY', 0.05),
    }


def get_tick_config(settings) -> dict:
    """Get configuration for TickWatcher"""
    return {
        'enabled': WatcherConfig.get_watcher_enabled(settings, 'TICK'),
        'lookback': WatcherConfig.get_watcher_lookback(settings, 'TICK', 1000),
        'min_confidence': WatcherConfig.get_watcher_min_confidence(settings, 'TICK', 0.05),
    }