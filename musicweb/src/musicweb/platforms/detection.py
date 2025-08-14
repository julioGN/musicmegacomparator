"""
Platform detection logic for music library files.
"""

from pathlib import Path


def detect_platform(file_path: str) -> str:
    """Detect the platform type from file content."""
    file_path = Path(file_path)
    
    # Check file extension and content
    if file_path.suffix.lower() == '.json':
        # Examine JSON content to determine platform
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                # Read first few lines to check content
                sample = f.read(2048)  # Read first 2KB
                sample_lower = sample.lower()
                
                # Check for Spotify JSON characteristics
                if '"platform":"spotify"' in sample or '"platform": "spotify"' in sample:
                    return 'spotify'
                elif 'open.spotify.com' in sample or 'spotify' in sample_lower:
                    return 'spotify'
                
                # Check for YouTube Music JSON characteristics
                elif 'youtube.com' in sample or 'music.youtube.com' in sample:
                    return 'youtube_music'
                elif '"videoid"' in sample_lower or '"video_id"' in sample_lower:
                    return 'youtube_music'
                
                # Check for Apple Music JSON characteristics
                elif 'apple.com' in sample or 'itunes' in sample_lower:
                    return 'apple_music'
                
                # Default to YouTube Music if no clear indicators (legacy behavior)
                else:
                    return 'youtube_music'
        
        except Exception:
            return 'youtube_music'  # Fallback
    
    elif file_path.suffix.lower() == '.xml':
        return 'apple_music_xml'
    
    # Check file content for CSV files
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            header_line = f.readline().lower()
        
        # Spotify CSV characteristics
        if 'duration (ms)' in header_line or 'artist name(s)' in header_line:
            return 'spotify'
        elif 'track name' in header_line and 'album name' in header_line:
            return 'spotify'
        
        # Apple Music CSV characteristics
        elif 'isrc' in header_line or 'apple' in header_line:
            return 'apple_music'
        
        # YouTube Music CSV characteristics
        elif 'channel' in header_line or 'video' in header_line:
            return 'youtube_music'
        
        else:
            # Default to Apple Music for unknown CSV
            return 'apple_music'
    
    except Exception:
        return 'unknown'