"""E5.T5 (infra-only mechanical split): per-domain config-extractor helpers extracted
from ``EnhancedConfigLoader``.

Behavior-preserving mixin — the 18 ``_extract_*_config_data`` methods moved verbatim
(signatures, ``self`` semantics, returned config dicts UNCHANGED) and composed via
inheritance. They read ``self.env_vars`` only (no schema/EnvLoader deps). No layer move,
no logic change.
"""
from typing import Dict, Any, Optional


class _ConfigExtractorsMixin:
    """Per-domain env -> config-dict extraction helpers (_extract_*_config_data)."""

    def _extract_broker_config_data(self) -> Dict[str, Any]:
        """Extract broker configuration data from environment variables."""
        broker_data = {
            'api_key': self.env_loader.get_env_var('BROKER_API_KEY', ''),
            'secret_key': self.env_loader.get_env_var('BROKER_SECRET_KEY', ''),
            'testnet': self.env_loader.get_bool_env_var('BROKER_TESTNET', True),
            'broker_name': self.env_loader.get_env_var('BROKER_NAME', 'default'),
            'paper_trading': self.env_loader.get_bool_env_var('BROKER_PAPER_TRADING', False),
            'bingx_api_key': self.env_loader.get_env_var('BINGX_API_KEY', ''),
            'bingx_secret_key': self.env_loader.get_env_var('BINGX_SECRET_KEY', ''),
            'bingx_order_placement_enabled': self.env_loader.get_bool_env_var('BINGX_ORDER_PLACEMENT_ENABLED', True),
            'bingx_testnet': self.env_loader.get_bool_env_var('BINGX_TESTNET', True),
            'default_broker': self.env_loader.get_env_var('DEFAULT_BROKER', 'bingx'),
            'binance_api_key': self.env_loader.get_env_var('BINANCE_API_KEY', ''),
            'binance_secret_key': self.env_loader.get_env_var('BINANCE_SECRET_KEY', ''),
            'binance_order_placement_enabled': self.env_loader.get_bool_env_var('BINANCE_ORDER_PLACEMENT_ENABLED', False),
            'binance_testnet': self.env_loader.get_bool_env_var('BINANCE_TESTNET', True),
            'mexc_api_key': self.env_loader.get_env_var('MEXC_API_KEY', ''),
            'mexc_secret_key': self.env_loader.get_env_var('MEXC_SECRET_KEY', ''),
            'mexc_order_placement_enabled': self.env_loader.get_bool_env_var('MEXC_ORDER_PLACEMENT_ENABLED', False),
            'mexc_testnet': self.env_loader.get_bool_env_var('MEXC_TESTNET', True),
            'phemex_api_key': self.env_loader.get_env_var('PHEMEX_API_KEY', ''),
            'phemex_secret_key': self.env_loader.get_env_var('PHEMEX_SECRET_KEY', ''),
            'phemex_order_placement_enabled': self.env_loader.get_bool_env_var('PHEMEX_ORDER_PLACEMENT_ENABLED', False),
            'phemex_testnet': self.env_loader.get_bool_env_var('PHEMEX_TESTNET', True),
            'binance_api_url': self.env_loader.get_env_var('BINANCE_API_URL', 'https://api.binance.com'),
            'binance_retry_attempts': self.env_loader.get_int_env_var('BINANCE_RETRY_ATTEMPTS', 3),
            'binance_rate_limit_delay': self.env_loader.get_float_env_var('BINANCE_RATE_LIMIT_DELAY', 0.1),
            'bingx_passphrase': self.env_loader.get_env_var('BINGX_PASSPHRASE', ''),
            'enabled_brokers': self.env_loader.get_list_env_var('ENABLED_BROKERS', ['bingx']),
        }
        return broker_data

    def _extract_risk_config_data(self) -> Dict[str, Any]:
        """Extract risk configuration data from environment variables."""
        risk_data = {
            'max_position_size': self.env_loader.get_float_env_var('RISK_MAX_POSITION_SIZE', 0.05),
            'max_drawdown': self.env_loader.get_float_env_var('RISK_MAX_DRAWDOWN', 0.15),
            'max_risk_per_trade': self.env_loader.get_float_env_var('RISK_MAX_RISK_PER_TRADE', 0.02),
            'max_correlation': self.env_loader.get_float_env_var('RISK_MAX_CORRELATION', 0.7),
            'max_leverage': self.env_loader.get_float_env_var('RISK_MAX_LEVERAGE', 5.0),
            'stop_loss_percentage': self.env_loader.get_float_env_var('RISK_STOP_LOSS_PERCENTAGE', 0.02),
            'take_profit_percentage': self.env_loader.get_float_env_var('RISK_TAKE_PROFIT_PERCENTAGE', 0.05),
            'max_total_exposure': self.env_loader.get_float_env_var('RISK_MAX_TOTAL_EXPOSURE', 0.80),
            'capital_per_symbol': self.env_loader.get_float_env_var('RISK_CAPITAL_PER_SYMBOL', 0.02),
            'max_exposure': self.env_loader.get_float_env_var('RISK_MAX_EXPOSURE', 0.60),
            'per_trade': self.env_loader.get_float_env_var('RISK_PER_TRADE', 0.02),
            'max_daily_loss': self.env_loader.get_float_env_var('RISK_MAX_DAILY_LOSS', 0.02),
            'max_total_positions': self.env_loader.get_int_env_var('RISK_MAX_TOTAL_POSITIONS', 5),
            'max_correlation_between_pos': self.env_loader.get_float_env_var('RISK_MAX_CORRELATION_BETWEEN_POS', 0.6),
            'max_sector_exposure': self.env_loader.get_float_env_var('RISK_MAX_SECTOR_EXPOSURE', 0.25),
            'max_single_asset_exposure': self.env_loader.get_float_env_var('RISK_MAX_SINGLE_ASSET_EXPOSURE', 0.10),
            'emergency_stop_drawdown': self.env_loader.get_float_env_var('RISK_EMERGENCY_STOP_DRAWDOWN', 0.15),
            'min_order_size': self.env_loader.get_float_env_var('MIN_ORDER_SIZE', 0.05),
            'max_order_size': self.env_loader.get_float_env_var('MAX_ORDER_SIZE', 0.05),
            'min_position_size': self.env_loader.get_float_env_var('MIN_POSITION_SIZE', 0.05),
            'max_position_concentration': self.env_loader.get_float_env_var('MAX_POSITION_CONCENTRATION', 0.3),
            'max_portfolio_risk': self.env_loader.get_float_env_var('MAX_PORTFOLIO_RISK', 0.02),
            'max_position_risk': self.env_loader.get_float_env_var('MAX_POSITION_RISK', 0.02),
            'max_drawdown_threshold': self.env_loader.get_float_env_var('MAX_DRAWDOWN_THRESHOLD', 0.3),
            'max_daily_loss_threshold': self.env_loader.get_float_env_var('MAX_DAILY_LOSS', 0.02),
            'max_total_positions_limit': self.env_loader.get_int_env_var('MAX_TOTAL_POSITIONS', 5),
            'max_correlation_limit': self.env_loader.get_float_env_var('MAX_CORRELATION', 0.7),
            'max_leverage_limit': self.env_loader.get_float_env_var('MAX_LEVERAGE', 5.0),
            'max_order_size_limit': self.env_loader.get_float_env_var('MAX_ORDER_SIZE', 0.05),
        }
        return risk_data

    def _extract_strategy_config_data(self) -> Dict[str, Any]:
        """Extract strategy configuration data from environment variables."""
        strategy_data = {
            'strategy_name': self.env_loader.get_env_var('DEFAULT_STRATEGY', 'crypto_breakout'),
            'risk_per_trade': self.env_loader.get_float_env_var('STRATEGY_RISK_PER_TRADE', 0.02),
            'max_position_size': self.env_loader.get_float_env_var('STRATEGY_MAX_POSITION_SIZE', 0.05),
            'min_volume_filter': self.env_loader.get_float_env_var('STRATEGY_MIN_VOLUME_FILTER', 10000.0),
            'signal_cooldown_minutes': self.env_loader.get_int_env_var('STRATEGY_SIGNAL_COOLDOWN_MINUTES', 30),
            'min_confidence_threshold': self.env_loader.get_float_env_var('STRATEGY_MIN_CONFIDENCE_THRESHOLD', 0.5),
            'high_confidence_threshold': self.env_loader.get_float_env_var('STRATEGY_HIGH_CONFIDENCE_THRESHOLD', 0.7),
            'neutral_buffer': self.env_loader.get_float_env_var('STRATEGY_NEUTRAL_BUFFER', 0.03),
            'strong_directional_bias_threshold': self.env_loader.get_float_env_var('STRATEGY_STRONG_DIRECTIONAL_BIAS_THRESHOLD', 0.3),
            'anomaly_ml_contamination': self.env_loader.get_float_env_var('ANOMALY_ML_CONTAMINATION', 0.1),
            'atr_default_percentage': self.env_loader.get_float_env_var('ATR_DEFAULT_PERCENTAGE', 0.02),
            'atr_fixed_dollar_risk': self.env_loader.get_float_env_var('ATR_FIXED_DOLLAR_RISK', 100.0),
            'atr_max_portfolio_percent': self.env_loader.get_float_env_var('ATR_MAX_PORTFOLIO_PERCENT', 0.05),
            'atr_min_multiple': self.env_loader.get_float_env_var('ATR_MIN_MULTIPLE', 1.0),
            'atr_multiplier': self.env_loader.get_float_env_var('ATR_MULTIPLIER', 1.5),
            'atr_to_volatility_multiplier': self.env_loader.get_float_env_var('ATR_TO_VOLATILITY_MULTIPLIER', 1.5),
            'base_reward_risk_ratio': self.env_loader.get_float_env_var('BASE_REWARD_RISK_RATIO', 0.3),
            'confidence_rr_multiplier': self.env_loader.get_float_env_var('CONFIDENCE_RR_MULTIPLIER', 0.3),
            'default_annual_volatility': self.env_loader.get_float_env_var('DEFAULT_ANNUAL_VOLATILITY', 0.2),
            'default_asset_volatility': self.env_loader.get_float_env_var('DEFAULT_ASSET_VOLATILITY', 0.2),
            'edge_estimation_factor': self.env_loader.get_float_env_var('EDGE_ESTIMATION_FACTOR', 0.55),
            'engine_confidence_threshold': self.env_loader.get_float_env_var('ENGINE_CONFIDENCE_THRESHOLD', 0.3),
            'enabled_engines': self.env_loader.get_list_env_var('ENABLED_ENGINES', ['engine1']),
            'high_volatility_threshold': self.env_loader.get_float_env_var('HIGH_VOLATILITY_THRESHOLD', 0.3),
            'high_volatility_win_rate_impact': self.env_loader.get_float_env_var('HIGH_VOLATILITY_WIN_RATE_IMPACT', 0.1),
            'low_volatility_threshold': self.env_loader.get_float_env_var('LOW_VOLATILITY_THRESHOLD', 0.3),
            'low_volatility_win_rate_impact': self.env_loader.get_float_env_var('LOW_VOLATILITY_WIN_RATE_IMPACT', 0.05),
            'maximum_win_rate_threshold': self.env_loader.get_float_env_var('MAXIMUM_WIN_RATE_THRESHOLD', 0.3),
            'max_reward_risk_ratio': self.env_loader.get_float_env_var('MAX_REWARD_RISK_RATIO', 0.3),
            'max_trend_impact_on_edge': self.env_loader.get_float_env_var('MAX_TREND_IMPACT_ON_EDGE', 0.1),
            'max_trend_impact_on_win_rate': self.env_loader.get_float_env_var('MAX_TREND_IMPACT_ON_WIN_RATE', 0.1),
            'max_volatility_impact_on_edge': self.env_loader.get_float_env_var('MAX_VOLATILITY_IMPACT_ON_EDGE', 0.1),
            'min_confidence_rr_factor': self.env_loader.get_float_env_var('MIN_CONFIDENCE_RR_FACTOR', 0.3),
            'min_reward_risk_ratio': self.env_loader.get_float_env_var('MIN_REWARD_RISK_RATIO', 0.3),
            'ml_weights_enabled': self.env_loader.get_bool_env_var('ML_WEIGHTS_ENABLED', True),
            'regime_detection_enabled': self.env_loader.get_bool_env_var('REGIME_DETECTION_ENABLED', True),
            'signal_fusion_enabled': self.env_loader.get_bool_env_var('SIGNAL_FUSION_ENABLED', True),
            'signal_threshold': self.env_loader.get_float_env_var('SIGNAL_THRESHOLD', 0.3),
            'target_volatility': self.env_loader.get_float_env_var('TARGET_VOLATILITY', 0.2),
            'trend_impact_on_win_rate_multiplier': self.env_loader.get_float_env_var('TREND_IMPACT_ON_WIN_RATE_MULTIPLIER', 1.5),
            'trend_max_rr_impact': self.env_loader.get_float_env_var('TREND_MAX_RR_IMPACT', 0.1),
            'trend_mtf_long_period': self.env_loader.get_int_env_var('TREND_MTF_LONG_PERIOD', 50),
            'trend_mtf_medium_period': self.env_loader.get_int_env_var('TREND_MTF_MEDIUM_PERIOD', 50),
            'trend_mtf_short_period': self.env_loader.get_int_env_var('TREND_MTF_SHORT_PERIOD', 50),
            'trend_rr_multiplier': self.env_loader.get_float_env_var('TREND_RR_MULTIPLIER', 1.5),
            'minimum_win_rate_threshold': self.env_loader.get_float_env_var('MINIMUM_WIN_RATE_THRESHOLD', 0.3),
            'opportunity_score_confidence_weight': self.env_loader.get_float_env_var('OPPORTUNITY_SCORE_CONFIDENCE_WEIGHT', 0.4),
            'opportunity_score_dominance_weight': self.env_loader.get_float_env_var('OPPORTUNITY_SCORE_DOMINANCE_WEIGHT', 0.2),
            'opportunity_score_position_size_weight': self.env_loader.get_float_env_var('OPPORTUNITY_SCORE_POSITION_SIZE_WEIGHT', 0.15),
            'opportunity_score_reward_risk_weight': self.env_loader.get_float_env_var('OPPORTUNITY_SCORE_REWARD_RISK_WEIGHT', 0.15),
            'opportunity_score_regime_bonus': self.env_loader.get_float_env_var('OPPORTUNITY_SCORE_REGIME_BONUS', 0.15),
            'enable_shorting': self.env_loader.get_bool_env_var('ENABLE_SHORTING', False),
        }
        return strategy_data

    def _extract_execution_config_data(self) -> Dict[str, Any]:
        """Extract execution configuration data from environment variables."""
        execution_data = {
            'order_type': self.env_loader.get_env_var('EXECUTION_ORDER_TYPE', 'MARKET'),
            'limit_slippage': self.env_loader.get_float_env_var('EXECUTION_LIMIT_SLIPPAGE', 0.002),
            'price_band_width': self.env_loader.get_float_env_var('EXECUTION_PRICE_BAND_WIDTH', 0.005),
            'max_partial_fill_percent': self.env_loader.get_float_env_var('EXECUTION_MAX_PARTIAL_FILL_PERCENT', 0.90),
            'min_order_quantity': self.env_loader.get_float_env_var('MIN_ORDER_QUANTITY', 0.001),
            'order_timeout': self.env_loader.get_int_env_var('ORDER_TIMEOUT', 30),
            'slippage_factor': self.env_loader.get_float_env_var('SLIPPAGE_FACTOR', 0.001),
            'slippage_rate': self.env_loader.get_float_env_var('SLIPPAGE_RATE', 0.001),
            'slippage_tolerance': self.env_loader.get_float_env_var('SLIPPAGE_TOLERANCE', 0.005),
            'smart_order_routing': self.env_loader.get_bool_env_var('SMART_ORDER_ROUTING', False),
            'enable_twap': self.env_loader.get_bool_env_var('ENABLE_TWAP', False),
            'enable_vwap': self.env_loader.get_bool_env_var('ENABLE_VWAP', False),
        }
        return execution_data

    def _extract_safety_config_data(self) -> Dict[str, Any]:
        """Extract safety configuration data from environment variables."""
        safety_data = {
            'kill_switch_enabled': self.env_loader.get_bool_env_var('SAFETY_KILL_SWITCH_ENABLED', True),
            'emergency_stop_enabled': self.env_loader.get_bool_env_var('SAFETY_EMERGENCY_STOP_ENABLED', True),
            'max_order_size_usd': self.env_loader.get_float_env_var('SAFETY_MAX_ORDER_SIZE_USD', 10000.0),
            'max_daily_orders': self.env_loader.get_int_env_var('SAFETY_MAX_DAILY_ORDERS', 50),
            'api_rate_limit_buffer': self.env_loader.get_float_env_var('SAFETY_API_RATE_LIMIT_BUFFER', 0.15),
            'enable_kill_switch': self.env_loader.get_bool_env_var('ENABLE_KILL_SWITCH', True),
        }
        return safety_data

    def _extract_data_config_data(self) -> Dict[str, Any]:
        """Extract data configuration data from environment variables."""
        data_data = {
            'path': self.env_loader.get_env_var('DATA_PATH', './data'),
            'results_dir': self.env_loader.get_env_var('RESULTS_DIR', './results'),
            'cache_dir': self.env_loader.get_env_var('CACHE_DIR', './cache'),
            'coin_history_cache_dir': self.env_loader.get_env_var('COIN_HISTORY_CACHE_DIR', './data/coin_history_cache'),
            'max_cache_age_hours': self.env_loader.get_int_env_var('MAX_CACHE_AGE_HOURS', 24),
            'max_coin_cache_size': self.env_loader.get_int_env_var('MAX_COIN_CACHE_SIZE', 50),
            'default_provider': self.env_loader.get_env_var('DEFAULT_DATA_PROVIDER', 'binance'),
            'default_timeframe': self.env_loader.get_env_var('DEFAULT_TIMEFRAME', '1h'),
            'supported_timeframes': self.env_loader.get_list_env_var('SUPPORTED_TIMEFRAMES', ['1m', '5m', '15m', '1h', '4h', '1d']),
            'cmc_api_key': self.env_loader.get_env_var('CMC_API_KEY', ''),
            'cmc_listings_url': self.env_loader.get_env_var('CMC_LISTINGS_URL', 'https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest'),
            'cmc_quotes_url': self.env_loader.get_env_var('CMC_QUOTES_URL', 'https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest'),
            'cmc_excluded_coins': self.env_loader.get_list_env_var('CMC_EXCLUDED_COINS', ['BTC', 'ETH', 'SOL', 'ADA', 'DOT', 'XRP', 'DOGE', 'LINK', 'BNB', 'AVAX', 'MATIC', 'USDC', 'USDT', 'DAI']),
            'cmc_max_calls_per_minute': self.env_loader.get_int_env_var('CMC_MAX_CALLS_PER_MINUTE', 10),
            'cmc_max_calls_per_hour': self.env_loader.get_int_env_var('CMC_MAX_CALLS_PER_HOUR', 300),
            'cmc_api_call_interval': self.env_loader.get_float_env_var('CMC_API_CALL_INTERVAL', 4.0),
            'cmc_cache_ttl_seconds': self.env_loader.get_int_env_var('CMC_CACHE_TTL_SECONDS', 300),
            'cmc_listings_cache_ttl_seconds': self.env_loader.get_int_env_var('CMC_LISTINGS_CACHE_TTL_SECONDS', 1800),
            'cmc_quote_cache_ttl_seconds': self.env_loader.get_int_env_var('CMC_QUOTE_CACHE_TTL_SECONDS', 300),
            'cmc_screen_top_coins_interval_hours': self.env_loader.get_int_env_var('CMC_SCREEN_TOP_COINS_INTERVAL_HOURS', 1),
            'cmc_screen_top_coins_limit': self.env_loader.get_int_env_var('CMC_SCREEN_TOP_COINS_LIMIT', 50),
            'cmc_max_coins_to_analyze_per_run': self.env_loader.get_int_env_var('CMC_MAX_COINS_TO_ANALYZE_PER_RUN', 20),
            'cmc_circuit_breaker_failure_threshold': self.env_loader.get_int_env_var('CMC_CIRCUIT_BREAKER_FAILURE_THRESHOLD', 3),
            'cmc_circuit_breaker_reset_timeout': self.env_loader.get_int_env_var('CMC_CIRCUIT_BREAKER_RESET_TIMEOUT', 600),
            'cmc_min_confidence_threshold': self.env_loader.get_float_env_var('CMC_MIN_CONFIDENCE_THRESHOLD', 0.02),
            'cmc_vol_confidence_weight': self.env_loader.get_float_env_var('CMC_VOL_CONFIDENCE_WEIGHT', 0.2),
            'cmc_volume_confidence_weight': self.env_loader.get_float_env_var('CMC_VOLUME_CONFIDENCE_WEIGHT', 0.3),
            'cmc_change_confidence_weight': self.env_loader.get_float_env_var('CMC_CHANGE_CONFIDENCE_WEIGHT', 0.2),
            'sync_interval_seconds': self.env_loader.get_int_env_var('SYNC_INTERVAL_SECONDS', 3600),
            'async_concurrency': self.env_loader.get_int_env_var('ASYNC_CONCURRENCY', 50),
            'download_threadpool_workers': self.env_loader.get_int_env_var('DOWNLOAD_THREADPOOL_WORKERS', 4),
            'retry_max_attempts': self.env_loader.get_int_env_var('RETRY_MAX_ATTEMPTS', 3),
            'retry_backoff_base': self.env_loader.get_float_env_var('RETRY_BACKOFF_BASE', 0.3),
            'retry_backoff_factor': self.env_loader.get_float_env_var('RETRY_BACKOFF_FACTOR', 1.5),
            'rate_limit_tokens_per_second': self.env_loader.get_float_env_var('RATE_LIMIT_TOKENS_PER_SECOND', 5),
            'temp_file_suffix': self.env_loader.get_env_var('TEMP_FILE_SUFFIX', '.partial'),
            'dir': self.env_loader.get_env_var('DATA_DIR', './data/history'),
            'raw_retention_days': self.env_loader.get_int_env_var('RAW_RETENTION_DAYS', 180),
            'processed_retention_days': self.env_loader.get_int_env_var('PROCESSED_RETENTION_DAYS', 730),
            'max_gap_fill_minutes': self.env_loader.get_int_env_var('MAX_GAP_FILL_MINUTES', 720),
            'sync_default_exchange': self.env_loader.get_env_var('SYNC_DEFAULT_EXCHANGE', 'bingx'),
            'sync_max_window_minutes': self.env_loader.get_int_env_var('SYNC_MAX_WINDOW_MINUTES', 720),
            'sync_rate_limit': self.env_loader.get_int_env_var('SYNC_RATE_LIMIT', 5),
            'filter_out_stablecoin_pairs': self.env_loader.get_bool_env_var('FILTER_OUT_STABLECOIN_PAIRS', True),
            'allowed_stablecoins': self.env_loader.get_list_env_var('ALLOWED_STABLECOINS', ['USDT', 'BUSD', 'USDC', 'DAI', 'PAX', 'TUSD', 'USDD', 'FDUSD']),
            'excluded_symbols_pattern': self.env_loader.get_env_var('EXCLUDED_SYMBOLS_PATTERN', 'USD[SD]/?USD[SD]|BTC/BTC|ETH/ETH'),
            'csv_data_path': self.env_loader.get_env_var('CSV_DATA_PATH', './data/history/raw/1m'),
            'default_watchlist_symbols': self.env_loader.get_list_env_var('DEFAULT_WATCHLIST_SYMBOLS', ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'ADAUSDT', 'DOGEUSDT', 'AVAXUSDT', 'TRXUSDT', 'DOTUSDT', 'LINKUSDT']),
            'failed_symbols_cache_duration': self.env_loader.get_int_env_var('FAILED_SYMBOLS_CACHE_DURATION', 300),
            'fallback_watchlist_symbols': self.env_loader.get_list_env_var('FALLBACK_WATCHLIST_SYMBOLS', ['BTCUSDT']),
            'historical_data_fallback_sources': self.env_loader.get_list_env_var('HISTORICAL_DATA_FALLBACK_SOURCES', ['binance', 'mexc', 'phemex', 'bingx']),
            'preferred_historical_data_source': self.env_loader.get_env_var('PREFERRED_HISTORICAL_DATA_SOURCE', 'binance'),
            'validate_symbol_data_availability': self.env_loader.get_env_var('VALIDATE_SYMBOL_DATA_AVAILABILITY', 'BTCUSDT'),
            'cmc_categories_url': self.env_loader.get_env_var('CMC_CATEGORIES_URL', 'https://pro-api.coinmarketcap.com/v1/cryptocurrency/categories/list'),
            'cmc_update_interval': self.env_loader.get_int_env_var('CMC_UPDATE_INTERVAL', 300),
            'cmc_volatility_high_threshold': self.env_loader.get_float_env_var('CMC_VOLATILITY_HIGH_THRESHOLD', 0.3),
            'cmc_volatility_low_threshold': self.env_loader.get_float_env_var('CMC_VOLATILITY_LOW_THRESHOLD', 0.3),
            'cmc_volume_high_threshold': self.env_loader.get_float_env_var('CMC_VOLUME_HIGH_THRESHOLD', 0.3),
            'cmc_volume_low_threshold': self.env_loader.get_float_env_var('CMC_VOLUME_LOW_THRESHOLD', 0.3),
        }
        return data_data

    def _extract_optimization_config_data(self) -> Dict[str, Any]:
        """Extract optimization configuration data from environment variables."""
        optimization_data = {
            'algorithm': self.env_loader.get_env_var('HYPEROPT_ALGORITHM', 'tpe'),
            'max_evals': self.env_loader.get_int_env_var('HYPEROPT_MAX_EVALS', 50),
            'early_stopping_rounds': self.env_loader.get_int_env_var('HYPEROPT_EARLY_STOPPING_ROUNDS', 5),
            'validation_split': self.env_loader.get_float_env_var('HYPEROPT_VALIDATION_SPLIT', 0.15),
            'objective_metric': self.env_loader.get_env_var('HYPEROPT_OBJECTIVE_METRIC', 'sharpe_ratio'),
            'min_returns': self.env_loader.get_float_env_var('OPTIMIZATION_MIN_RETURNS', 0.02),
            'min_sharpe_ratio': self.env_loader.get_float_env_var('OPTIMIZATION_MIN_SHARPE_RATIO', 0.05),
            'max_drawdown': self.env_loader.get_float_env_var('OPTIMIZATION_MAX_DRAWDOWN', 0.15),
            'min_win_rate': self.env_loader.get_float_env_var('OPTIMIZATION_MIN_WIN_RATE', 0.30),
            'retune_enabled': self.env_loader.get_bool_env_var('RETUNE_ENABLED', True),
            'retune_interval_hours': self.env_loader.get_int_env_var('RETUNE_INTERVAL_HOURS', 3),
            'retune_performance_threshold': self.env_loader.get_float_env_var('RETUNE_PERFORMANCE_THRESHOLD', 0.10),
            'retune_evals_per_retune': self.env_loader.get_int_env_var('RETUNE_EVALS_PER_RETUNE', 15),
            'retune_retention_period_days': self.env_loader.get_int_env_var('RETUNE_RETENTION_PERIOD_DAYS', 5),
        }
        return optimization_data

    def _extract_wfo_config_data(self) -> Dict[str, Any]:
        """Extract WFO configuration data from environment variables."""
        wfo_data = {
            'train_size': self.env_loader.get_int_env_var('WFO_TRAIN_SIZE', 90),
            'test_size': self.env_loader.get_int_env_var('WFO_TEST_SIZE', 30),
            'step_size': self.env_loader.get_int_env_var('WFO_STEP_SIZE', 30),
            'max_evals': self.env_loader.get_int_env_var('WFO_MAX_EVALS', 50),
            'performance_threshold': self.env_loader.get_float_env_var('WFO_PERFORMANCE_THRESHOLD', 0.1),
            'max_drawdown_threshold': self.env_loader.get_float_env_var('WFO_MAX_DRAWDOWN_THRESHOLD', 0.15),
            'retrain_frequency_days': self.env_loader.get_int_env_var('WFO_RETRAIN_FREQUENCY_DAYS', 30),
            'min_training_points': self.env_loader.get_int_env_var('WFO_MIN_TRAINING_POINTS', 30),
            'min_testing_points': self.env_loader.get_int_env_var('WFO_MIN_TESTING_POINTS', 10),
            'overfit_threshold': self.env_loader.get_float_env_var('WFO_OVERFIT_THRESHOLD', 1.0),
            'consistency_threshold': self.env_loader.get_float_env_var('WFO_CONSISTENCY_THRESHOLD', 0.60),
            'pass_rate_threshold': self.env_loader.get_float_env_var('WFO_PASS_RATE_THRESHOLD', 0.60),
            'wfo_enabled': self.env_loader.get_bool_env_var('WFO_ENABLED', True),
            'coins': self.env_loader.get_list_env_var('WFO_COINS', ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'XRPUSDT', 'SOLUSDT', 'DOTUSDT', 'DOGEUSDT', 'AVAXUSDT', 'SHIBUSDT', 'TRXUSDT', 'LTCUSDT', 'UNIUSDT', 'LINKUSDT', 'LUNAUSDT', 'TONUSDT', 'ALGOUSDT', 'XLMUSDT', 'ETCUSDT', 'BCHUSDT', 'NEARUSDT', 'FLOWUSDT', 'MANAUSDT', 'SANDUSDT', 'AAVEUSDT']),
            'data_dir': self.env_loader.get_env_var('WFO_DATA_DIR', './data'),
            'raw_dir': self.env_loader.get_env_var('WFO_RAW_DIR', './data/history/raw/1m'),
            'processed_dir': self.env_loader.get_env_var('WFO_PROCESSED_DIR', './data/history/processed'),
            'sync_days': self.env_loader.get_int_env_var('WFO_SYNC_DAYS', 180),
            'incremental_days': self.env_loader.get_int_env_var('WFO_INCREMENTAL_DAYS', 2),
            'refresh_interval_hours': self.env_loader.get_int_env_var('WFO_REFRESH_INTERVAL_HOURS', 24),
            'default_timeframes': self.env_loader.get_list_env_var('WFO_DEFAULT_TIMEFRAMES', ['5m', '15m', '30m', '1h']),
        }
        return wfo_data

    def _extract_monitoring_config_data(self) -> Dict[str, Any]:
        """Extract monitoring configuration data from environment variables."""
        monitoring_data = {
            'telegram_bot_name': self.env_loader.get_env_var('TELEGRAM_BOT_NAME', '@LynxionNotifierBot'),
            'telegram_bot_url': self.env_loader.get_env_var('TELEGRAM_BOT_URL', 't.me/LynxionNotifierBot'),
            'telegram_bot_update_url': self.env_loader.get_env_var('TELEGRAM_BOT_UPDATE_URL', 'https://api.telegram.org/bot8324444752:AAGoubuQSgXp6lhQGCxcOtGT6hLg3kTgWbY/getUpdates'),
            'telegram_bot_token': self.env_loader.get_env_var('TELEGRAM_BOT_TOKEN', '8324444752:AAGoubuQSgXp6lhQGCxcOtGT6hLg3kTgWbY'),
            'telegram_chat_id': self.env_loader.get_env_var('TELEGRAM_CHAT_ID', '71819811'),
            'telegram_notifications_enabled': self.env_loader.get_bool_env_var('TELEGRAM_NOTIFICATIONS_ENABLED', True),
            'logging_level': self.env_loader.get_env_var('LOG_LEVEL', 'DEBUG'),
            'log_file_path': self.env_loader.get_env_var('LOG_FILE_PATH', './logs/trading_system.log'),
            'log_max_file_size_mb': self.env_loader.get_int_env_var('LOG_MAX_FILE_SIZE_MB', 50),
            'log_backup_count': self.env_loader.get_int_env_var('LOG_BACKUP_COUNT', 5),
            'enabled': self.env_loader.get_bool_env_var('MONITORING_ENABLED', True),
            'metrics_reporting_interval_minutes': self.env_loader.get_int_env_var('METRICS_REPORTING_INTERVAL_MINUTES', 3),
            'forensic_logging_enabled': self.env_loader.get_bool_env_var('FORENSIC_LOGGING_ENABLED', True),
            'enable_metrics': self.env_loader.get_bool_env_var('ENABLE_METRICS', True),
        }
        return monitoring_data

    def _extract_analytics_config_data(self) -> Dict[str, Any]:
        """Extract analytics configuration data from environment variables."""
        # For now, return empty dict - analytics config will be filled based on actual requirements
        return {}

    def _extract_infrastructure_config_data(self) -> Dict[str, Any]:
        """Extract infrastructure configuration data from environment variables."""
        infrastructure_data = {
            'use_multiprocessing': self.env_loader.get_bool_env_var('PERFORMANCE_USE_MULTIPROCESSING', True),
            'num_workers': self.env_loader.get_int_env_var('PERFORMANCE_NUM_WORKERS', 2),
            'batch_size': self.env_loader.get_int_env_var('PERFORMANCE_BATCH_SIZE', 500),
            'memory_profiling': self.env_loader.get_bool_env_var('PERFORMANCE_MEMORY_PROFILING', False),
            'api_timeout': self.env_loader.get_int_env_var('API_TIMEOUT', 30),
            'max_workers': self.env_loader.get_int_env_var('MAX_WORKERS', 4),
            'redis_url': self.env_loader.get_env_var('REDIS_URL', 'redis://localhost:6379/0'),
            'debug': self.env_loader.get_bool_env_var('DEBUG', False),
            'environment': self.env_loader.get_env_var('ENVIRONMENT', 'production'),
            'use_mock_data': self.env_loader.get_bool_env_var('USE_MOCK_DATA', False),

            # Additional fields needed for position sizing service
            'edge_estimation_factor': self.env_loader.get_float_env_var('EDGE_ESTIMATION_FACTOR', 0.1),
            'default_asset_volatility': self.env_loader.get_float_env_var('DEFAULT_ASSET_VOLATILITY', 0.02),
            'max_volatility_impact_on_edge': self.env_loader.get_float_env_var('MAX_VOLATILITY_IMPACT_ON_EDGE', 0.2),
            'volatility_impact_multiplier': self.env_loader.get_float_env_var('VOLATILITY_IMPACT_MULTIPLIER', 2.0),
            'max_trend_impact_on_edge': self.env_loader.get_float_env_var('MAX_TREND_IMPACT_ON_EDGE', 0.5),
            'high_volatility_threshold': self.env_loader.get_float_env_var('HIGH_VOLATILITY_THRESHOLD', 0.05),
            'low_volatility_threshold': self.env_loader.get_float_env_var('LOW_VOLATILITY_THRESHOLD', 0.01),
            'high_volatility_win_rate_impact': self.env_loader.get_float_env_var('HIGH_VOLATILITY_WIN_RATE_IMPACT', 0.8),
            'low_volatility_win_rate_impact': self.env_loader.get_float_env_var('LOW_VOLATILITY_WIN_RATE_IMPACT', 0.9),
            'trend_impact_on_win_rate_multiplier': self.env_loader.get_float_env_var('TREND_IMPACT_ON_WIN_RATE_MULTIPLIER', 0.5),
            'max_trend_impact_on_win_rate': self.env_loader.get_float_env_var('MAX_TREND_IMPACT_ON_WIN_RATE', 0.2),
            'minimum_win_rate_threshold': self.env_loader.get_float_env_var('MINIMUM_WIN_RATE_THRESHOLD', 0.4),
            'maximum_win_rate_threshold': self.env_loader.get_float_env_var('MAXIMUM_WIN_RATE_THRESHOLD', 0.9),
            'base_reward_risk_ratio': self.env_loader.get_float_env_var('BASE_REWARD_RISK_RATIO', 1.5),
            'min_confidence_rr_factor': self.env_loader.get_float_env_var('MIN_CONFIDENCE_RR_FACTOR', 0.7),
            'confidence_rr_multiplier': self.env_loader.get_float_env_var('CONFIDENCE_RR_MULTIPLIER', 0.6),
            'min_reward_risk_ratio': self.env_loader.get_float_env_var('MIN_REWARD_RISK_RATIO', 0.5),
            'max_reward_risk_ratio': self.env_loader.get_float_env_var('MAX_REWARD_RISK_RATIO', 5.0),
            'default_annual_volatility': self.env_loader.get_float_env_var('DEFAULT_ANNUAL_VOLATILITY', 0.20),
        }
        return infrastructure_data

    def _extract_position_sizing_config_data(self) -> Dict[str, Any]:
        """Extract position sizing configuration data from environment variables."""
        position_sizing_data = {
            'fixed_position_size_enabled': self.env_loader.get_bool_env_var('FIXED_POSITION_SIZE_ENABLED', True),
            'fixed_position_amount': self.env_loader.get_float_env_var('FIXED_POSITION_AMOUNT', 4.0),
            'default_account_balance': self.env_loader.get_float_env_var('DEFAULT_ACCOUNT_BALANCE', 10000.0),
            'fixed_fractional_default_percentage': self.env_loader.get_float_env_var('FIXED_FRACTIONAL_DEFAULT_PERCENTAGE', 0.02),
            'fixed_fractional_percentage': self.env_loader.get_float_env_var('FIXED_FRACTIONAL_PERCENTAGE', 0.02),
            'fixed_fractional_risk_per_unit': self.env_loader.get_float_env_var('FIXED_FRACTIONAL_RISK_PER_UNIT', 0.02),
            'kelly_default_percentage': self.env_loader.get_float_env_var('KELLY_DEFAULT_PERCENTAGE', 0.02),
            'kelly_fraction': self.env_loader.get_float_env_var('KELLY_FRACTION', 0.25),
            'kelly_max_position_size': self.env_loader.get_float_env_var('KELLY_MAX_POSITION_SIZE', 0.05),
            'kelly_minimum_edge': self.env_loader.get_float_env_var('KELLY_MINIMUM_EDGE', 0.1),
            'kelly_var_confidence_level': self.env_loader.get_float_env_var('KELLY_VAR_CONFIDENCE_LEVEL', 0.3),
            'kelly_var_margin_of_safety_percentage': self.env_loader.get_float_env_var('KELLY_VAR_MARGIN_OF_SAFETY_PERCENTAGE', 0.05),
            'kelly_var_max_position_with_var': self.env_loader.get_float_env_var('KELLY_VAR_MAX_POSITION_WITH_VAR', 0.1),
            'kelly_var_stress_test_multiplier': self.env_loader.get_float_env_var('KELLY_VAR_STRESS_TEST_MULTIPLIER', 1.5),
            'martingale_base_risk_percentage': self.env_loader.get_float_env_var('MARTINGALE_BASE_RISK_PERCENTAGE', 0.02),
            'martingale_max_progression_levels': self.env_loader.get_int_env_var('MARTINGALE_MAX_PROGRESSION_LEVELS', 5),
            'martingale_max_total_exposure_multiplier': self.env_loader.get_float_env_var('MARTINGALE_MAX_TOTAL_EXPOSURE_MULTIPLIER', 1.5),
            'martingale_progression_multiplier': self.env_loader.get_float_env_var('MARTINGALE_PROGRESSION_MULTIPLIER', 1.5),
            'optimal_f_calculation_error_default': self.env_loader.get_float_env_var('OPTIMAL_F_CALCULATION_ERROR_DEFAULT', 0.1),
            'optimal_f_default_percentage': self.env_loader.get_float_env_var('OPTIMAL_F_DEFAULT_PERCENTAGE', 0.02),
            'optimal_f_error_fallback_percentage': self.env_loader.get_float_env_var('OPTIMAL_F_ERROR_FALLBACK_PERCENTAGE', 0.02),
            'optimal_f_max_per_trade': self.env_loader.get_float_env_var('OPTIMAL_F_MAX_PER_TRADE', 0.05),
            'method': self.env_loader.get_env_var('POSITION_SIZING_METHOD', 'risk_percentagerisk_percentage'),

            # Additional fields needed for position sizing service
            'atr_multiplier': self.env_loader.get_float_env_var('ATR_MULTIPLIER', 2.0),
            'atr_fixed_dollar_risk': self.env_loader.get_float_env_var('ATR_FIXED_DOLLAR_RISK', 1000.0),
            'atr_min_multiple': self.env_loader.get_float_env_var('ATR_MIN_MULTIPLE', 1.5),
            'atr_max_portfolio_percent': self.env_loader.get_float_env_var('ATR_MAX_PORTFOLIO_PERCENT', 0.10),
            'atr_default_percentage': self.env_loader.get_float_env_var('ATR_DEFAULT_PERCENTAGE', 0.015),
            'volatility_target': self.env_loader.get_float_env_var('VOLATILITY_TARGET', 0.15),
            'volatility_max_portfolio_percent': self.env_loader.get_float_env_var('VOLATILITY_MAX_PORTFOLIO_PERCENT', 0.15),
            'volatility_error_default_percentage': self.env_loader.get_float_env_var('VOLATILITY_ERROR_DEFAULT_PERCENTAGE', 0.01),
            'volatility_target_percentage': self.env_loader.get_float_env_var('VOLATILITY_TARGET_PERCENTAGE', 0.15),
            'volatility_max_portfolio_allocation': self.env_loader.get_float_env_var('VOLATILITY_MAX_PORTFOLIO_ALLOCATION', 0.15),
            'volatility_max_rr_impact': self.env_loader.get_float_env_var('VOLATILITY_MAX_RR_IMPACT', 0.5),
            'volatility_rr_multiplier': self.env_loader.get_float_env_var('VOLATILITY_RR_MULTIPLIER', 10.0),
            'atr_to_volatility_multiplier': self.env_loader.get_float_env_var('ATR_TO_VOLATILITY_MULTIPLIER', 1.0),
        }
        return position_sizing_data

    def _extract_watcher_config_data(self) -> Dict[str, Any]:
        """Extract watcher configuration data from environment variables."""
        watcher_data = {
            'polling_interval_seconds': self.env_loader.get_int_env_var('WATCHER_POLLING_INTERVAL_SECONDS', 15),
            'max_symbols_to_monitor': self.env_loader.get_int_env_var('WATCHER_MAX_SYMBOLS_TO_MONITOR', 10),
            'data_refresh_interval_minutes': self.env_loader.get_int_env_var('WATCHER_DATA_REFRESH_INTERVAL_MINUTES', 5),
            'risk_threshold': self.env_loader.get_float_env_var('WATCHER_RISK_THRESHOLD', 0.02),
            'min_confidence_threshold': self.env_loader.get_float_env_var('WATCHER_MIN_CONFIDENCE_THRESHOLD', 0.15),
            'max_confidence_with_patterns': self.env_loader.get_float_env_var('WATCHER_MAX_CONFIDENCE_WITH_PATTERNS', 0.2),
            'min_price_change_threshold': self.env_loader.get_float_env_var('WATCHER_MIN_PRICE_CHANGE_THRESHOLD', 0.0001),
            'max_confidence_with_movement': self.env_loader.get_float_env_var('WATCHER_MAX_CONFIDENCE_WITH_MOVEMENT', 0.25),
            'neutral_confidence': self.env_loader.get_float_env_var('WATCHER_NEUTRAL_CONFIDENCE', 0.05),
            'pattern_weight': self.env_loader.get_float_env_var('WATCHER_PATTERN_WEIGHT', 0.3),
            'momentum_weight': self.env_loader.get_float_env_var('WATCHER_MOMENTUM_WEIGHT', 0.2),
            'high_volatility_boost': self.env_loader.get_float_env_var('WATCHER_HIGH_VOLATILITY_BOOST', 0.1),
            'low_volatility_boost': self.env_loader.get_float_env_var('WATCHER_LOW_VOLATILITY_BOOST', 0.02),
            'normal_volatility_boost': self.env_loader.get_float_env_var('WATCHER_NORMAL_VOLATILITY_BOOST', 0.05),
            'min_confidence_when_signals_detected': self.env_loader.get_float_env_var('WATCHER_MIN_CONFIDENCE_WHEN_SIGNALS_DETECTED', 0.08),
            'max_confidence_cap': self.env_loader.get_float_env_var('WATCHER_MAX_CONFIDENCE_CAP', 0.85),
            'momentum_lookback_period': self.env_loader.get_int_env_var('WATCHER_MOMENTUM_LOOKBACK_PERIOD', 7),
            'momentum_sensitivity_factor': self.env_loader.get_float_env_var('WATCHER_MOMENTUM_SENSITIVITY_FACTOR', 7.0),
            'market_pulse_watcher_enabled': self.env_loader.get_bool_env_var('MARKET_PULSE_WATCHER_ENABLED', True),
            'volatility_watcher_enabled': self.env_loader.get_bool_env_var('VOLATILITY_WATCHER_ENABLED', True),
            'trend_mtf_watcher_enabled': self.env_loader.get_bool_env_var('TREND_MTF_WATCHER_ENABLED', True),
            'anomaly_ml_watcher_enabled': self.env_loader.get_bool_env_var('ANOMALY_ML_WATCHER_ENABLED', True),
            'orderflow_ws_watcher_enabled': self.env_loader.get_bool_env_var('ORDERFLOW_WS_WATCHER_ENABLED', True),
            'cmc_screener_enabled': self.env_loader.get_bool_env_var('CMC_SCREENER_ENABLED', True),
            'funding_rate_watcher_enabled': self.env_loader.get_bool_env_var('FUNDING_RATE_WATCHER_ENABLED', True),
            'liquidity_watcher_enabled': self.env_loader.get_bool_env_var('LIQUIDITY_WATCHER_ENABLED', True),
            'historical_candle_watcher_enabled': self.env_loader.get_bool_env_var('HISTORICAL_CANDLE_WATCHER_ENABLED', True),
            'tick_watcher_enabled': self.env_loader.get_bool_env_var('TICK_WATCHER_ENABLED', False),
            'broker_config': self.env_loader.get_env_var('WATCHER_BROKER_CONFIG', 'MarketPulse:bingx,Volatility:bingx,TrendMTF:bingx,AnomalyML:bingx,OrderFlow:bingx'),
            'target_broker_market_pulse': self.env_loader.get_env_var('TARGET_BROKER_MARKET_PULSE', 'bingx'),
            'target_broker_volatility': self.env_loader.get_env_var('TARGET_BROKER_VOLATILITY', 'bingx'),
            'target_broker_trend_mtf': self.env_loader.get_env_var('TARGET_BROKER_TREND_MTF', 'bingx'),
            'target_broker_anomaly_ml': self.env_loader.get_env_var('TARGET_BROKER_ANOMALY_ML', 'bingx'),
            'target_broker_orderflow_ws': self.env_loader.get_env_var('TARGET_BROKER_ORDERFLOW_WS', 'bingx'),
            'target_broker_funding_rate': self.env_loader.get_env_var('TARGET_BROKER_FUNDING_RATE', 'bingx'),
            'target_broker_liquidity': self.env_loader.get_env_var('TARGET_BROKER_LIQUIDITY', 'bingx'),
            'target_broker_historical_candle': self.env_loader.get_env_var('TARGET_BROKER_HISTORICAL_CANDLE', 'bingx'),
            'target_broker_tick_watcher': self.env_loader.get_env_var('TARGET_BROKER_TICK_WATCHER', 'bingx'),
            'use_improved_watchers': self.env_loader.get_bool_env_var('USE_IMPROVED_WATCHERS', True),
            'auto_enable_watchers': self.env_loader.get_bool_env_var('AUTO_ENABLE_WATCHERS', True),
            'enabled_watchers': self.env_loader.get_list_env_var('ENABLED_WATCHERS', ['market_pulse', 'volatility', 'trend_mtf', 'anomaly_ml', 'orderflow_ws', 'cmc_screener', 'funding_rate', 'liquidity', 'historical_candle']),
            'update_freq': self.env_loader.get_int_env_var('WATCHER_UPDATE_FREQ', 3030),
            'lookback': self.env_loader.get_int_env_var('WATCHER_LOOKBACK', 2020),
            'early_exit_momentum_threshold': self.env_loader.get_float_env_var('EARLY_EXIT_MOMENTUM_THRESHOLD', 0.0001),
            'early_exit_trend_confidence_threshold': self.env_loader.get_float_env_var('EARLY_EXIT_TREND_CONFIDENCE_THRESHOLD', 0.0001),
            'early_exit_volatility_threshold': self.env_loader.get_float_env_var('EARLY_EXIT_VOLATILITY_THRESHOLD', 0.0001),

            # Specific watcher configuration fields
            'market_pulse_lookback_period': self.env_loader.get_int_env_var('MARKET_PULSE_LOOKBACK_PERIOD', 20),
            'volatility_lookback_period': self.env_loader.get_int_env_var('VOLATILITY_LOOKBACK_PERIOD', 20),
            'trend_mtf_lookback_period': self.env_loader.get_int_env_var('TREND_MTF_LOOKBACK_PERIOD', 20),
            'anomaly_ml_lookback_period': self.env_loader.get_int_env_var('ANOMALY_ML_LOOKBACK_PERIOD', 50),
            'orderflow_ws_lookback_period': self.env_loader.get_int_env_var('ORDERFLOW_WS_LOOKBACK_PERIOD', 100),
            'cmc_screener_lookback_period': self.env_loader.get_int_env_var('CMC_SCREENER_LOOKBACK_PERIOD', 20),
            'funding_rate_lookback_period': self.env_loader.get_int_env_var('FUNDING_RATE_LOOKBACK_PERIOD', 24),
            'liquidity_lookback_period': self.env_loader.get_int_env_var('LIQUIDITY_LOOKBACK_PERIOD', 20),
            'historical_candle_lookback_period': self.env_loader.get_int_env_var('HISTORICAL_CANDLE_LOOKBACK_PERIOD', 50),
            'tick_lookback_period': self.env_loader.get_int_env_var('TICK_LOOKBACK_PERIOD', 1000),

            # Specific watcher min confidence thresholds
            'market_pulse_min_confidence_threshold': self.env_loader.get_float_env_var('MARKET_PULSE_MIN_CONFIDENCE_THRESHOLD', 0.05),
            'volatility_min_confidence_threshold': self.env_loader.get_float_env_var('VOLATILITY_MIN_CONFIDENCE_THRESHOLD', 0.05),
            'trend_mtf_min_confidence_threshold': self.env_loader.get_float_env_var('TREND_MTF_MIN_CONFIDENCE_THRESHOLD', 0.05),
            'anomaly_ml_min_confidence_threshold': self.env_loader.get_float_env_var('ANOMALY_ML_MIN_CONFIDENCE_THRESHOLD', 0.05),
            'orderflow_ws_min_confidence_threshold': self.env_loader.get_float_env_var('ORDERFLOW_WS_MIN_CONFIDENCE_THRESHOLD', 0.05),
            'cmc_screener_min_confidence_threshold': self.env_loader.get_float_env_var('CMC_SCREENER_MIN_CONFIDENCE_THRESHOLD', 0.05),
            'funding_rate_min_confidence_threshold': self.env_loader.get_float_env_var('FUNDING_RATE_MIN_CONFIDENCE_THRESHOLD', 0.05),
            'liquidity_min_confidence_threshold': self.env_loader.get_float_env_var('LIQUIDITY_MIN_CONFIDENCE_THRESHOLD', 0.05),
            'historical_candle_min_confidence_threshold': self.env_loader.get_float_env_var('HISTORICAL_CANDLE_MIN_CONFIDENCE_THRESHOLD', 0.05),
            'tick_min_confidence_threshold': self.env_loader.get_float_env_var('TICK_MIN_CONFIDENCE_THRESHOLD', 0.05),

            # Specific watcher max confidence thresholds
            'market_pulse_max_confidence_threshold': self.env_loader.get_float_env_var('MARKET_PULSE_MAX_CONFIDENCE_THRESHOLD', 0.95),
            'volatility_max_confidence_threshold': self.env_loader.get_float_env_var('VOLATILITY_MAX_CONFIDENCE_THRESHOLD', 0.95),
            'trend_mtf_max_confidence_threshold': self.env_loader.get_float_env_var('TREND_MTF_MAX_CONFIDENCE_THRESHOLD', 0.95),
            'anomaly_ml_max_confidence_threshold': self.env_loader.get_float_env_var('ANOMALY_ML_MAX_CONFIDENCE_THRESHOLD', 0.95),
            'orderflow_ws_max_confidence_threshold': self.env_loader.get_float_env_var('ORDERFLOW_WS_MAX_CONFIDENCE_THRESHOLD', 0.95),
            'cmc_screener_max_confidence_threshold': self.env_loader.get_float_env_var('CMC_SCREENER_MAX_CONFIDENCE_THRESHOLD', 0.95),
            'funding_rate_max_confidence_threshold': self.env_loader.get_float_env_var('FUNDING_RATE_MAX_CONFIDENCE_THRESHOLD', 0.95),
            'liquidity_max_confidence_threshold': self.env_loader.get_float_env_var('LIQUIDITY_MAX_CONFIDENCE_THRESHOLD', 0.95),
            'historical_candle_max_confidence_threshold': self.env_loader.get_float_env_var('HISTORICAL_CANDLE_MAX_CONFIDENCE_THRESHOLD', 0.95),
            'tick_max_confidence_threshold': self.env_loader.get_float_env_var('TICK_MAX_CONFIDENCE_THRESHOLD', 0.95),

            # Adaptive sensitivity settings
            'market_pulse_adaptive_sensitivity': self.env_loader.get_bool_env_var('MARKET_PULSE_ADAPTIVE_SENSITIVITY', False),
            'volatility_adaptive_sensitivity': self.env_loader.get_bool_env_var('VOLATILITY_ADAPTIVE_SENSITIVITY', False),
            'trend_mtf_adaptive_sensitivity': self.env_loader.get_bool_env_var('TREND_MTF_ADAPTIVE_SENSITIVITY', False),
            'anomaly_ml_adaptive_sensitivity': self.env_loader.get_bool_env_var('ANOMALY_ML_ADAPTIVE_SENSITIVITY', False),
            'orderflow_ws_adaptive_sensitivity': self.env_loader.get_bool_env_var('ORDERFLOW_WS_ADAPTIVE_SENSITIVITY', False),
            'cmc_screener_adaptive_sensitivity': self.env_loader.get_bool_env_var('CMC_SCREENER_ADAPTIVE_SENSITIVITY', False),
            'funding_rate_adaptive_sensitivity': self.env_loader.get_bool_env_var('FUNDING_RATE_ADAPTIVE_SENSITIVITY', False),
            'liquidity_adaptive_sensitivity': self.env_loader.get_bool_env_var('LIQUIDITY_ADAPTIVE_SENSITIVITY', False),
            'historical_candle_adaptive_sensitivity': self.env_loader.get_bool_env_var('HISTORICAL_CANDLE_ADAPTIVE_SENSITIVITY', False),
            'tick_adaptive_sensitivity': self.env_loader.get_bool_env_var('TICK_ADAPTIVE_SENSITIVITY', False),

            # Specific watcher pattern weights
            'market_pulse_pattern_weight': self.env_loader.get_float_env_var('MARKET_PULSE_PATTERN_WEIGHT', 0.4),
            'volatility_pattern_weight': self.env_loader.get_float_env_var('VOLATILITY_PATTERN_WEIGHT', 0.4),
            'trend_mtf_pattern_weight': self.env_loader.get_float_env_var('TREND_MTF_PATTERN_WEIGHT', 0.4),
            'anomaly_ml_pattern_weight': self.env_loader.get_float_env_var('ANOMALY_ML_PATTERN_WEIGHT', 0.4),
            'orderflow_ws_pattern_weight': self.env_loader.get_float_env_var('ORDERFLOW_WS_PATTERN_WEIGHT', 0.4),
            'cmc_screener_pattern_weight': self.env_loader.get_float_env_var('CMC_SCREENER_PATTERN_WEIGHT', 0.4),
            'funding_rate_pattern_weight': self.env_loader.get_float_env_var('FUNDING_RATE_PATTERN_WEIGHT', 0.4),
            'liquidity_pattern_weight': self.env_loader.get_float_env_var('LIQUIDITY_PATTERN_WEIGHT', 0.4),
            'historical_candle_pattern_weight': self.env_loader.get_float_env_var('HISTORICAL_CANDLE_PATTERN_WEIGHT', 0.4),
            'tick_pattern_weight': self.env_loader.get_float_env_var('TICK_PATTERN_WEIGHT', 0.4),

            # Specific watcher momentum weights
            'market_pulse_momentum_weight': self.env_loader.get_float_env_var('MARKET_PULSE_MOMENTUM_WEIGHT', 0.3),
            'volatility_momentum_weight': self.env_loader.get_float_env_var('VOLATILITY_MOMENTUM_WEIGHT', 0.3),
            'trend_mtf_momentum_weight': self.env_loader.get_float_env_var('TREND_MTF_MOMENTUM_WEIGHT', 0.3),
            'anomaly_ml_momentum_weight': self.env_loader.get_float_env_var('ANOMALY_ML_MOMENTUM_WEIGHT', 0.3),
            'orderflow_ws_momentum_weight': self.env_loader.get_float_env_var('ORDERFLOW_WS_MOMENTUM_WEIGHT', 0.3),
            'cmc_screener_momentum_weight': self.env_loader.get_float_env_var('CMC_SCREENER_MOMENTUM_WEIGHT', 0.3),
            'funding_rate_momentum_weight': self.env_loader.get_float_env_var('FUNDING_RATE_MOMENTUM_WEIGHT', 0.3),
            'liquidity_momentum_weight': self.env_loader.get_float_env_var('LIQUIDITY_MOMENTUM_WEIGHT', 0.3),
            'historical_candle_momentum_weight': self.env_loader.get_float_env_var('HISTORICAL_CANDLE_MOMENTUM_WEIGHT', 0.3),
            'tick_momentum_weight': self.env_loader.get_float_env_var('TICK_MOMENTUM_WEIGHT', 0.3),

            # Specific watcher high volatility boosts
            'market_pulse_high_volatility_boost': self.env_loader.get_float_env_var('MARKET_PULSE_HIGH_VOLATILITY_BOOST', 0.2),
            'volatility_high_volatility_boost': self.env_loader.get_float_env_var('VOLATILITY_HIGH_VOLATILITY_BOOST', 0.2),
            'trend_mtf_high_volatility_boost': self.env_loader.get_float_env_var('TREND_MTF_HIGH_VOLATILITY_BOOST', 0.2),
            'anomaly_ml_high_volatility_boost': self.env_loader.get_float_env_var('ANOMALY_ML_HIGH_VOLATILITY_BOOST', 0.2),
            'orderflow_ws_high_volatility_boost': self.env_loader.get_float_env_var('ORDERFLOW_WS_HIGH_VOLATILITY_BOOST', 0.2),
            'cmc_screener_high_volatility_boost': self.env_loader.get_float_env_var('CMC_SCREENER_HIGH_VOLATILITY_BOOST', 0.2),
            'funding_rate_high_volatility_boost': self.env_loader.get_float_env_var('FUNDING_RATE_HIGH_VOLATILITY_BOOST', 0.2),
            'liquidity_high_volatility_boost': self.env_loader.get_float_env_var('LIQUIDITY_HIGH_VOLATILITY_BOOST', 0.2),
            'historical_candle_high_volatility_boost': self.env_loader.get_float_env_var('HISTORICAL_CANDLE_HIGH_VOLATILITY_BOOST', 0.2),
            'tick_high_volatility_boost': self.env_loader.get_float_env_var('TICK_HIGH_VOLATILITY_BOOST', 0.2),

            # Specific watcher low volatility boosts
            'market_pulse_low_volatility_boost': self.env_loader.get_float_env_var('MARKET_PULSE_LOW_VOLATILITY_BOOST', 0.05),
            'volatility_low_volatility_boost': self.env_loader.get_float_env_var('VOLATILITY_LOW_VOLATILITY_BOOST', 0.05),
            'trend_mtf_low_volatility_boost': self.env_loader.get_float_env_var('TREND_MTF_LOW_VOLATILITY_BOOST', 0.05),
            'anomaly_ml_low_volatility_boost': self.env_loader.get_float_env_var('ANOMALY_ML_LOW_VOLATILITY_BOOST', 0.05),
            'orderflow_ws_low_volatility_boost': self.env_loader.get_float_env_var('ORDERFLOW_WS_LOW_VOLATILITY_BOOST', 0.05),
            'cmc_screener_low_volatility_boost': self.env_loader.get_float_env_var('CMC_SCREENER_LOW_VOLATILITY_BOOST', 0.05),
            'funding_rate_low_volatility_boost': self.env_loader.get_float_env_var('FUNDING_RATE_LOW_VOLATILITY_BOOST', 0.05),
            'liquidity_low_volatility_boost': self.env_loader.get_float_env_var('LIQUIDITY_LOW_VOLATILITY_BOOST', 0.05),
            'historical_candle_low_volatility_boost': self.env_loader.get_float_env_var('HISTORICAL_CANDLE_LOW_VOLATILITY_BOOST', 0.05),
            'tick_low_volatility_boost': self.env_loader.get_float_env_var('TICK_LOW_VOLATILITY_BOOST', 0.05),

            # Specific watcher normal volatility boosts
            'market_pulse_normal_volatility_boost': self.env_loader.get_float_env_var('MARKET_PULSE_NORMAL_VOLATILITY_BOOST', 0.1),
            'volatility_normal_volatility_boost': self.env_loader.get_float_env_var('VOLATILITY_NORMAL_VOLATILITY_BOOST', 0.1),
            'trend_mtf_normal_volatility_boost': self.env_loader.get_float_env_var('TREND_MTF_NORMAL_VOLATILITY_BOOST', 0.1),
            'anomaly_ml_normal_volatility_boost': self.env_loader.get_float_env_var('ANOMALY_ML_NORMAL_VOLATILITY_BOOST', 0.1),
            'orderflow_ws_normal_volatility_boost': self.env_loader.get_float_env_var('ORDERFLOW_WS_NORMAL_VOLATILITY_BOOST', 0.1),
            'cmc_screener_normal_volatility_boost': self.env_loader.get_float_env_var('CMC_SCREENER_NORMAL_VOLATILITY_BOOST', 0.1),
            'funding_rate_normal_volatility_boost': self.env_loader.get_float_env_var('FUNDING_RATE_NORMAL_VOLATILITY_BOOST', 0.1),
            'liquidity_normal_volatility_boost': self.env_loader.get_float_env_var('LIQUIDITY_NORMAL_VOLATILITY_BOOST', 0.1),
            'historical_candle_normal_volatility_boost': self.env_loader.get_float_env_var('HISTORICAL_CANDLE_NORMAL_VOLATILITY_BOOST', 0.1),
            'tick_normal_volatility_boost': self.env_loader.get_float_env_var('TICK_NORMAL_VOLATILITY_BOOST', 0.1),

            # Specific watcher momentum lookback periods
            'market_pulse_momentum_lookback_period': self.env_loader.get_int_env_var('MARKET_PULSE_MOMENTUM_LOOKBACK_PERIOD', 10),
            'volatility_momentum_lookback_period': self.env_loader.get_int_env_var('VOLATILITY_MOMENTUM_LOOKBACK_PERIOD', 10),
            'trend_mtf_momentum_lookback_period': self.env_loader.get_int_env_var('TREND_MTF_MOMENTUM_LOOKBACK_PERIOD', 10),
            'anomaly_ml_momentum_lookback_period': self.env_loader.get_int_env_var('ANOMALY_ML_MOMENTUM_LOOKBACK_PERIOD', 10),
            'orderflow_ws_momentum_lookback_period': self.env_loader.get_int_env_var('ORDERFLOW_WS_MOMENTUM_LOOKBACK_PERIOD', 10),
            'cmc_screener_momentum_lookback_period': self.env_loader.get_int_env_var('CMC_SCREENER_MOMENTUM_LOOKBACK_PERIOD', 10),
            'funding_rate_momentum_lookback_period': self.env_loader.get_int_env_var('FUNDING_RATE_MOMENTUM_LOOKBACK_PERIOD', 10),
            'liquidity_momentum_lookback_period': self.env_loader.get_int_env_var('LIQUIDITY_MOMENTUM_LOOKBACK_PERIOD', 10),
            'historical_candle_momentum_lookback_period': self.env_loader.get_int_env_var('HISTORICAL_CANDLE_MOMENTUM_LOOKBACK_PERIOD', 10),
            'tick_momentum_lookback_period': self.env_loader.get_int_env_var('TICK_MOMENTUM_LOOKBACK_PERIOD', 10),

            # Specific watcher momentum sensitivity factors
            'market_pulse_momentum_sensitivity_factor': self.env_loader.get_float_env_var('MARKET_PULSE_MOMENTUM_SENSITIVITY_FACTOR', 10.0),
            'volatility_momentum_sensitivity_factor': self.env_loader.get_float_env_var('VOLATILITY_MOMENTUM_SENSITIVITY_FACTOR', 10.0),
            'trend_mtf_momentum_sensitivity_factor': self.env_loader.get_float_env_var('TREND_MTF_MOMENTUM_SENSITIVITY_FACTOR', 10.0),
            'anomaly_ml_momentum_sensitivity_factor': self.env_loader.get_float_env_var('ANOMALY_ML_MOMENTUM_SENSITIVITY_FACTOR', 10.0),
            'orderflow_ws_momentum_sensitivity_factor': self.env_loader.get_float_env_var('ORDERFLOW_WS_MOMENTUM_SENSITIVITY_FACTOR', 10.0),
            'cmc_screener_momentum_sensitivity_factor': self.env_loader.get_float_env_var('CMC_SCREENER_MOMENTUM_SENSITIVITY_FACTOR', 10.0),
            'funding_rate_momentum_sensitivity_factor': self.env_loader.get_float_env_var('FUNDING_RATE_MOMENTUM_SENSITIVITY_FACTOR', 10.0),
            'liquidity_momentum_sensitivity_factor': self.env_loader.get_float_env_var('LIQUIDITY_MOMENTUM_SENSITIVITY_FACTOR', 10.0),
            'historical_candle_momentum_sensitivity_factor': self.env_loader.get_float_env_var('HISTORICAL_CANDLE_MOMENTUM_SENSITIVITY_FACTOR', 10.0),
            'tick_momentum_sensitivity_factor': self.env_loader.get_float_env_var('TICK_MOMENTUM_SENSITIVITY_FACTOR', 10.0),

            # Trend MTF specific fields
            'trend_mtf_short_period': self.env_loader.get_int_env_var('TREND_MTF_SHORT_PERIOD', 5),
            'trend_mtf_medium_period': self.env_loader.get_int_env_var('TREND_MTF_MEDIUM_PERIOD', 15),
            'trend_mtf_long_period': self.env_loader.get_int_env_var('TREND_MTF_LONG_PERIOD', 30),

            # Anomaly ML specific fields
            'anomaly_ml_contamination': self.env_loader.get_float_env_var('ANOMALY_ML_CONTAMINATION', 0.1),
        }
        return watcher_data

    def _extract_portfolio_config_data(self) -> Dict[str, Any]:
        """Extract portfolio configuration data from environment variables."""
        portfolio_data = {
            'rebalance_frequency': self.env_loader.get_env_var('REBALANCE_FREQUENCY', 'daily'),
            'correlation_consensus_weight': self.env_loader.get_float_env_var('CORRELATION_CONSENSUS_WEIGHT', 0.5),
            'correlation_confidence_weight': self.env_loader.get_float_env_var('CORRELATION_CONFIDENCE_WEIGHT', 0.3),
            'correlation_base_percentage': self.env_loader.get_float_env_var('CORRELATION_BASE_PERCENTAGE', 0.5),
            'correlation_default_percentage': self.env_loader.get_float_env_var('CORRELATION_DEFAULT_PERCENTAGE', 0.5),
            'correlation_diversification_factor': self.env_loader.get_float_env_var('CORRELATION_DIVERSIFICATION_FACTOR', 0.7),
            'correlation_max_correlation': self.env_loader.get_float_env_var('CORRELATION_MAX_CORRELATION', 0.7),
            'correlation_portfolio_impact_threshold': self.env_loader.get_float_env_var('CORRELATION_PORTFOLIO_IMPACT_THRESHOLD', 0.3),
        }
        return portfolio_data

    def _extract_backtest_config_data(self) -> Dict[str, Any]:
        """Extract backtest configuration data from environment variables."""
        backtest_data = {
            'initial_capital': self.env_loader.get_float_env_var('BACKTEST_INITIAL_CAPITAL', 10000.0),
            'fee_rate': self.env_loader.get_float_env_var('BACKTEST_FEE_RATE', 0.001),
            'slippage_factor': self.env_loader.get_float_env_var('BACKTEST_SLIPPAGE_FACTOR', 0.0005),
            'risk_per_trade': self.env_loader.get_float_env_var('BACKTEST_RISK_PER_TRADE', 0.02),
            'end_date': self.env_loader.get_env_var('BACKTEST_END_DATE', '2026-01-18'),
            'start_date': self.env_loader.get_env_var('BACKTEST_START_DATE', '2025-01-01'),
            'benchmark_symbol': self.env_loader.get_env_var('BENCHMARK_SYMBOL', 'BTCUSDT'),
            'commission_rate': self.env_loader.get_float_env_var('COMMISSION_RATE', 0.001),
        }
        return backtest_data

    def _extract_fusion_config_data(self) -> Dict[str, Any]:
        """Extract fusion configuration data from environment variables."""
        fusion_data = {
            'method': self.env_loader.get_env_var('FUSION_METHOD', 'weighted_average'),
            'weight_decay_rate': self.env_loader.get_float_env_var('FUSION_WEIGHT_DECAY_RATE', 0.05),
            'min_correlation_score': self.env_loader.get_float_env_var('FUSION_MIN_CORRELATION_SCORE', 0.1),
            'max_signals_per_asset': self.env_loader.get_int_env_var('FUSION_MAX_SIGNALS_PER_ASSET', 5),
        }
        return fusion_data
