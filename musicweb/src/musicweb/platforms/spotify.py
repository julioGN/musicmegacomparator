"""
Spotify parser for music library data.
"""

import json
import csv
import re
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import pandas as pd

from .base import BasePlatformParser
from ..core.models import Track, Library, TrackNormalizer

class SpotifyParser(BasePlatformParser):
    """Parser for Spotify CSV exports."""
    
    # Spotify-specific column mappings
    COLUMN_MAPPINGS = {
        'title': ['track name', 'song', 'title', 'name'],
        'artist': ['artist name(s)', 'artist', 'artists', 'artist name'],
        'album': ['album name', 'album', 'release name'],
        'duration': ['duration (ms)', 'duration_ms', 'duration', 'track duration (ms)'],
        'isrc': ['isrc', 'isrc code'],
        'year': ['release year', 'year', 'album year'],
        'track_id': ['track id', 'spotify id', 'id'],
        'url': ['track url', 'spotify url', 'external urls', 'url']
    }
    
    def __init__(self):
        super().__init__("Spotify")
    
    def parse_file(self, file_path: str) -> Library:
        """Parse Spotify file (CSV or JSON)."""
        file_path = Path(file_path)
        library = Library(f"Spotify Library from {file_path.name}", "spotify")
        
        if file_path.suffix.lower() == '.json':
            return self._parse_json(file_path, library)
        else:
            return self._parse_csv(file_path, library)
    
    def _parse_json(self, file_path: Path, library: Library) -> Library:
        """Parse Spotify JSON export."""
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
            print(f"Error parsing Spotify JSON file: {e}")
        
        return library
    
    def _parse_csv(self, file_path: Path, library: Library) -> Library:
        """Parse Spotify CSV file."""
        encoding = self._detect_encoding(str(file_path))
        
        try:
            df = pd.read_csv(file_path, encoding=encoding)
            
            # Map columns
            column_map = self._map_columns(df.columns.tolist())
            df = df.rename(columns=column_map)
            
            # Process each row
            for _, row in df.iterrows():
                track = self._row_to_track(row)
                if track:
                    library.add_track(track)
        
        except Exception:
            # Fallback to manual parsing
            library = self._parse_csv_manual(str(file_path), encoding)
        
        return library
    
    def _json_item_to_track(self, item: Dict[str, Any]) -> Optional[Track]:
        """Convert Spotify JSON item to Track object."""
        try:
            # Get title and artist
            title = item.get('title') or item.get('name') or item.get('trackName', '')
            artist = item.get('artist') or item.get('artistName') or item.get('artists', '')
            
            # Handle multiple artists (sometimes comma-separated string)
            if isinstance(artist, list):
                artist = ', '.join(str(a) for a in artist)
            else:
                artist = str(artist).strip()
            
            title = str(title).strip()
            
            if not title or not artist:
                return None
            
            # Get other fields
            album = item.get('album') or item.get('albumName')
            if album:
                album = str(album).strip()
            
            # Duration handling (Spotify usually has duration in seconds in JSON exports)
            duration = item.get('duration')
            if duration and not pd.isna(duration):
                try:
                    # If it's already in seconds, use as-is
                    duration = int(float(duration))
                except (ValueError, TypeError):
                    duration = None
            else:
                duration = None
            
            # Other metadata
            isrc = item.get('isrc') or item.get('isrcCode')
            if isrc:
                isrc = str(isrc).strip()
            
            track_id = item.get('id') or item.get('trackId') or item.get('spotifyId')
            if track_id:
                track_id = str(track_id).strip()
            
            url = item.get('trackLink') or item.get('url') or item.get('trackUrl')
            if url:
                url = str(url).strip()
            
            # Year from release date or year field
            year = None
            year_val = item.get('year') or item.get('releaseYear') or item.get('albumYear')
            if year_val:
                year = self._parse_year(year_val)
            
            return Track(
                title=title,
                artist=artist,
                album=album,
                duration=duration,
                isrc=isrc,
                platform="spotify",
                track_id=track_id,
                url=url,
                year=year
            )
        
        except Exception as e:
            print(f"Error parsing Spotify track: {e}")
            return None
    
    def _map_columns(self, columns: List[str]) -> Dict[str, str]:
        """Map CSV columns to standard field names."""
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
    
    def _row_to_track(self, row: pd.Series) -> Optional[Track]:
        """Convert DataFrame row to Track object."""
        try:
            title = str(row.get('title', '')).strip()
            artist = str(row.get('artist', '')).strip()
            
            if not title or not artist or title.lower() == 'nan' or artist.lower() == 'nan':
                return None
            
            album = str(row.get('album', '')).strip() or None
            if album and album.lower() == 'nan':
                album = None
            
            # Spotify durations are in milliseconds
            duration_ms = row.get('duration')
            duration = None
            if duration_ms and not pd.isna(duration_ms):
                try:
                    duration = int(float(duration_ms)) // 1000
                except (ValueError, TypeError):
                    pass
            
            isrc = str(row.get('isrc', '')).strip() or None
            year = self._parse_year(row.get('year'))
            track_id = str(row.get('track_id', '')).strip() or None
            url = str(row.get('url', '')).strip() or None
            
            return Track(
                title=title,
                artist=artist,
                album=album,
                duration=duration,
                isrc=isrc,
                platform="spotify",
                track_id=track_id,
                url=url,
                year=year
            )
        
        except Exception:
            return None
    
    def _parse_csv_manual(self, file_path: str, encoding: str) -> Library:
        """Manual CSV parsing fallback."""
        library = Library(f"Spotify Library from {Path(file_path).name}", "spotify")
        
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
                track = self._row_to_track(row)
                if track:
                    library.add_track(track)
        
        return library
    
    def _parse_year(self, year_val: Any) -> Optional[int]:
        """Parse year value."""
        if pd.isna(year_val) or not year_val:
            return None
        
        try:
            year_str = str(year_val).strip()
            year_match = re.search(r'\b(19|20)\d{2}\b', year_str)
            if year_match:
                return int(year_match.group())
            return int(float(year_str))
        except (ValueError, TypeError):
            return None


