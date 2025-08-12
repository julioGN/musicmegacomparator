#!/usr/bin/env python3
"""
Playlist internal deduplication - removes duplicates within the playlist itself.
"""

import json
import logging
import time
from pathlib import Path
from typing import List, Set, Dict, Any, Tuple
import sys
from difflib import SequenceMatcher
import re
from collections import defaultdict

try:
    from ytmusicapi import YTMusic
except ImportError:
    print("ytmusicapi not installed. Run: pip install ytmusicapi")
    sys.exit(1)


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)


def extract_playlist_id(url_or_id: str) -> str:
    """Extract playlist ID from URL."""
    if url_or_id.startswith('PL'):
        return url_or_id
    
    if 'list=' in url_or_id:
        return url_or_id.split('list=')[1].split('&')[0]
    
    raise ValueError(f"Could not extract playlist ID from: {url_or_id}")


def normalize_text(text: str) -> str:
    """Normalize text for comparison by removing extra characters and converting to lowercase."""
    if not text:
        return ""
    
    # Remove common parenthetical content that differs between versions
    text = re.sub(r'\s*\([^)]*(?:remaster|mix|version|edit|live|acoustic|demo|feat|featuring|explicit|clean)[^)]*\)', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s*\[[^\]]*(?:remaster|mix|version|edit|live|acoustic|demo|feat|featuring|explicit|clean)[^\]]*\]', '', text, flags=re.IGNORECASE)
    
    # Remove year indicators
    text = re.sub(r'\s*\(?\d{4}\)?', '', text)
    
    # Remove special characters and extra spaces
    text = re.sub(r'[^\w\s]', '', text)
    text = re.sub(r'\s+', ' ', text)
    
    return text.lower().strip()


def similarity_score(text1: str, text2: str) -> float:
    """Calculate similarity between two strings (0-1, where 1 is identical)."""
    return SequenceMatcher(None, text1, text2).ratio()


def get_artist_names(artists: List[Dict]) -> List[str]:
    """Extract artist names from artists list."""
    if not artists:
        return []
    return [artist.get('name', '') for artist in artists if artist.get('name')]


def create_track_signature(track: Dict) -> str:
    """Create a normalized signature for a track for duplicate detection."""
    title = normalize_text(track.get('title', ''))
    artists = get_artist_names(track.get('artists', []))
    artist_str = normalize_text(' '.join(artists))
    
    return f"{title}|{artist_str}"


