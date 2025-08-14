"""
Youtube Music parser for music library data.
"""

import json
import csv
import re
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import pandas as pd

from .base import BasePlatformParser
from ..core.models import Track, Library, TrackNormalizer

class YouTubeMusicParser(BasePlatformParser):
    """Parser for YouTube Music JSON/CSV exports."""
    
    COLUMN_MAPPINGS = {
        'title': ['title', 'song', 'track', 'name'],
        'artist': ['artist', 'artists', 'channel', 'uploader'],
        'album': ['album', 'playlist', 'release'],
        'duration': ['duration', 'length'],
        'track_id': ['id', 'video id', 'youtube id'],
        'url': ['url', 'link', 'video url']
    }
    
    def __init__(self):
        super().__init__("YouTube Music")
    
    def parse_file(self, file_path: str) -> Library:
        """Parse YouTube Music file (JSON or CSV)."""
        file_path = Path(file_path)
        library = Library(f"YouTube Music Library from {file_path.name}", "youtube_music")
        
        if file_path.suffix.lower() == '.json':
            return self._parse_json(file_path, library)
        else:
            return self._parse_csv(file_path, library)
    
    def _parse_json(self, file_path: Path, library: Library) -> Library:
        """Parse YouTube Music JSON export."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Handle different JSON structures
            tracks_data = data
            if isinstance(data, dict):
                # Look for tracks in common keys
                possible_keys = ['tracks', 'items', 'data', 'library', 'songs']
                for key in possible_keys:
                    if key in data and isinstance(data[key], list):
                        tracks_data = data[key]
                        break
            
            if not isinstance(tracks_data, list):
                tracks_data = [data] if isinstance(data, dict) else []
            
            for item in tracks_data:
                track = self._json_item_to_track(item)
                if track:
                    library.add_track(track)
        
        except Exception as e:
            print(f"Error parsing JSON file: {e}")
        
        return library
    
    def _parse_csv(self, file_path: Path, library: Library) -> Library:
        """Parse YouTube Music CSV export."""
        encoding = self._detect_encoding(str(file_path))
        
        try:
            df = pd.read_csv(file_path, encoding=encoding)
            
            column_map = self._map_columns(df.columns.tolist())
            df = df.rename(columns=column_map)
            
            for _, row in df.iterrows():
                track = self._csv_row_to_track(row)
                if track:
                    library.add_track(track)
        
        except Exception:
            # Manual parsing fallback
            library = self._parse_csv_manual(str(file_path), encoding, library)
        
        return library
    
    def _json_item_to_track(self, item: Dict[str, Any]) -> Optional[Track]:
        """Convert JSON item to Track object."""
        try:
            title = item.get('title') or item.get('name') or item.get('song', '')
            artist = item.get('artist') or item.get('channel') or item.get('uploader', '')
            
            if not title or not artist:
                return None
            
            # YouTube Music specific cleaning
            title = str(title).strip()
            artist = str(artist).strip()
            
            # Remove common YouTube artifacts
            title = re.sub(r'\s*\(Official\s+.*?\)', '', title, flags=re.IGNORECASE)
            title = re.sub(r'\s*\[Official\s+.*?\]', '', title, flags=re.IGNORECASE)
            
            album = item.get('album') or item.get('playlist')
            if album:
                album = str(album).strip()
            
            duration = self._parse_duration_json(item.get('duration'))
            track_id = item.get('id') or item.get('videoId') or item.get('video_id')
            url = item.get('url') or item.get('link')
            
            return Track(
                title=title,
                artist=artist,
                album=album,
                duration=duration,
                platform="youtube_music",
                track_id=str(track_id) if track_id else None,
                url=str(url) if url else None
            )
        
        except Exception:
            return None
    
    def _csv_row_to_track(self, row: pd.Series) -> Optional[Track]:
        """Convert CSV row to Track object."""
        try:
            title = str(row.get('title', '')).strip()
            artist = str(row.get('artist', '')).strip()
            
            if not title or not artist or title.lower() == 'nan' or artist.lower() == 'nan':
                return None
            
            # Clean YouTube artifacts
            title = re.sub(r'\s*\(Official\s+.*?\)', '', title, flags=re.IGNORECASE)
            title = re.sub(r'\s*\[Official\s+.*?\]', '', title, flags=re.IGNORECASE)
            
            album = str(row.get('album', '')).strip() or None
            if album and album.lower() == 'nan':
                album = None
            
            duration = TrackNormalizer.parse_duration(row.get('duration'))
            track_id = str(row.get('track_id', '')).strip() or None
            url = str(row.get('url', '')).strip() or None
            
            return Track(
                title=title,
                artist=artist,
                album=album,
                duration=duration,
                platform="youtube_music",
                track_id=track_id,
                url=url
            )
        
        except Exception:
            return None
    
    def _parse_csv_manual(self, file_path: str, encoding: str, library: Library) -> Library:
        """Manual CSV parsing fallback."""
        with open(file_path, 'r', encoding=encoding) as f:
            reader = csv.DictReader(f)
            
            fieldnames = [field.strip() for field in reader.fieldnames or []]
            column_map = self._map_columns(fieldnames)
            
            for row_dict in reader:
                mapped_row = {}
                for old_key, value in row_dict.items():
                    new_key = column_map.get(old_key, old_key)
                    mapped_row[new_key] = value
                
                row = pd.Series(mapped_row)
                track = self._csv_row_to_track(row)
                if track:
                    library.add_track(track)
        
        return library
    
    def _map_columns(self, columns: List[str]) -> Dict[str, str]:
        """Map columns to standard names."""
        column_map = {}
        columns_lower = [col.lower() for col in columns]
        
        for standard_name, variations in self.COLUMN_MAPPINGS.items():
            for variation in variations:
                for i, col_lower in enumerate(columns_lower):
                    if variation in col_lower:
                        column_map[columns[i]] = standard_name
                        break
                if standard_name in column_map.values():
                    break
        
        return column_map
    
    def _parse_duration_json(self, duration_val: Any) -> Optional[int]:
        """Parse duration from JSON format."""
        if not duration_val:
            return None
        
        duration_str = str(duration_val)
        
        # Handle ISO 8601 duration (PT3M45S)
        iso_match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration_str)
        if iso_match:
            hours, minutes, seconds = iso_match.groups()
            total_seconds = 0
            if hours:
                total_seconds += int(hours) * 3600
            if minutes:
                total_seconds += int(minutes) * 60
            if seconds:
                total_seconds += int(seconds)
            return total_seconds if total_seconds > 0 else None
        
        # Fallback to normal parsing
        return TrackNormalizer.parse_duration(duration_str)


def detect_platform(file_path: str) -> str:
    """Detect the platform type from file content."""
    file_path = Path(file_path)
    
    # Check file extension and content
    if file_path.suffix.lower() == '.json':
        # Examine JSON content to determine platform
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                # Read first few lines to check content
                sample = f.read(2048)  # Read first 2KB
                sample_lower = sample.lower()
                
                # Check for Spotify JSON characteristics
                if '"platform":"spotify"' in sample or '"platform": "spotify"' in sample:
                    return 'spotify'
                elif 'open.spotify.com' in sample or 'spotify' in sample_lower:
                    return 'spotify'
                
                # Check for YouTube Music JSON characteristics
                elif 'youtube.com' in sample or 'music.youtube.com' in sample:
                    return 'youtube_music'
                elif '"videoid"' in sample_lower or '"video_id"' in sample_lower:
                    return 'youtube_music'
                
                # Check for Apple Music JSON characteristics
                elif 'apple.com' in sample or 'itunes' in sample_lower:
                    return 'apple_music'
                
                # Default to YouTube Music if no clear indicators (legacy behavior)
                else:
                    return 'youtube_music'
        
        except Exception:
            return 'youtube_music'  # Fallback
    
    elif file_path.suffix.lower() == '.xml':
        return 'apple_music_xml'
    
    # Check file content for CSV files
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            header_line = f.readline().lower()
        
        # Spotify CSV characteristics
        if 'duration (ms)' in header_line or 'artist name(s)' in header_line:
            return 'spotify'
        elif 'track name' in header_line and 'album name' in header_line:
            return 'spotify'
        
        # Apple Music CSV characteristics
        elif 'isrc' in header_line or 'apple' in header_line:
            return 'apple_music'
        
        # YouTube Music CSV characteristics
        elif 'channel' in header_line or 'video' in header_line:
            return 'youtube_music'
        
        else:
            # Default to Apple Music for unknown CSV
            return 'apple_music'
    
    except Exception:
        return 'unknown'


def create_parser(platform: str) -> BasePlatformParser:
    """Factory function to create appropriate parser."""
    platform = platform.lower().replace('_', ' ').replace('-', ' ')
    
    if platform in ('apple music xml', 'apple xml', 'apple_music_xml', 'amxml'):
        return AppleMusicXMLParser()
    if 'apple' in platform or platform == 'am':
        return AppleMusicParser()
    elif 'spotify' in platform:
        return SpotifyParser()
    elif 'youtube' in platform or 'ytm' in platform or platform == 'yt':
        return YouTubeMusicParser()
    else:
        raise ValueError(f"Unknown platform: {platform}")

