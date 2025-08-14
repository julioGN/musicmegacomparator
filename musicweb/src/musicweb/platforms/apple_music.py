"""
Apple Music parser for music library data.
"""

import json
import csv
import re
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import pandas as pd
import plistlib

from .base import BasePlatformParser
from ..core.models import Track, Library, TrackNormalizer

class AppleMusicParser(BasePlatformParser):
    """Parser for Apple Music CSV exports."""
    
    # Common column name variations
    COLUMN_MAPPINGS = {
        'title': ['title', 'song', 'track', 'name', 'track name'],
        'artist': ['artist', 'artist name', 'artists', 'performer'],
        'album': ['album', 'album name', 'release'],
        'duration': ['duration', 'time', 'length', 'track time'],
        'isrc': ['isrc', 'isrc code'],
        'year': ['year', 'release year', 'album year'],
        'genre': ['genre', 'genres', 'primary genre'],
        'track_number': ['track number', 'track #', '#'],
        'track_id': ['track id', 'id', 'apple id'],
        'url': ['url', 'link', 'apple music url']
    }
    
    def __init__(self):
        super().__init__("Apple Music")
    
    def parse_file(self, file_path: str) -> Library:
        """Parse Apple Music CSV file."""
        library = Library(f"Apple Music Library from {Path(file_path).name}", "apple_music")
        
        encoding = self._detect_encoding(file_path)
        
        try:
            # Try pandas first
            df = pd.read_csv(file_path, encoding=encoding)
            
            # Map columns
            column_map = self._map_columns(df.columns.tolist())
            df = df.rename(columns=column_map)
            
            # Process each row
            for _, row in df.iterrows():
                track = self._row_to_track(row)
                if track:
                    library.add_track(track)
        
        except Exception as e:
            # Fallback to manual CSV parsing
            library = self._parse_csv_manual(file_path, encoding)
        
        return library
    
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
            # Required fields
            title = str(row.get('title', '')).strip()
            artist = str(row.get('artist', '')).strip()
            
            if not title or not artist or title.lower() == 'nan' or artist.lower() == 'nan':
                return None
            
            # Optional fields
            album = str(row.get('album', '')).strip() or None
            if album and album.lower() == 'nan':
                album = None
            
            duration = self._parse_duration(row.get('duration'))
            isrc = str(row.get('isrc', '')).strip() or None
            year = self._parse_year(row.get('year'))
            genre = str(row.get('genre', '')).strip() or None
            track_number = self._parse_int(row.get('track_number'))
            track_id = str(row.get('track_id', '')).strip() or None
            url = str(row.get('url', '')).strip() or None
            
            return Track(
                title=title,
                artist=artist,
                album=album,
                duration=duration,
                isrc=isrc,
                platform="apple_music",
                track_id=track_id,
                url=url,
                year=year,
                genre=genre,
                track_number=track_number
            )
        
        except Exception as e:
            return None
    
    def _parse_csv_manual(self, file_path: str, encoding: str) -> Library:
        """Manual CSV parsing fallback."""
        library = Library(f"Apple Music Library from {Path(file_path).name}", "apple_music")
        
        with open(file_path, 'r', encoding=encoding) as f:
            # Try different delimiters
            sample = f.read(1024)
            f.seek(0)
            
            delimiter = ','
            if ';' in sample and sample.count(';') > sample.count(','):
                delimiter = ';'
            elif '\t' in sample:
                delimiter = '\t'
            
            reader = csv.DictReader(f, delimiter=delimiter)
            
            # Map columns
            fieldnames = [field.strip() for field in reader.fieldnames or []]
            column_map = self._map_columns(fieldnames)
            
            for row_dict in reader:
                # Rename columns
                mapped_row = {}
                for old_key, value in row_dict.items():
                    new_key = column_map.get(old_key, old_key)
                    mapped_row[new_key] = value
                
                # Convert to pandas Series for consistency
                row = pd.Series(mapped_row)
                track = self._row_to_track(row)
                if track:
                    library.add_track(track)
        
        return library
    
    def _parse_duration(self, duration_val: Any) -> Optional[int]:
        """Parse duration to seconds."""
        if pd.isna(duration_val) or not duration_val:
            return None
        
        return TrackNormalizer.parse_duration(str(duration_val))
    
    def _parse_year(self, year_val: Any) -> Optional[int]:
        """Parse year value."""
        if pd.isna(year_val) or not year_val:
            return None
        
        try:
            year_str = str(year_val).strip()
            # Extract 4-digit year
            year_match = re.search(r'\b(19|20)\d{2}\b', year_str)
            if year_match:
                return int(year_match.group())
            return int(float(year_str))
        except (ValueError, TypeError):
            return None
    
    def _parse_int(self, val: Any) -> Optional[int]:
        """Parse integer value."""
        if pd.isna(val) or not val:
            return None
        
        try:
            return int(float(str(val)))
        except (ValueError, TypeError):
            return None



class AppleMusicXMLParser(BasePlatformParser):
    """Parser for native Apple Music/iTunes Library XML exports."""

    def __init__(self):
        super().__init__("Apple Music (XML)")

    def parse_file(self, file_path: str) -> Library:
        library = Library(f"Apple Music Library (XML) from {Path(file_path).name}", "apple_music")
        try:
            with open(file_path, 'rb') as f:
                data = plistlib.load(f)
        except Exception as e:
            # Not a valid plist
            return library

        # iTunes/Music library XML structure has a 'Tracks' dict mapping track IDs to dicts
        tracks_dict = data.get('Tracks') or data.get('tracks') or {}
        if not isinstance(tracks_dict, dict):
            return library

        for _, t in tracks_dict.items():
            track = self._dict_to_track(t)
            if track:
                library.add_track(track)
        return library

    def _dict_to_track(self, t: Dict[str, Any]) -> Optional[Track]:
        try:
            title = (t.get('Name') or t.get('name') or '').strip()
            artist = (t.get('Artist') or t.get('artist') or '').strip()
            if not title or not artist:
                return None

            album = (t.get('Album') or t.get('album') or None)

            # Durations in XML are milliseconds (Total Time)
            total_time = t.get('Total Time') or t.get('total time')
            duration = None
            if total_time is not None:
                try:
                    duration = int(total_time) // 1000
                except Exception:
                    duration = None

            year = None
            if 'Year' in t:
                try:
                    year = int(t['Year'])
                except Exception:
                    year = None

            genre = t.get('Genre') or t.get('genre')
            track_number = None
            if 'Track Number' in t:
                try:
                    track_number = int(t['Track Number'])
                except Exception:
                    track_number = None

            # ISRC is not typically present in Apple Music XML, but use if available
            isrc = t.get('ISRC') or t.get('isrc')

            # Prefer Persistent ID as stable identifier if present
            persistent_id = t.get('Persistent ID') or t.get('persistent id')
            track_id = persistent_id or str(t.get('Track ID') or '') or None

            url = t.get('Location')

            return Track(
                title=title,
                artist=artist,
                album=album,
                duration=duration,
                isrc=isrc,
                platform='apple_music',
                track_id=str(track_id) if track_id else None,
                url=str(url) if url else None,
                year=year,
                genre=genre,
                track_number=track_number
            )
        except Exception:
            return None

