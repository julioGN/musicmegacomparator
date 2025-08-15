"""
Streamlit Cloud entry point for MusicWeb.
"""

import sys
from pathlib import Path

# Add src to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

# Import and run the main app
from musicweb.web.app import *