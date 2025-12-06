"""
Custom exceptions and error handling for the enterprise hedge fund trading system.
"""
from typing import Optional, Dict, Any
from enum import Enum
import traceback
from datetime import datetime


class TradingErrorType(Enum):
    """Enumeration of trading error types"""
    DATA_ERROR = "data_error"
    RISK_ERROR = "risk_error"
    EXECUTION_ERROR = "execution_error"
    CONNECTIVITY_ERROR = "connectivity_error"
    VALIDATION_ERROR = "validation_error"
    CONFIGURATION_ERROR = "configuration_error"
    SYSTEM_ERROR = "system_error"


class TradingException(Exception):
    """Base exception for the trading system"""
    
    def __init__(self, 
                 message: str, 
                 error_type: TradingErrorType,
                 details: Optional[Dict[str, Any]] = None,
                 original_exception: Optional[Exception] = None):
        super().__init__(message)
        self.message = message
        self.error_type = error_type
        self.details = details or {}
        self.original_exception = original_exception
        self.timestamp = datetime.now()
        self.traceback = traceback.format_exc() if original_exception else None

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for logging/serialization"""
        return {
            'error_type': self.error_type.value,
            'message': self.message,
            'details': self.details,
            'timestamp': self.timestamp.isoformat(),
            'has_original_exception': self.original_exception is not None,
            'traceback': self.traceback
        }


class DataException(TradingException):
    """Exception for data-related errors"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None, original_exception: Optional[Exception] = None):
        super().__init__(message, TradingErrorType.DATA_ERROR, details, original_exception)


class RiskException(TradingException):
    """Exception for risk-related errors"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None, original_exception: Optional[Exception] = None):
        super().__init__(message, TradingErrorType.RISK_ERROR, details, original_exception)


class ExecutionException(TradingException):
    """Exception for execution-related errors"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None, original_exception: Optional = None):
        super().__init__(message, TradingErrorType.EXECUTION_ERROR, details, original_exception)


class ConnectivityException(TradingException):
    """Exception for connectivity-related errors"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None, original_exception: Optional[Exception] = None):
        super().__init__(message, TradingErrorType.CONNECTIVITY_ERROR, details, original_exception)


class ValidationException(TradingException):
    """Exception for validation-related errors"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None, original_exception: Optional[Exception] = None):
        super().__init__(message, TradingErrorType.VALIDATION_ERROR, details, original_exception)


class ConfigurationException(TradingException):
    """Exception for configuration-related errors"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None, original_exception: Optional[Exception] = None):
        super().__init__(message, TradingErrorType.CONFIGURATION_ERROR, details, original_exception)


class SystemException(TradingException):
    """Exception for system-level errors"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None, original_exception: Optional[Exception] = None):
        super().__init__(message, TradingErrorType.SYSTEM_ERROR, details, original_exception)


class ErrorHandlingService:
    """Service to handle errors consistently across the system"""
    
    def __init__(self):
        self.error_handlers = {}
    
    def handle_error(self, 
                     exception: Exception, 
                     context: Optional[str] = None,
                     should_raise: bool = True) -> Dict[str, Any]:
        """Handle an exception and return error information"""
        
        # Convert to TradingException if needed
        if not isinstance(exception, TradingException):
            trading_exception = TradingException(
                message=f"Unexpected error in {context or 'unknown context'}: {str(exception)}",
                error_type=TradingErrorType.SYSTEM_ERROR,
                details={'context': context},
                original_exception=exception
            )
        else:
            trading_exception = exception
        
        # Log the error (would integrate with a proper logger)
        error_info = trading_exception.to_dict()
        error_info['context'] = context
        
        print(f"ERROR HANDLED [{trading_exception.error_type.value}]: {trading_exception.message}")
        if trading_exception.details:
            print(f"  DETAILS: {trading_exception.details}")
        
        if should_raise:
            raise trading_exception
        
        return error_info
    
    def register_error_handler(self, error_type: TradingErrorType, handler_func):
        """Register a custom error handler for specific error types"""
        self.error_handlers[error_type] = handler_func


# Global error handling service instance
error_service = ErrorHandlingService()