#!/usr/bin/env python3
"""
Debug script to find why obvious duplicates aren't being detected.
"""

import logging
from ytmusicapi import YTMusic

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)

def debug_duplicates():
    logger = setup_logging()
    
    headers_path = "/Users/guerrero/Documents/musiccode/headers_auth.json"
    ytmusic = YTMusic(headers_path)
    
    playlist_id = "PL1LO5jourf4MqCSX94juP7bWk2eYTMCQ2"
    
    logger.info("=== DEBUGGING DUPLICATE DETECTION ===")
    
    # Get first 10 tracks from playlist for manual inspection
    logger.info("Getting first 10 tracks from playlist...")
    playlist_data = ytmusic.get_playlist(playlist_id, limit=10)
    tracks = playlist_data.get('tracks', [])
    
    # Get library and liked songs
    logger.info("Getting library songs...")
    library_songs = ytmusic.get_library_songs(limit=None)
    library_video_ids = {song.get('videoId') for song in library_songs if song.get('videoId')}
    logger.info(f"Library has {len(library_video_ids)} songs")
    
    logger.info("Getting liked songs...")
    liked_songs = ytmusic.get_liked_songs(limit=None)
    liked_video_ids = {track.get('videoId') for track in liked_songs.get('tracks', []) if track.get('videoId')}
    logger.info(f"Liked songs has {len(liked_video_ids)} songs")
    
    # Check each playlist track
    logger.info("\n=== CHECKING FIRST 10 PLAYLIST TRACKS ===")
    for i, track in enumerate(tracks[:10]):
        video_id = track.get('videoId')
        title = track.get('title', 'Unknown')
        artists = track.get('artists', [])
        artist_names = [a.get('name', '') for a in artists]
        artist_str = ', '.join(artist_names) if artist_names else 'Unknown Artist'
        
        in_library = video_id in library_video_ids
        in_liked = video_id in liked_video_ids
        
        logger.info(f"\nTrack {i+1}: '{title}' by {artist_str}")
        logger.info(f"  Video ID: {video_id}")
        logger.info(f"  In Library: {in_library}")
        logger.info(f"  In Liked: {in_liked}")
        logger.info(f"  Should remove (library): {in_library}")
        logger.info(f"  Should remove (liked): {in_liked}")
        
        # If you know this should be a duplicate, we can investigate further
        if not in_library and not in_liked:
            logger.info(f"  ❌ NOT DETECTED AS DUPLICATE - investigating...")
            
            # Search for similar tracks in library by title
            similar_library = [s for s in library_songs if s.get('title', '').lower() == title.lower()]
            logger.info(f"  Library tracks with same title: {len(similar_library)}")
            
            for sim in similar_library[:3]:  # Show first 3 matches
                sim_video_id = sim.get('videoId')
                sim_artists = sim.get('artists', [])
                sim_artist_names = [a.get('name', '') for a in sim_artists]
                logger.info(f"    Similar: '{sim.get('title')}' by {', '.join(sim_artist_names)} (ID: {sim_video_id})")
    
    # Sample some library tracks to see the format
    logger.info(f"\n=== SAMPLE LIBRARY TRACKS ===")
    for i, track in enumerate(library_songs[:5]):
        title = track.get('title', 'Unknown')
        video_id = track.get('videoId')
        artists = track.get('artists', [])
        artist_names = [a.get('name', '') for a in artists]
        logger.info(f"Library {i+1}: '{title}' by {', '.join(artist_names)} (ID: {video_id})")

if __name__ == "__main__":
    debug_duplicates()