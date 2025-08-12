#!/usr/bin/env python3
"""
YouTube Music Library Deduplicator - Backend Server
Requires: pip install ytmusicapi flask flask-cors
"""

import json
import os
import time
from datetime import datetime
from difflib import SequenceMatcher
from typing import List, Dict, Any, Tuple
import re

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from ytmusicapi import YTMusic

app = Flask(__name__)
CORS(app)

class YouTubeMusicDeduplicator:
    def __init__(self, headers_auth_path: str = "headers_auth.json"):
        """Initialize with YouTube Music authentication"""
        self.ytmusic = None
        self.library_songs = []
        self.duplicate_groups = []
        self.headers_auth_path = headers_auth_path
        
    def authenticate(self) -> bool:
        """Authenticate with YouTube Music"""
        try:
            if not os.path.exists(self.headers_auth_path):
                return False
            self.ytmusic = YTMusic(self.headers_auth_path)
            # Test connection
            self.ytmusic.get_library_songs(limit=1)
            return True
        except Exception as e:
            print(f"Authentication failed: {e}")
            return False
    
    def get_library_songs(self, limit: int = None) -> List[Dict]:
        """Fetch all library songs"""
        if not self.ytmusic:
            raise Exception("Not authenticated")
        
        try:
            songs = self.ytmusic.get_library_songs(limit=limit)
            self.library_songs = songs
            return songs
        except Exception as e:
            print(f"Error fetching library: {e}")
            return []
    
    def normalize_string(self, text: str) -> str:
        """Normalize string for comparison"""
        if not text:
            return ""
        # Remove extra whitespace, convert to lowercase, remove special chars
        normalized = re.sub(r'[^\w\s]', '', text.lower().strip())
        normalized = re.sub(r'\s+', ' ', normalized)
        return normalized
    
    def calculate_similarity(self, str1: str, str2: str) -> float:
        """Calculate similarity between two strings"""
        return SequenceMatcher(None, 
                             self.normalize_string(str1), 
                             self.normalize_string(str2)).ratio()
    
    def find_duplicates(self, similarity_threshold: float = 0.85) -> List[Dict]:
        """Find duplicate songs in library"""
        if not self.library_songs:
            return []
        
        duplicate_groups = []
        processed_indices = set()
        
        for i, song1 in enumerate(self.library_songs):
            if i in processed_indices:
                continue
                
            # Get song info
            title1 = song1.get('title', '')
            artists1 = [artist['name'] for artist in song1.get('artists', [])]
            artist1 = artists1[0] if artists1 else ''
            
            # Find similar songs
            duplicates = [song1]
            group_indices = {i}
            
            for j, song2 in enumerate(self.library_songs[i+1:], i+1):
                if j in processed_indices:
                    continue
                    
                title2 = song2.get('title', '')
                artists2 = [artist['name'] for artist in song2.get('artists', [])]
                artist2 = artists2[0] if artists2 else ''
                
                # Calculate similarity
                title_sim = self.calculate_similarity(title1, title2)
                artist_sim = self.calculate_similarity(artist1, artist2)
                
                # Consider it a duplicate if both title and artist are similar
                if title_sim >= similarity_threshold and artist_sim >= similarity_threshold:
                    duplicates.append(song2)
                    group_indices.add(j)
            
            # If we found duplicates, create a group
            if len(duplicates) > 1:
                # Rank duplicates by quality/preference
                ranked_duplicates = self.rank_duplicates(duplicates)
                
                duplicate_groups.append({
                    'id': len(duplicate_groups) + 1,
                    'title': title1,
                    'artist': artist1,
                    'duplicates': ranked_duplicates,
                    'similarity_scores': {
                        'title_similarity': title_sim,
                        'artist_similarity': artist_sim
                    }
                })
                
                processed_indices.update(group_indices)
        
        self.duplicate_groups = duplicate_groups
        return duplicate_groups
    
    def rank_duplicates(self, duplicates: List[Dict]) -> List[Dict]:
        """Rank duplicates by quality and source preference"""
        def get_quality_score(song: Dict) -> int:
            """Calculate quality score based on various factors"""
            score = 0
            
            # Album vs single preference
            album = song.get('album', {})
            if album:
                album_name = album.get('name', '').lower()
                if 'album' in album_name or len(album_name) > 10:
                    score += 10  # Prefer album versions
                elif 'single' in album_name:
                    score += 5
            
            # Duration preference (avoid very short versions)
            duration = song.get('duration_seconds', 0)
            if duration > 60:  # Prefer songs longer than 1 minute
                score += 5
            
            # Avoid explicit/clean versions if there's a choice
            title = song.get('title', '').lower()
            if 'explicit' in title:
                score += 3
            elif 'clean' in title or 'radio edit' in title:
                score -= 2
            
            # Video vs audio preference
            if song.get('videoType') == 'MUSIC_VIDEO_TYPE_ATV':
                score += 8  # Prefer official audio
            
            return score
        
        # Add ranking info to each duplicate
        ranked = []
        for song in duplicates:
            quality_score = get_quality_score(song)
            
            # Determine quality label
            if quality_score >= 15:
                quality = "High"
            elif quality_score >= 8:
                quality = "Medium"
            else:
                quality = "Low"
            
            # Determine source
            album = song.get('album', {})
            album_name = album.get('name', '') if album else ''
            
            if 'single' in album_name.lower():
                source = "Single"
            elif album_name and len(album_name) > 3:
                source = "Album"
            else:
                source = "Unknown"
            
            ranked_song = {
                'id': song.get('videoId', ''),
                'title': song.get('title', ''),
                'album': album_name,
                'source': source,
                'quality': quality,
                'quality_score': quality_score,
                'duration': song.get('duration', ''),
                'thumbnail': song.get('thumbnails', [{}])[-1].get('url', '') if song.get('thumbnails') else '',
                'artists': [artist['name'] for artist in song.get('artists', [])],
                'original_data': song
            }
            ranked.append(ranked_song)
        
        # Sort by quality score (highest first)
        ranked.sort(key=lambda x: x['quality_score'], reverse=True)
        return ranked
    
    def create_playlist(self, title: str, song_ids: List[str], description: str = "") -> str:
        """Create a playlist with given songs"""
        if not self.ytmusic:
            raise Exception("Not authenticated")
        
        try:
            playlist_id = self.ytmusic.create_playlist(
                title=title,
                description=description
            )
            
            if song_ids:
                # Add songs to playlist (YouTube Music expects videoIds)
                self.ytmusic.add_playlist_items(playlist_id, song_ids)
            
            return playlist_id
        except Exception as e:
            print(f"Error creating playlist: {e}")
            raise e
    
    def remove_songs_from_library(self, song_ids: List[str]) -> bool:
        """Remove songs from library (if supported)"""
        # Note: YouTube Music API doesn't support removing from library
        # This would require manual removal by the user
        print(f"Manual removal required for {len(song_ids)} songs")
        return False

