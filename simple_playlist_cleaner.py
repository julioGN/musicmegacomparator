#!/usr/bin/env python3
"""
Simple, direct playlist cleaner that focuses on getting the job done.
This script will fetch ALL tracks from a large playlist and remove duplicates.
"""

import json
import logging
import time
from pathlib import Path
from typing import List, Set, Dict, Any
import sys

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


def fetch_all_playlist_tracks(ytmusic: YTMusic, playlist_id: str, logger) -> List[Dict[str, Any]]:
    """Fetch ALL tracks from a playlist using ytmusicapi's built-in pagination."""
    
    logger.info(f"Fetching all tracks from playlist: {playlist_id}")
    
    # First, get basic playlist info to see reported track count
    try:
        basic_info = ytmusic.get_playlist(playlist_id, limit=1)
        reported_count = basic_info.get('trackCount', 0)
        title = basic_info.get('title', 'Unknown')
        duration = basic_info.get('duration', 'Unknown')
        
        logger.info(f"=== PLAYLIST DETAILS ===")
        logger.info(f"Title: {title}")
        logger.info(f"Reported track count: {reported_count}")
        logger.info(f"Duration: {duration}")
        logger.info(f"=======================")
    except Exception as e:
        logger.error(f"Could not get basic playlist info: {e}")
        return []
    
    # Now fetch ALL tracks using ytmusicapi's proper method
    try:
        logger.info("Fetching ALL tracks using ytmusicapi (limit=None)...")
        full_data = ytmusic.get_playlist(playlist_id, limit=None)
        
        if 'tracks' in full_data:
            tracks = full_data['tracks']
            logger.info(f"ytmusicapi returned {len(tracks)} tracks with limit=None")
            logger.info(f"Reported count: {reported_count}, Actual fetched: {len(tracks)}")
            
            # Verify tracks have proper data
            valid_tracks = [t for t in tracks if t.get('videoId') and t.get('setVideoId')]
            logger.info(f"Tracks with valid videoId and setVideoId: {len(valid_tracks)}")
            
            return tracks
        else:
            logger.error("No tracks found in response")
            return []
            
    except Exception as e:
        logger.error(f"Failed to fetch all tracks: {e}")
        return []


def fetch_with_manual_pagination(ytmusic: YTMusic, playlist_id: str, logger) -> List[Dict[str, Any]]:
    """Manually paginate through playlist using browse endpoint."""
    
    all_tracks = []
    seen_video_ids = set()
    continuation = None
    page = 0
    
    while page < 20:  # Max 20 pages for safety
        page += 1
        try:
            if continuation:
                logger.info(f"Fetching page {page} with continuation...")
                response = ytmusic._send_request('browse', {
                    'browseId': f'VL{playlist_id}',
                    'continuation': continuation
                })
            else:
                logger.info(f"Fetching page {page} (initial)...")
                response = ytmusic._send_request('browse', {
                    'browseId': f'VL{playlist_id}'
                })
            
            # Debug response structure
            if page == 1:
                logger.info(f"Response keys: {list(response.keys()) if isinstance(response, dict) else 'Not a dict'}")
                if 'contents' in response:
                    logger.info(f"Contents keys: {list(response['contents'].keys())}")
                    # Save the response for debugging
                    import json
                    with open('/Users/guerrero/Documents/musiccode/debug_response.json', 'w') as f:
                        json.dump(response, f, indent=2)
                    logger.info("Saved full response to debug_response.json")
            
            # Extract tracks from this page
            page_tracks = extract_tracks_from_response(response)
            logger.info(f"extract_tracks_from_response returned {len(page_tracks)} tracks")
            new_tracks = 0
            
            for track in page_tracks:
                video_id = track.get('videoId')
                if video_id and video_id not in seen_video_ids:
                    all_tracks.append(track)
                    seen_video_ids.add(video_id)
                    new_tracks += 1
            
            logger.info(f"Page {page}: +{new_tracks} new tracks (total: {len(all_tracks)})")
            
            # Look for continuation
            continuation = find_continuation(response)
            
            if not continuation or new_tracks == 0:
                logger.info("No more pages or no new tracks")
                break
                
        except Exception as e:
            logger.error(f"Error on page {page}: {e}")
            break
    
    return all_tracks


