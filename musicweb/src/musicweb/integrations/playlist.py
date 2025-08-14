"""
Playlist management and YouTube Music integration.
"""

import json
import time
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
import requests

from ..core.models import Track, TrackMatcher

# Optional YouTube Music API
try:
    from ytmusicapi import YTMusic
    from ytmusicapi.exceptions import YTMusicServerError
    HAVE_YTMUSIC = True
except ImportError:
    HAVE_YTMUSIC = False


class PlaylistManager:
    """Manage playlist creation and track searching."""
    
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
            
            # Perform search
            results = self.ytmusic.search(query, filter='songs', limit=limit)
            
            # Process and score results
            scored_results = []
            matcher = TrackMatcher(strict_mode=False)  # More lenient for search
            
            for result in results:
                if result.get('resultType') != 'song':
                    continue
                
                # Convert result to Track for comparison
                result_track = self._youtube_result_to_track(result)
                if not result_track:
                    continue
                
                # Calculate similarity
                confidence = matcher.calculate_match_confidence(track, result_track)
                
                scored_results.append({
                    'youtube_track': result,
                    'confidence': confidence,
                    'title': result_track.title,
                    'artist': result_track.artist,
                    'album': result_track.album,
                    'duration': result_track.duration
                })
            
            # Sort by confidence
            scored_results.sort(key=lambda x: x['confidence'], reverse=True)
            return scored_results
        
        except Exception as e:
            print(f"Search failed for '{track.title}' by '{track.artist}': {e}")
            # Check for specific JSON parsing errors
            if "Expecting value" in str(e):
                print(f"JSON parsing error - possible empty response from YouTube Music API")
            return []
    
    def find_best_match(self, track: Track) -> Optional[Dict[str, Any]]:
        """Find the best matching track on YouTube Music."""
        results = self.search_track(track, limit=10)
        
        if not results:
            return None
        
        # Return the best match if confidence is reasonable
        best_result = results[0]
        if best_result['confidence'] >= 0.7:  # Reasonable confidence threshold
            return best_result
        
        return None
    
    def create_playlist(self, playlist_name: str, tracks: List[Track], 
                       search_fallback: bool = True, 
                       progress_callback: Optional[callable] = None) -> Dict[str, Any]:
        """Create a YouTube Music playlist from a list of tracks."""
        if not self.is_available():
            return {
                'success': False,
                'error': 'YouTube Music not available',
                'playlist_id': None,
                'added_tracks': [],
                'failed_tracks': []
            }
        
        try:
            # Create playlist with better error handling
            response = self.ytmusic.create_playlist(
                title=playlist_name,
                description=f"Created from music library comparison tool"
            )
            
            # Check if response is valid
            if not response:
                raise Exception("Empty response from YouTube Music API")
            
            # Handle different response formats from ytmusicapi
            if isinstance(response, dict):
                playlist_id = response.get('id') or response.get('playlistId')
                if not playlist_id:
                    raise Exception(f"No playlist ID in response: {response}")
            elif isinstance(response, str):
                playlist_id = response
            else:
                raise Exception(f"Unexpected response type from YouTube Music API: {type(response)}, content: {response}")
            
            added_tracks = []
            failed_tracks = []
            
            # Process tracks in batches
            batch_size = 50
            for i in range(0, len(tracks), batch_size):
                batch = tracks[i:i + batch_size]
                
                if progress_callback:
                    progress_callback(i, len(tracks), f"Processing batch {i//batch_size + 1}")
                
                batch_results = self._add_tracks_to_playlist(
                    playlist_id, batch, search_fallback
                )
                
                # Check for batch processing errors
                if not batch_results:
                    failed_tracks.extend([{'track': t.to_dict(), 'reason': 'Batch processing failed'} for t in batch])
                else:
                    added_tracks.extend(batch_results['added'])
                    failed_tracks.extend(batch_results['failed'])
                
                # Rate limiting
                time.sleep(1.2)  # Respect API limits
            
            if progress_callback:
                progress_callback(len(tracks), len(tracks), "Playlist creation complete")
            
            return {
                'success': True,
                'playlist_id': playlist_id,
                'added_tracks': added_tracks,
                'failed_tracks': failed_tracks,
                'total_requested': len(tracks),
                'total_added': len(added_tracks),
                'total_failed': len(failed_tracks)
            }
        
        except Exception as e:
            error_msg = str(e)
            if "Expecting value" in error_msg:
                error_msg = f"YouTube Music API returned invalid response. This may be due to: 1) Authentication issues (check headers_auth.json), 2) Rate limiting, or 3) Network connectivity. Original error: {error_msg}"
            return {
                'success': False,
                'error': error_msg,
                'playlist_id': None,
                'added_tracks': [],
                'failed_tracks': [{'track': t.to_dict(), 'reason': 'Playlist creation failed'} for t in tracks]
            }
    
    def _add_tracks_to_playlist(self, playlist_id: str, tracks: List[Track], 
                               search_fallback: bool) -> Dict[str, List]:
        """Add a batch of tracks to a playlist."""
        added_tracks = []
        failed_tracks = []
        
        for track in tracks:
            try:
                # Find matching YouTube track
                match = self.find_best_match(track)
                
                if match and 'youtube_track' in match:
                    video_id = match['youtube_track'].get('videoId')
                    
                    if video_id:
                        # Add to playlist with error handling
                        try:
                            result = self.ytmusic.add_playlist_items(playlist_id, [video_id])
                            if result:  # Check if addition was successful
                                added_tracks.append({
                                    'original_track': track.to_dict(),
                                    'youtube_match': match,
                                    'confidence': match['confidence']
                                })
                            else:
                                failed_tracks.append({
                                    'track': track.to_dict(),
                                    'reason': 'Failed to add to playlist'
                                })
                        except Exception as add_error:
                            error_msg = str(add_error)
                            if "Expecting value" in error_msg:
                                error_msg = f"YouTube Music API returned invalid response (possible rate limit or authentication issue): {error_msg}"
                            failed_tracks.append({
                                'track': track.to_dict(),
                                'reason': f'Add to playlist error: {error_msg}'
                            })
                    else:
                        failed_tracks.append({
                            'track': track.to_dict(),
                            'reason': 'No video ID found'
                        })
                else:
                    failed_tracks.append({
                        'track': track.to_dict(),
                        'reason': 'No suitable match found'
                    })
                
                # Small delay between requests
                time.sleep(0.1)
            
            except Exception as e:
                failed_tracks.append({
                    'track': track.to_dict(),
                    'reason': str(e)
                })
        
        return {'added': added_tracks, 'failed': failed_tracks}
    
    def _youtube_result_to_track(self, result: Dict[str, Any]) -> Optional[Track]:
        """Convert YouTube search result to Track object."""
        try:
            title = result.get('title', '')
            
            # Extract artist info
            artists = result.get('artists', [])
            if artists and isinstance(artists, list):
                artist = ', '.join([a.get('name', '') for a in artists if a.get('name')])
            else:
                artist = ''
            
            # Extract album info
            album = None
            if 'album' in result and result['album']:
                album = result['album'].get('name', '')
            
            # Extract duration
            duration = None
            duration_text = result.get('duration', '')
            if duration_text and ':' in duration_text:
                try:
                    parts = duration_text.split(':')
                    if len(parts) == 2:
                        duration = int(parts[0]) * 60 + int(parts[1])
                except ValueError:
                    pass
            
            return Track(
                title=title,
                artist=artist,
                album=album,
                duration=duration,
                platform="youtube_music",
                track_id=result.get('videoId')
            )
        
        except Exception:
            return None
    
    def get_playlist_info(self, playlist_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a YouTube Music playlist."""
        if not self.is_available():
            return None
        
        try:
            playlist = self.ytmusic.get_playlist(playlist_id)
            
            return {
                'id': playlist_id,
                'title': playlist.get('title', ''),
                'description': playlist.get('description', ''),
                'track_count': playlist.get('trackCount', 0),
                'duration': playlist.get('duration', ''),
                'privacy': playlist.get('privacy', 'PRIVATE')
            }
        
        except Exception as e:
            print(f"Failed to get playlist info: {e}")
            return None
    
    def export_playlist(self, playlist_id: str, output_file: str) -> bool:
        """Export a YouTube Music playlist to CSV."""
        if not self.is_available():
            return False
        
        try:
            playlist = self.ytmusic.get_playlist(playlist_id, limit=None)
            tracks = playlist.get('tracks', [])
            
            # Convert to CSV
            import csv
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                fieldnames = ['title', 'artist', 'album', 'duration', 'video_id']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                
                for track in tracks:
                    artists = track.get('artists', [])
                    artist_names = ', '.join([a.get('name', '') for a in artists if a.get('name')])
                    
                    album_name = ''
                    if track.get('album'):
                        album_name = track['album'].get('name', '')
                    
                    writer.writerow({
                        'title': track.get('title', ''),
                        'artist': artist_names,
                        'album': album_name,
                        'duration': track.get('duration', ''),
                        'video_id': track.get('videoId', '')
                    })
            
            return True
        
        except Exception as e:
            print(f"Failed to export playlist: {e}")
            return False


class PlaylistAnalyzer:
    """Analyze and validate playlists."""
    
    def __init__(self, playlist_manager: Optional[PlaylistManager] = None):
        self.playlist_manager = playlist_manager
    
    def validate_tracks(self, tracks: List[Track]) -> Dict[str, Any]:
        """Validate tracks for playlist creation."""
        valid_tracks = []
        invalid_tracks = []
        warnings = []
        
        for track in tracks:
            issues = []
            
            # Check required fields
            if not track.title or not track.title.strip():
                issues.append("Missing title")
            if not track.artist or not track.artist.strip():
                issues.append("Missing artist")
            
            # Check for problematic content
            if not track.is_music:
                issues.append("Non-music content detected")
            
            # Check title length
            if len(track.title) > 100:
                warnings.append(f"Very long title: {track.title[:50]}...")
            
            if issues:
                invalid_tracks.append({
                    'track': track,
                    'issues': issues
                })
            else:
                valid_tracks.append(track)
        
        return {
            'valid_tracks': valid_tracks,
            'invalid_tracks': invalid_tracks,
            'warnings': warnings,
            'validation_passed': len(invalid_tracks) == 0
        }
    
    def analyze_playlist_potential(self, tracks: List[Track]) -> Dict[str, Any]:
        """Analyze how well tracks might match on YouTube Music."""
        if not self.playlist_manager or not self.playlist_manager.is_available():
            return {
                'analysis_available': False,
                'message': 'YouTube Music not available for analysis'
            }
        
        # Sample a subset of tracks for analysis
        sample_size = min(10, len(tracks))
        sample_tracks = tracks[:sample_size]
        
        match_results = []
        for track in sample_tracks:
            results = self.playlist_manager.search_track(track, limit=1)
            if results:
                match_results.append({
                    'track': track,
                    'best_match_confidence': results[0]['confidence'],
                    'has_good_match': results[0]['confidence'] >= 0.8
                })
            else:
                match_results.append({
                    'track': track,
                    'best_match_confidence': 0.0,
                    'has_good_match': False
                })
        
        # Calculate statistics
        good_matches = sum(1 for r in match_results if r['has_good_match'])
        avg_confidence = sum(r['best_match_confidence'] for r in match_results) / len(match_results)
        
        return {
            'analysis_available': True,
            'sample_size': sample_size,
            'total_tracks': len(tracks),
            'good_matches': good_matches,
            'good_match_rate': good_matches / sample_size,
            'avg_confidence': avg_confidence,
            'estimated_success_rate': good_matches / sample_size,
            'recommendation': self._get_recommendation(good_matches / sample_size, avg_confidence)
        }
    
    def _get_recommendation(self, success_rate: float, avg_confidence: float) -> str:
        """Get recommendation based on analysis."""
        if success_rate >= 0.8 and avg_confidence >= 0.8:
            return "Excellent match potential - proceed with confidence"
        elif success_rate >= 0.6 and avg_confidence >= 0.7:
            return "Good match potential - most tracks should be found"
        elif success_rate >= 0.4 and avg_confidence >= 0.6:
            return "Moderate match potential - expect some missing tracks"
        else:
            return "Low match potential - many tracks may not be found"