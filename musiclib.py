#!/usr/bin/env python3
"""
Quick launcher for the consolidated music tools.
Provides an easy way to start either the CLI or web interface.
"""

import sys
import subprocess
from pathlib import Path

def show_help():
    """Show available options."""
    print("""
🎵 MusicLib - Consolidated Music Tools Launcher

Usage: python musiclib.py [option]

Options:
  web, w     Launch web interface (Streamlit)
  cli, c     Show CLI help
  help, h    Show this help message

Examples:
  python musiclib.py web          # Launch web interface
  python musiclib.py cli          # Show CLI options
  
  # Direct CLI usage:
  python musiclib-cli.py compare --source apple.csv --target spotify.csv
  python musiclib-cli.py create-playlist --tracks missing.csv --headers auth.json
  python musiclib-cli.py analyze --libraries *.csv
  python musiclib-cli.py dedup-ytm --headers headers_auth.json --threshold 0.88
""")

def launch_web():
    """Launch the Streamlit web interface."""
    print("🚀 Launching web interface...")
    try:
        subprocess.run([sys.executable, "-m", "streamlit", "run", "musiclib-web.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to launch web interface: {e}")
        print("💡 Make sure streamlit is installed: pip install streamlit")
    except KeyboardInterrupt:
        print("\n👋 Web interface closed")

def show_cli_help():
    """Show CLI help."""
    print("📋 CLI Interface Help:")
    print("=" * 50)
    try:
        subprocess.run([sys.executable, "musiclib-cli.py", "--help"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to show CLI help: {e}")

def main():
    """Main launcher function."""
    if len(sys.argv) < 2:
        show_help()
        return
    
    option = sys.argv[1].lower()
    
    if option in ['web', 'w']:
        launch_web()
    elif option in ['cli', 'c']:
        show_cli_help()
    elif option in ['help', 'h', '--help', '-h']:
        show_help()
    else:
        print(f"❌ Unknown option: {option}")
        show_help()

if __name__ == '__main__':
    main()
