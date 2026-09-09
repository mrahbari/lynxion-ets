from types import SimpleNamespace


def _mixin_with_data_config(**values):
    from infrastructure.orchestrators._auto_detection_execution import (
        _AutoDetectionExecutionMixin,
    )

    mixin = _AutoDetectionExecutionMixin()
    mixin._settings = SimpleNamespace(data=SimpleNamespace(**values))
    return mixin


def test_execution_stablecoin_guard_reads_list_config_without_free_variables():
    mixin = _mixin_with_data_config(
        filter_out_stablecoin_pairs=True,
        allowed_stablecoins=["USDT", "USDC"],
    )

    enabled, stablecoins = mixin._stablecoin_filter_config()

    assert enabled is True
    assert stablecoins == {"USDT", "USDC"}


def test_execution_stablecoin_guard_normalizes_legacy_csv_config():
    mixin = _mixin_with_data_config(
        filter_out_stablecoin_pairs=False,
        allowed_stablecoins="USDT, usdc,",
    )

    enabled, stablecoins = mixin._stablecoin_filter_config()

    assert enabled is False
    assert stablecoins == {"USDT", "USDC"}
