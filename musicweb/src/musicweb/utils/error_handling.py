"""
Professional error handling utilities for MusicWeb.

Provides custom exceptions, error reporting, and user-friendly error messages.
"""

import traceback
import sys
from typing import Dict, Any, Optional, Callable, Type
from functools import wraps
import logging
from enum import Enum

from .logging_config import get_logger

logger = get_logger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class MusicWebError(Exception):
    """Base exception for MusicWeb application."""
    
    def __init__(
        self, 
        message: str, 
        error_code: str = None,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        user_message: str = None,
        context: Dict[str, Any] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.severity = severity
        self.user_message = user_message or self._get_user_friendly_message()
        self.context = context or {}
        
    def _get_user_friendly_message(self) -> str:
        """Get user-friendly error message."""
        return "An error occurred while processing your request. Please try again."
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for logging/API responses."""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "user_message": self.user_message,
            "severity": self.severity.value,
            "context": self.context,
            "type": self.__class__.__name__
        }


class ValidationError(MusicWebError):
    """Raised when input validation fails."""
    
    def __init__(self, field: str, value: Any, message: str = None):
        self.field = field
        self.value = value
        error_message = message or f"Invalid value for {field}: {value}"
        super().__init__(
            error_message,
            error_code="VALIDATION_ERROR",
            severity=ErrorSeverity.LOW,
            context={"field": field, "value": str(value)}
        )
    
    def _get_user_friendly_message(self) -> str:
        return f"Please check the value for {self.field} and try again."


class FileProcessingError(MusicWebError):
    """Raised when file processing fails."""
    
    def __init__(self, file_path: str, operation: str, original_error: Exception = None):
        self.file_path = file_path
        self.operation = operation
        self.original_error = original_error
        
        message = f"Failed to {operation} file: {file_path}"
        if original_error:
            message += f" - {str(original_error)}"
            
        super().__init__(
            message,
            error_code="FILE_PROCESSING_ERROR",
            severity=ErrorSeverity.MEDIUM,
            context={
                "file_path": file_path,
                "operation": operation,
                "original_error": str(original_error) if original_error else None
            }
        )
    
    def _get_user_friendly_message(self) -> str:
        return f"Unable to process the file. Please check that the file is valid and try again."


class PlatformError(MusicWebError):
    """Raised when platform integration fails."""
    
    def __init__(self, platform: str, operation: str, original_error: Exception = None):
        self.platform = platform
        self.operation = operation
        self.original_error = original_error
        
        message = f"{platform} {operation} failed"
        if original_error:
            message += f": {str(original_error)}"
            
        super().__init__(
            message,
            error_code="PLATFORM_ERROR",
            severity=ErrorSeverity.HIGH,
            context={
                "platform": platform,
                "operation": operation,
                "original_error": str(original_error) if original_error else None
            }
        )
    
    def _get_user_friendly_message(self) -> str:
        return f"There was an issue connecting to {self.platform}. Please check your credentials and try again."


class ConfigurationError(MusicWebError):
    """Raised when configuration is invalid."""
    
    def __init__(self, setting: str, value: Any = None, message: str = None):
        self.setting = setting
        self.value = value
        
        error_message = message or f"Invalid configuration for {setting}"
        if value is not None:
            error_message += f": {value}"
            
        super().__init__(
            error_message,
            error_code="CONFIGURATION_ERROR",
            severity=ErrorSeverity.HIGH,
            context={"setting": setting, "value": str(value) if value else None}
        )
    
    def _get_user_friendly_message(self) -> str:
        return f"Please check your configuration settings and try again."


class DataProcessingError(MusicWebError):
    """Raised when data processing fails."""
    
    def __init__(self, operation: str, data_type: str = None, original_error: Exception = None):
        self.operation = operation
        self.data_type = data_type
        self.original_error = original_error
        
        message = f"Data processing failed during {operation}"
        if data_type:
            message += f" for {data_type}"
        if original_error:
            message += f": {str(original_error)}"
            
        super().__init__(
            message,
            error_code="DATA_PROCESSING_ERROR",
            severity=ErrorSeverity.MEDIUM,
            context={
                "operation": operation,
                "data_type": data_type,
                "original_error": str(original_error) if original_error else None
            }
        )
    
    def _get_user_friendly_message(self) -> str:
        return "There was an issue processing your data. Please check the format and try again."


def handle_errors(
    default_return=None,
    reraise: bool = True,
    log_error: bool = True,
    error_mapping: Dict[Type[Exception], Type[MusicWebError]] = None
):
    """
    Decorator for consistent error handling.
    
    Args:
        default_return: Value to return if error occurs and reraise=False
        reraise: Whether to reraise the exception after handling
        log_error: Whether to log the error
        error_mapping: Map standard exceptions to custom exceptions
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except MusicWebError:
                # Already a MusicWeb error, just reraise
                if log_error:
                    logger.error(f"Error in {func.__name__}", exc_info=True)
                if reraise:
                    raise
                return default_return
            except Exception as e:
                # Convert to MusicWeb error if mapping exists
                if error_mapping and type(e) in error_mapping:
                    mapped_error = error_mapping[type(e)](
                        f"Error in {func.__name__}: {str(e)}",
                        original_error=e
                    )
                    if log_error:
                        logger.error(
                            f"Error in {func.__name__}: {mapped_error.to_dict()}",
                            exc_info=True
                        )
                    if reraise:
                        raise mapped_error
                    return default_return
                
                # Generic error handling
                if log_error:
                    logger.error(f"Unexpected error in {func.__name__}: {str(e)}", exc_info=True)
                
                if reraise:
                    # Wrap in generic MusicWeb error
                    raise MusicWebError(
                        f"Unexpected error in {func.__name__}: {str(e)}",
                        error_code="UNEXPECTED_ERROR",
                        severity=ErrorSeverity.HIGH,
                        context={"function": func.__name__, "original_error": str(e)}
                    )
                
                return default_return
        return wrapper
    return decorator


def safe_execute(
    func: Callable,
    *args,
    default_return=None,
    error_message: str = None,
    **kwargs
) -> Any:
    """
    Safely execute a function with error handling.
    
    Args:
        func: Function to execute
        *args: Arguments for the function
        default_return: Value to return on error
        error_message: Custom error message
        **kwargs: Keyword arguments for the function
        
    Returns:
        Function result or default_return on error
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        message = error_message or f"Error executing {func.__name__}"
        logger.error(f"{message}: {str(e)}", exc_info=True)
        return default_return


class ErrorReporter:
    """Central error reporting system."""
    
    def __init__(self):
        self.error_counts = {}
        self.logger = get_logger("error_reporter")
    
    def report_error(
        self, 
        error: Exception, 
        context: Dict[str, Any] = None,
        user_id: str = None,
        session_id: str = None
    ):
        """Report an error with context information."""
        error_info = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context or {},
            "user_id": user_id,
            "session_id": session_id,
            "traceback": traceback.format_exc()
        }
        
        # Track error frequency
        error_key = f"{type(error).__name__}:{str(error)}"
        self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1
        error_info["error_count"] = self.error_counts[error_key]
        
        # Log with appropriate level based on error type
        if isinstance(error, MusicWebError):
            if error.severity == ErrorSeverity.CRITICAL:
                self.logger.critical("Critical error occurred", extra=error_info)
            elif error.severity == ErrorSeverity.HIGH:
                self.logger.error("High severity error occurred", extra=error_info)
            elif error.severity == ErrorSeverity.MEDIUM:
                self.logger.warning("Medium severity error occurred", extra=error_info)
            else:
                self.logger.info("Low severity error occurred", extra=error_info)
        else:
            self.logger.error("Unhandled exception occurred", extra=error_info)
    
    def get_error_stats(self) -> Dict[str, int]:
        """Get error frequency statistics."""
        return self.error_counts.copy()


# Global error reporter instance
error_reporter = ErrorReporter()


def setup_global_exception_handler():
    """Set up global exception handler for unhandled exceptions."""
    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            # Allow keyboard interrupts to work normally
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        
        logger.critical(
            "Unhandled exception occurred",
            exc_info=(exc_type, exc_value, exc_traceback)
        )
        error_reporter.report_error(exc_value)
    
    sys.excepthook = handle_exception


# Common error mapping for standard exceptions
STANDARD_ERROR_MAPPING = {
    FileNotFoundError: lambda e: FileProcessingError("unknown", "read", e),
    PermissionError: lambda e: FileProcessingError("unknown", "access", e),
    ValueError: lambda e: ValidationError("unknown", "unknown", str(e)),
    TypeError: lambda e: ValidationError("unknown", "unknown", str(e)),
    ConnectionError: lambda e: PlatformError("unknown", "connect", e),
    TimeoutError: lambda e: PlatformError("unknown", "timeout", e),
}