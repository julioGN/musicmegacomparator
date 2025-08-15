"""
Professional logging configuration for MusicWeb.

Provides structured logging with proper formatting, rotation, and levels
for production deployment.
"""

import logging
import logging.handlers
import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any
import json
from datetime import datetime


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
            
        # Add extra fields if present
        if hasattr(record, 'user_id'):
            log_entry["user_id"] = record.user_id
        if hasattr(record, 'session_id'):
            log_entry["session_id"] = record.session_id
        if hasattr(record, 'operation'):
            log_entry["operation"] = record.operation
            
        return json.dumps(log_entry, default=str)


class ColoredFormatter(logging.Formatter):
    """Colored formatter for console output."""
    
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors."""
        log_color = self.COLORS.get(record.levelname, '')
        record.levelname = f"{log_color}{record.levelname}{self.RESET}"
        return super().format(record)


def setup_logging(
    app_name: str = "musicweb",
    log_level: str = "INFO",
    log_dir: Optional[Path] = None,
    enable_json: bool = False,
    enable_console: bool = True,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
) -> logging.Logger:
    """
    Set up professional logging configuration.
    
    Args:
        app_name: Name of the application
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory for log files (defaults to logs/)
        enable_json: Whether to use JSON formatting for files
        enable_console: Whether to enable console logging
        max_bytes: Maximum size of log files before rotation
        backup_count: Number of backup files to keep
        
    Returns:
        Configured logger instance
    """
    # Create logs directory
    if log_dir is None:
        log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Get or create logger
    logger = logging.getLogger(app_name)
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # File handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        log_dir / f"{app_name}.log",
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    
    if enable_json:
        file_formatter = JSONFormatter()
    else:
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(funcName)s:%(lineno)d - %(message)s'
        )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    # Error file handler (separate file for errors)
    error_handler = logging.handlers.RotatingFileHandler(
        log_dir / f"{app_name}_errors.log",
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(file_formatter)
    logger.addHandler(error_handler)
    
    # Console handler
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        if os.getenv('COLORIZE_LOGS', 'true').lower() == 'true':
            console_formatter = ColoredFormatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        else:
            console_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
    
    # Set up third-party library logging levels
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('streamlit').setLevel(logging.WARNING)
    
    logger.info(f"Logging configured for {app_name} at level {log_level}")
    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a specific module."""
    return logging.getLogger(f"musicweb.{name}")


def log_operation(operation: str):
    """Decorator to log function operations."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            logger = get_logger(func.__module__)
            start_time = datetime.now()
            
            try:
                logger.info(f"Starting operation: {operation}")
                result = func(*args, **kwargs)
                duration = (datetime.now() - start_time).total_seconds()
                logger.info(f"Completed operation: {operation} in {duration:.2f}s")
                return result
            except Exception as e:
                duration = (datetime.now() - start_time).total_seconds()
                logger.error(
                    f"Failed operation: {operation} after {duration:.2f}s - {str(e)}",
                    exc_info=True
                )
                raise
                
        return wrapper
    return decorator


def log_performance(func):
    """Decorator to log function performance metrics."""
    def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        start_time = datetime.now()
        
        result = func(*args, **kwargs)
        
        duration = (datetime.now() - start_time).total_seconds()
        logger.debug(f"Performance: {func.__name__} executed in {duration:.3f}s")
        
        return result
    return wrapper


class ContextLogger:
    """Context manager for logging with additional context."""
    
    def __init__(self, logger: logging.Logger, **context):
        self.logger = logger
        self.context = context
        
    def __enter__(self):
        # Add context to logger
        for key, value in self.context.items():
            setattr(self.logger, key, value)
        return self.logger
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Remove context from logger
        for key in self.context.keys():
            if hasattr(self.logger, key):
                delattr(self.logger, key)


# Environment-specific configuration
def configure_for_environment(env: str = None) -> Dict[str, Any]:
    """Get logging configuration for specific environment."""
    if env is None:
        env = os.getenv('ENVIRONMENT', 'development')
    
    configs = {
        'development': {
            'log_level': 'DEBUG',
            'enable_json': False,
            'enable_console': True,
        },
        'testing': {
            'log_level': 'WARNING',
            'enable_json': False,
            'enable_console': False,
        },
        'production': {
            'log_level': 'INFO',
            'enable_json': True,
            'enable_console': False,
        },
        'staging': {
            'log_level': 'INFO',
            'enable_json': True,
            'enable_console': True,
        }
    }
    
    return configs.get(env, configs['development'])


# Initialize default logger for the package
DEFAULT_CONFIG = configure_for_environment()
default_logger = setup_logging(**DEFAULT_CONFIG)