"""
Configuration Migration Helper Script

This script helps migrate remaining os.getenv calls to use the Configs system.
It creates a mapping of environment variables to their corresponding Configs fields.
"""
import os
import re
from typing import Dict, List, Tuple


def create_env_to_config_mapping() -> Dict[str, str]:
    """
    Create a mapping of environment variable names to their corresponding Configs fields.
    This mapping is based on the comprehensive analysis done previously.
    """
    return {
        # Broker configuration
        'BROKER_API_KEY': 'Configs.broker.api_key',
        'BROKER_SECRET_KEY': 'Configs.broker.secret_key',
        'BROKER_TESTNET': 'Configs.broker.testnet',
        'BROKER_NAME': 'Configs.broker.broker_name',
        'BROKER_PAPER_TRADING': 'Configs.broker.paper_trading',
        'BINGX_API_KEY': 'Configs.broker.bingx_api_key',
        'BINGX_SECRET_KEY': 'Configs.broker.bingx_secret_key',
        'BINGX_ORDER_PLACEMENT_ENABLED': 'Configs.broker.bingx_order_placement_enabled',
        'BINGX_TESTNET': 'Configs.broker.bingx_testnet',
        'DEFAULT_BROKER': 'Configs.broker.default_broker',
        'BINANCE_API_KEY': 'Configs.broker.binance_api_key',
        'BINANCE_SECRET_KEY': 'Configs.broker.binance_secret_key',
        'BINANCE_ORDER_PLACEMENT_ENABLED': 'Configs.broker.binance_order_placement_enabled',
        'BINANCE_TESTNET': 'Configs.broker.binance_testnet',
        'MEXC_API_KEY': 'Configs.broker.mexc_api_key',
        'MEXC_SECRET_KEY': 'Configs.broker.mexc_secret_key',
        'MEXC_ORDER_PLACEMENT_ENABLED': 'Configs.broker.mexc_order_placement_enabled',
        'MEXC_TESTNET': 'Configs.broker.mexc_testnet',
        'PHEMEX_API_KEY': 'Configs.broker.phemex_api_key',
        'PHEMEX_SECRET_KEY': 'Configs.broker.phemex_secret_key',
        'PHEMEX_ORDER_PLACEMENT_ENABLED': 'Configs.broker.phemex_order_placement_enabled',
        'PHEMEX_TESTNET': 'Configs.broker.phemex_testnet',
        'BINANCE_API_URL': 'Configs.broker.binance_api_url',
        'BINANCE_RETRY_ATTEMPTS': 'Configs.broker.binance_retry_attempts',
        'BINANCE_RATE_LIMIT_DELAY': 'Configs.broker.binance_rate_limit_delay',
        'BINGX_PASSPHRASE': 'Configs.broker.bingx_passphrase',
        'ENABLED_BROKERS': 'Configs.broker.enabled_brokers',

        # Risk configuration
        'RISK_MAX_POSITION_SIZE': 'Configs.risk.max_position_size',
        'RISK_MAX_TOTAL_EXPOSURE': 'Configs.risk.max_total_exposure',
        'RISK_MAX_DRAWDOWN': 'Configs.risk.max_drawdown',
        'RISK_MAX_LEVERAGE': 'Configs.risk.max_leverage',
        'RISK_CAPITAL_PER_SYMBOL': 'Configs.risk.capital_per_symbol',
        'RISK_MAX_EXPOSURE': 'Configs.risk.max_exposure',
        'RISK_PER_TRADE': 'Configs.risk.per_trade',
        'RISK_MAX_DAILY_LOSS': 'Configs.risk.max_daily_loss',
        'RISK_MAX_TOTAL_POSITIONS': 'Configs.risk.max_total_positions',
        'RISK_MAX_CORRELATION_BETWEEN_POS': 'Configs.risk.max_correlation_between_pos',
        'RISK_MAX_SECTOR_EXPOSURE': 'Configs.risk.max_sector_exposure',
        'RISK_MAX_SINGLE_ASSET_EXPOSURE': 'Configs.risk.max_single_asset_exposure',
        'RISK_EMERGENCY_STOP_DRAWDOWN': 'Configs.risk.emergency_stop_drawdown',
        'MIN_ORDER_SIZE': 'Configs.risk.min_order_size',
        'MAX_ORDER_SIZE': 'Configs.risk.max_order_size',
        'MIN_POSITION_SIZE': 'Configs.risk.min_position_size',
        'MAX_POSITION_CONCENTRATION': 'Configs.risk.max_position_concentration',
        'MAX_PORTFOLIO_RISK': 'Configs.risk.max_portfolio_risk',
        'MAX_POSITION_RISK': 'Configs.risk.max_position_risk',
        'MAX_DRAWDOWN_THRESHOLD': 'Configs.risk.max_drawdown_threshold',
        'MAX_DAILY_LOSS': 'Configs.risk.max_daily_loss',
        'MAX_TOTAL_POSITIONS': 'Configs.risk.max_total_positions',
        'MAX_CORRELATION': 'Configs.risk.max_correlation',
        'MAX_LEVERAGE': 'Configs.risk.max_leverage',
        'MAX_ORDER_SIZE': 'Configs.risk.max_order_size',
        'MAX_PORTFOLIO_RISK': 'Configs.risk.max_portfolio_risk',
        'MAX_POSITION_RISK': 'Configs.risk.max_position_risk',
        'MAX_DRAWDOWN': 'Configs.risk.max_drawdown',
        'MAX_DRAWDOWN_THRESHOLD': 'Configs.risk.max_drawdown_threshold',
        'MINIMUM_WIN_RATE_THRESHOLD': 'Configs.risk.minimum_win_rate_threshold',
        'MAXIMUM_WIN_RATE_THRESHOLD': 'Configs.risk.maximum_win_rate_threshold',
        'MAX_TREND_IMPACT_ON_EDGE': 'Configs.risk.max_trend_impact_on_edge',
        'MAX_TREND_IMPACT_ON_WIN_RATE': 'Configs.risk.max_trend_impact_on_win_rate',
        'MAX_VOLATILITY_IMPACT_ON_EDGE': 'Configs.risk.max_volatility_impact_on_edge',
        'MAX_CORRELATION': 'Configs.risk.max_correlation',
        'MAX_DAILY_LOSS': 'Configs.risk.max_daily_loss',
        'MAX_DRAWDOWN': 'Configs.risk.max_drawdown',
        'MAX_DRAWDOWN_THRESHOLD': 'Configs.risk.max_drawdown_threshold',
        'MAX_LEVERAGE': 'Configs.risk.max_leverage',
        'MAX_ORDER_SIZE': 'Configs.risk.max_order_size',
        'MAX_POSITION_CONCENTRATION': 'Configs.risk.max_position_concentration',
        'MAX_PORTFOLIO_RISK': 'Configs.risk.max_portfolio_risk',
        'MAX_POSITION_RISK': 'Configs.risk.max_position_risk',

        # Strategy configuration
        'DEFAULT_STRATEGY': 'Configs.strategy.default_strategy',
        'STRATEGY_RISK_PER_TRADE': 'Configs.strategy.risk_per_trade',
        'STRATEGY_MAX_POSITION_SIZE': 'Configs.strategy.max_position_size',
        'STRATEGY_MIN_VOLUME_FILTER': 'Configs.strategy.min_volume_filter',
        'STRATEGY_SIGNAL_COOLDOWN_MINUTES': 'Configs.strategy.signal_cooldown_minutes',
        'STRATEGY_MIN_CONFIDENCE_THRESHOLD': 'Configs.strategy.min_confidence_threshold',
        'STRATEGY_HIGH_CONFIDENCE_THRESHOLD': 'Configs.strategy.high_confidence_threshold',
        'STRATEGY_NEUTRAL_BUFFER': 'Configs.strategy.neutral_buffer',
        'STRATEGY_STRONG_DIRECTIONAL_BIAS_THRESHOLD': 'Configs.strategy.strong_directional_bias_threshold',
        'ANOMALY_ML_CONTAMINATION': 'Configs.strategy.anomaly_ml_contamination',
        'ATR_DEFAULT_PERCENTAGE': 'Configs.strategy.atr_default_percentage',
        'ATR_FIXED_DOLLAR_RISK': 'Configs.strategy.atr_fixed_dollar_risk',
        'ATR_MAX_PORTFOLIO_PERCENT': 'Configs.strategy.atr_max_portfolio_percent',
        'ATR_MIN_MULTIPLE': 'Configs.strategy.atr_min_multiple',
        'ATR_MULTIPLIER': 'Configs.strategy.atr_multiplier',
        'ATR_TO_VOLATILITY_MULTIPLIER': 'Configs.strategy.atr_to_volatility_multiplier',
        'BASE_REWARD_RISK_RATIO': 'Configs.strategy.base_reward_risk_ratio',
        'CONFIDENCE_RR_MULTIPLIER': 'Configs.strategy.confidence_rr_multiplier',
        'DEFAULT_ANNUAL_VOLATILITY': 'Configs.strategy.default_annual_volatility',
        'DEFAULT_ASSET_VOLATILITY': 'Configs.strategy.default_asset_volatility',
        'EDGE_ESTIMATION_FACTOR': 'Configs.strategy.edge_estimation_factor',
        'ENGINE_CONFIDENCE_THRESHOLD': 'Configs.strategy.engine_confidence_threshold',
        'ENABLED_ENGINES': 'Configs.strategy.enabled_engines',
        'HIGH_VOLATILITY_THRESHOLD': 'Configs.strategy.high_volatility_threshold',
        'HIGH_VOLATILITY_WIN_RATE_IMPACT': 'Configs.strategy.high_volatility_win_rate_impact',
        'LOW_VOLATILITY_THRESHOLD': 'Configs.strategy.low_volatility_threshold',
        'LOW_VOLATILITY_WIN_RATE_IMPACT': 'Configs.strategy.low_volatility_win_rate_impact',
        'MAXIMUM_WIN_RATE_THRESHOLD': 'Configs.strategy.maximum_win_rate_threshold',
        'MAX_REWARD_RISK_RATIO': 'Configs.strategy.max_reward_risk_ratio',
        'MAX_TREND_IMPACT_ON_EDGE': 'Configs.strategy.max_trend_impact_on_edge',
        'MAX_TREND_IMPACT_ON_WIN_RATE': 'Configs.strategy.max_trend_impact_on_win_rate',
        'MAX_VOLATILITY_IMPACT_ON_EDGE': 'Configs.strategy.max_volatility_impact_on_edge',
        'MIN_CONFIDENCE_RR_FACTOR': 'Configs.strategy.min_confidence_rr_factor',
        'MIN_REWARD_RISK_RATIO': 'Configs.strategy.min_reward_risk_ratio',
        'ML_WEIGHTS_ENABLED': 'Configs.strategy.ml_weights_enabled',
        'REGIME_DETECTION_ENABLED': 'Configs.strategy.regime_detection_enabled',
        'SIGNAL_FUSION_ENABLED': 'Configs.strategy.signal_fusion_enabled',
        'SIGNAL_THRESHOLD': 'Configs.strategy.signal_threshold',
        'TARGET_VOLATILITY': 'Configs.strategy.target_volatility',
        'TREND_IMPACT_ON_WIN_RATE_MULTIPLIER': 'Configs.strategy.trend_impact_on_win_rate_multiplier',
        'TREND_MAX_RR_IMPACT': 'Configs.strategy.trend_max_rr_impact',
        'TREND_MTF_LONG_PERIOD': 'Configs.strategy.trend_mtf_long_period',
        'TREND_MTF_MEDIUM_PERIOD': 'Configs.strategy.trend_mtf_medium_period',
        'TREND_MTF_SHORT_PERIOD': 'Configs.strategy.trend_mtf_short_period',
        'TREND_RR_MULTIPLIER': 'Configs.strategy.trend_rr_multiplier',
        'MINIMUM_WIN_RATE_THRESHOLD': 'Configs.strategy.minimum_win_rate_threshold',
        'OPPORTUNITY_SCORE_CONFIDENCE_WEIGHT': 'Configs.strategy.opportunity_score_confidence_weight',
        'OPPORTUNITY_SCORE_DOMINANCE_WEIGHT': 'Configs.strategy.opportunity_score_dominance_weight',
        'OPPORTUNITY_SCORE_POSITION_SIZE_WEIGHT': 'Configs.strategy.opportunity_score_position_size_weight',
        'OPPORTUNITY_SCORE_REWARD_RISK_WEIGHT': 'Configs.strategy.opportunity_score_reward_risk_weight',
        'OPPORTUNITY_SCORE_REGIME_BONUS': 'Configs.strategy.opportunity_score_regime_bonus',
        'ENABLE_SHORTING': 'Configs.strategy.enable_shorting',

        # Execution configuration
        'EXECUTION_ORDER_TYPE': 'Configs.execution.order_type',
        'EXECUTION_LIMIT_SLIPPAGE': 'Configs.execution.limit_slippage',
        'EXECUTION_PRICE_BAND_WIDTH': 'Configs.execution.price_band_width',
        'EXECUTION_MAX_PARTIAL_FILL_PERCENT': 'Configs.execution.max_partial_fill_percent',
        'PREVENT_SAME_DIRECTION_TRADE_PER_SYMBOL': 'Configs.execution.prevent_same_direction_trade_per_symbol',
        'SLIPPAGE_FACTOR': 'Configs.execution.slippage_factor',
        'SLIPPAGE_RATE': 'Configs.execution.slippage_rate',
        'SLIPPAGE_TOLERANCE': 'Configs.execution.slippage_tolerance',
        'ORDER_TIMEOUT': 'Configs.execution.order_timeout',
        'RETRY_ATTEMPTS': 'Configs.execution.retry_attempts',
        'MIN_ORDER_QUANTITY': 'Configs.execution.min_order_quantity',
        'COMMISSION_RATE': 'Configs.execution.commission_rate',
        'FEE_RATE': 'Configs.execution.fee_rate',
        'ENABLE_TWAP': 'Configs.execution.enable_twap',
        'ENABLE_VWAP': 'Configs.execution.enable_vwap',
        'SMART_ORDER_ROUTING': 'Configs.execution.smart_order_routing',

        # Safety configuration
        'SAFETY_KILL_SWITCH_ENABLED': 'Configs.safety.kill_switch_enabled',
        'SAFETY_EMERGENCY_STOP_ENABLED': 'Configs.safety.emergency_stop_enabled',
        'SAFETY_MAX_ORDER_SIZE_USD': 'Configs.safety.max_order_size_usd',
        'SAFETY_MAX_DAILY_ORDERS': 'Configs.safety.max_daily_orders',
        'SAFETY_API_RATE_LIMIT_BUFFER': 'Configs.safety.api_rate_limit_buffer',
        'ENABLE_KILL_SWITCH': 'Configs.safety.enable_kill_switch',

        # Data configuration
        'DATA_PATH': 'Configs.data.path',
        'RESULTS_DIR': 'Configs.data.results_dir',
        'CACHE_DIR': 'Configs.data.cache_dir',
        'COIN_HISTORY_CACHE_DIR': 'Configs.data.coin_history_cache_dir',
        'MAX_CACHE_AGE_HOURS': 'Configs.data.max_cache_age_hours',
        'MAX_COIN_CACHE_SIZE': 'Configs.data.max_coin_cache_size',
        'DEFAULT_DATA_PROVIDER': 'Configs.data.default_provider',
        'DEFAULT_TIMEFRAME': 'Configs.data.default_timeframe',
        'SUPPORTED_TIMEFRAMES': 'Configs.data.supported_timeframes',
        'WFO_COINS': 'Configs.wfo.wfo_coins',
        'CSV_DATA_PATH': 'Configs.data.csv_data_path',
        'CMC_API_KEY': 'Configs.data.cmc_api_key',
        'CMC_LISTINGS_URL': 'Configs.data.cmc_listings_url',
        'CMC_QUOTES_URL': 'Configs.data.cmc_quotes_url',
        'CMC_EXCLUDED_COINS': 'Configs.data.cmc_excluded_coins',
        'CMC_MAX_CALLS_PER_MINUTE': 'Configs.data.cmc_max_calls_per_minute',
        'CMC_MAX_CALLS_PER_HOUR': 'Configs.data.cmc_max_calls_per_hour',
        'CMC_API_CALL_INTERVAL': 'Configs.data.cmc_api_call_interval',
        'CMC_CACHE_TTL_SECONDS': 'Configs.data.cmc_cache_ttl_seconds',
        'CMC_LISTINGS_CACHE_TTL_SECONDS': 'Configs.data.cmc_listings_cache_ttl_seconds',
        'CMC_QUOTE_CACHE_TTL_SECONDS': 'Configs.data.cmc_quote_cache_ttl_seconds',
        'CMC_SCREEN_TOP_COINS_INTERVAL_HOURS': 'Configs.data.cmc_screen_top_coins_interval_hours',
        'CMC_SCREEN_TOP_COINS_LIMIT': 'Configs.data.cmc_screen_top_coins_limit',
        'CMC_MAX_COINS_TO_ANALYZE_PER_RUN': 'Configs.data.cmc_max_coins_to_analyze_per_run',
        'CMC_CIRCUIT_BREAKER_FAILURE_THRESHOLD': 'Configs.data.cmc_circuit_breaker_failure_threshold',
        'CMC_CIRCUIT_BREAKER_RESET_TIMEOUT': 'Configs.data.cmc_circuit_breaker_reset_timeout',
        'CMC_MIN_CONFIDENCE_THRESHOLD': 'Configs.data.cmc_min_confidence_threshold',
        'CMC_VOL_CONFIDENCE_WEIGHT': 'Configs.data.cmc_vol_confidence_weight',
        'CMC_VOLUME_CONFIDENCE_WEIGHT': 'Configs.data.cmc_volume_confidence_weight',
        'CMC_CHANGE_CONFIDENCE_WEIGHT': 'Configs.data.cmc_change_confidence_weight',
        'SYNC_INTERVAL_SECONDS': 'Configs.data.sync_interval_seconds',
        'ASYNC_CONCURRENCY': 'Configs.data.async_concurrency',
        'DOWNLOAD_THREADPOOL_WORKERS': 'Configs.data.download_threadpool_workers',
        'RETRY_MAX_ATTEMPTS': 'Configs.data.retry_max_attempts',
        'RETRY_BACKOFF_BASE': 'Configs.data.retry_backoff_base',
        'RETRY_BACKOFF_FACTOR': 'Configs.data.retry_backoff_factor',
        'RATE_LIMIT_TOKENS_PER_SECOND': 'Configs.data.rate_limit_tokens_per_second',
        'TEMP_FILE_SUFFIX': 'Configs.data.temp_file_suffix',
        'DATA_DIR': 'Configs.data.dir',
        'RAW_RETENTION_DAYS': 'Configs.data.raw_retention_days',
        'PROCESSED_RETENTION_DAYS': 'Configs.data.processed_retention_days',
        'MAX_GAP_FILL_MINUTES': 'Configs.data.max_gap_fill_minutes',
        'SYNC_DEFAULT_EXCHANGE': 'Configs.data.sync_default_exchange',
        'SYNC_MAX_WINDOW_MINUTES': 'Configs.data.sync_max_window_minutes',
        'SYNC_RATE_LIMIT': 'Configs.data.sync_rate_limit',
        'FILTER_OUT_STABLECOIN_PAIRS': 'Configs.data.filter_out_stablecoin_pairs',
        'ALLOWED_STABLECOINS': 'Configs.data.allowed_stablecoins',
        'EXCLUDED_SYMBOLS_PATTERN': 'Configs.data.excluded_symbols_pattern',
        'CSV_DATA_PATH': 'Configs.data.csv_data_path',
        'DEFAULT_WATCHLIST_SYMBOLS': 'Configs.data.default_watchlist_symbols',
        'FAILED_SYMBOLS_CACHE_DURATION': 'Configs.data.failed_symbols_cache_duration',
        'FALLBACK_WATCHLIST_SYMBOLS': 'Configs.data.fallback_watchlist_symbols',
        'HISTORICAL_DATA_FALLBACK_SOURCES': 'Configs.data.historical_data_fallback_sources',
        'PREFERRED_HISTORICAL_DATA_SOURCE': 'Configs.data.preferred_historical_data_source',
        'VALIDATE_SYMBOL_DATA_AVAILABILITY': 'Configs.data.validate_symbol_data_availability',
        'CMC_CATEGORIES_URL': 'Configs.data.cmc_categories_url',
        'CMC_UPDATE_INTERVAL': 'Configs.data.cmc_update_interval',
        'CMC_VOLATILITY_HIGH_THRESHOLD': 'Configs.data.cmc_volatility_high_threshold',
        'CMC_VOLATILITY_LOW_THRESHOLD': 'Configs.data.cmc_volatility_low_threshold',
        'CMC_VOLUME_HIGH_THRESHOLD': 'Configs.data.cmc_volume_high_threshold',
        'CMC_VOLUME_LOW_THRESHOLD': 'Configs.data.cmc_volume_low_threshold',

        # Watcher configuration
        'MARKET_PULSE_WATCHER_ENABLED': 'Configs.watcher.market_pulse_watcher_enabled',
        'VOLATILITY_WATCHER_ENABLED': 'Configs.watcher.volatility_watcher_enabled',
        'TREND_MTF_WATCHER_ENABLED': 'Configs.watcher.trend_mtf_watcher_enabled',
        'ANOMALY_ML_WATCHER_ENABLED': 'Configs.watcher.anomaly_ml_watcher_enabled',
        'ORDERFLOW_WS_WATCHER_ENABLED': 'Configs.watcher.orderflow_ws_watcher_enabled',
        'CMC_SCREENER_ENABLED': 'Configs.watcher.cmc_screener_enabled',
        'FUNDING_RATE_WATCHER_ENABLED': 'Configs.watcher.funding_rate_watcher_enabled',
        'LIQUIDITY_WATCHER_ENABLED': 'Configs.watcher.liquidity_watcher_enabled',
        'HISTORICAL_CANDLE_WATCHER_ENABLED': 'Configs.watcher.historical_candle_watcher_enabled',
        'TICK_WATCHER_ENABLED': 'Configs.watcher.tick_watcher_enabled',
        'WATCHER_POLLING_INTERVAL_SECONDS': 'Configs.watcher.polling_interval_seconds',
        'WATCHER_MAX_SYMBOLS_TO_MONITOR': 'Configs.watcher.max_symbols_to_monitor',
        'WATCHER_DATA_REFRESH_INTERVAL_MINUTES': 'Configs.watcher.data_refresh_interval_minutes',
        'WATCHER_RISK_THRESHOLD': 'Configs.watcher.risk_threshold',
        'WATCHER_MIN_CONFIDENCE_THRESHOLD': 'Configs.watcher.min_confidence_threshold',
        'WATCHER_MAX_CONFIDENCE_WITH_PATTERNS': 'Configs.watcher.max_confidence_with_patterns',
        'WATCHER_MIN_PRICE_CHANGE_THRESHOLD': 'Configs.watcher.min_price_change_threshold',
        'WATCHER_MAX_CONFIDENCE_WITH_MOVEMENT': 'Configs.watcher.max_confidence_with_movement',
        'WATCHER_NEUTRAL_CONFIDENCE': 'Configs.watcher.neutral_confidence',
        'WATCHER_PATTERN_WEIGHT': 'Configs.watcher.pattern_weight',
        'WATCHER_MOMENTUM_WEIGHT': 'Configs.watcher.momentum_weight',
        'WATCHER_HIGH_VOLATILITY_BOOST': 'Configs.watcher.high_volatility_boost',
        'WATCHER_LOW_VOLATILITY_BOOST': 'Configs.watcher.low_volatility_boost',
        'WATCHER_NORMAL_VOLATILITY_BOOST': 'Configs.watcher.normal_volatility_boost',
        'WATCHER_MIN_CONFIDENCE_WHEN_SIGNALS_DETECTED': 'Configs.watcher.min_confidence_when_signals_detected',
        'WATCHER_MAX_CONFIDENCE_CAP': 'Configs.watcher.max_confidence_cap',
        'WATCHER_MOMENTUM_LOOKBACK_PERIOD': 'Configs.watcher.momentum_lookback_period',
        'WATCHER_MOMENTUM_SENSITIVITY_FACTOR': 'Configs.watcher.momentum_sensitivity_factor',
        'WATCHER_BROKER_CONFIG': 'Configs.watcher.broker_config',
        'TARGET_BROKER_MARKET_PULSE': 'Configs.watcher.target_broker_market_pulse',
        'TARGET_BROKER_VOLATILITY': 'Configs.watcher.target_broker_volatility',
        'TARGET_BROKER_TREND_MTF': 'Configs.watcher.target_broker_trend_mtf',
        'TARGET_BROKER_ANOMALY_ML': 'Configs.watcher.target_broker_anomaly_ml',
        'TARGET_BROKER_ORDERFLOW_WS': 'Configs.watcher.target_broker_orderflow_ws',
        'TARGET_BROKER_FUNDING_RATE': 'Configs.watcher.target_broker_funding_rate',
        'TARGET_BROKER_LIQUIDITY': 'Configs.watcher.target_broker_liquidity',
        'TARGET_BROKER_HISTORICAL_CANDLE': 'Configs.watcher.target_broker_historical_candle',
        'TARGET_BROKER_TICK_WATCHER': 'Configs.watcher.target_broker_tick_watcher',
        'USE_IMPROVED_WATCHERS': 'Configs.watcher.use_improved_watchers',
        'AUTO_ENABLE_WATCHERS': 'Configs.watcher.auto_enable_watchers',
        'ENABLED_WATCHERS': 'Configs.watcher.enabled_watchers',
        'WATCHER_UPDATE_FREQ': 'Configs.watcher.update_freq',
        'WATCHER_LOOKBACK': 'Configs.watcher.lookback',
        'EARLY_EXIT_MOMENTUM_THRESHOLD': 'Configs.watcher.early_exit_momentum_threshold',
        'EARLY_EXIT_TREND_CONFIDENCE_THRESHOLD': 'Configs.watcher.early_exit_trend_confidence_threshold',
        'EARLY_EXIT_VOLATILITY_THRESHOLD': 'Configs.watcher.early_exit_volatility_threshold',

        # Optimization configuration
        'HYPEROPT_ALGORITHM': 'Configs.optimization.algorithm',
        'HYPEROPT_MAX_EVALS': 'Configs.optimization.max_evals',
        'HYPEROPT_EARLY_STOPPING_ROUNDS': 'Configs.optimization.early_stopping_rounds',
        'HYPEROPT_VALIDATION_SPLIT': 'Configs.optimization.validation_split',
        'HYPEROPT_OBJECTIVE_METRIC': 'Configs.optimization.objective_metric',
        'OPTIMIZATION_MIN_RETURNS': 'Configs.optimization.min_returns',
        'OPTIMIZATION_MIN_SHARPE_RATIO': 'Configs.optimization.min_sharpe_ratio',
        'OPTIMIZATION_MAX_DRAWDOWN': 'Configs.optimization.max_drawdown',
        'OPTIMIZATION_MIN_WIN_RATE': 'Configs.optimization.min_win_rate',
        'RETUNE_ENABLED': 'Configs.optimization.retune_enabled',
        'RETUNE_INTERVAL_HOURS': 'Configs.optimization.retune_interval_hours',
        'RETUNE_PERFORMANCE_THRESHOLD': 'Configs.optimization.retune_performance_threshold',
        'RETUNE_EVALS_PER_RETUNE': 'Configs.optimization.retune_evals_per_retune',
        'RETUNE_RETENTION_PERIOD_DAYS': 'Configs.optimization.retune_retention_period_days',

        # WFO configuration
        'WFO_TRAIN_SIZE': 'Configs.wfo.train_size',
        'WFO_TEST_SIZE': 'Configs.wfo.test_size',
        'WFO_STEP_SIZE': 'Configs.wfo.step_size',
        'WFO_MAX_EVALS': 'Configs.wfo.max_evals',
        'WFO_PERFORMANCE_THRESHOLD': 'Configs.wfo.performance_threshold',
        'WFO_MAX_DRAWDOWN_THRESHOLD': 'Configs.wfo.max_drawdown_threshold',
        'WFO_RETRAIN_FREQUENCY_DAYS': 'Configs.wfo.retrain_frequency_days',
        'WFO_MIN_TRAINING_POINTS': 'Configs.wfo.min_training_points',
        'WFO_MIN_TESTING_POINTS': 'Configs.wfo.min_testing_points',
        'WFO_OVERFIT_THRESHOLD': 'Configs.wfo.overfit_threshold',
        'WFO_CONSISTENCY_THRESHOLD': 'Configs.wfo.consistency_threshold',
        'WFO_PASS_RATE_THRESHOLD': 'Configs.wfo.pass_rate_threshold',
        'WFO_ENABLED': 'Configs.wfo.wfo_enabled',
        'WFO_COINS': 'Configs.wfo.wfo_coins',
        'WFO_DATA_DIR': 'Configs.wfo.data_dir',
        'WFO_RAW_DIR': 'Configs.wfo.raw_dir',
        'WFO_PROCESSED_DIR': 'Configs.wfo.processed_dir',
        'WFO_SYNC_DAYS': 'Configs.wfo.sync_days',
        'WFO_INCREMENTAL_DAYS': 'Configs.wfo.incremental_days',
        'WFO_REFRESH_INTERVAL_HOURS': 'Configs.wfo.refresh_interval_hours',
        'WFO_DEFAULT_TIMEFRAMES': 'Configs.wfo.default_timeframes',

        # Monitoring configuration
        'TELEGRAM_BOT_NAME': 'Configs.monitoring.telegram_bot_name',
        'TELEGRAM_BOT_URL': 'Configs.monitoring.telegram_bot_url',
        'TELEGRAM_BOT_UPDATE_URL': 'Configs.monitoring.telegram_bot_update_url',
        'TELEGRAM_BOT_TOKEN': 'Configs.monitoring.telegram_bot_token',
        'TELEGRAM_CHAT_ID': 'Configs.monitoring.telegram_chat_id',
        'TELEGRAM_NOTIFICATIONS_ENABLED': 'Configs.monitoring.telegram_notifications_enabled',
        'LOG_LEVEL': 'Configs.monitoring.logging_level',
        'LOG_FILE_PATH': 'Configs.monitoring.log_file_path',
        'LOG_MAX_FILE_SIZE_MB': 'Configs.monitoring.log_max_file_size_mb',
        'LOG_BACKUP_COUNT': 'Configs.monitoring.log_backup_count',
        'MONITORING_ENABLED': 'Configs.monitoring.enabled',
        'METRICS_REPORTING_INTERVAL_MINUTES': 'Configs.monitoring.metrics_reporting_interval_minutes',
        'FORENSIC_LOGGING_ENABLED': 'Configs.monitoring.forensic_logging_enabled',
        'ENABLE_METRICS': 'Configs.monitoring.enable_metrics',

        # Infrastructure configuration
        'PERFORMANCE_USE_MULTIPROCESSING': 'Configs.infrastructure.use_multiprocessing',
        'PERFORMANCE_NUM_WORKERS': 'Configs.infrastructure.num_workers',
        'PERFORMANCE_BATCH_SIZE': 'Configs.infrastructure.batch_size',
        'PERFORMANCE_MEMORY_PROFILING': 'Configs.infrastructure.memory_profiling',
        'API_TIMEOUT': 'Configs.infrastructure.api_timeout',
        'MAX_WORKERS': 'Configs.infrastructure.max_workers',
        'REDIS_URL': 'Configs.infrastructure.redis_url',
        'DEBUG': 'Configs.infrastructure.debug',
        'ENVIRONMENT': 'Configs.infrastructure.environment',
        'USE_MOCK_DATA': 'Configs.infrastructure.use_mock_data',

        # Position Sizing configuration
        'FIXED_POSITION_SIZE_ENABLED': 'Configs.position_sizing.fixed_position_size_enabled',
        'FIXED_POSITION_AMOUNT': 'Configs.position_sizing.fixed_position_amount',
        'DEFAULT_ACCOUNT_BALANCE': 'Configs.position_sizing.default_account_balance',
        'FIXED_FRACTIONAL_DEFAULT_PERCENTAGE': 'Configs.position_sizing.fixed_fractional_default_percentage',
        'FIXED_FRACTIONAL_PERCENTAGE': 'Configs.position_sizing.fixed_fractional_percentage',
        'FIXED_FRACTIONAL_RISK_PER_UNIT': 'Configs.position_sizing.fixed_fractional_risk_per_unit',
        'KELLY_DEFAULT_PERCENTAGE': 'Configs.position_sizing.kelly_default_percentage',
        'KELLY_FRACTION': 'Configs.position_sizing.kelly_fraction',
        'KELLY_MAX_POSITION_SIZE': 'Configs.position_sizing.kelly_max_position_size',
        'KELLY_MINIMUM_EDGE': 'Configs.position_sizing.kelly_minimum_edge',
        'KELLY_VAR_CONFIDENCE_LEVEL': 'Configs.position_sizing.kelly_var_confidence_level',
        'KELLY_VAR_MARGIN_OF_SAFETY_PERCENTAGE': 'Configs.position_sizing.kelly_var_margin_of_safety_percentage',
        'KELLY_VAR_MAX_POSITION_WITH_VAR': 'Configs.position_sizing.kelly_var_max_position_with_var',
        'KELLY_VAR_STRESS_TEST_MULTIPLIER': 'Configs.position_sizing.kelly_var_stress_test_multiplier',
        'MARTINGALE_BASE_RISK_PERCENTAGE': 'Configs.position_sizing.martingale_base_risk_percentage',
        'MARTINGALE_MAX_PROGRESSION_LEVELS': 'Configs.position_sizing.martingale_max_progression_levels',
        'MARTINGALE_MAX_TOTAL_EXPOSURE_MULTIPLIER': 'Configs.position_sizing.martingale_max_total_exposure_multiplier',
        'MARTINGALE_PROGRESSION_MULTIPLIER': 'Configs.position_sizing.martingale_progression_multiplier',
        'OPTIMAL_F_CALCULATION_ERROR_DEFAULT': 'Configs.position_sizing.optimal_f_calculation_error_default',
        'OPTIMAL_F_DEFAULT_PERCENTAGE': 'Configs.position_sizing.optimal_f_default_percentage',
        'OPTIMAL_F_ERROR_FALLBACK_PERCENTAGE': 'Configs.position_sizing.optimal_f_error_fallback_percentage',
        'OPTIMAL_F_MAX_PER_TRADE': 'Configs.position_sizing.optimal_f_max_per_trade',
        'POSITION_SIZING_METHOD': 'Configs.position_sizing.method',

        # Portfolio configuration
        'REBALANCE_FREQUENCY': 'Configs.portfolio.rebalance_frequency',
        'CORRELATION_CONSENSUS_WEIGHT': 'Configs.portfolio.correlation_consensus_weight',
        'CORRELATION_CONFIDENCE_WEIGHT': 'Configs.portfolio.correlation_confidence_weight',
        'CORRELATION_BASE_PERCENTAGE': 'Configs.portfolio.correlation_base_percentage',
        'CORRELATION_DEFAULT_PERCENTAGE': 'Configs.portfolio.correlation_default_percentage',
        'CORRELATION_DIVERSIFICATION_FACTOR': 'Configs.portfolio.correlation_diversification_factor',
        'CORRELATION_MAX_CORRELATION': 'Configs.portfolio.correlation_max_correlation',
        'CORRELATION_PORTFOLIO_IMPACT_THRESHOLD': 'Configs.portfolio.correlation_portfolio_impact_threshold',

        # Backtest configuration
        'BACKTEST_INITIAL_CAPITAL': 'Configs.backtest.initial_capital',
        'BACKTEST_FEE_RATE': 'Configs.backtest.fee_rate',
        'BACKTEST_SLIPPAGE_FACTOR': 'Configs.backtest.slippage_factor',
        'BACKTEST_RISK_PER_TRADE': 'Configs.backtest.risk_per_trade',
        'BACKTEST_END_DATE': 'Configs.backtest.end_date',
        'BACKTEST_START_DATE': 'Configs.backtest.start_date',
        'BENCHMARK_SYMBOL': 'Configs.backtest.benchmark_symbol',
        'COMMISSION_RATE': 'Configs.backtest.commission_rate',

        # Fusion configuration
        'FUSION_METHOD': 'Configs.fusion.method',
        'FUSION_WEIGHT_DECAY_RATE': 'Configs.fusion.weight_decay_rate',
        'FUSION_MIN_CORRELATION_SCORE': 'Configs.fusion.min_correlation_score',
        'FUSION_MAX_SIGNALS_PER_ASSET': 'Configs.fusion.max_signals_per_asset',

        # General configuration
        'APP_ENV': 'Configs.infrastructure.environment',
        'ENVIRONMENT': 'Configs.infrastructure.environment',
        'LYNXION_ENV': 'Configs.infrastructure.lynxion_env',
        'USE_MOCK_DATA_FOR_VALIDATION': 'Configs.infrastructure.use_mock_data',
        'FAILED_SYMBOLS_CACHE_DURATION': 'Configs.data.failed_symbols_cache_duration',
        'FALLBACK_WATCHLIST_SYMBOLS': 'Configs.data.fallback_watchlist_symbols',
        'PREFERRED_HISTORICAL_DATA_SOURCE': 'Configs.data.preferred_historical_data_source',
        'HISTORICAL_DATA_FALLBACK_SOURCES': 'Configs.data.historical_data_fallback_sources',
        'VALIDATE_SYMBOL_DATA_AVAILABILITY': 'Configs.data.validate_symbol_data_availability',
        'DEFAULT_ACCOUNT_BALANCE': 'Configs.position_sizing.default_account_balance',
        'FIXED_POSITION_AMOUNT': 'Configs.position_sizing.fixed_position_amount',
        'FIXED_POSITION_SIZE_ENABLED': 'Configs.position_sizing.fixed_position_size_enabled',
        'PREVENT_SAME_DIRECTION_TRADE_PER_SYMBOL': 'Configs.execution.prevent_same_direction_trade_per_symbol',
        'FILTER_OUT_STABLECOIN_PAIRS': 'Configs.data.filter_out_stablecoin_pairs',
        'ALLOWED_STABLECOINS': 'Configs.data.allowed_stablecoins',
        'EXCLUDED_SYMBOLS_PATTERN': 'Configs.data.excluded_symbols_pattern',
        'CSV_DATA_PATH': 'Configs.data.csv_data_path',
        'DEFAULT_WATCHLIST_SYMBOLS': 'Configs.data.default_watchlist_symbols',
        'SYNC_DEFAULT_EXCHANGE': 'Configs.data.sync_default_exchange',
        'SYNC_MAX_WINDOW_MINUTES': 'Configs.data.sync_max_window_minutes',
        'SYNC_RATE_LIMIT': 'Configs.data.sync_rate_limit',
        'COINS_CONFIG_PATH': 'Configs.data.coins_config_path',
        'PREFERRED_HISTORICAL_DATA_SOURCE': 'Configs.data.preferred_historical_data_source',
        'HISTORICAL_DATA_FALLBACK_SOURCES': 'Configs.data.historical_data_fallback_sources',
        'FAILED_SYMBOLS_CACHE_DURATION': 'Configs.data.failed_symbols_cache_duration',
        'FALLBACK_WATCHLIST_SYMBOLS': 'Configs.data.fallback_watchlist_symbols',
        'VALIDATE_SYMBOL_DATA_AVAILABILITY': 'Configs.data.validate_symbol_data_availability',
        'CMC_CATEGORIES_URL': 'Configs.data.cmc_categories_url',
        'CMC_UPDATE_INTERVAL': 'Configs.data.cmc_update_interval',
        'CMC_VOLATILITY_HIGH_THRESHOLD': 'Configs.data.cmc_volatility_high_threshold',
        'CMC_VOLATILITY_LOW_THRESHOLD': 'Configs.data.cmc_volatility_low_threshold',
        'CMC_VOLUME_HIGH_THRESHOLD': 'Configs.data.cmc_volume_high_threshold',
        'CMC_VOLUME_LOW_THRESHOLD': 'Configs.data.cmc_volume_low_threshold',
        'CORRELATION_BASE_PERCENTAGE': 'Configs.fusion.correlation_base_percentage',
        'CORRELATION_DEFAULT_PERCENTAGE': 'Configs.fusion.correlation_default_percentage',
        'CORRELATION_DIVERSIFICATION_FACTOR': 'Configs.fusion.correlation_diversification_factor',
        'CORRELATION_MAX_CORRELATION': 'Configs.fusion.correlation_max_correlation',
        'CORRELATION_PORTFOLIO_IMPACT_THRESHOLD': 'Configs.fusion.correlation_portfolio_impact_threshold',
        'CORRELATION_CONSENSUS_WEIGHT': 'Configs.fusion.correlation_consensus_weight',
        'CORRELATION_CONFIDENCE_WEIGHT': 'Configs.fusion.correlation_confidence_weight',
        'PERFORMANCE_DEVIATION_THRESHOLD': 'Configs.risk.performance_deviation_threshold',
        'MAX_TOTAL_DRAWDOWN': 'Configs.risk.max_total_drawdown',
        'MAX_DAILY_LOSS': 'Configs.risk.max_daily_loss',
        'USE_CONSOLIDATED_.*': 'Configs.watcher.use_consolidated_*',  # Pattern for consolidated watchers
    }


