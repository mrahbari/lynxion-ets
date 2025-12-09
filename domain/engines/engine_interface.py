"""
Domain interfaces for engine operations in the enterprise hedge fund trading system.
This provides an alternative engine interface for engines that process raw data directly,
as opposed to the EnginePort which processes signals in the hexagonal architecture.
"""
from abc import abstractmethod
from typing import Protocol, Dict, Any
import pandas as pd
from domain.entities.engine_entities import EngineResult


class EngineInterface(Protocol):
    """
    Interface for engines that process raw market data directly and return EngineResult.
    This is an alternative to EnginePort that works at the data level rather than signal level.
    """

    @abstractmethod
    def compute(self, data: pd.DataFrame, context: Dict[str, Any] = None) -> EngineResult:
        """
        Compute an engine result based on market data
        Args:
            data: Market data in OHLCV format as a pandas DataFrame
            context: Additional context information for the computation
        Returns:
            EngineResult containing score and signal
        """
        pass

    @abstractmethod
    def validate_data(self, data: pd.DataFrame) -> bool:
        """
        Validate if the provided data is suitable for the engine
        Args:
            data: Market data to validate
        Returns:
            True if data is valid, False otherwise
        """
        pass