"""
External service integrations for MusicWeb.

This module provides integrations with external music services
including YouTube Music API, playlist management, and deduplication services.
"""

from .youtube_music import YouTubeMusicAPI
from .playlist import PlaylistManager
from .deduplication import DeduplicationService

__all__ = [
    "YouTubeMusicAPI",
    "PlaylistManager", 
    "DeduplicationService"
]