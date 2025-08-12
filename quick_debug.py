#!/usr/bin/env python3
"""
Quick debug to check library duplicates only.
"""

import logging
from ytmusicapi import YTMusic

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)

def quick_debug():
    logger = setup_logging()
    
    headers_path = "/Users/guerrero/Documents/musiccode/headers_auth.json"
    ytmusic = YTMusic(headers_path)
    
    playlist_id = "PL1LO5jourf4MqCSX94juP7bWk2eYTMCQ2"
    
    logger.info("=== QUICK LIBRARY DUPLICATE CHECK ===")
    
    # Get first 20 tracks from playlist
    logger.info("Getting first 20 tracks from playlist...")
    playlist_data = ytmusic.get_playlist(playlist_id, limit=20)
    tracks = playlist_data.get('tracks', [])
    logger.info(f"Got {len(tracks)} playlist tracks")
    
    # Get library songs (we know this works fast)
    logger.info("Getting library songs...")
    library_songs = ytmusic.get_library_songs(limit=None)
    library_video_ids = {song.get('videoId') for song in library_songs if song.get('videoId')}
    logger.info(f"Library has {len(library_video_ids)} songs")
    
    # Quick check for matches
    matches_found = 0
    for i, track in enumerate(tracks):
        video_id = track.get('videoId')
        title = track.get('title', 'Unknown')
        artists = track.get('artists', [])
        artist_names = [a.get('name', '') for a in artists]
        artist_str = ', '.join(artist_names) if artist_names else 'Unknown Artist'
        
        in_library = video_id in library_video_ids
        
        if in_library:
            matches_found += 1
            logger.info(f"✅ MATCH {matches_found}: '{title}' by {artist_str}")
            logger.info(f"   Video ID: {video_id}")
        else:
            logger.info(f"❌ NO MATCH: '{title}' by {artist_str} (ID: {video_id})")
    
    logger.info(f"\n=== SUMMARY ===")
    logger.info(f"Checked: {len(tracks)} tracks")
    logger.info(f"Library matches: {matches_found}")
    logger.info(f"Match rate: {matches_found/len(tracks)*100:.1f}%")
    
    if matches_found == 0:
        logger.info("\n🔍 NO MATCHES FOUND - Let's investigate further...")
        
        # Check if video IDs look reasonable
        sample_playlist_ids = [t.get('videoId') for t in tracks[:5]]
        sample_library_ids = list(library_video_ids)[:5]
        
        logger.info(f"Sample playlist video IDs: {sample_playlist_ids}")
        logger.info(f"Sample library video IDs: {sample_library_ids}")
        
        # Check for title-based matches (different video IDs, same song)
        logger.info(f"\n🔍 CHECKING FOR TITLE MATCHES...")
        library_titles = {song.get('title', '').lower() for song in library_songs}
        
        title_matches = 0
        for track in tracks[:10]:
            title = track.get('title', '').lower()
            if title in library_titles:
                title_matches += 1
                logger.info(f"📝 TITLE MATCH: '{track.get('title')}'")
        
        logger.info(f"Title matches in first 10: {title_matches}")

if __name__ == "__main__":
    quick_debug()