class PlaylistDuplicate:
    def __init__(self, signature: str, tracks: List[Dict]):
        self.signature = signature
        self.tracks = tracks  # List of all tracks with this signature
        self.duplicate_count = len(tracks)
        self.tracks_to_keep = []
        self.tracks_to_remove = []
        self.confidence = self._calculate_confidence()
        self.review_needed = self._needs_review()
        
        self._decide_which_to_keep()
    
    def _calculate_confidence(self) -> float:
        """Calculate confidence for automatic removal."""
        if self.duplicate_count == 2:
            return 0.9  # High confidence for simple duplicates
        elif self.duplicate_count <= 5:
            return 0.7  # Medium confidence for small groups
        else:
            return 0.5  # Lower confidence for large groups
    
    def _needs_review(self) -> bool:
        """Determine if this duplicate group needs manual review."""
        # Review if confidence is low
        if self.confidence < 0.8:
            return True
        
        # Review if there are many duplicates
        if self.duplicate_count > 3:
            return True
        
        # Review if tracks have very different durations (might be different versions)
        durations = [self._parse_duration(t.get('duration', '')) for t in self.tracks]
        durations = [d for d in durations if d > 0]
        
        if len(durations) > 1:
            max_dur = max(durations)
            min_dur = min(durations)
            if max_dur > 0 and (max_dur - min_dur) / max_dur > 0.2:  # >20% difference
                return True
        
        return False
    
    def _parse_duration(self, duration_str: str) -> int:
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
    
    def _decide_which_to_keep(self):
        """Decide which track to keep and which to remove."""
        if not self.tracks:
            return
        
        # Sort tracks by preference (prefer studio versions, shorter titles, etc.)
        sorted_tracks = sorted(self.tracks, key=self._track_preference_score)
        
        # Keep the first (best) track
        self.tracks_to_keep = [sorted_tracks[0]]
        self.tracks_to_remove = sorted_tracks[1:]
    
    def _track_preference_score(self, track: Dict) -> tuple:
        """Score for track preference (lower is better)."""
        title = track.get('title', '').lower()
        
        # Penalty for live versions
        live_penalty = 1 if any(word in title for word in ['live', 'concert', 'tour']) else 0
        
        # Penalty for remixes/alternate versions
        remix_penalty = 1 if any(word in title for word in ['remix', 'alternate', 'demo', 'acoustic']) else 0
        
        # Penalty for explicit versions (prefer clean)
        explicit_penalty = 1 if 'explicit' in title else 0
        
        # Prefer shorter titles (often original versions)
        title_length_penalty = len(title) / 100
        
        return (live_penalty, remix_penalty, explicit_penalty, title_length_penalty)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'signature': self.signature,
            'duplicate_count': self.duplicate_count,
            'confidence': self.confidence,
            'review_needed': self.review_needed,
            'tracks_to_keep': [
                {
                    'videoId': track.get('videoId'),
                    'setVideoId': track.get('setVideoId'),
                    'title': track.get('title'),
                    'artists': [a.get('name') for a in track.get('artists', [])],
                    'duration': track.get('duration')
                }
                for track in self.tracks_to_keep
            ],
            'tracks_to_remove': [
                {
                    'videoId': track.get('videoId'),
                    'setVideoId': track.get('setVideoId'),
                    'title': track.get('title'),
                    'artists': [a.get('name') for a in track.get('artists', [])],
                    'duration': track.get('duration')
                }
                for track in self.tracks_to_remove
            ]
        }


def find_playlist_duplicates(playlist_tracks: List[Dict], logger) -> List[PlaylistDuplicate]:
    """Find duplicate tracks within the playlist."""
    
    logger.info(f"Analyzing {len(playlist_tracks)} playlist tracks for internal duplicates...")
    
    # Group tracks by signature
    signature_groups = defaultdict(list)
    
    for track in playlist_tracks:
        signature = create_track_signature(track)
        if signature:  # Only process tracks with valid signatures
            signature_groups[signature].append(track)
    
    # Find groups with duplicates
    duplicates = []
    total_duplicate_tracks = 0
    
    for signature, tracks in signature_groups.items():
        if len(tracks) > 1:
            duplicate_group = PlaylistDuplicate(signature, tracks)
            duplicates.append(duplicate_group)
            total_duplicate_tracks += len(tracks) - 1  # -1 because we keep one
            
            logger.info(f"Found {len(tracks)} copies of: {signature}")
    
    logger.info(f"Found {len(duplicates)} duplicate groups with {total_duplicate_tracks} tracks to remove")
    return duplicates


def save_dedup_review_data(duplicates: List[PlaylistDuplicate], output_file: str, logger):
    """Save duplicates that need review to JSON file."""
    
    auto_remove = [dup for dup in duplicates if not dup.review_needed]
    needs_review = [dup for dup in duplicates if dup.review_needed]
    
    total_auto_remove = sum(len(dup.tracks_to_remove) for dup in auto_remove)
    total_review = sum(len(dup.tracks_to_remove) for dup in needs_review)
    
    review_data = {
        'summary': {
            'total_duplicate_groups': len(duplicates),
            'auto_remove_groups': len(auto_remove),
            'auto_remove_tracks': total_auto_remove,
            'review_groups': len(needs_review),
            'review_tracks': total_review,
            'generated_at': time.strftime('%Y-%m-%d %H:%M:%S')
        },
        'auto_remove': [dup.to_dict() for dup in auto_remove],
        'needs_review': [dup.to_dict() for dup in needs_review]
    }
    
    with open(output_file, 'w') as f:
        json.dump(review_data, f, indent=2)
    
    logger.info(f"Review data saved to {output_file}")
    logger.info(f"Auto-remove: {len(auto_remove)} groups ({total_auto_remove} tracks)")
    logger.info(f"Manual review: {len(needs_review)} groups ({total_review} tracks)")


