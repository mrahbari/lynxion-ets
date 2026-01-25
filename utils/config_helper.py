"""
Configuration Helper Utilities

Provides convenient functions for accessing configuration values through the Configs system
with proper fallback handling.
"""
from typing import Any, Optional, Union
from application.configs.configs import Configs


def cfg_get(config_obj: Any, attr_name: str, default: Any = None) -> Any:
    """
    Get a configuration attribute with fallback to default value.
    
    Args:
        config_obj: Configuration object (e.g., Configs.broker, Configs.risk)
        attr_name: Attribute name to retrieve
        default: Default value if attribute doesn't exist or config_obj is None
    
    Returns:
        Value of the attribute or default value
    """
    if config_obj is None:
        return default
    
    return getattr(config_obj, attr_name, default)


def cfg_get_bool(config_obj: Any, attr_name: str, default: bool = False) -> bool:
    """
    Get a boolean configuration attribute with fallback to default value.
    
    Args:
        config_obj: Configuration object (e.g., Configs.broker, Configs.risk)
        attr_name: Attribute name to retrieve
        default: Default value if attribute doesn't exist or config_obj is None
    
    Returns:
        Boolean value of the attribute or default value
    """
    if config_obj is None:
        return default
    
    value = getattr(config_obj, attr_name, default)
    if isinstance(value, bool):
        return value
    elif isinstance(value, str):
        return value.lower() in ('true', '1', 'yes', 'on')
    elif isinstance(value, (int, float)):
        return bool(value)
    else:
        return bool(value)


def cfg_get_int(config_obj: Any, attr_name: str, default: int = 0) -> int:
    """
    Get an integer configuration attribute with fallback to default value.
    
    Args:
        config_obj: Configuration object (e.g., Configs.broker, Configs.risk)
        attr_name: Attribute name to retrieve
        default: Default value if attribute doesn't exist or config_obj is None
    
    Returns:
        Integer value of the attribute or default value
    """
    if config_obj is None:
        return default
    
    value = getattr(config_obj, attr_name, default)
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def cfg_get_float(config_obj: Any, attr_name: str, default: float = 0.0) -> float:
    """
    Get a float configuration attribute with fallback to default value.
    
    Args:
        config_obj: Configuration object (e.g., Configs.broker, Configs.risk)
        attr_name: Attribute name to retrieve
        default: Default value if attribute doesn't exist or config_obj is None
    
    Returns:
        Float value of the attribute or default value
    """
    if config_obj is None:
        return default
    
    value = getattr(config_obj, attr_name, default)
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def cfg_get_list(config_obj: Any, attr_name: str, default: list = None, delimiter: str = ',') -> list:
    """
    Get a list configuration attribute with fallback to default value.
    
    Args:
        config_obj: Configuration object (e.g., Configs.broker, Configs.risk)
        attr_name: Attribute name to retrieve
        default: Default value if attribute doesn't exist or config_obj is None
        delimiter: Delimiter to split the value on (default: ',')
    
    Returns:
        List value of the attribute or default value
    """
    if default is None:
        default = []
        
    if config_obj is None:
        return default
    
    value = getattr(config_obj, attr_name, None)
    if value is None:
        return default
    
    if isinstance(value, list):
        return value
    elif isinstance(value, str):
        return [item.strip() for item in value.split(delimiter) if item.strip()]
    else:
        return default


def cfg_get_str(config_obj: Any, attr_name: str, default: str = "") -> str:
    """
    Get a string configuration attribute with fallback to default value.
    
    Args:
        config_obj: Configuration object (e.g., Configs.broker, Configs.risk)
        attr_name: Attribute name to retrieve
        default: Default value if attribute doesn't exist or config_obj is None
    
    Returns:
        String value of the attribute or default value
    """
    if config_obj is None:
        return default
    
    value = getattr(config_obj, attr_name, default)
    if value is None:
        return default
    return str(value)