"""
YouTube Music API integration.
"""

from typing import Dict, List, Optional, Any
from pathlib import Path

# Optional YouTube Music API
try:
    from ytmusicapi import YTMusic
    from ytmusicapi.exceptions import YTMusicServerError
    HAVE_YTMUSIC = True
except ImportError:
    HAVE_YTMUSIC = False

from ..core.models import Track


class YouTubeMusicAPI:
    """YouTube Music API integration wrapper."""
    
    def __init__(self, headers_file: Optional[str] = None):
        self.ytmusic = None
        self.headers_file = headers_file
        
        if HAVE_YTMUSIC and headers_file and Path(headers_file).exists():
            try:
                self.ytmusic = YTMusic(headers_file)
            except Exception as e:
                print(f"Failed to initialize YouTube Music: {e}")
    
    def is_available(self) -> bool:
        """Check if YouTube Music functionality is available."""
        return self.ytmusic is not None
    
    def search_track(self, track: Track, limit: int = 5) -> List[Dict[str, Any]]:
        """Search for a track on YouTube Music."""
        if not self.is_available():
            return []
        
        try:
            # Build search query
            query_parts = [track.title, track.artist]
            if track.album:
                query_parts.append(track.album)
            
            query = " ".join(query_parts)
            
            # Search for songs
            results = self.ytmusic.search(query, filter="songs", limit=limit)
            
            return results
        
        except Exception as e:
            print(f"Error searching for track: {e}")
            return []
    
    def get_library(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """Get user's YouTube Music library."""
        if not self.is_available():
            return []
        
        try:
            # Get liked songs and uploaded songs
            library_tracks = []
            
            # Get liked songs
            try:
                liked = self.ytmusic.get_liked_songs(limit=limit)
                if liked and 'tracks' in liked:
                    library_tracks.extend(liked['tracks'])
            except Exception as e:
                print(f"Error getting liked songs: {e}")
            
            # Get uploaded songs
            try:
                uploaded = self.ytmusic.get_library_upload_songs(limit=limit)
                if uploaded:
                    library_tracks.extend(uploaded)
            except Exception as e:
                print(f"Error getting uploaded songs: {e}")
            
            return library_tracks
        
        except Exception as e:
            print(f"Error getting library: {e}")
            return []
    
    def create_playlist(self, title: str, description: str = "") -> Optional[str]:
        """Create a new playlist and return its ID."""
        if not self.is_available():
            return None
        
        try:
            response = self.ytmusic.create_playlist(title=title, description=description)
            if isinstance(response, dict):
                return response.get('id') or response.get('playlistId')
            elif isinstance(response, str):
                return response
            return None
        
        except Exception as e:
            print(f"Error creating playlist: {e}")
            return None
    
    def add_songs_to_playlist(self, playlist_id: str, video_ids: List[str]) -> bool:
        """Add songs to a playlist."""
        if not self.is_available():
            return False
        
        try:
            self.ytmusic.add_playlist_items(playlist_id, video_ids)
            return True
        
        except Exception as e:
            print(f"Error adding songs to playlist: {e}")
            return False