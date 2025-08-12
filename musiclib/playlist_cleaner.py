"""
Enhanced YouTube Music Playlist Cleanup System

Provides comprehensive playlist cleanup functionality:
- Remove liked songs from playlists
- Deduplicate playlists against user's library
- Handle API response structure changes gracefully
- Performance optimized with caching and batching
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import parse_qs, urlparse
import logging
import re
from difflib import SequenceMatcher
from collections import defaultdict

try:
    from ytmusicapi import YTMusic  # type: ignore
except Exception:  # pragma: no cover
    YTMusic = None  # type: ignore


@dataclass
class PlaylistTrack:
    """Represents a track in a playlist with all relevant metadata."""
    video_id: str
    set_video_id: str
    title: str
    artists: List[str]
    album: Optional[str]
    duration: Optional[str]
    is_liked: bool = False
    is_explicit: bool = False
    thumbnail: Optional[str] = None


@dataclass
class CleanupResult:
    """Results from a playlist cleanup operation."""
    playlist_id: str
    playlist_name: str
    original_count: int
    removed_liked: int
    removed_duplicates: int
    final_count: int
    errors: List[str]
    processing_time: float


@dataclass
class DuplicateGroup:
    """Represents a group of duplicate tracks within a playlist."""
    signature: str
    tracks: List[PlaylistTrack]
    duplicate_count: int
    tracks_to_keep: List[PlaylistTrack]
    tracks_to_remove: List[PlaylistTrack]
    confidence: float
    review_needed: bool
    
    def __post_init__(self):
        if not self.tracks_to_keep and not self.tracks_to_remove:
            self._decide_which_to_keep()
    
    def _decide_which_to_keep(self):
        """Decide which track to keep and which to remove."""
        if not self.tracks:
            return
        
        # Sort tracks by preference (prefer studio versions, shorter titles, etc.)
        sorted_tracks = sorted(self.tracks, key=self._track_preference_score)
        
        # Keep the first (best) track
        self.tracks_to_keep = [sorted_tracks[0]]
        self.tracks_to_remove = sorted_tracks[1:]
    
    def _track_preference_score(self, track: PlaylistTrack) -> tuple:
        """Score for track preference (lower is better)."""
        title = track.title.lower()
        
        # Penalty for live versions
        live_penalty = 1 if any(word in title for word in ['live', 'concert', 'tour']) else 0
        
        # Penalty for remixes/alternate versions
        remix_penalty = 1 if any(word in title for word in ['remix', 'alternate', 'demo', 'acoustic']) else 0
        
        # Penalty for explicit versions (prefer clean)
        explicit_penalty = 1 if 'explicit' in title else 0
        
        # Prefer shorter titles (often original versions)
        title_length_penalty = len(title) / 100
        
        return (live_penalty, remix_penalty, explicit_penalty, title_length_penalty)


class PlaylistCleaner:
    """Enhanced playlist cleaner with robust error handling, similarity matching, and internal deduplication."""
    
    def __init__(self, ytmusic: Optional[YTMusic] = None, headers_path: Optional[str] = None):
        self.ytmusic = ytmusic
        self.headers_path = headers_path
        self._library_cache: Optional[List[Dict[str, Any]]] = None
        self._liked_cache: Optional[Set[str]] = None
        self.logger = logging.getLogger(__name__)
        
        if not self.ytmusic and headers_path:
            self._authenticate()
    
    def _authenticate(self) -> bool:
        """Authenticate with YouTube Music."""
        if not YTMusic:
            raise RuntimeError("ytmusicapi not installed")
        
        try:
            self.ytmusic = YTMusic(self.headers_path)
            # Test connection
            self.ytmusic.get_library_songs(limit=1)
            return True
        except Exception as e:
            self.logger.error(f"Authentication failed: {e}")
            return False
    
    def extract_playlist_id(self, url_or_id: str) -> Optional[str]:
        """Extract playlist ID from URL or return ID if already provided."""
        if url_or_id.startswith('PL') or url_or_id.startswith('RDAMPL'):
            return url_or_id
        
        try:
            parsed = urlparse(url_or_id)
            if 'list' in parsed.query:
                return parse_qs(parsed.query)['list'][0]
        except Exception:
            pass
        
        return None
    
    def get_playlist_tracks_robust(self, playlist_id: str) -> List[PlaylistTrack]:
        """Get playlist tracks with robust error handling for large playlists."""
        if not self.ytmusic:
            raise RuntimeError("Not authenticated")
        
        self.logger.info(f"Fetching playlist tracks for playlist: {playlist_id}")
        
        try:
            # First, try to get all tracks at once with limit=None
            self.logger.info("Attempting to fetch all tracks at once...")
            playlist_data = self.ytmusic.get_playlist(playlist_id, limit=None)
            
            # Debug: Log the response structure
            self.logger.info(f"Playlist response keys: {list(playlist_data.keys())}")
            if 'trackCount' in playlist_data:
                self.logger.info(f"Playlist trackCount: {playlist_data['trackCount']}")
            
            # Check if we got a tracks list
            if 'tracks' in playlist_data and playlist_data['tracks']:
                tracks = []
                track_list = playlist_data['tracks']
                
                self.logger.info(f"Raw tracks list length: {len(track_list)}")
                
                for i, track_data in enumerate(track_list):
                    track = self._parse_track_data(track_data)
                    if track:
                        tracks.append(track)
                    elif i < 5:  # Log first few failures for debugging
                        self.logger.debug(f"Failed to parse track {i}: {track_data}")
                
                self.logger.info(f"Successfully parsed {len(tracks)} tracks from {len(track_list)} raw tracks")
                
                # ALWAYS check if we might have hit a limit or if this is a large playlist
                track_count = len(tracks)
                expected_count = playlist_data.get('trackCount', track_count)
                
                self.logger.info(f"Got {track_count} tracks, expected {expected_count}")
                
                # For playlists with >100 tracks, ALWAYS use chunked approach to get everything
                if expected_count > 100 or (track_count == 100 and expected_count >= track_count):
                    self.logger.info(f"Large playlist detected ({expected_count} expected, {track_count} fetched). Using chunked approach to get all tracks...")
                    chunked_tracks = self._fetch_playlist_chunked(playlist_id, expected_count)
                    if len(chunked_tracks) >= track_count:
                        self.logger.info(f"Chunked approach got {len(chunked_tracks)} tracks, using that instead")
                        return chunked_tracks
                    else:
                        self.logger.warning(f"Chunked approach only got {len(chunked_tracks)} tracks, keeping original {track_count}")
                
                # Also check if we got exactly 100 tracks (common API limit)
                elif track_count == 100:
                    self.logger.warning(f"Got exactly 100 tracks - this might be a limit. Trying chunked approach...")
                    chunked_tracks = self._fetch_playlist_chunked(playlist_id, expected_count)
                    if len(chunked_tracks) > track_count:
                        self.logger.info(f"Chunked approach got {len(chunked_tracks)} tracks, using that instead")
                        return chunked_tracks
                
                return tracks
                
            else:
                # No tracks found in standard location, try alternative structure parsing
                self.logger.info("No tracks in standard location, trying alternative parsing...")
                track_list = self._extract_tracks_from_any_structure(playlist_data)
                
                tracks = []
                for track_data in track_list:
                    track = self._parse_track_data(track_data)
                    if track:
                        tracks.append(track)
                
                if tracks:
                    self.logger.info(f"Found {len(tracks)} tracks using alternative parsing")
                    return tracks
                else:
                    # Try chunked approach as fallback
                    self.logger.info("Alternative parsing failed, trying chunked approach...")
                    return self._fetch_playlist_chunked(playlist_id)
                    
        except Exception as e:
            self.logger.error(f"Error getting playlist tracks: {e}")
            # Try chunked approach as final fallback
            try:
                self.logger.info("Attempting chunked fetch as fallback...")
                return self._fetch_playlist_chunked(playlist_id)
            except Exception as fallback_e:
                self.logger.error(f"Chunked fallback also failed: {fallback_e}")
                return []
    
    def _fetch_playlist_chunked(self, playlist_id: str, expected_count: Optional[int] = None) -> List[PlaylistTrack]:
        """Fetch ALL playlist tracks using ytmusicapi's built-in pagination (works with 1.11.0+)."""
        self.logger.info(f"Fetching large playlist with limit=None (expected: {expected_count} tracks)")
        
        try:
            # Use ytmusicapi's built-in pagination with limit=None
            # This should work properly with ytmusicapi 1.11.0+
            self.logger.info("Attempting to fetch all tracks with limit=None...")
            playlist_data = self.ytmusic.get_playlist(playlist_id, limit=None)
            
            tracks = []
            if 'tracks' in playlist_data and playlist_data['tracks']:
                track_list = playlist_data['tracks']
                self.logger.info(f"Got {len(track_list)} tracks from limit=None call")
                
                for track_data in track_list:
                    track = self._parse_track_data(track_data)
                    if track:
                        tracks.append(track)
                
                self.logger.info(f"Successfully parsed {len(tracks)} tracks from limit=None")
                return tracks
            
            else:
                self.logger.warning("No tracks found with limit=None, falling back to iterative approach...")
                return self._fetch_playlist_iterative(playlist_id, expected_count)
                
        except Exception as e:
            self.logger.error(f"limit=None approach failed: {e}")
            self.logger.info("Falling back to iterative approach...")
            return self._fetch_playlist_iterative(playlist_id, expected_count)
    
    def _extract_tracks_from_browse_response(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract tracks from a browse API response."""
        tracks = []
        
        # Try to find tracks in the browse response structure
        try:
            # Common paths for playlist tracks in browse responses
            possible_paths = [
                ['contents', 'singleColumnBrowseResultsRenderer', 'tabs', 0, 'tabRenderer', 'content', 'sectionListRenderer', 'contents', 0, 'musicPlaylistShelfRenderer', 'contents'],
                ['contents', 'twoColumnBrowseResultsRenderer', 'tabs', 0, 'tabRenderer', 'content', 'sectionListRenderer', 'contents', 0, 'musicPlaylistShelfRenderer', 'contents'],
                ['contents', 'sectionListRenderer', 'contents', 0, 'musicPlaylistShelfRenderer', 'contents']
            ]
            
            for path in possible_paths:
                try:
                    current = response
                    for key in path:
                        if isinstance(key, int):
                            current = current[key]
                        else:
                            current = current[key]
                    
                    if isinstance(current, list):
                        tracks = current
                        break
                        
                except (KeyError, IndexError, TypeError):
                    continue
            
            # If we didn't find tracks in standard paths, search recursively
            if not tracks:
                tracks = self._extract_tracks_from_any_structure(response['contents'])
                
        except Exception as e:
            self.logger.debug(f"Error extracting tracks from browse response: {e}")
        
        return tracks
    
    def _find_continuation_token(self, response: Dict[str, Any]) -> Optional[str]:
        """Find continuation token in API response."""
        try:
            # Look in common places for continuation tokens
            if 'continuations' in response:
                continuations = response['continuations']
                if continuations and len(continuations) > 0:
                    cont_data = continuations[0]
                    if 'nextContinuationData' in cont_data:
                        return cont_data['nextContinuationData'].get('continuation')
                    elif 'continuation' in cont_data:
                        return cont_data['continuation']
            
            # Look deeper in the response structure
            if 'contents' in response:
                # Search for continuation in the contents structure
                continuation = self._search_for_continuation(response['contents'])
                if continuation:
                    return continuation
                    
        except Exception as e:
            self.logger.debug(f"Error finding continuation token: {e}")
        
        return None
    
    def _search_for_continuation(self, data: Any) -> Optional[str]:
        """Recursively search for continuation tokens in data structure."""
        if isinstance(data, dict):
            # Direct continuation check
            if 'continuation' in data:
                return data['continuation']
            if 'nextContinuationData' in data:
                return data['nextContinuationData'].get('continuation')
            
            # Search in all dict values
            for value in data.values():
                result = self._search_for_continuation(value)
                if result:
                    return result
                    
        elif isinstance(data, list):
            # Search in all list items
            for item in data:
                result = self._search_for_continuation(item)
                if result:
                    return result
        
        return None
    
    def _fetch_playlist_iterative(self, playlist_id: str, expected_count: Optional[int] = None) -> List[PlaylistTrack]:
        """Try to fetch playlist using iterative approach with increasing limits."""
        self.logger.info(f"Starting iterative fetch (expected: {expected_count} tracks)")
        
        # Try progressively larger limits
        limits_to_try = [500, 1000, 2000, 5000, None]
        
        for limit in limits_to_try:
            try:
                self.logger.info(f"Trying with limit={limit}...")
                playlist_data = self.ytmusic.get_playlist(playlist_id, limit=limit)
                
                if 'tracks' not in playlist_data or not playlist_data['tracks']:
                    self.logger.warning(f"No tracks found with limit={limit}")
                    continue
                
                track_list = playlist_data['tracks']
                self.logger.info(f"Got {len(track_list)} tracks with limit={limit}")
                
                tracks = []
                for track_data in track_list:
                    track = self._parse_track_data(track_data)
                    if track:
                        tracks.append(track)
                
                self.logger.info(f"Successfully parsed {len(tracks)} tracks with limit={limit}")
                
                # If we got close to or more than expected, use this result
                if expected_count is None or len(tracks) >= expected_count * 0.9 or limit is None:
                    return tracks
                
                # If we didn't get enough tracks and there are more limits to try, continue
                if len(tracks) < expected_count * 0.9 and limit != limits_to_try[-1]:
                    self.logger.info(f"Got {len(tracks)} but expected ~{expected_count}, trying larger limit...")
                    continue
                else:
                    return tracks
                    
            except Exception as e:
                self.logger.error(f"Failed with limit={limit}: {e}")
                continue
        
        self.logger.error("All iterative attempts failed")
        return []
    
    def _extract_tracks_from_any_structure(self, data: Any) -> List[Dict[str, Any]]:
        """Recursively search for track-like structures in the response."""
        tracks = []
        
        if isinstance(data, dict):
            # Look for musicResponsiveListItemRenderer which typically contains track info
            if 'musicResponsiveListItemRenderer' in data:
                tracks.append(data)
            else:
                for value in data.values():
                    tracks.extend(self._extract_tracks_from_any_structure(value))
        elif isinstance(data, list):
            for item in data:
                tracks.extend(self._extract_tracks_from_any_structure(item))
        
        return tracks
    
    def _parse_track_data(self, track_data: Dict[str, Any]) -> Optional[PlaylistTrack]:
        """Parse track data from various possible formats."""
        try:
            # Handle direct track format
            if 'videoId' in track_data:
                return PlaylistTrack(
                    video_id=track_data.get('videoId', ''),
                    set_video_id=track_data.get('setVideoId', ''),
                    title=track_data.get('title', ''),
                    artists=[a.get('name', '') for a in track_data.get('artists', [])],
                    album=track_data.get('album', {}).get('name') if track_data.get('album') else None,
                    duration=track_data.get('duration'),
                    is_explicit=track_data.get('isExplicit', False)
                )
            
            # Handle musicResponsiveListItemRenderer format
            elif 'musicResponsiveListItemRenderer' in track_data:
                renderer = track_data['musicResponsiveListItemRenderer']
                
                # Extract basic IDs
                video_id = ""
                set_video_id = ""
                
                # Look for IDs in various places
                if 'playNavigationEndpoint' in renderer:
                    nav = renderer['playNavigationEndpoint']
                    if 'videoId' in nav:
                        video_id = nav['videoId']
                    if 'watchEndpoint' in nav and 'videoId' in nav['watchEndpoint']:
                        video_id = nav['watchEndpoint']['videoId']
                
                # Look for setVideoId in menu
                if 'menu' in renderer:
                    menu_items = renderer['menu'].get('menuRenderer', {}).get('items', [])
                    for item in menu_items:
                        if 'menuServiceItemRenderer' in item:
                            service = item['menuServiceItemRenderer'].get('serviceEndpoint', {})
                            if 'removeFromPlaylistEndpoint' in service:
                                set_video_id = service['removeFromPlaylistEndpoint'].get('setVideoId', '')
                
                # Extract text content (title, artist)
                text_runs = []
                if 'flexColumns' in renderer:
                    for column in renderer['flexColumns']:
                        if 'musicResponsiveListItemFlexColumnRenderer' in column:
                            text_data = column['musicResponsiveListItemFlexColumnRenderer'].get('text', {})
                            if 'runs' in text_data:
                                for run in text_data['runs']:
                                    if 'text' in run:
                                        text_runs.append(run['text'])
                
                title = text_runs[0] if text_runs else ""
                artists = text_runs[1:2] if len(text_runs) > 1 else []
                
                if video_id:
                    return PlaylistTrack(
                        video_id=video_id,
                        set_video_id=set_video_id,
                        title=title,
                        artists=artists,
                        album=None,
                        duration=None
                    )
            
        except Exception as e:
            self.logger.warning(f"Error parsing track data: {e}")
        
        return None
    
    def _fallback_playlist_extraction(self, playlist_id: str) -> List[PlaylistTrack]:
        """Fallback method to extract playlist tracks using alternative approaches."""
        tracks = []
        
        try:
            # Try using the browse endpoint directly
            browse_response = self.ytmusic._send_request('browse', {'browseId': f'VL{playlist_id}'})
            
            # Parse the raw browse response
            if 'contents' in browse_response:
                tracks_data = self._extract_tracks_from_any_structure(browse_response['contents'])
                for track_data in tracks_data:
                    track = self._parse_track_data(track_data)
                    if track:
                        tracks.append(track)
        
        except Exception as e:
            self.logger.error(f"Fallback extraction failed: {e}")
        
        return tracks
    
    def get_library_songs_cached(self) -> List[Dict[str, Any]]:
        """Get library songs with caching for performance."""
        if self._library_cache is None:
            if not self.ytmusic:
                raise RuntimeError("Not authenticated")
            
            self.logger.info("Fetching library songs...")
            try:
                # Try to get all library songs
                self._library_cache = self.ytmusic.get_library_songs(limit=None) or []
                self.logger.info(f"Loaded {len(self._library_cache)} library songs")
                
                # Debug: Check if we got a reasonable number
                if len(self._library_cache) == 100:
                    self.logger.warning("Got exactly 100 library songs - might have hit a limit")
                elif len(self._library_cache) < 10:
                    self.logger.warning(f"Only got {len(self._library_cache)} library songs - this seems low")
                
                # Log some sample video IDs for debugging
                if self._library_cache:
                    sample_ids = [song.get('videoId') for song in self._library_cache[:3] if song.get('videoId')]
                    self.logger.debug(f"Sample library video IDs: {sample_ids}")
                    
            except Exception as e:
                self.logger.error(f"Failed to fetch library songs: {e}")
                self._library_cache = []
        
        return self._library_cache
    
    def get_liked_songs_cached(self) -> Set[str]:
        """Get liked songs with caching for performance."""
        if self._liked_cache is None:
            if not self.ytmusic:
                raise RuntimeError("Not authenticated")
            
            self.logger.info("Fetching liked songs...")
            try:
                liked_playlist = self.ytmusic.get_liked_songs(limit=None)
                self.logger.info(f"Liked playlist response keys: {list(liked_playlist.keys()) if liked_playlist else 'None'}")
                
                if 'tracks' in liked_playlist:
                    liked_tracks = liked_playlist['tracks']
                    self.logger.info(f"Raw liked tracks count: {len(liked_tracks)}")
                    
                    self._liked_cache = {track.get('videoId') for track in liked_tracks if track.get('videoId')}
                    self.logger.info(f"Loaded {len(self._liked_cache)} liked song video IDs")
                    
                    # Debug: Log some sample liked IDs
                    if self._liked_cache:
                        sample_liked = list(self._liked_cache)[:3]
                        self.logger.debug(f"Sample liked video IDs: {sample_liked}")
                        
                elif 'trackCount' in liked_playlist:
                    track_count = liked_playlist['trackCount']
                    self.logger.warning(f"Liked playlist says it has {track_count} tracks but no tracks found")
                    self._liked_cache = set()
                else:
                    self.logger.warning("No tracks or trackCount found in liked playlist response")
                    self._liked_cache = set()
                    
            except Exception as e:
                self.logger.error(f"Could not fetch liked songs: {e}")
                self._liked_cache = set()
        
        return self._liked_cache
    
    def clean_playlist(self, playlist_url_or_id: str, remove_liked: bool = True, deduplicate_against_library: bool = True) -> CleanupResult:
        """Clean a playlist by removing liked songs and duplicates from library."""
        start_time = time.time()
        
        playlist_id = self.extract_playlist_id(playlist_url_or_id)
        if not playlist_id:
            raise ValueError(f"Could not extract playlist ID from: {playlist_url_or_id}")
        
        self.logger.info(f"Starting cleanup for playlist: {playlist_id}")
        
        # Get playlist info
        try:
            playlist_info = self.ytmusic.get_playlist(playlist_id, limit=1)
            playlist_name = playlist_info.get('title', 'Unknown Playlist')
        except Exception:
            playlist_name = f"Playlist {playlist_id}"
        
        # Get all tracks from playlist
        tracks = self.get_playlist_tracks_robust(playlist_id)
        original_count = len(tracks)
        
        self.logger.info(f"Found {original_count} tracks in playlist")
        
        errors = []
        tracks_to_remove = []
        
        # Get liked songs and library if needed
        liked_songs = set()
        library_video_ids = set()
        
        if remove_liked:
            liked_songs = self.get_liked_songs_cached()
        
        if deduplicate_against_library:
            library_songs = self.get_library_songs_cached()
            library_video_ids = {song.get('videoId') for song in library_songs if song.get('videoId')}
        
        # Identify tracks to remove
        removed_liked = 0
        removed_duplicates = 0
        
        self.logger.info(f"Analyzing {len(tracks)} tracks for removal...")
        self.logger.info(f"Liked songs set size: {len(liked_songs)}")
        self.logger.info(f"Library video IDs set size: {len(library_video_ids)}")
        
        for i, track in enumerate(tracks):
            should_remove = False
            
            # Debug first few tracks
            if i < 5:
                self.logger.debug(f"Track {i}: {track.title} - {track.video_id}")
                self.logger.debug(f"  In liked: {track.video_id in liked_songs}")
                self.logger.debug(f"  In library: {track.video_id in library_video_ids}")
            
            if remove_liked and track.video_id in liked_songs:
                should_remove = True
                removed_liked += 1
                self.logger.debug(f"Marking for removal (liked): {track.title}")
            
            elif deduplicate_against_library and track.video_id in library_video_ids:
                should_remove = True
                removed_duplicates += 1
                self.logger.debug(f"Marking for removal (in library): {track.title}")
            
            if should_remove and track.set_video_id:
                tracks_to_remove.append({
                    'videoId': track.video_id,
                    'setVideoId': track.set_video_id
                })
            elif should_remove and not track.set_video_id:
                self.logger.warning(f"Track marked for removal but no setVideoId: {track.title}")
        
        self.logger.info(f"Analysis complete: {removed_liked} liked, {removed_duplicates} duplicates, {len(tracks_to_remove)} total to remove")
        
        # Remove tracks in batches
        if tracks_to_remove:
            self.logger.info(f"Removing {len(tracks_to_remove)} tracks from playlist")
            
            # Process in batches to avoid API limits
            batch_size = 50
            for i in range(0, len(tracks_to_remove), batch_size):
                batch = tracks_to_remove[i:i + batch_size]
                try:
                    self.ytmusic.remove_playlist_items(playlist_id, batch)
                    self.logger.info(f"Removed batch {i//batch_size + 1} ({len(batch)} tracks)")
                    time.sleep(1)  # Rate limiting
                except Exception as e:
                    error_msg = f"Error removing batch {i//batch_size + 1}: {e}"
                    errors.append(error_msg)
                    self.logger.error(error_msg)
        
        final_count = original_count - len(tracks_to_remove)
        processing_time = time.time() - start_time
        
        result = CleanupResult(
            playlist_id=playlist_id,
            playlist_name=playlist_name,
            original_count=original_count,
            removed_liked=removed_liked,
            removed_duplicates=removed_duplicates,
            final_count=final_count,
            errors=errors,
            processing_time=processing_time
        )
        
        self.logger.info(f"Cleanup completed in {processing_time:.2f}s. Removed {len(tracks_to_remove)} tracks.")
        
        return result
    
    def clear_cache(self):
        """Clear cached data to force refresh."""
        self._library_cache = None
        self._liked_cache = None
    
    def normalize_text(self, text: str) -> str:
        """Normalize text for comparison."""
        if not text:
            return ""
        
        # Remove version indicators
        text = re.sub(r'\s*\([^)]*(?:remaster|mix|version|edit|live|acoustic|demo|feat|featuring|explicit|clean)[^)]*\)', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\s*\[[^\]]*(?:remaster|mix|version|edit|live|acoustic|demo|feat|featuring|explicit|clean)[^\]]*\]', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\s*\(?\d{4}\)?', '', text)
        text = re.sub(r'[^\w\s]', '', text)
        text = re.sub(r'\s+', ' ', text)
        
        return text.lower().strip()
    
    def similarity_score(self, text1: str, text2: str) -> float:
        """Calculate similarity between two strings."""
        return SequenceMatcher(None, text1, text2).ratio()
    
    def find_library_duplicates_with_similarity(self, playlist_tracks: List[PlaylistTrack], similarity_threshold: float = 0.85) -> Dict[str, Any]:
        """Find playlist tracks that match tracks in the library using similarity matching."""
        library_songs = self.get_library_songs_cached()
        
        self.logger.info(f"Comparing {len(playlist_tracks)} playlist tracks against {len(library_songs)} library tracks with similarity matching...")
        
        # Create lookup structures for library tracks
        library_video_ids = {track.get('videoId') for track in library_songs if track.get('videoId')}
        
        # Create normalized lookup for similarity matching
        library_normalized = {}
        for track in library_songs:
            title = self.normalize_text(track.get('title', ''))
            artists = [a.get('name', '') for a in track.get('artists', []) if a.get('name')]
            
            if title and artists:
                for artist in artists:
                    artist_norm = self.normalize_text(artist)
                    key = f"{title}|{artist_norm}"
                    if key not in library_normalized:
                        library_normalized[key] = []
                    library_normalized[key].append(track)
        
        self.logger.info(f"Created lookup index for {len(library_normalized)} unique title-artist combinations")
        
        matches = []
        processed = 0
        
        for playlist_track in playlist_tracks:
            processed += 1
            if processed % 100 == 0:
                self.logger.info(f"Processed {processed}/{len(playlist_tracks)} tracks...")
            
            video_id = playlist_track.video_id
            
            # Strategy 1: Exact video ID match
            if video_id and video_id in library_video_ids:
                matches.append({
                    'playlist_track': playlist_track,
                    'match_type': 'exact_video_id',
                    'confidence': 1.0,
                    'library_matches': [{'videoId': video_id, 'reason': 'Exact video ID match'}]
                })
                continue
            
            # Strategy 2: Similarity matching
            playlist_title = self.normalize_text(playlist_track.title)
            playlist_artists = playlist_track.artists
            
            if not playlist_title or not playlist_artists:
                continue
            
            best_matches = []
            
            for playlist_artist in playlist_artists:
                playlist_artist_norm = self.normalize_text(playlist_artist)
                lookup_key = f"{playlist_title}|{playlist_artist_norm}"
                
                # Direct lookup first
                if lookup_key in library_normalized:
                    for lib_track in library_normalized[lookup_key]:
                        best_matches.append({
                            'library_track': lib_track,
                            'similarity': 1.0,
                            'reason': 'Exact normalized match'
                        })
                
                # Fuzzy matching for close matches
                else:
                    for lib_key, lib_tracks in library_normalized.items():
                        similarity = self.similarity_score(lookup_key, lib_key)
                        if similarity >= similarity_threshold:
                            for lib_track in lib_tracks:
                                best_matches.append({
                                    'library_track': lib_track,
                                    'similarity': similarity,
                                    'reason': f'Similarity match ({similarity:.1%})'
                                })
            
            if best_matches:
                # Sort by similarity and take best matches
                best_matches.sort(key=lambda x: x['similarity'], reverse=True)
                top_matches = best_matches[:3]  # Top 3 matches
                
                confidence = top_matches[0]['similarity'] * 0.9  # Slight confidence reduction for similarity matches
                
                matches.append({
                    'playlist_track': playlist_track,
                    'match_type': 'similarity',
                    'confidence': confidence,
                    'library_matches': top_matches
                })
        
        self.logger.info(f"Found {len(matches)} playlist tracks that exist in your library")
        
        # Separate high confidence and needs review
        high_confidence = [m for m in matches if m['confidence'] >= 0.95]
        needs_review = [m for m in matches if m['confidence'] < 0.95]
        
        return {
            'total_matches': len(matches),
            'high_confidence': high_confidence,
            'needs_review': needs_review,
            'all_matches': matches
        }
    
    def clean_playlist_with_similarity(self, playlist_url_or_id: str, remove_liked: bool = True, 
                                     deduplicate_against_library: bool = True, similarity_threshold: float = 0.85,
                                     auto_remove_high_confidence: bool = True) -> Dict[str, Any]:
        """Enhanced playlist cleaning with similarity-based duplicate detection."""
        start_time = time.time()
        
        playlist_id = self.extract_playlist_id(playlist_url_or_id)
        if not playlist_id:
            raise ValueError(f"Could not extract playlist ID from: {playlist_url_or_id}")
        
        self.logger.info(f"Starting enhanced cleanup for playlist: {playlist_id}")
        
        # Get playlist info
        try:
            playlist_info = self.ytmusic.get_playlist(playlist_id, limit=1)
            playlist_name = playlist_info.get('title', 'Unknown Playlist')
        except Exception:
            playlist_name = f"Playlist {playlist_id}"
        
        # Get all tracks from playlist
        tracks = self.get_playlist_tracks_robust(playlist_id)
        original_count = len(tracks)
        
        self.logger.info(f"Found {original_count} tracks in playlist")
        
        errors = []
        tracks_to_remove = []
        
        # Get liked songs if needed
        liked_songs = set()
        if remove_liked:
            liked_songs = self.get_liked_songs_cached()
        
        # Find similarity-based library duplicates if needed
        similarity_matches = {'total_matches': 0, 'high_confidence': [], 'needs_review': [], 'all_matches': []}
        if deduplicate_against_library:
            similarity_matches = self.find_library_duplicates_with_similarity(tracks, similarity_threshold)
        
        # Identify tracks to remove
        removed_liked = 0
        removed_duplicates = 0
        
        # Create sets for quick lookup
        high_confidence_video_ids = {m['playlist_track'].video_id for m in similarity_matches['high_confidence']}
        
        for track in tracks:
            should_remove = False
            
            if remove_liked and track.video_id in liked_songs:
                should_remove = True
                removed_liked += 1
                self.logger.debug(f"Marking for removal (liked): {track.title}")
            
            elif deduplicate_against_library and auto_remove_high_confidence and track.video_id in high_confidence_video_ids:
                should_remove = True
                removed_duplicates += 1
                self.logger.debug(f"Marking for removal (high confidence library duplicate): {track.title}")
            
            if should_remove and track.set_video_id:
                tracks_to_remove.append({
                    'videoId': track.video_id,
                    'setVideoId': track.set_video_id
                })
            elif should_remove and not track.set_video_id:
                self.logger.warning(f"Track marked for removal but no setVideoId: {track.title}")
        
        self.logger.info(f"Analysis complete: {removed_liked} liked, {removed_duplicates} high-confidence duplicates, {len(tracks_to_remove)} total to remove")
        
        # Remove tracks in batches
        removal_errors = []
        if tracks_to_remove:
            self.logger.info(f"Removing {len(tracks_to_remove)} tracks from playlist")
            
            batch_size = 50
            for i in range(0, len(tracks_to_remove), batch_size):
                batch = tracks_to_remove[i:i + batch_size]
                try:
                    self.ytmusic.remove_playlist_items(playlist_id, batch)
                    self.logger.info(f"Removed batch {i//batch_size + 1} ({len(batch)} tracks)")
                    time.sleep(1)  # Rate limiting
                except Exception as e:
                    error_msg = f"Error removing batch {i//batch_size + 1}: {e}"
                    removal_errors.append(error_msg)
                    self.logger.error(error_msg)
        
        final_count = original_count - len(tracks_to_remove)
        processing_time = time.time() - start_time
        
        result = {
            'playlist_id': playlist_id,
            'playlist_name': playlist_name,
            'original_count': original_count,
            'removed_liked': removed_liked,
            'removed_duplicates': removed_duplicates,
            'final_count': final_count,
            'processing_time': processing_time,
            'similarity_matches': similarity_matches,
            'errors': removal_errors
        }
        
        self.logger.info(f"Enhanced cleanup completed in {processing_time:.2f}s. Removed {len(tracks_to_remove)} tracks.")
        
        return result
    
    def create_track_signature(self, track: PlaylistTrack) -> str:
        """Create a normalized signature for a track for duplicate detection."""
        title = self.normalize_text(track.title)
        artist_str = self.normalize_text(' '.join(track.artists))
        
        return f"{title}|{artist_str}"
    
    def find_playlist_internal_duplicates(self, playlist_tracks: List[PlaylistTrack]) -> List[DuplicateGroup]:
        """Find duplicate tracks within the playlist itself."""
        
        self.logger.info(f"Analyzing {len(playlist_tracks)} playlist tracks for internal duplicates...")
        
        # Group tracks by signature
        signature_groups = defaultdict(list)
        
        for track in playlist_tracks:
            signature = self.create_track_signature(track)
            if signature:  # Only process tracks with valid signatures
                signature_groups[signature].append(track)
        
        # Find groups with duplicates
        duplicates = []
        total_duplicate_tracks = 0
        
        for signature, tracks in signature_groups.items():
            if len(tracks) > 1:
                duplicate_group = DuplicateGroup(
                    signature=signature,
                    tracks=tracks,
                    duplicate_count=len(tracks),
                    tracks_to_keep=[],
                    tracks_to_remove=[],
                    confidence=self._calculate_duplicate_confidence(tracks),
                    review_needed=self._duplicate_needs_review(tracks)
                )
                duplicates.append(duplicate_group)
                total_duplicate_tracks += len(tracks) - 1  # -1 because we keep one
                
                self.logger.info(f"Found {len(tracks)} copies of: {signature}")
        
        self.logger.info(f"Found {len(duplicates)} duplicate groups with {total_duplicate_tracks} tracks to remove")
        return duplicates
    
    def _calculate_duplicate_confidence(self, tracks: List[PlaylistTrack]) -> float:
        """Calculate confidence for automatic removal."""
        count = len(tracks)
        if count == 2:
            return 0.9  # High confidence for simple duplicates
        elif count <= 5:
            return 0.7  # Medium confidence for small groups
        else:
            return 0.5  # Lower confidence for large groups
    
    def _duplicate_needs_review(self, tracks: List[PlaylistTrack]) -> bool:
        """Determine if this duplicate group needs manual review."""
        count = len(tracks)
        
        # Review if confidence is low
        if self._calculate_duplicate_confidence(tracks) < 0.8:
            return True
        
        # Review if there are many duplicates
        if count > 3:
            return True
        
        # Review if tracks have very different durations (might be different versions)
        durations = [self._parse_duration(t.duration) for t in tracks if t.duration]
        
        if len(durations) > 1:
            max_dur = max(durations)
            min_dur = min(durations)
            if max_dur > 0 and (max_dur - min_dur) / max_dur > 0.2:  # >20% difference
                return True
        
        return False
    
    def _parse_duration(self, duration_str: Optional[str]) -> int:
        """Parse duration string to seconds."""
        if not duration_str or ':' not in duration_str:
            return 0
        
        try:
            parts = duration_str.split(':')
            if len(parts) == 2:
                return int(parts[0]) * 60 + int(parts[1])
            elif len(parts) == 3:
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        except:
            pass
        
        return 0
    
    def deduplicate_playlist_internal(self, playlist_url_or_id: str, auto_remove: bool = False) -> Dict[str, Any]:
        """Remove internal duplicates from a playlist."""
        start_time = time.time()
        
        playlist_id = self.extract_playlist_id(playlist_url_or_id)
        if not playlist_id:
            raise ValueError(f"Could not extract playlist ID from: {playlist_url_or_id}")
        
        self.logger.info(f"Starting internal deduplication for playlist: {playlist_id}")
        
        # Get playlist info
        try:
            playlist_info = self.ytmusic.get_playlist(playlist_id, limit=1)
            playlist_name = playlist_info.get('title', 'Unknown Playlist')
        except Exception:
            playlist_name = f"Playlist {playlist_id}"
        
        # Get all tracks from playlist
        tracks = self.get_playlist_tracks_robust(playlist_id)
        original_count = len(tracks)
        
        self.logger.info(f"Found {original_count} tracks in playlist")
        
        # Find duplicates
        duplicates = self.find_playlist_internal_duplicates(tracks)
        
        if not duplicates:
            self.logger.info("🎉 No internal duplicates found! Playlist is already clean.")
            return {
                'playlist_id': playlist_id,
                'playlist_name': playlist_name,
                'original_count': original_count,
                'duplicate_groups': 0,
                'auto_removed': 0,
                'needs_review': 0,
                'final_count': original_count,
                'processing_time': time.time() - start_time,
                'duplicates': [],
                'errors': []
            }
        
        # Separate auto-remove candidates and review needed
        auto_remove_candidates = [dup for dup in duplicates if not dup.review_needed]
        needs_review = [dup for dup in duplicates if dup.review_needed]
        
        # Auto-remove high confidence duplicates if requested
        tracks_to_remove = []
        errors = []
        
        if auto_remove and auto_remove_candidates:
            self.logger.info(f"Auto-removing {len(auto_remove_candidates)} high-confidence duplicate groups...")
            
            for duplicate_group in auto_remove_candidates:
                for track in duplicate_group.tracks_to_remove:
                    if track.set_video_id:
                        tracks_to_remove.append({
                            'videoId': track.video_id,
                            'setVideoId': track.set_video_id
                        })
                        self.logger.info(f"REMOVING: {track.title} by {', '.join(track.artists)}")
            
            # Remove in batches
            if tracks_to_remove:
                batch_size = 50
                for i in range(0, len(tracks_to_remove), batch_size):
                    batch = tracks_to_remove[i:i + batch_size]
                    try:
                        self.ytmusic.remove_playlist_items(playlist_id, batch)
                        self.logger.info(f"Removed batch {i//batch_size + 1} ({len(batch)} tracks)")
                        time.sleep(1)  # Rate limiting
                    except Exception as e:
                        error_msg = f"Failed to remove batch {i//batch_size + 1}: {e}"
                        errors.append(error_msg)
                        self.logger.error(error_msg)
        
        final_count = original_count - len(tracks_to_remove)
        processing_time = time.time() - start_time
        
        # Convert duplicates to serializable format
        duplicates_data = []
        for dup in duplicates:
            duplicates_data.append({
                'signature': dup.signature,
                'duplicate_count': dup.duplicate_count,
                'confidence': dup.confidence,
                'review_needed': dup.review_needed,
                'tracks_to_keep': [{
                    'videoId': t.video_id,
                    'setVideoId': t.set_video_id,
                    'title': t.title,
                    'artists': t.artists,
                    'duration': t.duration
                } for t in dup.tracks_to_keep],
                'tracks_to_remove': [{
                    'videoId': t.video_id,
                    'setVideoId': t.set_video_id,
                    'title': t.title,
                    'artists': t.artists,
                    'duration': t.duration
                } for t in dup.tracks_to_remove]
            })
        
        result = {
            'playlist_id': playlist_id,
            'playlist_name': playlist_name,
            'original_count': original_count,
            'duplicate_groups': len(duplicates),
            'auto_removed': len(tracks_to_remove),
            'needs_review': len(needs_review),
            'final_count': final_count,
            'processing_time': processing_time,
            'duplicates': duplicates_data,
            'errors': errors
        }
        
        self.logger.info(f"Internal deduplication completed in {processing_time:.2f}s. Removed {len(tracks_to_remove)} duplicate tracks.")
        
        return result