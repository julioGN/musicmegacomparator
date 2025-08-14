"""
Platform-specific parsers for different music streaming services.

This module provides parsers for extracting and normalizing music library data
from various streaming platforms including Spotify, Apple Music, and YouTube Music.
"""

from .base import BasePlatformParser
from .spotify import SpotifyParser
from .apple_music import AppleMusicParser, AppleMusicXMLParser
from .youtube_music import YouTubeMusicParser
from .detection import detect_platform

# Parser factory
def create_parser(platform: str) -> BasePlatformParser:
    """Factory function to create appropriate parser for the platform."""
    platform = platform.lower().replace('_', ' ').replace('-', ' ')
    
    if platform in ('apple music xml', 'apple xml', 'apple_music_xml', 'amxml'):
        return AppleMusicXMLParser()
    elif 'apple' in platform or platform == 'am':
        return AppleMusicParser()
    elif 'spotify' in platform:
        return SpotifyParser()
    elif 'youtube' in platform or 'ytm' in platform or platform == 'yt':
        return YouTubeMusicParser()
    else:
        raise ValueError(f"Unknown platform: {platform}")

__all__ = [
    "BasePlatformParser",
    "SpotifyParser", 
    "AppleMusicParser",
    "AppleMusicXMLParser",
    "YouTubeMusicParser",
    "detect_platform",
    "create_parser"
]