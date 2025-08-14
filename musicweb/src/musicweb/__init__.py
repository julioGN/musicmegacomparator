"""
MusicWeb - Professional Music Library Management Suite

A comprehensive tool for comparing, analyzing, and managing music libraries
across multiple streaming platforms including Spotify, Apple Music, and YouTube Music.
"""

__version__ = "1.0.0"
__author__ = "MusicWeb Team"
__email__ = "contact@musicweb.app"

# Core imports for easy access
from .core.models import Track, Library
from .core.comparison import LibraryComparator
from .platforms.detection import detect_platform
from .platforms import create_parser

__all__ = [
    "Track",
    "Library", 
    "LibraryComparator",
    "detect_platform",
    "create_parser",
    "__version__"
]
