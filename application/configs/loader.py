from typing import Dict, Any
from application.configs.env_loader import EnvLoader
from application.configs.profile_loader import ProfileLoader
from application.configs.environments import Environment
from application.configs.schemas.broker import BrokerConfig
from application.configs.schemas.risk import RiskConfig
from application.configs.schemas.strategy import StrategyConfig
from application.configs.schemas.execution import ExecutionConfig
from application.configs.schemas.safety import SafetyConfig
from application.configs.schemas.data import DataConfig
from application.configs.schemas.optimization import OptimizationConfig
from application.configs.schemas.wfo import WFOConfig
from application.configs.schemas.monitoring import MonitoringConfig
from application.configs.schemas.analytics import AnalyticsConfig
from application.configs.schemas.infrastructure import InfrastructureConfig
from application.configs.schemas.position_sizing import PositionSizingConfig
from application.configs.schemas.watcher import WatcherConfig
from application.configs.schemas.portfolio import PortfolioConfig
from application.configs.schemas.backtest import BacktestConfig
from application.configs.schemas.fusion import FusionConfig


class ConfigLoader:
    """
    Responsible for loading and assembling all configuration components.
    """

    def __init__(self, env_file_path: str = None):
        """
        Initialize the config loader.

        Args:
            env_file_path: Optional path to .env file
        """
        self.env_loader = EnvLoader()
        self.env_vars = self.env_loader.load(env_file_path)
        self.profile_config = None

    def load_config(self, environment: Environment = None) -> Dict[str, Any]:
        """
        Load configuration for the specified environment.

        Args:
            environment: Target environment. If None, uses current environment.

        Returns:
            Dictionary containing all configuration objects
        """
        # Load profile configuration
        self.profile_config = ProfileLoader.load_profile(environment)

        # Create configuration objects from profile and environment variables
        config_objects = {}

        # Broker configuration - merge environment variables if available
        broker_data = self.profile_config.get("broker", {}).dict()
        if 'BROKER_API_KEY' in self.env_vars:
            broker_data['api_key'] = self.env_vars['BROKER_API_KEY']
        if 'BROKER_SECRET_KEY' in self.env_vars:
            broker_data['secret_key'] = self.env_vars['BROKER_SECRET_KEY']
        # Add other broker env vars if they exist
        for env_key, config_attr in [
            ('BINGX_API_KEY', 'bingx_api_key'),
            ('BINGX_SECRET_KEY', 'bingx_secret_key'),
            ('BINGX_ORDER_PLACEMENT_ENABLED', 'bingx_order_placement_enabled'),
            ('BINGX_TESTNET', 'bingx_testnet'),
            ('DEFAULT_BROKER', 'default_broker'),
            ('BINANCE_API_KEY', 'binance_api_key'),
            ('BINANCE_SECRET_KEY', 'binance_secret_key'),
            ('BINANCE_ORDER_PLACEMENT_ENABLED', 'binance_order_placement_enabled'),
            ('BINANCE_TESTNET', 'binance_testnet'),
            ('MEXC_API_KEY', 'mexc_api_key'),
            ('MEXC_SECRET_KEY', 'mexc_secret_key'),
            ('MEXC_ORDER_PLACEMENT_ENABLED', 'mexc_order_placement_enabled'),
            ('MEXC_TESTNET', 'mexc_testnet'),
            ('PHEMEX_API_KEY', 'phemex_api_key'),
            ('PHEMEX_SECRET_KEY', 'phemex_secret_key'),
            ('PHEMEX_ORDER_PLACEMENT_ENABLED', 'phemex_order_placement_enabled'),
            ('PHEMEX_TESTNET', 'phemex_testnet'),
            ('BINANCE_API_URL', 'binance_api_url'),
            ('BINANCE_RETRY_ATTEMPTS', 'binance_retry_attempts'),
            ('BINANCE_RATE_LIMIT_DELAY', 'binance_rate_limit_delay'),
            ('BINGX_PASSPHRASE', 'bingx_passphrase'),
            ('ENABLED_BROKERS', 'enabled_brokers')
        ]:
            if env_key in self.env_vars:
                if config_attr.endswith('_enabled') or config_attr in ['testnet', 'paper_trading']:
                    # Convert string to boolean
                    broker_data[config_attr] = self.env_vars[env_key].lower() in ('true', '1', 'yes', 'on')
                elif config_attr.endswith('_attempts') or config_attr.endswith('_workers'):
                    # Convert string to integer
                    broker_data[config_attr] = int(self.env_vars[env_key])
                elif config_attr.endswith('_delay'):
                    # Convert string to float
                    broker_data[config_attr] = float(self.env_vars[env_key])
                elif config_attr == 'enabled_brokers':
                    # Convert comma-separated string to list
                    broker_data[config_attr] = [item.strip() for item in self.env_vars[env_key].split(',')]
                else:
                    broker_data[config_attr] = self.env_vars[env_key]
        config_objects['broker'] = BrokerConfig(**broker_data)

        # Risk configuration
        risk_data = self.profile_config.get("risk", {}).dict()
        # Add risk env vars if they exist
        for env_key, config_attr in [
            ('RISK_MAX_POSITION_SIZE', 'max_position_size'),
            ('RISK_MAX_TOTAL_EXPOSURE', 'max_total_exposure'),
            ('RISK_MAX_DRAWDOWN', 'max_drawdown'),
            ('RISK_MAX_LEVERAGE', 'max_leverage'),
            ('RISK_CAPITAL_PER_SYMBOL', 'capital_per_symbol'),
            ('RISK_MAX_EXPOSURE', 'max_exposure'),
            ('RISK_PER_TRADE', 'per_trade'),
            ('RISK_MAX_DAILY_LOSS', 'max_daily_loss'),
            ('RISK_MAX_TOTAL_POSITIONS', 'max_total_positions'),
            ('RISK_MAX_CORRELATION_BETWEEN_POS', 'max_correlation_between_pos'),
            ('RISK_MAX_SECTOR_EXPOSURE', 'max_sector_exposure'),
            ('RISK_MAX_SINGLE_ASSET_EXPOSURE', 'max_single_asset_exposure'),
            ('RISK_EMERGENCY_STOP_DRAWDOWN', 'emergency_stop_drawdown'),
            ('MIN_ORDER_SIZE', 'min_order_size'),
            ('MAX_ORDER_SIZE', 'max_order_size'),
            ('MIN_POSITION_SIZE', 'min_position_size'),
            ('MAX_POSITION_CONCENTRATION', 'max_position_concentration'),
            ('MAX_PORTFOLIO_RISK', 'max_portfolio_risk'),
            ('MAX_POSITION_RISK', 'max_position_risk'),
            ('MAX_DRAWDOWN_THRESHOLD', 'max_drawdown_threshold')
        ]:
            if env_key in self.env_vars:
                if config_attr.endswith('_positions'):
                    # Convert string to integer
                    risk_data[config_attr] = int(self.env_vars[env_key])
                else:
                    # Convert string to float
                    risk_data[config_attr] = float(self.env_vars[env_key])
        config_objects['risk'] = RiskConfig(**risk_data)

        # Strategy configuration
        strategy_data = self.profile_config.get("strategy", {}).dict()
        # Add strategy env vars if they exist
        for env_key, config_attr in [
            ('DEFAULT_STRATEGY', 'default_strategy'),
            ('STRATEGY_RISK_PER_TRADE', 'risk_per_trade'),
            ('STRATEGY_MAX_POSITION_SIZE', 'max_position_size'),
            ('STRATEGY_MIN_VOLUME_FILTER', 'min_volume_filter'),
            ('STRATEGY_SIGNAL_COOLDOWN_MINUTES', 'signal_cooldown_minutes'),
            ('STRATEGY_MIN_CONFIDENCE_THRESHOLD', 'min_confidence_threshold'),
            ('STRATEGY_HIGH_CONFIDENCE_THRESHOLD', 'high_confidence_threshold'),
            ('STRATEGY_NEUTRAL_BUFFER', 'neutral_buffer'),
            ('STRATEGY_STRONG_DIRECTIONAL_BIAS_THRESHOLD', 'strong_directional_bias_threshold'),
            ('ANOMALY_ML_CONTAMINATION', 'anomaly_ml_contamination'),
            ('ATR_DEFAULT_PERCENTAGE', 'atr_default_percentage'),
            ('ATR_FIXED_DOLLAR_RISK', 'atr_fixed_dollar_risk'),
            ('ATR_MAX_PORTFOLIO_PERCENT', 'atr_max_portfolio_percent'),
            ('ATR_MIN_MULTIPLE', 'atr_min_multiple'),
            ('ATR_MULTIPLIER', 'atr_multiplier'),
            ('ATR_TO_VOLATILITY_MULTIPLIER', 'atr_to_volatility_multiplier'),
            ('BASE_REWARD_RISK_RATIO', 'base_reward_risk_ratio'),
            ('CONFIDENCE_RR_MULTIPLIER', 'confidence_rr_multiplier'),
            ('DEFAULT_ANNUAL_VOLATILITY', 'default_annual_volatility'),
            ('DEFAULT_ASSET_VOLATILITY', 'default_asset_volatility'),
            ('EDGE_ESTIMATION_FACTOR', 'edge_estimation_factor'),
            ('ENGINE_CONFIDENCE_THRESHOLD', 'engine_confidence_threshold'),
            ('ENABLED_ENGINES', 'enabled_engines'),
            ('HIGH_VOLATILITY_THRESHOLD', 'high_volatility_threshold'),
            ('HIGH_VOLATILITY_WIN_RATE_IMPACT', 'high_volatility_win_rate_impact'),
            ('LOW_VOLATILITY_THRESHOLD', 'low_volatility_threshold'),
            ('LOW_VOLATILITY_WIN_RATE_IMPACT', 'low_volatility_win_rate_impact'),
            ('MAXIMUM_WIN_RATE_THRESHOLD', 'maximum_win_rate_threshold'),
            ('MAX_REWARD_RISK_RATIO', 'max_reward_risk_ratio'),
            ('MAX_TREND_IMPACT_ON_EDGE', 'max_trend_impact_on_edge'),
            ('MAX_TREND_IMPACT_ON_WIN_RATE', 'max_trend_impact_on_win_rate'),
            ('MAX_VOLATILITY_IMPACT_ON_EDGE', 'max_volatility_impact_on_edge'),
            ('MIN_CONFIDENCE_RR_FACTOR', 'min_confidence_rr_factor'),
            ('MIN_REWARD_RISK_RATIO', 'min_reward_risk_ratio'),
            ('ML_WEIGHTS_ENABLED', 'ml_weights_enabled'),
            ('REGIME_DETECTION_ENABLED', 'regime_detection_enabled'),
            ('SIGNAL_FUSION_ENABLED', 'signal_fusion_enabled'),
            ('SIGNAL_THRESHOLD', 'signal_threshold'),
            ('TARGET_VOLATILITY', 'target_volatility'),
            ('TREND_IMPACT_ON_WIN_RATE_MULTIPLIER', 'trend_impact_on_win_rate_multiplier'),
            ('TREND_MAX_RR_IMPACT', 'trend_max_rr_impact'),
            ('TREND_MTF_LONG_PERIOD', 'trend_mtf_long_period'),
            ('TREND_MTF_MEDIUM_PERIOD', 'trend_mtf_medium_period'),
            ('TREND_MTF_SHORT_PERIOD', 'trend_mtf_short_period'),
            ('TREND_RR_MULTIPLIER', 'trend_rr_multiplier'),
            ('MINIMUM_WIN_RATE_THRESHOLD', 'minimum_win_rate_threshold'),
            ('OPPORTUNITY_SCORE_CONFIDENCE_WEIGHT', 'opportunity_score_confidence_weight'),
            ('OPPORTUNITY_SCORE_DOMINANCE_WEIGHT', 'opportunity_score_dominance_weight'),
            ('OPPORTUNITY_SCORE_POSITION_SIZE_WEIGHT', 'opportunity_score_position_size_weight'),
            ('OPPORTUNITY_SCORE_REWARD_RISK_WEIGHT', 'opportunity_score_reward_risk_weight'),
            ('OPPORTUNITY_SCORE_REGIME_BONUS', 'opportunity_score_regime_bonus'),
            ('ENABLE_SHORTING', 'enable_shorting')
        ]:
            if env_key in self.env_vars:
                if config_attr.endswith('_enabled') or config_attr in ['ml_weights_enabled', 'regime_detection_enabled', 'signal_fusion_enabled', 'enable_shorting']:
                    # Convert string to boolean
                    strategy_data[config_attr] = self.env_vars[env_key].lower() in ('true', '1', 'yes', 'on')
                elif config_attr.endswith('_period') or config_attr.endswith('_minutes') or config_attr.endswith('_levels'):
                    # Convert string to integer
                    strategy_data[config_attr] = int(self.env_vars[env_key])
                elif config_attr == 'enabled_engines':
                    # Convert comma-separated string to list
                    strategy_data[config_attr] = [item.strip() for item in self.env_vars[env_key].split(',')]
                else:
                    # Convert string to float
                    strategy_data[config_attr] = float(self.env_vars[env_key])
        config_objects['strategy'] = StrategyConfig(**strategy_data)

        # Execution configuration
        execution_data = self.profile_config.get("execution", {}).dict()
        # Add execution env vars if they exist
        for env_key, config_attr in [
            ('EXECUTION_ORDER_TYPE', 'order_type'),
            ('EXECUTION_LIMIT_SLIPPAGE', 'limit_slippage'),
            ('EXECUTION_PRICE_BAND_WIDTH', 'price_band_width'),
            ('EXECUTION_MAX_PARTIAL_FILL_PERCENT', 'max_partial_fill_percent'),
            ('PREVENT_SAME_DIRECTION_TRADE_PER_SYMBOL', 'prevent_same_direction_trade_per_symbol'),
            ('ENABLE_TWAP', 'enable_twap'),
            ('ENABLE_VWAP', 'enable_vwap'),
            ('SMART_ORDER_ROUTING', 'smart_order_routing'),
            ('MIN_ORDER_QUANTITY', 'min_order_quantity'),
            ('ORDER_TIMEOUT', 'order_timeout')
        ]:
            if env_key in self.env_vars:
                if config_attr in ['order_type']:  # String fields
                    execution_data[config_attr] = self.env_vars[env_key]
                elif config_attr.endswith('_enabled') or config_attr in ['prevent_same_direction_trade_per_symbol', 'enable_twap', 'enable_vwap', 'smart_order_routing']:
                    # Convert string to boolean
                    execution_data[config_attr] = self.env_vars[env_key].lower() in ('true', '1', 'yes', 'on')
                elif config_attr.endswith('_timeout'):
                    # Convert string to integer
                    execution_data[config_attr] = int(self.env_vars[env_key])
                else:
                    # Convert string to float
                    execution_data[config_attr] = float(self.env_vars[env_key])
        config_objects['execution'] = ExecutionConfig(**execution_data)

        # Safety configuration
        safety_data = self.profile_config.get("safety", {}).dict()
        # Add safety env vars if they exist
        for env_key, config_attr in [
            ('SAFETY_KILL_SWITCH_ENABLED', 'kill_switch_enabled'),
            ('SAFETY_EMERGENCY_STOP_ENABLED', 'emergency_stop_enabled'),
            ('SAFETY_MAX_ORDER_SIZE_USD', 'max_order_size_usd'),
            ('SAFETY_MAX_DAILY_ORDERS', 'max_daily_orders'),
            ('SAFETY_API_RATE_LIMIT_BUFFER', 'api_rate_limit_buffer'),
            ('ENABLE_KILL_SWITCH', 'enable_kill_switch')
        ]:
            if env_key in self.env_vars:
                if config_attr.endswith('_enabled') or config_attr == 'enable_kill_switch':
                    # Convert string to boolean
                    safety_data[config_attr] = self.env_vars[env_key].lower() in ('true', '1', 'yes', 'on')
                elif config_attr.endswith('_orders'):
                    # Convert string to integer
                    safety_data[config_attr] = int(self.env_vars[env_key])
                else:
                    # Convert string to float
                    safety_data[config_attr] = float(self.env_vars[env_key])
        config_objects['safety'] = SafetyConfig(**safety_data)

        # Data configuration
        data_data = self.profile_config.get("data", {}).dict()
        # Add data env vars if they exist
        for env_key, config_attr in [
            ('DATA_PATH', 'path'),
            ('RESULTS_DIR', 'results_dir'),
            ('CACHE_DIR', 'cache_dir'),
            ('COIN_HISTORY_CACHE_DIR', 'coin_history_cache_dir'),
            ('MAX_CACHE_AGE_HOURS', 'max_cache_age_hours'),
            ('MAX_COIN_CACHE_SIZE', 'max_coin_cache_size'),
            ('DEFAULT_DATA_PROVIDER', 'default_provider'),
            ('DEFAULT_TIMEFRAME', 'default_timeframe'),
            ('SUPPORTED_TIMEFRAMES', 'supported_timeframes'),
            ('COINS_CONFIG_PATH', 'coins_config_path'),
            ('WFO_DATA_DIR', 'wfo_data_dir'),
            ('WFO_RAW_DIR', 'wfo_raw_dir'),
            ('WFO_PROCESSED_DIR', 'wfo_processed_dir'),
            ('CMC_API_KEY', 'cmc_api_key'),
            ('CMC_LISTINGS_URL', 'cmc_listings_url'),
            ('CMC_QUOTES_URL', 'cmc_quotes_url'),
            ('CMC_EXCLUDED_COINS', 'cmc_excluded_coins'),
            ('CMC_MAX_CALLS_PER_MINUTE', 'cmc_max_calls_per_minute'),
            ('CMC_MAX_CALLS_PER_HOUR', 'cmc_max_calls_per_hour'),
            ('CMC_API_CALL_INTERVAL', 'cmc_api_call_interval'),
            ('CMC_CACHE_TTL_SECONDS', 'cmc_cache_ttl_seconds'),
            ('CMC_LISTINGS_CACHE_TTL_SECONDS', 'cmc_listings_cache_ttl_seconds'),
            ('CMC_QUOTE_CACHE_TTL_SECONDS', 'cmc_quote_cache_ttl_seconds'),
            ('CMC_SCREEN_TOP_COINS_INTERVAL_HOURS', 'cmc_screen_top_coins_interval_hours'),
            ('CMC_SCREEN_TOP_COINS_LIMIT', 'cmc_screen_top_coins_limit'),
            ('CMC_MAX_COINS_TO_ANALYZE_PER_RUN', 'cmc_max_coins_to_analyze_per_run'),
            ('CMC_CIRCUIT_BREAKER_FAILURE_THRESHOLD', 'cmc_circuit_breaker_failure_threshold'),
            ('CMC_CIRCUIT_BREAKER_RESET_TIMEOUT', 'cmc_circuit_breaker_reset_timeout'),
            ('CMC_MIN_CONFIDENCE_THRESHOLD', 'cmc_min_confidence_threshold'),
            ('CMC_VOL_CONFIDENCE_WEIGHT', 'cmc_vol_confidence_weight'),
            ('CMC_VOLUME_CONFIDENCE_WEIGHT', 'cmc_volume_confidence_weight'),
            ('CMC_CHANGE_CONFIDENCE_WEIGHT', 'cmc_change_confidence_weight'),
            ('SYNC_INTERVAL_SECONDS', 'sync_interval_seconds'),
            ('ASYNC_CONCURRENCY', 'async_concurrency'),
            ('DOWNLOAD_THREADPOOL_WORKERS', 'download_threadpool_workers'),
            ('RETRY_MAX_ATTEMPTS', 'retry_max_attempts'),
            ('RETRY_BACKOFF_BASE', 'retry_backoff_base'),
            ('RETRY_BACKOFF_FACTOR', 'retry_backoff_factor'),
            ('RATE_LIMIT_TOKENS_PER_SECOND', 'rate_limit_tokens_per_second'),
            ('TEMP_FILE_SUFFIX', 'temp_file_suffix'),
            ('DATA_DIR', 'dir'),
            ('RAW_RETENTION_DAYS', 'raw_retention_days'),
            ('PROCESSED_RETENTION_DAYS', 'processed_retention_days'),
            ('MAX_GAP_FILL_MINUTES', 'max_gap_fill_minutes'),
            ('SYNC_DEFAULT_EXCHANGE', 'sync_default_exchange'),
            ('SYNC_MAX_WINDOW_MINUTES', 'sync_max_window_minutes'),
            ('SYNC_RATE_LIMIT', 'sync_rate_limit'),
            ('FILTER_OUT_STABLECOIN_PAIRS', 'filter_out_stablecoin_pairs'),
            ('ALLOWED_STABLECOINS', 'allowed_stablecoins'),
            ('EXCLUDED_SYMBOLS_PATTERN', 'excluded_symbols_pattern'),
            ('CSV_DATA_PATH', 'csv_data_path'),
            ('DEFAULT_WATCHLIST_SYMBOLS', 'default_watchlist_symbols'),
            ('FAILED_SYMBOLS_CACHE_DURATION', 'failed_symbols_cache_duration'),
            ('FALLBACK_WATCHLIST_SYMBOLS', 'fallback_watchlist_symbols'),
            ('HISTORICAL_DATA_FALLBACK_SOURCES', 'historical_data_fallback_sources'),
            ('PREFERRED_HISTORICAL_DATA_SOURCE', 'preferred_historical_data_source'),
            ('VALIDATE_SYMBOL_DATA_AVAILABILITY', 'validate_symbol_data_availability'),
            ('CMC_CATEGORIES_URL', 'cmc_categories_url'),
            ('CMC_UPDATE_INTERVAL', 'cmc_update_interval'),
            ('CMC_VOLATILITY_HIGH_THRESHOLD', 'cmc_volatility_high_threshold'),
            ('CMC_VOLATILITY_LOW_THRESHOLD', 'cmc_volatility_low_threshold'),
            ('CMC_VOLUME_HIGH_THRESHOLD', 'cmc_volume_high_threshold'),
            ('CMC_VOLUME_LOW_THRESHOLD', 'cmc_volume_low_threshold')
        ]:
            if env_key in self.env_vars:
                if config_attr.endswith('_enabled') or config_attr in ['filter_out_stablecoin_pairs']:
                    # Convert string to boolean
                    data_data[config_attr] = self.env_vars[env_key].lower() in ('true', '1', 'yes', 'on')
                elif config_attr.endswith('_hours') or config_attr.endswith('_days') or config_attr.endswith('_minutes') or config_attr.endswith('_attempts') or config_attr.endswith('_workers') or config_attr.endswith('_seconds') or config_attr.endswith('_size') or config_attr.endswith('_limit') or config_attr.endswith('_duration'):
                    # Convert string to integer
                    data_data[config_attr] = int(self.env_vars[env_key])
                elif config_attr.endswith('_interval') or config_attr.endswith('_factor'):
                    # Convert string to float
                    data_data[config_attr] = float(self.env_vars[env_key])
                else:
                    data_data[config_attr] = self.env_vars[env_key]
        config_objects['data'] = DataConfig(**data_data)

        # Optimization configuration
        optimization_data = self.profile_config.get("optimization", {}).dict()
        # Add optimization env vars if they exist
        for env_key, config_attr in [
            ('HYPEROPT_ALGORITHM', 'algorithm'),
            ('HYPEROPT_MAX_EVALS', 'max_evals'),
            ('HYPEROPT_EARLY_STOPPING_ROUNDS', 'early_stopping_rounds'),
            ('HYPEROPT_VALIDATION_SPLIT', 'validation_split'),
            ('HYPEROPT_OBJECTIVE_METRIC', 'objective_metric'),
            ('OPTIMIZATION_MIN_RETURNS', 'min_returns'),
            ('OPTIMIZATION_MIN_SHARPE_RATIO', 'min_sharpe_ratio'),
            ('OPTIMIZATION_MAX_DRAWDOWN', 'max_drawdown'),
            ('OPTIMIZATION_MIN_WIN_RATE', 'min_win_rate'),
            ('RETUNE_ENABLED', 'retune_enabled'),
            ('RETUNE_INTERVAL_HOURS', 'retune_interval_hours'),
            ('RETUNE_PERFORMANCE_THRESHOLD', 'retune_performance_threshold'),
            ('RETUNE_EVALS_PER_RETUNE', 'retune_evals_per_retune'),
            ('RETUNE_RETENTION_PERIOD_DAYS', 'retune_retention_period_days')
        ]:
            if env_key in self.env_vars:
                if config_attr.endswith('_enabled'):
                    # Convert string to boolean
                    optimization_data[config_attr] = self.env_vars[env_key].lower() in ('true', '1', 'yes', 'on')
                elif config_attr.endswith('_hours') or config_attr.endswith('_days') or config_attr.endswith('_rounds') or config_attr.endswith('_evals'):
                    # Convert string to integer
                    optimization_data[config_attr] = int(self.env_vars[env_key])
                else:
                    # Convert string to float
                    optimization_data[config_attr] = float(self.env_vars[env_key])
        config_objects['optimization'] = OptimizationConfig(**optimization_data)

        # WFO configuration
        wfo_data = self.profile_config.get("wfo", {}).dict()
        # Add WFO env vars if they exist
        for env_key, config_attr in [
            ('WFO_TRAIN_SIZE', 'train_size'),
            ('WFO_TEST_SIZE', 'test_size'),
            ('WFO_STEP_SIZE', 'step_size'),
            ('WFO_MAX_EVALS', 'max_evals'),
            ('WFO_PERFORMANCE_THRESHOLD', 'performance_threshold'),
            ('WFO_MAX_DRAWDOWN_THRESHOLD', 'max_drawdown_threshold'),
            ('WFO_RETRAIN_FREQUENCY_DAYS', 'retrain_frequency_days'),
            ('WFO_MIN_TRAINING_POINTS', 'min_training_points'),
            ('WFO_MIN_TESTING_POINTS', 'min_testing_points'),
            ('WFO_OVERFIT_THRESHOLD', 'overfit_threshold'),
            ('WFO_CONSISTENCY_THRESHOLD', 'consistency_threshold'),
            ('WFO_PASS_RATE_THRESHOLD', 'pass_rate_threshold'),
            ('WFO_ENABLED', 'wfo_enabled'),
            ('WFO_COINS', 'coins'),
            ('WFO_SYNC_DAYS', 'sync_days'),
            ('WFO_INCREMENTAL_DAYS', 'incremental_days'),
            ('WFO_REFRESH_INTERVAL_HOURS', 'refresh_interval_hours'),
            ('WFO_DEFAULT_TIMEFRAMES', 'default_timeframes')
        ]:
            if env_key in self.env_vars:
                if config_attr == 'wfo_enabled':
                    # Convert string to boolean
                    wfo_data[config_attr] = self.env_vars[env_key].lower() in ('true', '1', 'yes', 'on')
                elif config_attr.endswith('_days') or config_attr.endswith('_hours') or config_attr.endswith('_points') or config_attr.endswith('_evals'):
                    # Convert string to integer
                    wfo_data[config_attr] = int(self.env_vars[env_key])
                elif config_attr.endswith('_threshold'):
                    # Convert string to float
                    wfo_data[config_attr] = float(self.env_vars[env_key])
                else:
                    wfo_data[config_attr] = self.env_vars[env_key]
        config_objects['wfo'] = WFOConfig(**wfo_data)

        # Monitoring configuration
        monitoring_data = self.profile_config.get("monitoring", {}).dict()
        # Add monitoring env vars if they exist
        for env_key, config_attr in [
            ('TELEGRAM_BOT_NAME', 'telegram_bot_name'),
            ('TELEGRAM_BOT_URL', 'telegram_bot_url'),
            ('TELEGRAM_BOT_UPDATE_URL', 'telegram_bot_update_url'),
            ('TELEGRAM_BOT_TOKEN', 'telegram_bot_token'),
            ('TELEGRAM_CHAT_ID', 'telegram_chat_id'),
            ('TELEGRAM_NOTIFICATIONS_ENABLED', 'telegram_notifications_enabled'),
            ('LOG_LEVEL', 'logging_level'),
            ('LOG_FILE_PATH', 'log_file_path'),
            ('LOG_MAX_FILE_SIZE_MB', 'log_max_file_size_mb'),
            ('LOG_BACKUP_COUNT', 'log_backup_count'),
            ('MONITORING_ENABLED', 'enabled'),
            ('METRICS_REPORTING_INTERVAL_MINUTES', 'metrics_reporting_interval_minutes'),
            ('FORENSIC_LOGGING_ENABLED', 'forensic_logging_enabled'),
            ('ENABLE_METRICS', 'enable_metrics')
        ]:
            if env_key in self.env_vars:
                if config_attr.endswith('_enabled') or config_attr in ['telegram_notifications_enabled', 'forensic_logging_enabled', 'enable_metrics']:
                    # Convert string to boolean
                    monitoring_data[config_attr] = self.env_vars[env_key].lower() in ('true', '1', 'yes', 'on')
                elif config_attr.endswith('_mb') or config_attr.endswith('_count') or config_attr.endswith('_minutes'):
                    # Convert string to integer
                    monitoring_data[config_attr] = int(self.env_vars[env_key])
                else:
                    monitoring_data[config_attr] = self.env_vars[env_key]
        config_objects['monitoring'] = MonitoringConfig(**monitoring_data)

        # Analytics configuration
        analytics_data = self.profile_config.get("analytics", {}).dict()
        config_objects['analytics'] = AnalyticsConfig(**analytics_data)

        # Infrastructure configuration
        infrastructure_data = self.profile_config.get("infrastructure", {}).dict()
        # Add infrastructure env vars if they exist
        for env_key, config_attr in [
            ('PERFORMANCE_USE_MULTIPROCESSING', 'use_multiprocessing'),
            ('PERFORMANCE_NUM_WORKERS', 'num_workers'),
            ('PERFORMANCE_BATCH_SIZE', 'batch_size'),
            ('PERFORMANCE_MEMORY_PROFILING', 'memory_profiling'),
            ('API_TIMEOUT', 'api_timeout'),
            ('MAX_WORKERS', 'max_workers'),
            ('REDIS_URL', 'redis_url'),
            ('DEBUG', 'debug'),
            ('ENVIRONMENT', 'environment'),
            ('USE_MOCK_DATA', 'use_mock_data')
        ]:
            if env_key in self.env_vars:
                if config_attr.endswith('_enabled') or config_attr in ['use_multiprocessing', 'memory_profiling', 'debug', 'use_mock_data']:
                    # Convert string to boolean
                    infrastructure_data[config_attr] = self.env_vars[env_key].lower() in ('true', '1', 'yes', 'on')
                elif config_attr.endswith('_workers') or config_attr.endswith('_size'):
                    # Convert string to integer
                    infrastructure_data[config_attr] = int(self.env_vars[env_key])
                elif config_attr.endswith('_timeout'):
                    # Convert string to integer
                    infrastructure_data[config_attr] = int(self.env_vars[env_key])
                else:
                    infrastructure_data[config_attr] = self.env_vars[env_key]
        config_objects['infrastructure'] = InfrastructureConfig(**infrastructure_data)

        # Position Sizing configuration
        position_sizing_data = self.profile_config.get("position_sizing", {}).dict()
        # Add position sizing env vars if they exist
        for env_key, config_attr in [
            ('FIXED_POSITION_SIZE_ENABLED', 'fixed_position_size_enabled'),
            ('FIXED_POSITION_AMOUNT', 'fixed_position_amount'),
            ('DEFAULT_ACCOUNT_BALANCE', 'default_account_balance'),
            ('FIXED_FRACTIONAL_DEFAULT_PERCENTAGE', 'fixed_fractional_default_percentage'),
            ('FIXED_FRACTIONAL_PERCENTAGE', 'fixed_fractional_percentage'),
            ('FIXED_FRACTIONAL_RISK_PER_UNIT', 'fixed_fractional_risk_per_unit'),
            ('KELLY_DEFAULT_PERCENTAGE', 'kelly_default_percentage'),
            ('KELLY_FRACTION', 'kelly_fraction'),
            ('KELLY_MAX_POSITION_SIZE', 'kelly_max_position_size'),
            ('KELLY_MINIMUM_EDGE', 'kelly_minimum_edge'),
            ('KELLY_VAR_CONFIDENCE_LEVEL', 'kelly_var_confidence_level'),
            ('KELLY_VAR_MARGIN_OF_SAFETY_PERCENTAGE', 'kelly_var_margin_of_safety_percentage'),
            ('KELLY_VAR_MAX_POSITION_WITH_VAR', 'kelly_var_max_position_with_var'),
            ('KELLY_VAR_STRESS_TEST_MULTIPLIER', 'kelly_var_stress_test_multiplier'),
            ('MARTINGALE_BASE_RISK_PERCENTAGE', 'martingale_base_risk_percentage'),
            ('MARTINGALE_MAX_PROGRESSION_LEVELS', 'martingale_max_progression_levels'),
            ('MARTINGALE_MAX_TOTAL_EXPOSURE_MULTIPLIER', 'martingale_max_total_exposure_multiplier'),
            ('MARTINGALE_PROGRESSION_MULTIPLIER', 'martingale_progression_multiplier'),
            ('OPTIMAL_F_CALCULATION_ERROR_DEFAULT', 'optimal_f_calculation_error_default'),
            ('OPTIMAL_F_DEFAULT_PERCENTAGE', 'optimal_f_default_percentage'),
            ('OPTIMAL_F_ERROR_FALLBACK_PERCENTAGE', 'optimal_f_error_fallback_percentage'),
            ('OPTIMAL_F_MAX_PER_TRADE', 'optimal_f_max_per_trade'),
            ('POSITION_SIZING_METHOD', 'method')
        ]:
            if env_key in self.env_vars:
                if config_attr.endswith('_enabled'):
                    # Convert string to boolean
                    position_sizing_data[config_attr] = self.env_vars[env_key].lower() in ('true', '1', 'yes', 'on')
                elif config_attr.endswith('_levels') or config_attr.endswith('_multiplier'):
                    # Convert string to float
                    position_sizing_data[config_attr] = float(self.env_vars[env_key])
                else:
                    # Convert string to float
                    position_sizing_data[config_attr] = float(self.env_vars[env_key])
        config_objects['position_sizing'] = PositionSizingConfig(**position_sizing_data)

        # Watcher configuration
        watcher_data = self.profile_config.get("watcher", {}).dict()
        # Add watcher env vars if they exist
        for env_key, config_attr in [
            ('WATCHER_POLLING_INTERVAL_SECONDS', 'polling_interval_seconds'),
            ('WATCHER_MAX_SYMBOLS_TO_MONITOR', 'max_symbols_to_monitor'),
            ('WATCHER_DATA_REFRESH_INTERVAL_MINUTES', 'data_refresh_interval_minutes'),
            ('WATCHER_RISK_THRESHOLD', 'risk_threshold'),
            ('WATCHER_MIN_CONFIDENCE_THRESHOLD', 'min_confidence_threshold'),
            ('WATCHER_MAX_CONFIDENCE_WITH_PATTERNS', 'max_confidence_with_patterns'),
            ('WATCHER_MIN_PRICE_CHANGE_THRESHOLD', 'min_price_change_threshold'),
            ('WATCHER_MAX_CONFIDENCE_WITH_MOVEMENT', 'max_confidence_with_movement'),
            ('WATCHER_NEUTRAL_CONFIDENCE', 'neutral_confidence'),
            ('WATCHER_PATTERN_WEIGHT', 'pattern_weight'),
            ('WATCHER_MOMENTUM_WEIGHT', 'momentum_weight'),
            ('WATCHER_HIGH_VOLATILITY_BOOST', 'high_volatility_boost'),
            ('WATCHER_LOW_VOLATILITY_BOOST', 'low_volatility_boost'),
            ('WATCHER_NORMAL_VOLATILITY_BOOST', 'normal_volatility_boost'),
            ('WATCHER_MIN_CONFIDENCE_WHEN_SIGNALS_DETECTED', 'min_confidence_when_signals_detected'),
            ('WATCHER_MAX_CONFIDENCE_CAP', 'max_confidence_cap'),
            ('WATCHER_MOMENTUM_LOOKBACK_PERIOD', 'momentum_lookback_period'),
            ('WATCHER_MOMENTUM_SENSITIVITY_FACTOR', 'momentum_sensitivity_factor'),
            ('MARKET_PULSE_WATCHER_ENABLED', 'market_pulse_watcher_enabled'),  # This might be a typo in the original env file - should be MARKET_PULSE_WATCHER_ENABLED
            ('VOLATILITY_WATCHER_ENABLED', 'volatility_watcher_enabled'),
            ('TREND_MTF_WATCHER_ENABLED', 'trend_mtf_watcher_enabled'),
            ('ANOMALY_ML_WATCHER_ENABLED', 'anomaly_ml_watcher_enabled'),
            ('ORDERFLOW_WS_WATCHER_ENABLED', 'orderflow_ws_watcher_enabled'),
            ('CMC_SCREENER_ENABLED', 'cmc_screener_enabled'),
            ('FUNDING_RATE_WATCHER_ENABLED', 'funding_rate_watcher_enabled'),
            ('LIQUIDITY_WATCHER_ENABLED', 'liquidity_watcher_enabled'),
            ('HISTORICAL_CANDLE_WATCHER_ENABLED', 'historical_candle_watcher_enabled'),
            ('TICK_WATCHER_ENABLED', 'tick_watcher_enabled'),
            ('WATCHER_BROKER_CONFIG', 'broker_config'),
            ('TARGET_BROKER_MARKET_PULSE', 'target_broker_market_pulse'),  # This might be a typo in the original env file - should be TARGET_BROKER_MARKET_PULSE
            ('TARGET_BROKER_VOLATILITY', 'target_broker_volatility'),
            ('TARGET_BROKER_TREND_MTF', 'target_broker_trend_mtf'),
            ('TARGET_BROKER_ANOMALY_ML', 'target_broker_anomaly_ml'),
            ('TARGET_BROKER_ORDERFLOW_WS', 'target_broker_orderflow_ws'),
            ('TARGET_BROKER_FUNDING_RATE', 'target_broker_funding_rate'),
            ('TARGET_BROKER_LIQUIDITY', 'target_broker_liquidity'),
            ('TARGET_BROKER_HISTORICAL_CANDLE', 'target_broker_historical_candle'),
            ('TARGET_BROKER_TICK_WATCHER', 'target_broker_tick_watcher'),
            ('USE_IMPROVED_WATCHERS', 'use_improved_watchers'),
            ('AUTO_ENABLE_WATCHERS', 'auto_enable_watchers'),
            ('ENABLED_WATCHERS', 'enabled_watchers'),
            ('WATCHER_UPDATE_FREQ', 'update_freq'),
            ('WATCHER_LOOKBACK', 'lookback'),
            ('EARLY_EXIT_MOMENTUM_THRESHOLD', 'early_exit_momentum_threshold'),
            ('EARLY_EXIT_TREND_CONFIDENCE_THRESHOLD', 'early_exit_trend_confidence_threshold'),
            ('EARLY_EXIT_VOLATILITY_THRESHOLD', 'early_exit_volatility_threshold')
        ]:
            if env_key in self.env_vars:
                if config_attr.endswith('_enabled') or config_attr in ['use_improved_watchers', 'auto_enable_watchers']:
                    # Convert string to boolean
                    watcher_data[config_attr] = self.env_vars[env_key].lower() in ('true', '1', 'yes', 'on')
                elif config_attr.endswith('_seconds') or config_attr.endswith('_minutes') or config_attr.endswith('_period') or config_attr.endswith('_freq') or config_attr.endswith('_lookback'):
                    # Convert string to integer
                    watcher_data[config_attr] = int(self.env_vars[env_key])
                elif config_attr.endswith('_threshold') or config_attr.endswith('_weight') or config_attr.endswith('_boost') or config_attr.endswith('_factor'):
                    # Convert string to float
                    watcher_data[config_attr] = float(self.env_vars[env_key])
                elif config_attr == 'enabled_watchers':
                    # Convert comma-separated string to list
                    watcher_data[config_attr] = [item.strip() for item in self.env_vars[env_key].split(',')]
                else:
                    watcher_data[config_attr] = self.env_vars[env_key]
        config_objects['watcher'] = WatcherConfig(**watcher_data)

        # Portfolio configuration
        portfolio_data = self.profile_config.get("portfolio", {}).dict()
        # Add portfolio env vars if they exist
        for env_key, config_attr in [
            ('REBALANCE_FREQUENCY', 'rebalance_frequency'),
            ('CORRELATION_CONSENSUS_WEIGHT', 'correlation_consensus_weight'),
            ('CORRELATION_CONFIDENCE_WEIGHT', 'correlation_confidence_weight'),
            ('CORRELATION_BASE_PERCENTAGE', 'correlation_base_percentage'),
            ('CORRELATION_DEFAULT_PERCENTAGE', 'correlation_default_percentage'),
            ('CORRELATION_DIVERSIFICATION_FACTOR', 'correlation_diversification_factor'),
            ('CORRELATION_MAX_CORRELATION', 'correlation_max_correlation'),
            ('CORRELATION_PORTFOLIO_IMPACT_THRESHOLD', 'correlation_portfolio_impact_threshold')
        ]:
            if env_key in self.env_vars:
                # Convert string to float
                portfolio_data[config_attr] = float(self.env_vars[env_key]) if config_attr not in ['rebalance_frequency'] else self.env_vars[env_key]
        config_objects['portfolio'] = PortfolioConfig(**portfolio_data)

        # Backtest configuration
        backtest_data = self.profile_config.get("backtest", {}).dict()
        # Add backtest env vars if they exist
        for env_key, config_attr in [
            ('BACKTEST_INITIAL_CAPITAL', 'initial_capital'),
            ('BACKTEST_FEE_RATE', 'fee_rate'),
            ('BACKTEST_SLIPPAGE_FACTOR', 'slippage_factor'),
            ('BACKTEST_RISK_PER_TRADE', 'risk_per_trade'),
            ('BACKTEST_END_DATE', 'end_date'),
            ('BACKTEST_START_DATE', 'start_date'),
            ('BENCHMARK_SYMBOL', 'benchmark_symbol'),
            ('COMMISSION_RATE', 'commission_rate')
        ]:
            if env_key in self.env_vars:
                if config_attr in ['end_date', 'start_date', 'benchmark_symbol']:
                    backtest_data[config_attr] = self.env_vars[env_key]
                else:
                    # Convert string to float
                    backtest_data[config_attr] = float(self.env_vars[env_key])
        config_objects['backtest'] = BacktestConfig(**backtest_data)

        # Fusion configuration
        fusion_data = self.profile_config.get("fusion", {}).dict()
        # Add fusion env vars if they exist
        for env_key, config_attr in [
            ('FUSION_METHOD', 'method'),
            ('FUSION_WEIGHT_DECAY_RATE', 'weight_decay_rate'),
            ('FUSION_MIN_CORRELATION_SCORE', 'min_correlation_score'),
            ('FUSION_MAX_SIGNALS_PER_ASSET', 'max_signals_per_asset')
        ]:
            if env_key in self.env_vars:
                if config_attr.endswith('_signals') or config_attr.endswith('_assets'):
                    # Convert string to integer
                    fusion_data[config_attr] = int(self.env_vars[env_key])
                elif config_attr.endswith('_rate') or config_attr.endswith('_score'):
                    # Convert string to float
                    fusion_data[config_attr] = float(self.env_vars[env_key])
                else:
                    fusion_data[config_attr] = self.env_vars[env_key]
        config_objects['fusion'] = FusionConfig(**fusion_data)

        # Infrastructure configuration
        infrastructure_data = self.profile_config.get("infrastructure", {}).dict()
        # Add infrastructure env vars if they exist
        for env_key, config_attr in [
            ('PERFORMANCE_USE_MULTIPROCESSING', 'use_multiprocessing'),
            ('PERFORMANCE_NUM_WORKERS', 'num_workers'),
            ('PERFORMANCE_BATCH_SIZE', 'batch_size'),
            ('PERFORMANCE_MEMORY_PROFILING', 'memory_profiling'),
            ('API_TIMEOUT', 'api_timeout'),
            ('MAX_WORKERS', 'max_workers'),
            ('REDIS_URL', 'redis_url'),
            ('DEBUG', 'debug'),
            ('ENVIRONMENT', 'environment'),
            ('USE_MOCK_DATA', 'use_mock_data')
        ]:
            if env_key in self.env_vars:
                if config_attr.endswith('_enabled') or config_attr in ['use_multiprocessing', 'memory_profiling', 'debug', 'use_mock_data']:
                    # Convert string to boolean
                    infrastructure_data[config_attr] = self.env_vars[env_key].lower() in ('true', '1', 'yes', 'on')
                elif config_attr.endswith('_workers') or config_attr.endswith('_size'):
                    # Convert string to integer
                    infrastructure_data[config_attr] = int(self.env_vars[env_key])
                elif config_attr.endswith('_timeout'):
                    # Convert string to integer
                    infrastructure_data[config_attr] = int(self.env_vars[env_key])
                else:
                    infrastructure_data[config_attr] = self.env_vars[env_key]
        config_objects['infrastructure'] = InfrastructureConfig(**infrastructure_data)

        # Position Sizing configuration
        position_sizing_data = self.profile_config.get("position_sizing", {}).dict()
        # Add position sizing env vars if they exist
        for env_key, config_attr in [
            ('FIXED_POSITION_SIZE_ENABLED', 'fixed_position_size_enabled'),
            ('FIXED_POSITION_AMOUNT', 'fixed_position_amount'),
            ('DEFAULT_ACCOUNT_BALANCE', 'default_account_balance'),
            ('FIXED_FRACTIONAL_DEFAULT_PERCENTAGE', 'fixed_fractional_default_percentage'),
            ('FIXED_FRACTIONAL_PERCENTAGE', 'fixed_fractional_percentage'),
            ('FIXED_FRACTIONAL_RISK_PER_UNIT', 'fixed_fractional_risk_per_unit'),
            ('KELLY_DEFAULT_PERCENTAGE', 'kelly_default_percentage'),
            ('KELLY_FRACTION', 'kelly_fraction'),
            ('KELLY_MAX_POSITION_SIZE', 'kelly_max_position_size'),
            ('KELLY_MINIMUM_EDGE', 'kelly_minimum_edge'),
            ('KELLY_VAR_CONFIDENCE_LEVEL', 'kelly_var_confidence_level'),
            ('KELLY_VAR_MARGIN_OF_SAFETY_PERCENTAGE', 'kelly_var_margin_of_safety_percentage'),
            ('KELLY_VAR_MAX_POSITION_WITH_VAR', 'kelly_var_max_position_with_var'),
            ('KELLY_VAR_STRESS_TEST_MULTIPLIER', 'kelly_var_stress_test_multiplier'),
            ('MARTINGALE_BASE_RISK_PERCENTAGE', 'martingale_base_risk_percentage'),
            ('MARTINGALE_MAX_PROGRESSION_LEVELS', 'martingale_max_progression_levels'),
            ('MARTINGALE_MAX_TOTAL_EXPOSURE_MULTIPLIER', 'martingale_max_total_exposure_multiplier'),
            ('MARTINGALE_PROGRESSION_MULTIPLIER', 'martingale_progression_multiplier'),
            ('OPTIMAL_F_CALCULATION_ERROR_DEFAULT', 'optimal_f_calculation_error_default'),
            ('OPTIMAL_F_DEFAULT_PERCENTAGE', 'optimal_f_default_percentage'),
            ('OPTIMAL_F_ERROR_FALLBACK_PERCENTAGE', 'optimal_f_error_fallback_percentage'),
            ('OPTIMAL_F_MAX_PER_TRADE', 'optimal_f_max_per_trade'),
            ('POSITION_SIZING_METHOD', 'method')
        ]:
            if env_key in self.env_vars:
                if config_attr.endswith('_enabled'):
                    # Convert string to boolean
                    position_sizing_data[config_attr] = self.env_vars[env_key].lower() in ('true', '1', 'yes', 'on')
                elif config_attr.endswith('_levels') or config_attr.endswith('_multiplier'):
                    # Convert string to float
                    position_sizing_data[config_attr] = float(self.env_vars[env_key])
                else:
                    # Convert string to float
                    position_sizing_data[config_attr] = float(self.env_vars[env_key])
        config_objects['position_sizing'] = PositionSizingConfig(**position_sizing_data)

        # Watcher configuration
        watcher_data = self.profile_config.get("watcher", {}).dict()
        # Add watcher env vars if they exist
        for env_key, config_attr in [
            ('WATCHER_POLLING_INTERVAL_SECONDS', 'polling_interval_seconds'),
            ('WATCHER_MAX_SYMBOLS_TO_MONITOR', 'max_symbols_to_monitor'),
            ('WATCHER_DATA_REFRESH_INTERVAL_MINUTES', 'data_refresh_interval_minutes'),
            ('WATCHER_RISK_THRESHOLD', 'risk_threshold'),
            ('WATCHER_MIN_CONFIDENCE_THRESHOLD', 'min_confidence_threshold'),
            ('WATCHER_MAX_CONFIDENCE_WITH_PATTERNS', 'max_confidence_with_patterns'),
            ('WATCHER_MIN_PRICE_CHANGE_THRESHOLD', 'min_price_change_threshold'),
            ('WATCHER_MAX_CONFIDENCE_WITH_MOVEMENT', 'max_confidence_with_movement'),
            ('WATCHER_NEUTRAL_CONFIDENCE', 'neutral_confidence'),
            ('WATCHER_PATTERN_WEIGHT', 'pattern_weight'),
            ('WATCHER_MOMENTUM_WEIGHT', 'momentum_weight'),
            ('WATCHER_HIGH_VOLATILITY_BOOST', 'high_volatility_boost'),
            ('WATCHER_LOW_VOLATILITY_BOOST', 'low_volatility_boost'),
            ('WATCHER_NORMAL_VOLATILITY_BOOST', 'normal_volatility_boost'),
            ('WATCHER_MIN_CONFIDENCE_WHEN_SIGNALS_DETECTED', 'min_confidence_when_signals_detected'),
            ('WATCHER_MAX_CONFIDENCE_CAP', 'max_confidence_cap'),
            ('WATCHER_MOMENTUM_LOOKBACK_PERIOD', 'momentum_lookback_period'),
            ('WATCHER_MOMENTUM_SENSITIVITY_FACTOR', 'momentum_sensitivity_factor'),
            ('MARKET_PULSE_WATCHER_ENABLED', 'market_pulse_watcher_enabled'),
            ('VOLATILITY_WATCHER_ENABLED', 'volatility_watcher_enabled'),
            ('TREND_MTF_WATCHER_ENABLED', 'trend_mtf_watcher_enabled'),
            ('ANOMALY_ML_WATCHER_ENABLED', 'anomaly_ml_watcher_enabled'),
            ('ORDERFLOW_WS_WATCHER_ENABLED', 'orderflow_ws_watcher_enabled'),
            ('CMC_SCREENER_ENABLED', 'cmc_screener_enabled'),
            ('FUNDING_RATE_WATCHER_ENABLED', 'funding_rate_watcher_enabled'),
            ('LIQUIDITY_WATCHER_ENABLED', 'liquidity_watcher_enabled'),
            ('HISTORICAL_CANDLE_WATCHER_ENABLED', 'historical_candle_watcher_enabled'),
            ('TICK_WATCHER_ENABLED', 'tick_watcher_enabled'),
            ('WATCHER_BROKER_CONFIG', 'broker_config'),
            ('TARGET_BROKER_MARKET_PULSE', 'target_broker_market_pulse'),
            ('TARGET_BROKER_VOLATILITY', 'target_broker_volatility'),
            ('TARGET_BROKER_TREND_MTF', 'target_broker_trend_mtf'),
            ('TARGET_BROKER_ANOMALY_ML', 'target_broker_anomaly_ml'),
            ('TARGET_BROKER_ORDERFLOW_WS', 'target_broker_orderflow_ws'),
            ('TARGET_BROKER_FUNDING_RATE', 'target_broker_funding_rate'),
            ('TARGET_BROKER_LIQUIDITY', 'target_broker_liquidity'),
            ('TARGET_BROKER_HISTORICAL_CANDLE', 'target_broker_historical_candle'),
            ('TARGET_BROKER_TICK_WATCHER', 'target_broker_tick_watcher'),
            ('USE_IMPROVED_WATCHERS', 'use_improved_watchers'),
            ('AUTO_ENABLE_WATCHERS', 'auto_enable_watchers'),
            ('ENABLED_WATCHERS', 'enabled_watchers'),
            ('WATCHER_UPDATE_FREQ', 'update_freq'),
            ('WATCHER_LOOKBACK', 'lookback'),
            ('EARLY_EXIT_MOMENTUM_THRESHOLD', 'early_exit_momentum_threshold'),
            ('EARLY_EXIT_TREND_CONFIDENCE_THRESHOLD', 'early_exit_trend_confidence_threshold'),
            ('EARLY_EXIT_VOLATILITY_THRESHOLD', 'early_exit_volatility_threshold')
        ]:
            if env_key in self.env_vars:
                if config_attr.endswith('_enabled') or config_attr in ['use_improved_watchers', 'auto_enable_watchers']:
                    # Convert string to boolean
                    watcher_data[config_attr] = self.env_vars[env_key].lower() in ('true', '1', 'yes', 'on')
                elif config_attr.endswith('_seconds') or config_attr.endswith('_minutes') or config_attr.endswith('_period') or config_attr.endswith('_freq') or config_attr.endswith('_lookback'):
                    # Convert string to integer
                    watcher_data[config_attr] = int(self.env_vars[env_key])
                elif config_attr.endswith('_threshold') or config_attr.endswith('_weight') or config_attr.endswith('_boost') or config_attr.endswith('_factor'):
                    # Convert string to float
                    watcher_data[config_attr] = float(self.env_vars[env_key])
                elif config_attr == 'enabled_watchers':
                    # Convert comma-separated string to list
                    watcher_data[config_attr] = [item.strip() for item in self.env_vars[env_key].split(',')]
                else:
                    watcher_data[config_attr] = self.env_vars[env_key]
        config_objects['watcher'] = WatcherConfig(**watcher_data)

        # Portfolio configuration
        portfolio_data = self.profile_config.get("portfolio", {}).dict()
        # Add portfolio env vars if they exist
        for env_key, config_attr in [
            ('REBALANCE_FREQUENCY', 'rebalance_frequency'),
            ('CORRELATION_CONSENSUS_WEIGHT', 'correlation_consensus_weight'),
            ('CORRELATION_CONFIDENCE_WEIGHT', 'correlation_confidence_weight'),
            ('CORRELATION_BASE_PERCENTAGE', 'correlation_base_percentage'),
            ('CORRELATION_DEFAULT_PERCENTAGE', 'correlation_default_percentage'),
            ('CORRELATION_DIVERSIFICATION_FACTOR', 'correlation_diversification_factor'),
            ('CORRELATION_MAX_CORRELATION', 'correlation_max_correlation'),
            ('CORRELATION_PORTFOLIO_IMPACT_THRESHOLD', 'correlation_portfolio_impact_threshold')
        ]:
            if env_key in self.env_vars:
                # Convert string to float
                portfolio_data[config_attr] = float(self.env_vars[env_key]) if config_attr not in ['rebalance_frequency'] else self.env_vars[env_key]
        config_objects['portfolio'] = PortfolioConfig(**portfolio_data)

        # Backtest configuration
        backtest_data = self.profile_config.get("backtest", {}).dict()
        # Add backtest env vars if they exist
        for env_key, config_attr in [
            ('BACKTEST_INITIAL_CAPITAL', 'initial_capital'),
            ('BACKTEST_FEE_RATE', 'fee_rate'),
            ('BACKTEST_SLIPPAGE_FACTOR', 'slippage_factor'),
            ('BACKTEST_RISK_PER_TRADE', 'risk_per_trade'),
            ('BACKTEST_END_DATE', 'end_date'),
            ('BACKTEST_START_DATE', 'start_date'),
            ('BENCHMARK_SYMBOL', 'benchmark_symbol'),
            ('COMMISSION_RATE', 'commission_rate')
        ]:
            if env_key in self.env_vars:
                if config_attr in ['end_date', 'start_date', 'benchmark_symbol']:
                    backtest_data[config_attr] = self.env_vars[env_key]
                else:
                    # Convert string to float
                    backtest_data[config_attr] = float(self.env_vars[env_key])
        config_objects['backtest'] = BacktestConfig(**backtest_data)

        return config_objects
    
    def get_env_var(self, key: str, default: str = None) -> str:
        """
        Get an environment variable value.
        
        Args:
            key: Environment variable key
            default: Default value if key is not found
            
        Returns:
            Value of the environment variable or default
        """
        return self.env_loader.get_env_var(key, default)
    
    def get_required_env_var(self, key: str) -> str:
        """
        Get a required environment variable value. Raises exception if not found.
        
        Args:
            key: Environment variable key
            
        Returns:
            Value of the environment variable
        """
        return self.env_loader.get_required_env_var(key)