#!/usr/bin/env python3
"""
Debug script to understand what's happening with playlist fetching.
"""

import logging
import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))

from musiclib.playlist_cleaner import PlaylistCleaner

def debug_playlist_fetch():
    """Debug the playlist fetching process."""
    
    # Setup logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # You'll need to provide your headers file path
    headers_path = input("Enter path to your headers_auth.json file: ").strip()
    if not Path(headers_path).exists():
        print(f"Headers file not found: {headers_path}")
        return
    
    playlist_url = "https://music.youtube.com/playlist?list=PL1LO5jourf4MqCSX94juP7bWk2eYTMCQ2&si=-idwc0lg2KK0LYnq"
    
    print("Creating playlist cleaner...")
    cleaner = PlaylistCleaner(headers_path=headers_path)
    
    print("\n=== DEBUGGING PLAYLIST FETCH ===")
    playlist_id = cleaner.extract_playlist_id(playlist_url)
    print(f"Extracted playlist ID: {playlist_id}")
    
    # Test direct ytmusicapi call
    print("\n=== DIRECT YTMUSICAPI TEST ===")
    try:
        direct_result = cleaner.ytmusic.get_playlist(playlist_id, limit=None)
        print(f"Direct call - Response keys: {list(direct_result.keys())}")
        if 'trackCount' in direct_result:
            print(f"Direct call - Track count: {direct_result['trackCount']}")
        if 'tracks' in direct_result:
            print(f"Direct call - Tracks returned: {len(direct_result['tracks'])}")
        
        # Try with different limits
        for limit in [100, 200, 500, 1000, 2000]:
            try:
                limited_result = cleaner.ytmusic.get_playlist(playlist_id, limit=limit)
                track_count = len(limited_result.get('tracks', []))
                print(f"Direct call (limit={limit}) - Got {track_count} tracks")
                if track_count < limit:
                    print(f"  --> Got fewer than limit, probably all tracks")
                    break
            except Exception as e:
                print(f"Direct call (limit={limit}) - Error: {e}")
    except Exception as e:
        print(f"Direct call failed: {e}")
    
    print("\n=== ROBUST FETCH TEST ===")
    tracks = cleaner.get_playlist_tracks_robust(playlist_id)
    print(f"Robust fetch returned {len(tracks)} tracks")
    
    if tracks:
        print(f"First track: {tracks[0].title} - {tracks[0].video_id}")
        if len(tracks) > 1:
            print(f"Last track: {tracks[-1].title} - {tracks[-1].video_id}")
    
    print("\n=== LIBRARY FETCH TEST ===")
    library_songs = cleaner.get_library_songs_cached()
    print(f"Library fetch returned {len(library_songs)} songs")
    
    print("\n=== LIKED SONGS TEST ===")
    liked_songs = cleaner.get_liked_songs_cached()
    print(f"Liked songs fetch returned {len(liked_songs)} songs")
    
    if tracks and library_songs:
        print("\n=== INTERSECTION TEST ===")
        playlist_ids = {track.video_id for track in tracks}
        library_ids = {song.get('videoId') for song in library_songs if song.get('videoId')}
        
        intersection = playlist_ids & library_ids
        print(f"Playlist video IDs: {len(playlist_ids)}")
        print(f"Library video IDs: {len(library_ids)}")
        print(f"Intersection: {len(intersection)}")
        
        if intersection:
            print(f"Sample intersecting IDs: {list(intersection)[:5]}")
    
    if tracks and liked_songs:
        print("\n=== LIKED INTERSECTION TEST ===")
        playlist_ids = {track.video_id for track in tracks}
        
        liked_intersection = playlist_ids & liked_songs
        print(f"Playlist vs Liked intersection: {len(liked_intersection)}")
        
        if liked_intersection:
            print(f"Sample liked intersecting IDs: {list(liked_intersection)[:5]}")

if __name__ == "__main__":
    debug_playlist_fetch()