def deduplicate_playlist(ytmusic: YTMusic, playlist_id: str, logger, auto_remove: bool = False, review_file: str = None):
    """Deduplicate tracks within the playlist."""
    
    logger.info("Starting playlist internal deduplication")
    
    # Fetch playlist tracks
    logger.info("Fetching all playlist tracks...")
    playlist_data = ytmusic.get_playlist(playlist_id, limit=None)
    playlist_tracks = playlist_data.get('tracks', [])
    playlist_title = playlist_data.get('title', 'Unknown Playlist')
    
    logger.info(f"Playlist: '{playlist_title}' with {len(playlist_tracks)} tracks")
    
    # Find duplicates
    duplicates = find_playlist_duplicates(playlist_tracks, logger)
    
    if not duplicates:
        logger.info("🎉 No duplicates found! Playlist is already clean.")
        return
    
    # Save review data
    if review_file:
        save_dedup_review_data(duplicates, review_file, logger)
    
    # Auto-remove high confidence duplicates if requested
    if auto_remove:
        auto_candidates = [dup for dup in duplicates if not dup.review_needed]
        
        if auto_candidates:
            logger.info(f"Auto-removing {len(auto_candidates)} high-confidence duplicate groups...")
            
            tracks_to_remove = []
            for duplicate_group in auto_candidates:
                for track in duplicate_group.tracks_to_remove:
                    if track.get('videoId') and track.get('setVideoId'):
                        tracks_to_remove.append({
                            'videoId': track['videoId'],
                            'setVideoId': track['setVideoId']
                        })
                        logger.info(f"REMOVING: {track.get('title')} by {', '.join(track.get('artists', []))}")
            
            # Remove in batches
            if tracks_to_remove:
                batch_size = 50
                for i in range(0, len(tracks_to_remove), batch_size):
                    batch = tracks_to_remove[i:i + batch_size]
                    try:
                        ytmusic.remove_playlist_items(playlist_id, batch)
                        logger.info(f"Removed batch {i//batch_size + 1} ({len(batch)} tracks)")
                        time.sleep(1)  # Rate limiting
                    except Exception as e:
                        logger.error(f"Failed to remove batch {i//batch_size + 1}: {e}")
                
                logger.info(f"Auto-removal complete! Removed {len(tracks_to_remove)} duplicate tracks")
        else:
            logger.info("No high-confidence duplicates found for auto-removal")


def main():
    logger = setup_logging()
    
    # Configuration
    headers_path = "/Users/guerrero/Documents/musiccode/headers_auth.json"
    if not Path(headers_path).exists():
        logger.error(f"Headers file not found: {headers_path}")
        return
    
    playlist_url = "https://music.youtube.com/playlist?list=PL1LO5jourf4MqCSX94juP7bWk2eYTMCQ2&si=gSS-xtZtM7xT-j4l"
    playlist_id = extract_playlist_id(playlist_url)
    
    # Options
    review_file = "/Users/guerrero/Documents/musiccode/playlist_dedup_review.json"
    auto_remove = False  # Set to True to automatically remove high-confidence duplicates
    
    # Authenticate
    logger.info("Authenticating...")
    ytmusic = YTMusic(headers_path)
    
    # Run deduplication
    deduplicate_playlist(ytmusic, playlist_id, logger, auto_remove=auto_remove, review_file=review_file)
    
    logger.info(f"\nNext steps:")
    logger.info(f"1. Review the duplicates in: {review_file}")
    logger.info(f"2. Use the web app to manually review uncertain cases")
    logger.info(f"3. Re-run with auto_remove=True to automatically remove confirmed duplicates")


if __name__ == "__main__":
    main()