"""
MusicLib - Unified Music Library Management and Comparison

A comprehensive Python library for comparing and managing music libraries 
across multiple streaming platforms (Apple Music, Spotify, YouTube Music).

Features:
- Advanced fuzzy matching algorithms
- Cross-platform library comparison
- Playlist creation and management  
- Content filtering and normalization
- MusicBrainz enrichment
- Multiple interface options (CLI, Web, Streamlit)
"""

__version__ = "1.0.0"
__author__ = "Music Library Tools"

from .core import Track, Library, TrackMatcher
from .platforms import AppleMusicParser, SpotifyParser, YouTubeMusicParser, create_parser, detect_platform
from .comparison import LibraryComparator
from .playlist import PlaylistManager
from .enrichment import MusicBrainzEnricher, EnrichmentManager

__all__ = [
    'Track', 
    'Library', 
    'TrackMatcher',
    'AppleMusicParser', 
    'SpotifyParser', 
    'YouTubeMusicParser',
    'create_parser',
    'detect_platform',
    'LibraryComparator',
    'PlaylistManager',
    'MusicBrainzEnricher',
    'EnrichmentManager'
]