def replace_env_access_with_configs(file_path: str):
    """
    Replace os.getenv calls with Configs access in a given file.
    """
    mapping = create_env_to_config_mapping()

    with open(file_path, 'r') as f:
        content = f.read()

    # Import statement to add if not present
    import_statement = "from application.configs.configs import Configs\n"

    # Check if Configs import is already present
    has_configs_import = 'from application.configs.configs import Configs' in content

    # Pattern to match os.getenv calls
    pattern = r"os\.getenv\(\s*['\"]([A-Z_][A-Z0-9_]*)['\"](?:\s*,\s*(?:['\"]([^'\"]*)['\"]|\s*([^,\)]+)\s*))?\)"

    def replace_match(match):
        env_var = match.group(1)
        default_val = match.group(2) or match.group(3)

        # Look up the corresponding Configs field
        if env_var in mapping:
            config_field = mapping[env_var]

            # Handle different default value types
            if default_val is None:
                # No default provided - use the config field directly
                return config_field
            elif default_val.lower() in ['true', 'false']:
                # Boolean default
                return f"{config_field} if {config_field} is not None else {default_val.lower()}"
            elif default_val.isdigit() or '.' in default_val:
                # Numeric default
                return f"{config_field} if {config_field} is not None else {default_val}"
            else:
                # String default
                return f"{config_field} if {config_field} is not None else '{default_val}'"
        else:
            # If not in mapping, return the original call but warn
            print(f"Warning: Environment variable {env_var} not found in mapping")
            return match.group(0)

    # Replace all os.getenv calls
    updated_content, num_replacements = re.subn(pattern, replace_match, content)

    # Add Configs import if not present
    if not has_configs_import and num_replacements > 0:
        # Find the import section and add Configs import
        import_section_end = 0
        lines = updated_content.split('\n')
        for i, line in enumerate(lines):
            if line.strip().startswith('import ') or line.strip().startswith('from '):
                import_section_end = i + 1
            elif line.strip() and not line.strip().startswith('#') and not line.strip().startswith('"""'):
                break

        # Insert the import after the import section
        new_lines = lines[:import_section_end] + [import_statement] + [''] + lines[import_section_end:]
        updated_content = '\n'.join(new_lines)

    if num_replacements > 0:
        with open(file_path, 'w') as f:
            f.write(updated_content)
        print(f"Updated {num_replacements} os.getenv calls in {file_path}")
    else:
        print(f"No os.getenv calls found in {file_path}")


def main():
    """
    Main function to run the migration helper.
    """
    print("Configuration Migration Helper")
    print("===============================")
    print("This script helps migrate os.getenv calls to use the Configs system.")
    print("")

    # Example usage for a single file
    # replace_env_access_with_configs('/path/to/your/file.py')


if __name__ == "__main__":
    main()
