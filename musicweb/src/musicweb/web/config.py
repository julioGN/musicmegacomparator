"""
Web application configuration.
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class WebConfig:
    """Configuration settings for the web application."""
    
    # App settings
    app_title: str = "🎵 MusicWeb - Professional Music Library Management"
    app_description: str = "Compare, analyze, and manage music libraries across platforms"
    
    # UI settings
    page_icon: str = "🎵"
    layout: str = "wide"
    initial_sidebar_state: str = "expanded"
    
    # File upload settings
    max_file_size_mb: int = 100
    supported_formats: list = None
    
    # API settings
    youtube_music_headers_file: Optional[str] = None
    musicbrainz_rate_limit: float = 1.2  # seconds between requests
    
    # Performance settings
    cache_ttl: int = 3600  # 1 hour
    max_library_size: int = 50000  # tracks
    
    def __post_init__(self):
        if self.supported_formats is None:
            self.supported_formats = ['csv', 'json', 'xml']
        
        # Load from environment variables
        self.youtube_music_headers_file = os.getenv('YOUTUBE_MUSIC_HEADERS_FILE')
        
        # Override from environment
        if os.getenv('MAX_FILE_SIZE_MB'):
            self.max_file_size_mb = int(os.getenv('MAX_FILE_SIZE_MB'))
        
        if os.getenv('CACHE_TTL'):
            self.cache_ttl = int(os.getenv('CACHE_TTL'))


# Global config instance
config = WebConfig()