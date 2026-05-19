import os
from dotenv import load_dotenv
from typing import Dict, Any, Optional, Union
import logging


class EnvLoader:
    """
    Singleton class responsible for loading environment variables from .env file.
    This is the ONLY place where .env files are accessed in the entire application.
    """

    _instance = None
    _loaded = False
    _env_vars: Dict[str, str] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EnvLoader, cls).__new__(cls)
        return cls._instance

    def load(self, env_file_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Load environment variables from .env file.

        Args:
            env_file_path: Optional path to .env file. If not provided, looks for .env in current directory

        Returns:
            Dictionary of loaded environment variables

        Raises:
            FileNotFoundError: If .env file is not found and no environment variables are set
            RuntimeError: If environment variables are accessed after initial load
        """
        if self._loaded:
            # Return cached environment variables if already loaded
            return self._env_vars.copy()

        # Load .env file if path provided or look for default .env
        if env_file_path:
            load_dotenv(dotenv_path=env_file_path, override=False)
        else:
            load_dotenv(override=False)  # Only load if not already present

        # Capture all environment variables that are relevant to our application
        for key, value in os.environ.items():
            if any(key.startswith(prefix) for prefix in [
                'APP_', 'BROKER_', 'RISK_', 'STRATEGY_', 'EXECUTION_',
                'SAFETY_', 'DATA_', 'OPTIMIZATION_', 'MONITORING_',
                'WATCHER_', 'WFO_', 'CMC_', 'BINANCE_', 'BINGX_', 'MEXC_', 'PHEMEX_',
                'TELEGRAM_', 'BACKTEST_', 'LOG_', 'PERFORMANCE_', 'SAFETY_',
                'SYNC_', 'FIXED_', 'KELLY_', 'MARTINGALE_', 'OPTIMAL_',
                'CORRELATION_', 'FUSION_', 'HYPEROPT_', 'ENGINE_', 'ANOMALY_',
                'VOLATILITY_', 'TREND_', 'ORDERFLOW_', 'LIQUIDITY_', 'FUNDING_',
                'HISTORICAL_', 'TICK_', 'TARGET_', 'USE_', 'AUTO_', 'ENABLE_',
                'MAX_', 'MIN_', 'DEFAULT_', 'API_', 'CACHE_', 'RESULTS_',
                'CSV_', 'TEMP_', 'RATE_', 'RETRY_', 'WORKERS_', 'POSITION_',
                'PORTFOLIO_', 'REBALANCE_', 'TARGET_', 'SLIPPAGE_', 'FEE_',
                'COMMISSION_', 'EDGE_', 'WIN_', 'REWARD_', 'RISK_', 'CONFIDENCE_',
                'VOLATILITY_', 'ATR_', 'VAR_', 'ENVIRONMENT_', 'ENV_', 'WFO_',
                'SYNC_', 'DOWNLOAD_', 'UPLOAD_', 'TEMP_', 'DATA_', 'HISTORY_',
                'RAW_', 'PROCESSED_', 'RETENTION_', 'GAP_', 'EXCHANGE_', 'WINDOW_',
                'LIMIT_', 'TOKENS_', 'CONCURRENCY_', 'THREADPOOL_', 'BACKUP_',
                'SIZE_', 'COUNT_', 'INTERVAL_', 'FREQUENCY_', 'THRESHOLD_', 'WEIGHT_',
                'BOOST_', 'FACTOR_', 'MULTIPLIER_', 'RATIO_', 'PERCENTAGE_',
                'AMOUNT_', 'QUANTITY_', 'CAP_', 'EXPOSURE_', 'CONCENTRATION_',
                'DRAWDOWN_', 'LEVERAGE_', 'ORDER_', 'TRADE_', 'SYMBOL_', 'PAIR_',
                'COIN_', 'ASSET_', 'MARKET_', 'CATEGORY_', 'TYPE_', 'METHOD_',
                'ALGORITHM_', 'OBJECTIVE_', 'SPLIT_', 'EVALS_', 'ROUNDS_',
                'PASS_', 'RATE_', 'IMPACT_', 'BONUS_', 'PENALTY_', 'OFFSET_',
                'INDEX_', 'ID_', 'KEY_', 'SECRET_', 'TOKEN_', 'URL_', 'PATH_',
                'DIR_', 'FILE_', 'NAME_', 'TITLE_', 'DESCRIPTION_', 'CODE_',
                'NUMBER_', 'VALUE_', 'SETTING_', 'CONFIG_', 'PARAMETER_', 'OPTION_',
                'FLAG_', 'MODE_', 'STATE_', 'STATUS_', 'ACTIVE_', 'INACTIVE_',
                'ON_', 'OFF_', 'TRUE_', 'FALSE_', 'YES_', 'NO_', 'ENABLE_',
                'DISABLE_', 'START_', 'STOP_', 'PAUSE_', 'RESUME_', 'RESET_',
                'CLEAR_', 'UPDATE_', 'REFRESH_', 'SYNC_', 'ASYNC_', 'BLOCKING_',
                'NON_BLOCKING_', 'SINGLE_', 'MULTI_', 'BATCH_', 'STREAM_',
                'QUEUE_', 'TOPIC_', 'CHANNEL_', 'ENDPOINT_', 'HOST_', 'PORT_',
                'TIMEOUT_', 'RETRY_', 'ATTEMPT_', 'SUCCESS_', 'FAILURE_',
                'ERROR_', 'WARNING_', 'INFO_', 'DEBUG_', 'TRACE_', 'LEVEL_',
                'FORMAT_', 'PATTERN_', 'MASK_', 'FILTER_', 'INCLUDE_', 'EXCLUDE_',
                'WHITELIST_', 'BLACKLIST_', 'ALLOWED_', 'DENIED_', 'RESTRICTED_',
                'PUBLIC_', 'PRIVATE_', 'INTERNAL_', 'EXTERNAL_', 'LOCAL_',
                'REMOTE_', 'GLOBAL_', 'REGIONAL_', 'NATIONAL_', 'INTERNATIONAL_',
                'COUNTRY_', 'CITY_', 'ADDRESS_', 'LOCATION_', 'COORDINATES_',
                'LATITUDE_', 'LONGITUDE_', 'ALTITUDE_', 'DISTANCE_', 'SPEED_',
                'ACCELERATION_', 'MASS_', 'VOLUME_', 'DENSITY_', 'PRESSURE_',
                'TEMPERATURE_', 'HUMIDITY_', 'LIGHT_', 'SOUND_', 'VIBRATION_',
                'COLOR_', 'SHAPE_', 'SIZE_', 'WEIGHT_', 'DURATION_', 'FREQUENCY_',
                'AMPLITUDE_', 'PHASE_', 'WAVELENGTH_', 'FREQUENCY_', 'PERIOD_',
                'CYCLE_', 'OSCILLATION_', 'VARIANCE_', 'STD_DEV_', 'MEAN_',
                'MEDIAN_', 'MODE_', 'RANGE_', 'QUARTILE_', 'PERCENTILE_',
                'SKEWNESS_', 'KURTOSIS_', 'CORRELATION_', 'COVARIANCE_',
                'REGRESSION_', 'SLOPE_', 'INTERCEPT_', 'R_SQUARED_', 'P_VALUE_',
                'T_STATISTIC_', 'Z_SCORE_', 'CHI_SQUARE_', 'F_STATISTIC_',
                'ANOVA_', 'T_TEST_', 'CHI_TEST_', 'F_TEST_', 'KS_TEST_',
                'AD_TEST_', 'JB_TEST_', 'PP_TEST_', 'ADF_TEST_', 'KPSS_TEST_',
                'ARCH_', 'GARCH_', 'EGARCH_', 'GJR_GARCH_', 'APARCH_', 'FIGARCH_',
                'HARCH_', 'MS_GARCH_', 'NGARCH_', 'NIGARCH_', 'TGARCH_',
                'AVGARCH_', 'CVGARCH_', 'DCC_GARCH_', 'GO_GARCH_', 'OGARCH_',
                'PCA_', 'FACTOR_', 'ICA_', 'CCA_', 'PLS_', 'PCR_', 'RIDGE_',
                'LASSO_', 'ELASTIC_NET_', 'POLYNOMIAL_', 'SPLINE_', 'KERNEL_',
                'SVM_', 'RANDOM_FOREST_', 'GRADIENT_BOOSTING_', 'XGBOOST_',
                'LIGHTGBM_', 'CATBOOST_', 'LINEAR_', 'LOGISTIC_', 'NAIVE_BAYES_',
                'KNN_', 'DECISION_TREE_', 'NEURAL_NETWORK_', 'CNN_', 'RNN_',
                'LSTM_', 'GRU_', 'TRANSFORMER_', 'BERT_', 'GPT_', 'T5_',
                'UNET_', 'RESNET_', 'VGG_', 'INCEPTION_', 'MOBILENET_',
                'EFFICIENTNET_', 'YOLO_', 'RCNN_', 'SSD_', 'FAST_RCNN_',
                'MASK_RCNN_', 'GENERATIVE_ADVERSARIAL_', 'VAE_', 'AE_',
                'AUTOENCODER_', 'VARIATIONAL_', 'DIFFUSION_', 'FLOW_',
                'NORMALIZING_FLOW_', 'NF_', 'GAN_', 'DQN_', 'A2C_', 'PPO_',
                'SAC_', 'TD3_', 'DDPG_', 'REINFORCE_', 'Q_LEARNING_',
                'SARSA_', 'EXPECTED_SARSA_', 'DOUBLE_Q_LEARNING_',
                'DEEP_Q_LEARNING_', 'DEEP_REINFORCE_', 'ACTOR_CRITIC_',
                'POLICY_GRADIENT_', 'VALUE_ITERATION_', 'POLICY_ITERATION_',
                'MONTE_CARLO_', 'TEMPORAL_DIFFERENCE_', 'SARSA_LAMBDA_',
                'Q_LAMBDA_', 'TRUE_ONLINE_SARSA_LAMBDA_', 'ROYAL_SARSA_',
                'DOUBLE_EXPECTED_SARSA_', 'DEEP_EXPECTED_SARSA_',
                'DEEP_DOUBLE_Q_LEARNING_', 'DEEP_DOUBLE_EXPECTED_SARSA_'
            ]):
                self._env_vars[key] = value

        self._loaded = True
        return self._env_vars.copy()

    @staticmethod
    def get_env_var(key: str, default: Optional[str] = None) -> Optional[str]:
        """
        Get an environment variable value.

        Args:
            key: Environment variable key
            default: Default value if key is not found

        Returns:
            Value of the environment variable or default
        """
        loader = EnvLoader()
        if not loader._loaded:
            # Load environment if not already loaded (using default location)
            loader.load()
        
        return loader._env_vars.get(key, default)

    @staticmethod
    def get_required_env_var(key: str) -> str:
        """
        Get a required environment variable value. Raises exception if not found.

        Args:
            key: Environment variable key

        Returns:
            Value of the environment variable

        Raises:
            ValueError: If the environment variable is not set
        """
        value = EnvLoader.get_env_var(key)
        if value is None:
            raise ValueError(f"Required environment variable '{key}' is not set")
        return value

    @staticmethod
    def get_bool_env_var(key: str, default: bool = False) -> bool:
        """
        Get a boolean environment variable value.

        Args:
            key: Environment variable key
            default: Default value if key is not found

        Returns:
            Boolean value of the environment variable or default
        """
        value = EnvLoader.get_env_var(key)
        if value is None:
            return default
        
        return value.lower() in ('true', '1', 'yes', 'on', 'enabled', 'active')

    @staticmethod
    def get_int_env_var(key: str, default: int = 0) -> int:
        """
        Get an integer environment variable value.

        Args:
            key: Environment variable key
            default: Default value if key is not found

        Returns:
            Integer value of the environment variable or default
        """
        value = EnvLoader.get_env_var(key)
        if value is None:
            return default
        
        try:
            return int(value)
        except ValueError:
            logging.warning(f"Could not convert environment variable '{key}'='{value}' to integer. Using default: {default}")
            return default

    @staticmethod
    def get_float_env_var(key: str, default: float = 0.0) -> float:
        """
        Get a float environment variable value.

        Args:
            key: Environment variable key
            default: Default value if key is not found

        Returns:
            Float value of the environment variable or default
        """
        value = EnvLoader.get_env_var(key)
        if value is None:
            return default
        
        try:
            return float(value)
        except ValueError:
            logging.warning(f"Could not convert environment variable '{key}'='{value}' to float. Using default: {default}")
            return default

    @staticmethod
    def get_list_env_var(key: str, default: list = None, delimiter: str = ',') -> list:
        """
        Get a list environment variable value.

        Args:
            key: Environment variable key
            default: Default value if key is not found
            delimiter: Delimiter to split the value on (default: ',')

        Returns:
            List value of the environment variable or default
        """
        if default is None:
            default = []
            
        value = EnvLoader.get_env_var(key)
        if value is None:
            return default
        
        return [item.strip() for item in value.split(delimiter)]