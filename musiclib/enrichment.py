"""
Music metadata enrichment using MusicBrainz and other services.
"""

import time
import json
import requests
from typing import Dict, List, Optional, Any, Tuple
from urllib.parse import quote_plus
import re

from .core import Track


class MusicBrainzEnricher:
    """Enrich track metadata using MusicBrainz API."""
    
    def __init__(self, user_agent: str = "MusicLibraryTool/1.0"):
        self.base_url = "https://musicbrainz.org/ws/2"
        self.headers = {
            'User-Agent': user_agent,
            'Accept': 'application/json'
        }
        self.rate_limit_delay = 1.2  # MusicBrainz requires 1 request per second
        self.last_request_time = 0
    
    def enrich_track(self, track: Track) -> Optional[Dict[str, Any]]:
        """Enrich a single track with MusicBrainz data."""
        try:
            # Rate limiting
            self._respect_rate_limit()
            
            # Try multiple search strategies
            enrichment_data = None
            
            # 1. Search by ISRC if available
            if track.isrc:
                enrichment_data = self._search_by_isrc(track.isrc)
            
            # 2. Search by artist and title
            if not enrichment_data:
                enrichment_data = self._search_by_artist_title(track.artist, track.title)
            
            # 3. Search with album if available
            if not enrichment_data and track.album:
                enrichment_data = self._search_by_artist_title_album(track.artist, track.title, track.album)
            
            return enrichment_data
        
        except Exception as e:
            print(f"Enrichment failed for '{track.title}' by '{track.artist}': {e}")
            return None
    
    def enrich_tracks(self, tracks: List[Track], 
                     progress_callback: Optional[callable] = None) -> Dict[str, Dict[str, Any]]:
        """Enrich multiple tracks with MusicBrainz data."""
        enriched_data = {}
        
        for i, track in enumerate(tracks):
            if progress_callback:
                progress_callback(i, len(tracks), f"Enriching: {track.title}")
            
            track_key = f"{track.normalized_title}|{track.normalized_artist}"
            enrichment = self.enrich_track(track)
            
            if enrichment:
                enriched_data[track_key] = enrichment
        
        if progress_callback:
            progress_callback(len(tracks), len(tracks), "Enrichment complete")
        
        return enriched_data
    
    def _respect_rate_limit(self) -> None:
        """Ensure we don't exceed MusicBrainz rate limits."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - time_since_last)
        
        self.last_request_time = time.time()
    
    def _search_by_isrc(self, isrc: str) -> Optional[Dict[str, Any]]:
        """Search MusicBrainz by ISRC."""
        try:
            url = f"{self.base_url}/recording"
            params = {
                'query': f'isrc:{isrc}',
                'fmt': 'json',
                'limit': 1
            }
            
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            recordings = data.get('recordings', [])
            
            if recordings:
                return self._extract_recording_info(recordings[0])
            
            return None
        
        except Exception as e:
            print(f"ISRC search failed for {isrc}: {e}")
            return None
    
    def _search_by_artist_title(self, artist: str, title: str) -> Optional[Dict[str, Any]]:
        """Search MusicBrainz by artist and title."""
        try:
            # Clean and prepare search terms
            clean_artist = self._clean_search_term(artist)
            clean_title = self._clean_search_term(title)
            
            url = f"{self.base_url}/recording"
            
            # Try multiple query strategies
            queries = [
                f'artist:"{clean_artist}" AND recording:"{clean_title}"',
                f'artist:{clean_artist} AND recording:{clean_title}',
                f'"{clean_title}" AND artist:{clean_artist}'
            ]
            
            for query in queries:
                params = {
                    'query': query,
                    'fmt': 'json',
                    'limit': 5  # Get multiple results to find best match
                }
                
                response = requests.get(url, headers=self.headers, params=params, timeout=10)
                response.raise_for_status()
                
                data = response.json()
                recordings = data.get('recordings', [])
                
                if recordings:
                    # Find best match from results
                    best_match = self._find_best_recording_match(recordings, artist, title)
                    if best_match:
                        return best_match
                
                # Rate limit between different query attempts
                time.sleep(0.5)
            
            return None
        
        except Exception as e:
            print(f"Artist/title search failed for '{title}' by '{artist}': {e}")
            return None
    
    def _search_by_artist_title_album(self, artist: str, title: str, album: str) -> Optional[Dict[str, Any]]:
        """Search MusicBrainz by artist, title, and album."""
        try:
            clean_artist = self._clean_search_term(artist)
            clean_title = self._clean_search_term(title)
            clean_album = self._clean_search_term(album)
            
            url = f"{self.base_url}/recording"
            
            queries = [
                f'artist:"{clean_artist}" AND recording:"{clean_title}" AND release:"{clean_album}"',
                f'artist:{clean_artist} AND recording:{clean_title} AND release:{clean_album}'
            ]
            
            for query in queries:
                params = {
                    'query': query,
                    'fmt': 'json',
                    'limit': 3
                }
                
                response = requests.get(url, headers=self.headers, params=params, timeout=10)
                response.raise_for_status()
                
                data = response.json()
                recordings = data.get('recordings', [])
                
                if recordings:
                    best_match = self._find_best_recording_match(recordings, artist, title, album)
                    if best_match:
                        return best_match
                
                time.sleep(0.5)
            
            return None
        
        except Exception as e:
            print(f"Artist/title/album search failed: {e}")
            return None
    
    def _clean_search_term(self, term: str) -> str:
        """Clean search terms for MusicBrainz queries."""
        if not term:
            return ""
        
        # Remove special characters that can break queries
        cleaned = re.sub(r'[^\w\s\-\']', ' ', term)
        
        # Remove extra whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        return cleaned
    
    def _find_best_recording_match(self, recordings: List[Dict], target_artist: str, 
                                 target_title: str, target_album: str = None) -> Optional[Dict[str, Any]]:
        """Find the best matching recording from MusicBrainz results."""
        best_match = None
        best_score = 0.0
        
        for recording in recordings:
            score = self._calculate_recording_similarity(
                recording, target_artist, target_title, target_album
            )
            
            if score > best_score and score >= 0.7:  # Minimum similarity threshold
                best_match = recording
                best_score = score
        
        if best_match:
            return self._extract_recording_info(best_match)
        
        return None
    
    def _calculate_recording_similarity(self, recording: Dict, target_artist: str, 
                                     target_title: str, target_album: str = None) -> float:
        """Calculate similarity between MusicBrainz recording and target track."""
        try:
            # Get recording info
            mb_title = recording.get('title', '').lower()
            
            # Get artist info
            mb_artists = []
            for credit in recording.get('artist-credit', []):
                if isinstance(credit, dict) and 'artist' in credit:
                    mb_artists.append(credit['artist'].get('name', '').lower())
                elif isinstance(credit, str):
                    mb_artists.append(credit.lower())
            
            mb_artist = ' '.join(mb_artists)
            
            # Calculate title similarity
            target_title_lower = target_title.lower()
            title_similarity = self._simple_similarity(mb_title, target_title_lower)
            
            # Calculate artist similarity
            target_artist_lower = target_artist.lower()
            artist_similarity = self._simple_similarity(mb_artist, target_artist_lower)
            
            # Weighted score
            total_score = title_similarity * 0.6 + artist_similarity * 0.4
            
            # Bonus for album match if provided
            if target_album:
                releases = recording.get('releases', [])
                for release in releases:
                    mb_album = release.get('title', '').lower()
                    album_similarity = self._simple_similarity(mb_album, target_album.lower())
                    if album_similarity > 0.8:
                        total_score += 0.1  # Small bonus
                        break
            
            return min(1.0, total_score)
        
        except Exception:
            return 0.0
    
    def _simple_similarity(self, str1: str, str2: str) -> float:
        """Simple string similarity calculation."""
        if not str1 or not str2:
            return 0.0
        
        # Jaccard similarity on words
        words1 = set(str1.lower().split())
        words2 = set(str2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0
    
    def _extract_recording_info(self, recording: Dict) -> Dict[str, Any]:
        """Extract useful information from MusicBrainz recording."""
        try:
            # Basic info
            info = {
                'musicbrainz_id': recording.get('id'),
                'title': recording.get('title'),
                'length': recording.get('length'),  # in milliseconds
                'disambiguation': recording.get('disambiguation'),
            }
            
            # Artist credits
            artists = []
            for credit in recording.get('artist-credit', []):
                if isinstance(credit, dict) and 'artist' in credit:
                    artist_info = {
                        'name': credit['artist'].get('name'),
                        'id': credit['artist'].get('id'),
                        'sort_name': credit['artist'].get('sort-name')
                    }
                    artists.append(artist_info)
            info['artists'] = artists
            
            # Releases (albums)
            releases = []
            for release in recording.get('releases', []):
                release_info = {
                    'title': release.get('title'),
                    'id': release.get('id'),
                    'date': release.get('date'),
                    'country': release.get('country'),
                    'barcode': release.get('barcode')
                }
                releases.append(release_info)
            info['releases'] = releases
            
            # ISRCs
            isrcs = [isrc for isrc in recording.get('isrcs', [])]
            info['isrcs'] = isrcs
            
            # Tags/genres
            tags = []
            for tag in recording.get('tags', []):
                tags.append({
                    'name': tag.get('name'),
                    'count': tag.get('count', 0)
                })
            info['tags'] = sorted(tags, key=lambda x: x['count'], reverse=True)
            
            return info
        
        except Exception as e:
            print(f"Failed to extract recording info: {e}")
            return {}


class EnrichmentManager:
    """Manage enrichment from multiple sources."""
    
    def __init__(self):
        self.musicbrainz = MusicBrainzEnricher()
        self.cache = {}  # Simple in-memory cache
    
    def enrich_track(self, track: Track) -> Dict[str, Any]:
        """Enrich track from multiple sources with caching."""
        cache_key = f"{track.normalized_title}|{track.normalized_artist}"
        
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        enrichment_data = {
            'original_track': track.to_dict(),
            'musicbrainz': None,
            'enriched_fields': {}
        }
        
        # Try MusicBrainz
        mb_data = self.musicbrainz.enrich_track(track)
        if mb_data:
            enrichment_data['musicbrainz'] = mb_data
            
            # Extract useful fields
            if 'length' in mb_data and mb_data['length'] and not track.duration:
                enrichment_data['enriched_fields']['duration'] = mb_data['length'] // 1000
            
            if 'isrcs' in mb_data and mb_data['isrcs'] and not track.isrc:
                enrichment_data['enriched_fields']['isrc'] = mb_data['isrcs'][0]
            
            # Genre from tags
            if 'tags' in mb_data and mb_data['tags'] and not track.genre:
                top_tags = [tag['name'] for tag in mb_data['tags'][:3]]
                enrichment_data['enriched_fields']['genre'] = ', '.join(top_tags)
        
        # Cache result
        self.cache[cache_key] = enrichment_data
        return enrichment_data
    
    def apply_enrichment(self, track: Track, enrichment_data: Dict[str, Any]) -> Track:
        """Apply enrichment data to create enhanced track."""
        enhanced_fields = enrichment_data.get('enriched_fields', {})
        
        # Create new track with enhanced data
        enhanced_track = Track(
            title=track.title,
            artist=track.artist,
            album=track.album,
            duration=enhanced_fields.get('duration', track.duration),
            isrc=enhanced_fields.get('isrc', track.isrc),
            platform=track.platform,
            track_id=track.track_id,
            url=track.url,
            year=enhanced_fields.get('year', track.year),
            genre=enhanced_fields.get('genre', track.genre),
            track_number=track.track_number
        )
        
        return enhanced_track
    
    def bulk_enrich(self, tracks: List[Track], 
                   progress_callback: Optional[callable] = None) -> List[Tuple[Track, Dict[str, Any]]]:
        """Enrich multiple tracks and return enhanced versions."""
        enriched_tracks = []
        
        for i, track in enumerate(tracks):
            if progress_callback:
                progress_callback(i, len(tracks), f"Enriching: {track.title}")
            
            enrichment_data = self.enrich_track(track)
            enhanced_track = self.apply_enrichment(track, enrichment_data)
            
            enriched_tracks.append((enhanced_track, enrichment_data))
        
        if progress_callback:
            progress_callback(len(tracks), len(tracks), "Enrichment complete")
        
        return enriched_tracks