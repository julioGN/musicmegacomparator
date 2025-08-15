"""
MusicWeb - Professional Music Library Management Suite

A comprehensive tool for comparing, analyzing, and managing music libraries
across multiple streaming platforms including Spotify, Apple Music, and YouTube Music.
"""

__version__ = "1.0.0"
__author__ = "MusicWeb Team"
__email__ = "contact@musicweb.app"
__license__ = "MIT"
__description__ = "Professional Music Library Management Suite"

# Import main classes for easy access
from .core.models import Track, Library
from .core.comparison import LibraryComparator
from .platforms import create_parser
from .platforms.detection import detect_platform

# Try to import optional utilities
try:
    from .utils.logging_config import get_logger, setup_logging
except ImportError:
    get_logger = None
    setup_logging = None

try:
    from .utils.error_handling import MusicWebError
except ImportError:
    MusicWebError = Exception

# Package metadata
__all__ = [
    "__version__",
    "__author__",
    "__email__",
    "__license__",
    "__description__",
    "Track",
    "Library", 
    "LibraryComparator",
    "create_parser",
    "detect_platform",
    "get_logger",
    "setup_logging",
    "MusicWebError",
]

# Configure default logging for the package if available
if setup_logging:
    try:
        logger = setup_logging("musicweb")
        logger.info(f"MusicWeb v{__version__} initialized")
    except Exception:
        # Fallback if logging setup fails
        pass
