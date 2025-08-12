#!/usr/bin/env python3
"""
YouTube Music Deduplicator Setup Script
Helps users set up authentication and install dependencies
"""

import os
import sys
import json
import subprocess
from pathlib import Path

def print_header():
    print("=" * 60)
    print("🎵 YouTube Music Library Deduplicator Setup")
    print("=" * 60)
    print()

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 7):
        print("❌ Python 3.7 or higher is required")
        print(f"   Current version: {sys.version}")
        return False
    
    print(f"✅ Python version: {sys.version.split()[0]}")
    return True

def install_dependencies():
    """Install required Python packages"""
    print("\n📦 Installing dependencies...")
    
    packages = [
        "ytmusicapi",
        "flask", 
        "flask-cors"
    ]
    
    for package in packages:
        try:
            print(f"   Installing {package}...")
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", package
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print(f"   ✅ {package} installed")
        except subprocess.CalledProcessError:
            print(f"   ❌ Failed to install {package}")
            return False
    
    return True

def check_auth_file():
    """Check if authentication file exists"""
    auth_file = Path("headers_auth.json")
    
    if auth_file.exists():
        print("✅ headers_auth.json found")
        try:
            with open(auth_file, 'r') as f:
                data = json.load(f)
                if isinstance(data, dict) and len(data) > 0:
                    print("✅ Authentication file appears valid")
                    return True
                else:
                    print("⚠️  Authentication file is empty or invalid")
                    return False
        except json.JSONDecodeError:
            print("⚠️  Authentication file contains invalid JSON")
            return False
    else:
        print("❌ headers_auth.json not found")
        return False

def create_auth_guide():
    """Create a detailed authentication guide"""
    print("\n📋 Creating authentication guide...")
    
    guide_content = '''# YouTube Music Authentication Setup Guide

## Step 1: Open YouTube Music
1. Go to https://music.youtube.com in your browser
2. Make sure you're logged into your Google account
3. Navigate to your library (any page will work)

## Step 2: Open Developer Tools
1. Press F12 (or Ctrl+Shift+I on Windows/Linux, Cmd+Opt+I on Mac)
2. Click on the "Network" tab
3. Make sure "Preserve log" is checked (if available)

## Step 3: Refresh and Find Request
1. Refresh the YouTube Music page (F5 or Ctrl+R)
2. Wait for the page to load completely
3. In the Network tab, look for requests to:
   - `music.youtube.com/youtubei/v1/browse`
   - `music.youtube.com/youtubei/v1/search`
   - Any request starting with `music.youtube.com/youtubei/v1/`

## Step 4: Copy Request Headers
1. Click on one of the requests from step 3
2. In the right panel, find the "Request Headers" section
3. Right-click in the Request Headers area
4. Select "Copy" → "Copy request headers" (or similar option)

## Step 5: Create Authentication File
1. Create a new file called `headers_auth.json` in the same folder as this script
2. The file should contain JSON like this:

```json
{
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36...",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Content-Type": "application/json",
    "X-Goog-AuthUser": "0",
    "x-origin": "https://music.youtube.com",
    "Cookie": "VISITOR_INFO1_LIVE=...; CONSENT=...; [VERY LONG COOKIE STRING]"
}
```

## Important Notes:
- The Cookie field is the most important - it contains your authentication
- Headers may vary slightly between browsers
- You may need to repeat this process if authentication expires
- Never share your headers_auth.json file - it contains your login credentials

## Troubleshooting:
- If authentication fails, try getting fresh headers
- Make sure you're logged into YouTube Music when copying headers
- Some ad blockers may interfere - try disabling them temporarily
- If you see CORS errors, make sure the server is running on localhost

## Security Warning:
The headers_auth.json file contains your YouTube Music login credentials.
Keep this file private and never share it with others.
'''
    
    with open("AUTHENTICATION_GUIDE.md", "w") as f:
        f.write(guide_content)
    
    print("✅ Created AUTHENTICATION_GUIDE.md")

def create_example_auth_file():
    """Create an example authentication file"""
    example_auth = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Content-Type": "application/json",
        "X-Goog-AuthUser": "0",
        "x-origin": "https://music.youtube.com",
        "Cookie": "REPLACE_WITH_YOUR_ACTUAL_COOKIE_STRING_FROM_BROWSER_DEV_TOOLS"
    }
    
    with open("headers_auth_example.json", "w") as f:
        json.dump(example_auth, f, indent=2)
    
    print("✅ Created headers_auth_example.json template")

def create_run_script():
    """Create a simple run script"""
    run_script_content = '''#!/usr/bin/env python3
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
        print("\\n👋 Server stopped")
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1)
'''
    
    with open("run.py", "w") as f:
        f.write(run_script_content)
    
    # Make it executable on Unix systems
    try:
        os.chmod("run.py", 0o755)
    except:
        pass
    
    print("✅ Created run.py script")

def show_next_steps(auth_exists):
    """Show what the user should do next"""
    print("\n🚀 Setup Complete!")
    print("\n📋 Next Steps:")
    
    if not auth_exists:
        print("1. 📖 Read the AUTHENTICATION_GUIDE.md file")
        print("2. 🔑 Create your headers_auth.json file following the guide")
        print("3. 🏃 Run: python youtube_music_deduplicator.py")
        print("4. 🌐 Open http://localhost:5003 in your browser")
    else:
        print("1. 🏃 Run: python youtube_music_deduplicator.py")
        print("   Or run: python run.py")
        print("2. 🌐 Open http://localhost:5003 in your browser")
        print("3. 🔍 Click 'Scan Library for Duplicates'")
    
    print("\n💡 Tips:")
    print("   - Keep the terminal window open while using the app")
    print("   - Check the terminal for detailed logging")
    print("   - If authentication fails, get fresh headers from your browser")

def main():
    """Main setup function"""
    print_header()
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Install dependencies
    print("\n📦 Checking dependencies...")
    if not install_dependencies():
        print("❌ Failed to install dependencies")
        print("   Try running: pip install ytmusicapi flask flask-cors")
        sys.exit(1)
    
    # Check authentication
    print("\n🔑 Checking authentication...")
    auth_exists = check_auth_file()
    
    # Create supporting files
    print("\n📄 Creating support files...")
    create_auth_guide()
    create_example_auth_file()
    create_run_script()
    
    # Show next steps
    show_next_steps(auth_exists)

if __name__ == "__main__":
    main()