def extract_tracks_from_response(response: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract track data from API response."""
    tracks = []
    
    # Look for tracks in various response structures
    if 'tracks' in response:
        return response['tracks']
    
    # For browse responses, look for playlist shelf contents
    try:
        shelf_contents = (response
                         .get('contents', {})
                         .get('twoColumnBrowseResultsRenderer', {})
                         .get('secondaryContents', {})
                         .get('sectionListRenderer', {})
                         .get('contents', []))
        
        print(f"DEBUG: Found {len(shelf_contents)} shelf sections")
        
        for i, section in enumerate(shelf_contents):
            print(f"DEBUG: Section {i} keys: {list(section.keys())}")
            if 'musicPlaylistShelfRenderer' in section:
                shelf_items = section['musicPlaylistShelfRenderer'].get('contents', [])
                print(f"DEBUG: Found shelf with {len(shelf_items)} items")
                for j, item in enumerate(shelf_items):
                    if 'musicResponsiveListItemRenderer' in item:
                        track = parse_responsive_item(item['musicResponsiveListItemRenderer'])
                        if track:
                            tracks.append(track)
                        else:
                            print(f"DEBUG: Item {j} failed to parse")
                            
    except Exception as e:
        print(f"Error parsing browse response: {e}")
        import traceback
        traceback.print_exc()
    
    # Fallback: search recursively for musicResponsiveListItemRenderer
    if not tracks:
        def search_for_tracks(data):
            if isinstance(data, dict):
                if 'musicResponsiveListItemRenderer' in data:
                    # Convert to standard track format
                    track = parse_responsive_item(data['musicResponsiveListItemRenderer'])
                    if track:
                        tracks.append(track)
                else:
                    for value in data.values():
                        search_for_tracks(value)
            elif isinstance(data, list):
                for item in data:
                    search_for_tracks(item)
        
        if 'contents' in response:
            search_for_tracks(response['contents'])
    
    return tracks


def parse_responsive_item(item: Dict[str, Any]) -> Dict[str, Any]:
    """Parse a musicResponsiveListItemRenderer into standard track format."""
    try:
        # Debug first item to understand structure
        if not hasattr(parse_responsive_item, '_debug_done'):
            print(f"DEBUG: Sample item keys: {list(item.keys())}")
            if 'flexColumns' in item:
                print(f"DEBUG: flexColumns count: {len(item['flexColumns'])}")
                if item['flexColumns']:
                    first_col = item['flexColumns'][0]
                    print(f"DEBUG: First column keys: {list(first_col.keys())}")
            parse_responsive_item._debug_done = True
        
        # Extract video ID - try multiple approaches
        video_id = ""
        set_video_id = ""
        
        # Method 1: Look in overlay
        if 'overlay' in item:
            overlay = item['overlay'].get('musicItemThumbnailOverlayRenderer', {})
            content = overlay.get('content', {}).get('musicPlayButtonRenderer', {})
            nav = content.get('playNavigationEndpoint', {})
            if 'videoId' in nav:
                video_id = nav['videoId']
        
        # Method 2: Look in flexColumns navigation
        if not video_id and 'flexColumns' in item:
            for column in item['flexColumns']:
                if 'musicResponsiveListItemFlexColumnRenderer' in column:
                    text_data = column['musicResponsiveListItemFlexColumnRenderer'].get('text', {})
                    if 'runs' in text_data:
                        for run in text_data['runs']:
                            if 'navigationEndpoint' in run:
                                nav = run['navigationEndpoint']
                                if 'watchEndpoint' in nav and 'videoId' in nav['watchEndpoint']:
                                    video_id = nav['watchEndpoint']['videoId']
                                    break
                if video_id:
                    break
        
        # Method 3: Look for setVideoId in playlistItemData (primary location)
        if 'playlistItemData' in item:
            set_video_id = item['playlistItemData'].get('playlistSetVideoId', '')
        
        # Method 4: Fallback - look for setVideoId in menu
        if not set_video_id and 'menu' in item:
            menu_items = item['menu'].get('menuRenderer', {}).get('items', [])
            for menu_item in menu_items:
                if 'menuServiceItemRenderer' in menu_item:
                    service = menu_item['menuServiceItemRenderer'].get('serviceEndpoint', {})
                    if 'playlistEditEndpoint' in service:
                        actions = service['playlistEditEndpoint'].get('actions', [])
                        if actions:
                            set_video_id = actions[0].get('setVideoId', '')
        
        # Extract text content (title, artist)
        title = ""
        artists = []
        
        if 'flexColumns' in item:
            for i, column in enumerate(item['flexColumns']):
                if 'musicResponsiveListItemFlexColumnRenderer' in column:
                    text_data = column['musicResponsiveListItemFlexColumnRenderer'].get('text', {})
                    if 'runs' in text_data:
                        text = ''.join(run.get('text', '') for run in text_data['runs'])
                        if i == 0:  # First column is usually title
                            title = text
                        elif i == 1:  # Second column is usually artist
                            artists = [text]
        
        if video_id:
            return {
                'videoId': video_id,
                'setVideoId': set_video_id,
                'title': title,
                'artists': [{'name': artist} for artist in artists] if artists else []
            }
            
    except Exception as e:
        print(f"DEBUG: Parse error: {e}")
    
    return None


def find_continuation(response: Dict[str, Any]) -> str:
    """Find continuation token in response."""
    
    # First try the specific path we found
    try:
        continuations = (response
                        .get('contents', {})
                        .get('twoColumnBrowseResultsRenderer', {})
                        .get('secondaryContents', {})
                        .get('sectionListRenderer', {})
                        .get('continuations', []))
        
        for cont in continuations:
            if 'nextContinuationData' in cont:
                return cont['nextContinuationData'].get('continuation')
                
    except Exception:
        pass
    
    # Fallback: search recursively
    def search_continuation(data):
        if isinstance(data, dict):
            if 'continuation' in data:
                return data['continuation']
            if 'nextContinuationData' in data:
                return data['nextContinuationData'].get('continuation')
            
            for value in data.values():
                result = search_continuation(value)
                if result:
                    return result
        elif isinstance(data, list):
            for item in data:
                result = search_continuation(item)
                if result:
                    return result
        return None
    
    return search_continuation(response)


def get_all_library_songs(ytmusic: YTMusic, logger) -> Set[str]:
    """Get all video IDs from user's library."""
    logger.info("Fetching all library songs...")
    
    try:
        # Try to get all library songs
        library_songs = ytmusic.get_library_songs(limit=None) or []
        logger.info(f"Got {len(library_songs)} library songs")
        
        video_ids = {song.get('videoId') for song in library_songs if song.get('videoId')}
        logger.info(f"Extracted {len(video_ids)} video IDs from library")
        
        return video_ids
        
    except Exception as e:
        logger.error(f"Failed to get library songs: {e}")
        return set()


def get_all_liked_songs(ytmusic: YTMusic, logger) -> Set[str]:
    """Get all video IDs from user's liked songs using ytmusicapi's proper method."""
    logger.info("Fetching all liked songs using ytmusicapi...")
    
    try:
        # Use ytmusicapi's built-in method with limit=None to get ALL liked songs
        logger.info("Using ytmusicapi get_liked_songs(limit=None)...")
        liked_playlist = ytmusic.get_liked_songs(limit=None)
        
        if 'tracks' in liked_playlist:
            tracks = liked_playlist['tracks']
            logger.info(f"ytmusicapi returned {len(tracks)} liked songs")
            
            # Extract video IDs
            video_ids = {track.get('videoId') for track in tracks if track.get('videoId')}
            logger.info(f"Extracted {len(video_ids)} unique video IDs from liked songs")
            
            return video_ids
        else:
            logger.warning("No tracks found in liked songs response")
            return set()
            
    except Exception as e:
        logger.error(f"Failed to get liked songs: {e}")
        return set()


def clean_playlist(ytmusic: YTMusic, playlist_id: str, remove_liked: bool, remove_library_dupes: bool, logger, dry_run: bool = True):
    """Clean the playlist by removing liked songs and library duplicates."""
    
    logger.info(f"Starting playlist cleanup (dry_run={dry_run})")
    
    # Get all playlist tracks
    all_tracks = fetch_all_playlist_tracks(ytmusic, playlist_id, logger)
    if not all_tracks:
        logger.error("Could not fetch playlist tracks")
        return
    
    logger.info(f"Playlist has {len(all_tracks)} tracks")
    
    # Get comparison data
    liked_songs = set()
    library_songs = set()
    
    if remove_liked:
        liked_songs = get_all_liked_songs(ytmusic, logger)
    
    if remove_library_dupes:
        library_songs = get_all_library_songs(ytmusic, logger)
    
    # Find tracks to remove
    tracks_to_remove = []
    removed_liked = 0
    removed_dupes = 0
    
    # Show first few tracks and their status for debugging
    logger.info("Checking first 5 tracks for matches...")
    logger.info(f"Total tracks to check: {len(all_tracks)}")
    logger.info(f"Liked songs count: {len(liked_songs)}")
    logger.info(f"Library songs count: {len(library_songs)}")
    
    for i, track in enumerate(all_tracks):
        video_id = track.get('videoId')
        set_video_id = track.get('setVideoId')
        title = track.get('title', 'Unknown')
        
        # Debug first few tracks regardless of validity
        if i < 5:
            in_liked = video_id in liked_songs if video_id else False
            in_library = video_id in library_songs if video_id else False
            logger.info(f"Track {i+1}: '{title}' | videoId: {video_id} | setVideoId: {set_video_id} | in_liked: {in_liked} | in_library: {in_library}")
        
        if not video_id or not set_video_id:
            if i < 5:
                logger.info(f"Track {i+1}: Skipping - missing videoId or setVideoId")
            continue
        
        should_remove = False
        reason = ""
        
        if remove_liked and video_id in liked_songs:
            should_remove = True
            removed_liked += 1
            reason = "liked"
        elif remove_library_dupes and video_id in library_songs:
            should_remove = True
            removed_dupes += 1
            reason = "library duplicate"
        
        if should_remove:
            tracks_to_remove.append({
                'videoId': video_id,
                'setVideoId': set_video_id
            })
            logger.info(f"REMOVE ({reason}): {title}")
    
    logger.info(f"\nSUMMARY:")
    logger.info(f"Total tracks: {len(all_tracks)}")
    logger.info(f"Liked songs to remove: {removed_liked}")
    logger.info(f"Library duplicates to remove: {removed_dupes}")
    logger.info(f"Total to remove: {len(tracks_to_remove)}")
    logger.info(f"Remaining tracks: {len(all_tracks) - len(tracks_to_remove)}")
    
    if dry_run:
        logger.info("\nDRY RUN - No changes made")
        return
    
    # Actually remove tracks
    if tracks_to_remove:
        logger.info(f"\nRemoving {len(tracks_to_remove)} tracks...")
        
        # Remove in batches of 50
        batch_size = 50
        for i in range(0, len(tracks_to_remove), batch_size):
            batch = tracks_to_remove[i:i + batch_size]
            try:
                ytmusic.remove_playlist_items(playlist_id, batch)
                logger.info(f"Removed batch {i//batch_size + 1} ({len(batch)} tracks)")
                time.sleep(1)  # Rate limiting
            except Exception as e:
                logger.error(f"Failed to remove batch {i//batch_size + 1}: {e}")
        
        logger.info("Cleanup complete!")
    else:
        logger.info("No tracks to remove")


def main():
    logger = setup_logging()
    
    # Configuration - use existing headers file
    headers_path = "/Users/guerrero/Documents/musiccode/headers_auth.json"
    if not Path(headers_path).exists():
        logger.error(f"Headers file not found: {headers_path}")
        return
    
    playlist_url = "https://music.youtube.com/playlist?list=PL1LO5jourf4MqCSX94juP7bWk2eYTMCQ2&si=gSS-xtZtM7xT-j4l"
    playlist_id = extract_playlist_id(playlist_url)
    
    # Options - start with dry run to see what's happening
    remove_liked = True
    remove_library_dupes = True
    dry_run = True  # Always dry run for debugging
    
    # Authenticate
    logger.info("Authenticating...")
    ytmusic = YTMusic(headers_path)
    
    # Run cleanup
    clean_playlist(ytmusic, playlist_id, remove_liked, remove_library_dupes, logger, dry_run)


if __name__ == "__main__":
    main()