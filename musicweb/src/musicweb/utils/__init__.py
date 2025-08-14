"""
Utility functions for MusicWeb.

This module contains common utilities for file handling,
validation, logging, and other cross-cutting concerns.
"""

from .file_utils import detect_encoding, validate_file_size, get_file_info
from .validation import validate_track_data, validate_library_data
from .logging import setup_logging, get_logger

__all__ = [
    "detect_encoding",
    "validate_file_size", 
    "get_file_info",
    "validate_track_data",
    "validate_library_data",
    "setup_logging",
    "get_logger"
]