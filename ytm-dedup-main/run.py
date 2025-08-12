#!/usr/bin/env python3
"""
Quick start script for YouTube Music Deduplicator
"""

import os
import sys

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    try:
        # Import and run the main server
        from youtube_music_deduplicator import app
        
        print("🎵 YouTube Music Deduplicator")
        print("🌐 Starting server at http://localhost:5003")
        print("📱 Open your browser to http://localhost:5003")
        print("⏹️  Press Ctrl+C to stop")
        print()
        
        app.run(debug=False, host='0.0.0.0', port=5003)
        
    except ImportError:
        print("❌ Error: youtube_music_deduplicator.py not found")
        print("   Make sure all files are in the same directory")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n👋 Server stopped")
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1)