# Global deduplicator instance
deduplicator = YouTubeMusicDeduplicator()

@app.route('/')
def index():
    """Serve the main HTML page"""
    return send_from_directory('.', 'youtube_music_deduplicator.html')

@app.route('/api/status')
def get_status():
    """Get authentication and library status"""
    is_authenticated = deduplicator.ytmusic is not None
    return jsonify({
        'authenticated': is_authenticated,
        'library_count': len(deduplicator.library_songs),
        'duplicate_groups': len(deduplicator.duplicate_groups)
    })

@app.route('/api/authenticate', methods=['POST'])
def authenticate():
    """Authenticate with YouTube Music"""
    try:
        # Check if headers_auth.json exists
        if not os.path.exists('headers_auth.json'):
            return jsonify({
                'success': False,
                'error': 'headers_auth.json not found. Please create it first.'
            }), 400
        
        success = deduplicator.authenticate()
        return jsonify({
            'success': success,
            'message': 'Authentication successful' if success else 'Authentication failed'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/scan', methods=['POST'])
def scan_library():
    """Scan library for duplicates"""
    try:
        data = request.get_json() or {}
        limit = data.get('limit')  # None = all songs
        similarity_threshold = data.get('similarity_threshold', 0.85)
        
        # Get library songs
        songs = deduplicator.get_library_songs(limit=limit)
        if not songs:
            return jsonify({
                'success': False,
                'error': 'No songs found or authentication failed'
            }), 400
        
        # Find duplicates
        duplicates = deduplicator.find_duplicates(similarity_threshold)
        
        return jsonify({
            'success': True,
            'total_songs': len(songs),
            'duplicate_groups': len(duplicates),
            'total_duplicates': sum(len(group['duplicates']) for group in duplicates),
            'can_remove': sum(len(group['duplicates']) - 1 for group in duplicates),
            'groups': duplicates
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/create-playlist', methods=['POST'])
def create_playlist():
    """Create a playlist from selected duplicates"""
    try:
        data = request.get_json()
        playlist_name = data.get('name', '🗂️ True Duplicates')
        selected_groups = data.get('selected_groups', [])
        playlist_type = data.get('type', 'all')  # 'all' or 'selected'
        
        # Collect song IDs
        song_ids = []
        
        if playlist_type == 'all':
            # Add all duplicates
            for group in deduplicator.duplicate_groups:
                for duplicate in group['duplicates']:
                    song_ids.append(duplicate['id'])
        else:
            # Add only selected groups
            for group_id in selected_groups:
                group = next((g for g in deduplicator.duplicate_groups if g['id'] == group_id), None)
                if group:
                    for duplicate in group['duplicates']:
                        song_ids.append(duplicate['id'])
        
        if not song_ids:
            return jsonify({
                'success': False,
                'error': 'No songs to add to playlist'
            }), 400
        
        # Create playlist
        description = f"Duplicate songs found on {datetime.now().strftime('%Y-%m-%d')} - Created by YouTube Music Deduplicator"
        playlist_id = deduplicator.create_playlist(playlist_name, song_ids, description)
        
        return jsonify({
            'success': True,
            'playlist_id': playlist_id,
            'playlist_url': f'https://music.youtube.com/playlist?list={playlist_id}',
            'songs_added': len(song_ids)
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/export', methods=['GET'])
def export_results():
    """Export duplicate results as JSON"""
    try:
        results = {
            'scan_date': datetime.now().isoformat(),
            'total_library_songs': len(deduplicator.library_songs),
            'duplicate_groups': len(deduplicator.duplicate_groups),
            'total_duplicates': sum(len(group['duplicates']) for group in deduplicator.duplicate_groups),
            'can_remove': sum(len(group['duplicates']) - 1 for group in deduplicator.duplicate_groups),
            'groups': deduplicator.duplicate_groups,
            'settings': {
                'similarity_threshold': 0.85
            }
        }
        
        return jsonify(results)
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/setup-auth', methods=['POST'])
def setup_auth():
    """Instructions for setting up authentication"""
    instructions = {
        'steps': [
            "1. Open YouTube Music in your browser",
            "2. Open Developer Tools (F12)",
            "3. Go to Network tab",
            "4. Refresh the page",
            "5. Find a request to 'music.youtube.com/youtubei/v1/'",
            "6. Right-click → Copy → Copy request headers",
            "7. Create headers_auth.json with the copied headers",
            "8. Restart this server"
        ],
        'sample_format': {
            "User-Agent": "Mozilla/5.0...",
            "Cookie": "VISITOR_INFO1_LIVE=...; CONSENT=...",
            "X-Goog-AuthUser": "0",
            "x-origin": "https://music.youtube.com"
        }
    }
    
    return jsonify(instructions)

if __name__ == '__main__':
    print("YouTube Music Library Deduplicator Server")
    print("=========================================")
    print()
    
    if not os.path.exists('headers_auth.json'):
        print("⚠️  headers_auth.json not found!")
        print("📋 Visit http://localhost:5003/api/setup-auth for setup instructions")
        print()
    
    print("🚀 Starting server on http://localhost:5003")
    print("📱 Open your browser to http://localhost:5003")
    print()
    
    app.run(debug=True, host='0.0.0.0', port=5003)