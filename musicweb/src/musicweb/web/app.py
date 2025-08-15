#!/usr/bin/env python3
"""
MusicWeb - Unified Streamlit Web Interface for Music Library Management

A comprehensive web interface for comparing and managing music libraries
across multiple streaming platforms.
"""

import json
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import sqlite3
import io

import streamlit as st
import pandas as pd
import sys
from pathlib import Path

# Add src to path for Streamlit Cloud compatibility
src_path = Path(__file__).parent.parent.parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

# Import core modules with fallback handling
try:
    from musicweb.core.models import Track, Library
    from musicweb.core.comparison import LibraryComparator
    from musicweb.platforms import create_parser
    from musicweb.platforms.detection import detect_platform
except ImportError:
    # Fallback for Streamlit Cloud
    import os
    current_dir = os.path.dirname(os.path.abspath(__file__))
    src_dir = os.path.join(current_dir, '..', '..')
    sys.path.insert(0, src_dir)
    
    from musicweb.core.models import Track, Library
    from musicweb.core.comparison import LibraryComparator
    from musicweb.platforms import create_parser
    from musicweb.platforms.detection import detect_platform
try:
    from musicweb.integrations.playlist import PlaylistManager
except Exception:
    PlaylistManager = None  # optional
try:
    from musicweb.core.enrichment import EnrichmentManager
except Exception:
    EnrichmentManager = None
try:
    from musicweb.integrations.deduplication import YouTubeMusicDeduplicator
except Exception:
    YouTubeMusicDeduplicator = None
try:
    from musicweb.integrations.playlist_cleanup import PlaylistCleaner
except Exception:
    PlaylistCleaner = None
try:
    from musicweb.integrations.cleaner import YTMusicCleaner
except Exception:
    YTMusicCleaner = None
from musicweb.web.playlist_audit import parse_playlist_bytes, audit_playlist

# Try to import optional visualization dependencies
try:
    import matplotlib.pyplot as plt
    from matplotlib_venn import venn2, venn3
    import plotly.express as px
    import plotly.graph_objects as go
    HAVE_VISUALIZATION = True
except ImportError:
    HAVE_VISUALIZATION = False

import base64

def get_logo_base64():
    """Get the logo as base64 encoded string."""
    try:
        # Use importlib.resources for proper package resource access
        try:
            from importlib.resources import files
        except ImportError:
            # Fallback for Python < 3.9
            from importlib_resources import files
        
        # Access logo from package resources
        package_files = files("musicweb.web.assets")
        logo_data = (package_files / "mwlogo.png").read_bytes()
        return base64.b64encode(logo_data).decode()
    except Exception:
        # Fallback to direct file access if importlib.resources fails
        try:
            logo_path = Path(__file__).parent / "assets" / "mwlogo.png"
            with open(logo_path, "rb") as f:
                return base64.b64encode(f.read()).decode()
        except Exception:
            # Final fallback if logo file not found
            return ""


# Page configuration
st.set_page_config(
    page_title="Mega Music Comparator",
    page_icon="🕸️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Enhanced CSS for production-ready UI
st.markdown("""
<style>
/* Tab styling */
.stTabs [data-baseweb="tab-list"] {
    gap: 2px;
    border-bottom: 2px solid #e0e0e0;
    padding-bottom: 0;
}
.stTabs [data-baseweb="tab"] {
    height: 50px;
    padding: 8px 20px;
    border-radius: 8px 8px 0 0;
    border: 2px solid transparent;
    font-weight: 600;
    transition: all 0.2s ease;
}
.stTabs [data-baseweb="tab"]:hover {
    background-color: #f8f9fa;
    border-color: #e0e0e0;
}
.stTabs [data-baseweb="tab"][aria-selected="true"] {
    background-color: #ffffff;
    border-color: #e0e0e0;
    border-bottom-color: #ffffff;
    color: #1f77b4;
}

/* Metric cards */
.metric-container {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 1.5rem;
    border-radius: 12px;
    margin: 0.5rem 0;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    position: relative;
    overflow: hidden;
}

.metric-container::before {
    content: '';
    position: absolute;
    top: -50%;
    right: -50%;
    width: 100%;
    height: 100%;
    background: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Cpath d='M50 10L60 30L80 30L65 45L70 65L50 55L30 65L35 45L20 30L40 30Z' fill='none' stroke='rgba(255,255,255,0.1)' stroke-width='0.5'/%3E%3C/svg%3E") repeat;
    opacity: 0.1;
    animation: webPattern 20s linear infinite;
}

@keyframes webPattern {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}

/* Enhanced dataframes */
.stDataFrame {
    border-radius: 8px;
    overflow: hidden;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}
.stDataFrame thead th {
    background-color: #f8f9fa;
    font-weight: 600;
    color: #495057;
    border-bottom: 2px solid #dee2e6;
}
.stDataFrame tbody tr:nth-child(odd) {
    background-color: rgba(0, 123, 255, 0.05);
}
.stDataFrame tbody tr:hover {
    background-color: rgba(0, 123, 255, 0.1);
    transition: background-color 0.2s ease;
}

/* Buttons */
.stButton > button {
    border-radius: 8px;
    font-weight: 600;
    transition: all 0.2s ease;
    border: 2px solid transparent;
}
.stButton > button:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
}
.stButton > button[kind="primary"] {
    background: linear-gradient(45deg, #007bff, #0056b3);
    border-color: #007bff;
}

/* Section headers */
h1, h2, h3 {
    margin-bottom: 1rem;
    color: #2c3e50;
}
h1 {
    border-bottom: 3px solid #007bff;
    padding-bottom: 0.5rem;
}
h2 {
    color: #34495e;
}

/* Sidebar styling */
.css-1d391kg {
    background-color: #f8f9fa;
}

/* Upload area */
.stFileUploader {
    border: 2px dashed #007bff;
    border-radius: 8px;
    padding: 1rem;
    background-color: #f8f9fa;
    transition: all 0.2s ease;
}
.stFileUploader:hover {
    border-color: #0056b3;
    background-color: #e9ecef;
}

/* Progress bars */
.stProgress .st-bo {
    background-color: #e9ecef;
    border-radius: 10px;
}
.stProgress .st-bp {
    background: linear-gradient(90deg, #007bff, #28a745);
    border-radius: 10px;
}

/* Expanders */
.streamlit-expanderHeader {
    font-weight: 600;
    border-radius: 8px;
    background-color: #f8f9fa;
    border: 1px solid #e9ecef;
}

/* Info/warning/error boxes */
.stAlert {
    border-radius: 8px;
    border-left: 4px solid;
}
.stAlert[kind="info"] {
    border-left-color: #17a2b8;
    background-color: #d1ecf1;
}
.stAlert[kind="success"] {
    border-left-color: #28a745;
    background-color: #d4edda;
}
.stAlert[kind="warning"] {
    border-left-color: #ffc107;
    background-color: #fff3cd;
}
.stAlert[kind="error"] {
    border-left-color: #dc3545;
    background-color: #f8d7da;
}

/* Loading spinner */
.stSpinner {
    text-align: center;
}

/* Responsive design */
@media (max-width: 768px) {
    .stTabs [data-baseweb="tab"] {
        padding: 6px 12px;
        height: 40px;
        font-size: 0.9rem;
    }
    .metric-container {
        padding: 1rem;
    }
}

/* Logo and branding enhancements */
.logo-container {
    position: relative;
    display: inline-block;
}

.logo-container::before {
    content: '';
    position: absolute;
    top: -10px;
    left: -10px;
    right: -10px;
    bottom: -10px;
    background: radial-gradient(circle at center, rgba(102, 126, 234, 0.1) 0%, transparent 70%);
    border-radius: 50%;
    z-index: -1;
    animation: logoGlow 3s ease-in-out infinite alternate;
}

@keyframes logoGlow {
    0% { opacity: 0.3; transform: scale(0.95); }
    100% { opacity: 0.6; transform: scale(1.05); }
}

/* Musical note decorations */
.musical-notes {
    position: absolute;
    width: 100%;
    height: 100%;
    pointer-events: none;
    overflow: hidden;
}

.musical-notes::after {
    content: '♪ ♫ ♪ ♫';
    position: absolute;
    top: 20%;
    right: -20px;
    font-size: 1.2rem;
    color: rgba(102, 126, 234, 0.2);
    animation: float 6s ease-in-out infinite;
}

@keyframes float {
    0%, 100% { transform: translateY(0px) rotate(0deg); }
    50% { transform: translateY(-10px) rotate(5deg); }
}
</style>
""", unsafe_allow_html=True)


# Helpers for thumbnails and explicit flags
def _yt_thumb_from_track(track: Track) -> Optional[str]:
    try:
        # Only attempt for YouTube Music
        if getattr(track, 'platform', '') != 'youtube_music':
            return None
        vid = getattr(track, 'track_id', None)
        if not vid:
            url = getattr(track, 'url', '') or ''
            if 'watch?v=' in url:
                vid = url.split('watch?v=')[1].split('&')[0]
        if vid:
            return f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"
    except Exception:
        pass
    return None


def _explicit_hint_from_title(title: str) -> bool:
    try:
        return 'explicit' in (title or '').lower()
    except Exception:
        return False


class SessionManager:
    """Manage session state for the web interface."""
    
    @staticmethod
    def initialize_session():
        """Initialize session state variables."""
        if 'libraries' not in st.session_state:
            st.session_state.libraries = {}
        
        if 'comparison_results' not in st.session_state:
            st.session_state.comparison_results = {}
        
        if 'playlist_manager' not in st.session_state:
            st.session_state.playlist_manager = None
        
        if 'enrichment_data' not in st.session_state:
            st.session_state.enrichment_data = {}
        
        if 'ytm_dedup' not in st.session_state:
            st.session_state.ytm_dedup = None
        if 'ytm_dedup_results' not in st.session_state:
            st.session_state.ytm_dedup_results = None
        if 'ytm_headers_path' not in st.session_state:
            st.session_state.ytm_headers_path = None
        if 'ytm_dedup_selected_group_ids' not in st.session_state:
            st.session_state.ytm_dedup_selected_group_ids = []
    
    @staticmethod
    def add_library(name: str, library: Library):
        """Add library to session state."""
        st.session_state.libraries[name] = library
    
    @staticmethod
    def get_library(name: str) -> Optional[Library]:
        """Get library from session state."""
        return st.session_state.libraries.get(name)
    
    @staticmethod
    def list_libraries() -> List[str]:
        """List available library names."""
        return list(st.session_state.libraries.keys())


def render_header():
    """Render the main header with enhanced branding."""
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("""
        <div style="text-align: center; padding: 2rem 0; position: relative;" class="musical-notes">
            <div class="logo-container" style="margin-bottom: 1rem;">
                <img src="data:image/png;base64,{logo_base64}" style="width: 150px; height: 150px; margin-bottom: 1rem; filter: drop-shadow(0 6px 12px rgba(0, 0, 0, 0.15)); transition: transform 0.3s ease;" alt="Mega Music Comparator Logo"/>
            </div>
            <p style="font-size: 1.4rem; color: #2c3e50; margin: 0; font-weight: 600; letter-spacing: 0.5px;">
                Mega Music Comparator
            </p>
            <div style="width: 120px; height: 3px; background: linear-gradient(45deg, #667eea, #764ba2); margin: 1rem auto; border-radius: 2px;"></div>
        </div>
        """.format(logo_base64=get_logo_base64()), unsafe_allow_html=True)


def render_sidebar():
    """Render the sidebar with file uploads and library management."""
    # Small logo in sidebar
    if get_logo_base64():
        st.sidebar.markdown(f"""
        <div style="text-align: center; padding: 0.5rem 0;">
            <img src="data:image/png;base64,{get_logo_base64()}" style="width: 50px; height: 50px; opacity: 0.9;" alt="Mega Music Comparator"/>
        </div>
        """, unsafe_allow_html=True)
    
    st.sidebar.header("▶ Library Management")
    
    # File upload section with better UX
    with st.sidebar.expander("⬆ Upload Library Files", expanded=True):
        st.markdown("""
        <div style="background-color: #e8f5e8; padding: 1rem; border-radius: 8px; margin-bottom: 1rem;">
            <p style="margin: 0; font-size: 0.9rem; color: #2d5016;">
                <strong>Supported formats:</strong><br>
                • Apple Music: CSV or XML export<br>
                • Spotify: CSV (Exportify) or JSON export<br>
                • YouTube Music: JSON from Google Takeout<br>
                • Generic: CSV with Title, Artist, Album columns
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        uploaded_files = st.file_uploader(
            "Choose library files",
            accept_multiple_files=True,
            type=['csv', 'json', 'xml'],
            help="Drag and drop files or click to browse"
        )
        
        if uploaded_files:
            for uploaded_file in uploaded_files:
                # Enhanced file loading with better feedback
                if st.button(f"📤 Load {uploaded_file.name}", key=f"load_{uploaded_file.name}", use_container_width=True):
                    with st.spinner(f"Loading {uploaded_file.name}..."):
                        progress_bar = st.progress(0)
                        progress_bar.progress(0.3)
                        
                        success = load_uploaded_file(uploaded_file)
                        
                        progress_bar.progress(1.0)
                        
                        if success:
                            progress_bar.empty()
                            st.balloons()
                            st.success(f"✅ Successfully loaded {uploaded_file.name}")
                            time.sleep(1)  # Brief pause to show success
                            st.rerun()
                        else:
                            progress_bar.empty()
    
    # Existing libraries
    libraries = SessionManager.list_libraries()
    if libraries:
        st.sidebar.header("♪ Loaded Libraries")
        for lib_name in libraries:
            library = SessionManager.get_library(lib_name)
            with st.sidebar.expander(f"♫ {lib_name}", expanded=False):
                st.write(f"**Platform:** {library.platform}")
                st.write(f"**Total tracks:** {library.total_tracks:,}")
                st.write(f"**Music tracks:** {library.music_count:,}")
                st.write(f"**Non-music:** {library.non_music_count:,}")
                st.write(f"**Artists:** {len(library.artist_counts):,}")
                
                if st.button(f"Remove {lib_name}", key=f"remove_{lib_name}"):
                    del st.session_state.libraries[lib_name]
                    st.rerun()
    
    # YouTube Music setup
    st.sidebar.header("♫ YouTube Music")
    headers_file = st.sidebar.file_uploader(
        "Upload headers file",
        type=['json', 'txt', 'i'],
        help="Headers in JSON format or raw HTTP headers format"
    )
    
    if headers_file:
        if st.sidebar.button("Setup YouTube Music"):
            # Process the headers file (converts raw to JSON if needed)
            tmp_path = process_headers_upload(headers_file)
            
            if tmp_path:
                try:
                    playlist_manager = PlaylistManager(tmp_path)
                    if playlist_manager.is_available():
                        st.session_state.playlist_manager = playlist_manager
                        st.session_state.ytm_headers_path = tmp_path
                        st.sidebar.success("● YouTube Music connected")
                        
                        # Show format info if conversion occurred
                        if not headers_file.name.endswith('.json'):
                            st.sidebar.info("▣ Raw headers converted to JSON format")
                    else:
                        st.sidebar.error("✖ Failed to connect to YouTube Music")
                except Exception as e:
                    st.sidebar.error(f"✖ Setup failed: {e}")
            # Keep the headers file path for reuse in Dedup tab


def load_uploaded_file(uploaded_file) -> bool:
    """Load an uploaded file into session state with enhanced error handling."""
    try:
        # Validate file size (max 100MB)
        file_size = len(uploaded_file.getvalue())
        if file_size > 100 * 1024 * 1024:  # 100MB limit
            st.error("❌ File too large. Maximum size is 100MB.")
            return False
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix=Path(uploaded_file.name).suffix) as tmp:
            tmp.write(uploaded_file.getvalue())
            tmp_path = tmp.name
        
        # Detect platform
        platform = detect_platform(tmp_path)
        
        if not platform:
            st.error(f"❌ Unsupported file format: {uploaded_file.name}")
            Path(tmp_path).unlink(missing_ok=True)
            return False
        
        # Create parser and load library
        parser = create_parser(platform)
        library = parser.parse_file(tmp_path)
        
        # Validate library has content
        if library.total_tracks == 0:
            st.warning(f"⚠️ No tracks found in {uploaded_file.name}")
            Path(tmp_path).unlink(missing_ok=True)
            return False
        
        # Add to session state with cleaner name
        clean_name = uploaded_file.name.replace('.csv', '').replace('.json', '').replace('.xml', '')
        lib_name = f"{platform.title()} - {clean_name}"
        SessionManager.add_library(lib_name, library)
        
        # Cleanup
        Path(tmp_path).unlink(missing_ok=True)
        
        return True
    
    except Exception as e:
        st.error(f"❌ Error loading {uploaded_file.name}: {str(e)}")
        if 'tmp_path' in locals():
            Path(tmp_path).unlink(missing_ok=True)
        return False


def convert_raw_headers_to_json(raw_headers_text: str) -> Dict[str, str]:
    """Convert raw HTTP headers text to JSON format."""
    headers = {}
    
    for line in raw_headers_text.splitlines():
        line = line.strip()
        if not line or ':' not in line:
            continue
        
        # Skip the first line if it's an HTTP request line (starts with GET/POST/etc)
        if any(line.startswith(method) for method in ['GET', 'POST', 'PUT', 'DELETE', 'HEAD', 'OPTIONS']):
            continue
            
        key, val = line.split(':', 1)
        headers[key.strip()] = val.strip()
    
    # Ensure required defaults if missing
    headers.setdefault('X-Goog-AuthUser', '0')
    headers.setdefault('x-origin', 'https://music.youtube.com')
    
    return headers


def process_headers_upload(uploaded_file) -> Optional[str]:
    """Process uploaded headers file, converting raw headers to JSON if needed."""
    try:
        content = uploaded_file.getvalue().decode('utf-8')
        
        # Try to parse as JSON first
        try:
            json.loads(content)
            # It's already valid JSON, save as-is
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
                tmp.write(content)
                return tmp.name
        except json.JSONDecodeError:
            # Not JSON, treat as raw headers
            headers_dict = convert_raw_headers_to_json(content)
            
            # Save converted JSON
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
                json.dump(headers_dict, tmp, indent=2)
                return tmp.name
                
    except Exception as e:
        st.error(f"Error processing headers file: {e}")
        return None


def render_overview_tab():
    """Render the overview tab."""
    st.header("📊 Library Overview")
    
    libraries = SessionManager.list_libraries()
    
    if not libraries:
        st.markdown("""
        <div style="text-align: center; padding: 3rem; background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); border-radius: 12px; margin: 2rem 0;">
            <h3 style="color: #495057; margin-bottom: 1rem;">🚀 Welcome to MusicWeb!</h3>
            <p style="color: #6c757d; font-size: 1.1rem; margin-bottom: 2rem;">
                To get started, upload your music library files using the sidebar.
            </p>
            <div style="display: flex; justify-content: center; gap: 2rem; flex-wrap: wrap;">
                <div style="text-align: center; flex: 1; min-width: 200px;">
                    <div style="font-size: 2rem; margin-bottom: 0.5rem;">🍎</div>
                    <strong>Apple Music</strong><br>
                    <small>Export as CSV</small>
                </div>
                <div style="text-align: center; flex: 1; min-width: 200px;">
                    <div style="font-size: 2rem; margin-bottom: 0.5rem;">🎵</div>
                    <strong>Spotify</strong><br>
                    <small>Use Exportify tool</small>
                </div>
                <div style="text-align: center; flex: 1; min-width: 200px;">
                    <div style="font-size: 2rem; margin-bottom: 0.5rem;">📺</div>
                    <strong>YouTube Music</strong><br>
                    <small>Google Takeout JSON</small>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        return
    
    # Enhanced summary metrics with visual improvements
    total_libraries = len(libraries)
    total_tracks = sum(SessionManager.get_library(name).total_tracks for name in libraries)
    total_music = sum(SessionManager.get_library(name).music_count for name in libraries)
    total_artists = len(set().union(*(SessionManager.get_library(name).artist_counts.keys() for name in libraries)))
    
    st.markdown("### 📊 Library Summary")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 1.5rem; border-radius: 12px; text-align: center; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);">
            <div style="font-size: 2rem; margin-bottom: 0.5rem;">📚</div>
            <div style="font-size: 2rem; font-weight: bold;">{}</div>
            <div style="font-size: 0.9rem; opacity: 0.9;">Libraries</div>
        </div>
        """.format(total_libraries), unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); color: white; padding: 1.5rem; border-radius: 12px; text-align: center; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);">
            <div style="font-size: 2rem; margin-bottom: 0.5rem;">🎵</div>
            <div style="font-size: 2rem; font-weight: bold;">{:,}</div>
            <div style="font-size: 0.9rem; opacity: 0.9;">Total Tracks</div>
        </div>
        """.format(total_tracks), unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); color: white; padding: 1.5rem; border-radius: 12px; text-align: center; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);">
            <div style="font-size: 2rem; margin-bottom: 0.5rem;">🎶</div>
            <div style="font-size: 2rem; font-weight: bold;">{:,}</div>
            <div style="font-size: 0.9rem; opacity: 0.9;">Music Tracks</div>
        </div>
        """.format(total_music), unsafe_allow_html=True)
    
    with col4:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #fa709a 0%, #fee140 100%); color: white; padding: 1.5rem; border-radius: 12px; text-align: center; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);">
            <div style="font-size: 2rem; margin-bottom: 0.5rem;">👨‍🎤</div>
            <div style="font-size: 2rem; font-weight: bold;">{:,}</div>
            <div style="font-size: 0.9rem; opacity: 0.9;">Unique Artists</div>
        </div>
        """.format(total_artists), unsafe_allow_html=True)
    
    # Library details
    st.subheader("📚 Library Details")
    
    lib_data = []
    for lib_name in libraries:
        library = SessionManager.get_library(lib_name)
        lib_data.append({
            'Library': lib_name,
            'Platform': library.platform.title(),
            'Total Tracks': library.total_tracks,
            'Music Tracks': library.music_count,
            'Non-Music': library.non_music_count,
            'Unique Artists': len(library.artist_counts),
            'Top Artist': library.top_artists[0][0] if library.top_artists else 'N/A'
        })
    
    df = pd.DataFrame(lib_data)
    st.dataframe(df, use_container_width=True)
    
    # Visualization
    if HAVE_VISUALIZATION and len(libraries) > 1:
        st.subheader("📈 Library Comparison")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Track counts
            fig = px.bar(
                df, 
                x='Library', 
                y='Music Tracks',
                title='Music Tracks by Library',
                color='Platform'
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Artist counts
            fig = px.bar(
                df, 
                x='Library', 
                y='Unique Artists',
                title='Unique Artists by Library',
                color='Platform'
            )
            st.plotly_chart(fig, use_container_width=True)


def render_compare_tab():
    """Render the comparison tab."""
    st.header("🔍 Library Comparison")
    
    libraries = SessionManager.list_libraries()
    
    if len(libraries) < 2:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #fff3cd 0%, #ffeaa7 100%); padding: 2rem; border-radius: 12px; text-align: center; border-left: 4px solid #ffc107;">
            <h4 style="color: #856404; margin-bottom: 1rem;">📊 Library Comparison</h4>
            <p style="color: #856404; margin-bottom: 1rem;">You need at least 2 libraries to perform comparison analysis.</p>
            <p style="color: #856404; margin: 0; font-size: 0.9rem;">Upload more libraries using the sidebar to unlock this feature.</p>
        </div>
        """, unsafe_allow_html=True)
        return
    
    # Comparison setup
    col1, col2 = st.columns(2)
    
    with col1:
        source_lib = st.selectbox("Source Library", libraries)
    with col2:
        target_lib = st.selectbox("Target Library", [lib for lib in libraries if lib != source_lib])
    
    # Comparison options
    with st.expander("⚙️ Comparison Options", expanded=False):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            strict_mode = st.checkbox("Strict Matching", value=True, help="Higher precision, fewer false matches")
        with col2:
            use_duration = st.checkbox("Use Duration", value=True, help="Include duration in matching")
        with col3:
            use_album = st.checkbox("Use Album", value=False, help="Include album in matching")
    
    # Enhanced comparison button
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🔍 Compare Libraries", type="primary", use_container_width=True):
            if source_lib and target_lib:
                with st.spinner("Comparing libraries..."):
                    source_library = SessionManager.get_library(source_lib)
                    target_library = SessionManager.get_library(target_lib)
                    
                    comparator = LibraryComparator(
                        strict_mode=strict_mode,
                        enable_duration=use_duration,
                        enable_album=use_album
                    )
                    
                    # Enhanced progress display
                    progress_container = st.container()
                    with progress_container:
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                    def progress_callback(current, total, message):
                        progress = current / total if total > 0 else 0
                        progress_bar.progress(progress)
                        status_text.markdown(f"**{message}** ({current}/{total})")
                    
                    comparator.progress_callback = progress_callback
                    
                    result = comparator.compare_libraries(source_library, target_library)
                    
                    # Store result
                    comparison_key = f"{source_lib}_vs_{target_lib}"
                    st.session_state.comparison_results[comparison_key] = result
                    
                    progress_bar.empty()
                    status_text.empty()
                
                st.markdown("""
                <div style="background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%); padding: 1.5rem; border-radius: 12px; border-left: 4px solid #28a745; margin: 1rem 0;">
                    <h4 style="color: #155724; margin: 0;">✅ Comparison Complete!</h4>
                    <p style="color: #155724; margin: 0.5rem 0 0 0;">Your libraries have been analyzed successfully.</p>
                </div>
                """, unsafe_allow_html=True)
    
    # Display results
    comparison_key = f"{source_lib}_vs_{target_lib}"
    if comparison_key in st.session_state.comparison_results:
        result = st.session_state.comparison_results[comparison_key]
        display_comparison_results(result)


def display_comparison_results(result):
    """Display comparison results."""
    stats = result.get_stats()
    
    # Enhanced summary metrics
    st.markdown("### 📊 Comparison Results")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #28a745 0%, #20c997 100%); color: white; padding: 1.5rem; border-radius: 12px; text-align: center; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);">
            <div style="font-size: 1.5rem; margin-bottom: 0.5rem;">✅</div>
            <div style="font-size: 1.8rem; font-weight: bold;">{:,}</div>
            <div style="font-size: 0.9rem; opacity: 0.9;">Total Matches</div>
        </div>
        """.format(stats['total_matches']), unsafe_allow_html=True)
    
    with col2:
        match_rate = stats['match_rate']
        color = "#28a745" if match_rate >= 80 else "#ffc107" if match_rate >= 60 else "#dc3545"
        st.markdown("""
        <div style="background: linear-gradient(135deg, {} 0%, {} 100%); color: white; padding: 1.5rem; border-radius: 12px; text-align: center; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);">
            <div style="font-size: 1.5rem; margin-bottom: 0.5rem;">🎯</div>
            <div style="font-size: 1.8rem; font-weight: bold;">{:.1f}%</div>
            <div style="font-size: 0.9rem; opacity: 0.9;">Match Rate</div>
        </div>
        """.format(color, color, match_rate), unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #007bff 0%, #6610f2 100%); color: white; padding: 1.5rem; border-radius: 12px; text-align: center; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);">
            <div style="font-size: 1.5rem; margin-bottom: 0.5rem;">🏆</div>
            <div style="font-size: 1.8rem; font-weight: bold;">{:.1f}%</div>
            <div style="font-size: 0.9rem; opacity: 0.9;">Avg Confidence</div>
        </div>
        """.format(stats['avg_confidence']), unsafe_allow_html=True)
    
    with col4:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #6c757d 0%, #495057 100%); color: white; padding: 1.5rem; border-radius: 12px; text-align: center; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);">
            <div style="font-size: 1.5rem; margin-bottom: 0.5rem;">❌</div>
            <div style="font-size: 1.8rem; font-weight: bold;">{:,}</div>
            <div style="font-size: 0.9rem; opacity: 0.9;">Missing Tracks</div>
        </div>
        """.format(stats['missing_tracks']), unsafe_allow_html=True)
    
    # Match breakdown
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Exact Matches", f"{stats['exact_matches']:,}")
    with col2:
        st.metric("Fuzzy Matches", f"{stats['fuzzy_matches']:,}")
    with col3:
        st.metric("ISRC Matches", f"{stats['isrc_matches']:,}")
    
    # Detailed results
    tabs = st.tabs(["🎯 Matched Tracks", "❌ Missing Tracks", "📈 Visualizations"])
    
    with tabs[0]:
        if result.matches:
            matches_data = []
            for match in result.matches:
                s_thumb = _yt_thumb_from_track(match.source_track)
                t_thumb = _yt_thumb_from_track(match.target_track)
                s_explicit = _explicit_hint_from_title(match.source_track.title)
                t_explicit = _explicit_hint_from_title(match.target_track.title)
                matches_data.append({
                    'Source Thumb': s_thumb or '',
                    'Source Title': match.source_track.title,
                    'Source Artist': match.source_track.artist,
                    'Source Explicit': s_explicit,
                    'Target Thumb': t_thumb or '',
                    'Target Title': match.target_track.title,
                    'Target Artist': match.target_track.artist,
                    'Target Explicit': t_explicit,
                    'Confidence': f"{match.confidence:.1%}",
                    'Match Type': match.match_type.title()
                })
            
            matches_df = pd.DataFrame(matches_data)
            try:
                st.dataframe(
                    matches_df,
                    use_container_width=True,
                    column_config={
                        'Source Thumb': st.column_config.ImageColumn('Src', width='small'),
                        'Target Thumb': st.column_config.ImageColumn('Dst', width='small'),
                        'Source Explicit': st.column_config.CheckboxColumn('Src Explicit'),
                        'Target Explicit': st.column_config.CheckboxColumn('Dst Explicit'),
                    }
                )
            except Exception:
                # Fallback without column_config on older Streamlit
                st.dataframe(matches_df, use_container_width=True)
            
            # Enhanced download section
            st.markdown("---")
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                csv = matches_df.to_csv(index=False)
                st.download_button(
                    "📥 Download Matched Tracks CSV",
                    csv,
                    f"matched_tracks_{int(time.time())}.csv",
                    "text/csv",
                    use_container_width=True
                )
        else:
            st.info("No matched tracks found")
    
    with tabs[1]:
        if result.missing_tracks:
            missing_data = []
            for track in result.missing_tracks:
                thumb = _yt_thumb_from_track(track)
                explicit = _explicit_hint_from_title(track.title)
                missing_data.append({
                    'Thumb': thumb or '',
                    'Title': track.title,
                    'Artist': track.artist,
                    'Album': track.album or '',
                    'Duration': f"{track.duration}s" if track.duration else '',
                    'Explicit': explicit,
                    'Platform': track.platform or ''
                })
            
            missing_df = pd.DataFrame(missing_data)
            try:
                st.dataframe(
                    missing_df,
                    use_container_width=True,
                    column_config={
                        'Thumb': st.column_config.ImageColumn('Thumb', width='small'),
                        'Explicit': st.column_config.CheckboxColumn('Explicit'),
                    }
                )
            except Exception:
                st.dataframe(missing_df, use_container_width=True)
            
            # Enhanced download section
            st.markdown("---")
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                csv = missing_df.to_csv(index=False)
                st.download_button(
                    "📥 Download Missing Tracks CSV",
                    csv,
                    f"missing_tracks_{int(time.time())}.csv",
                    "text/csv",
                    use_container_width=True
                )
            
            # Enhanced YouTube Music playlist creation
            if st.session_state.playlist_manager:
                st.markdown("---")
                st.markdown("### 🎵 Create YouTube Music Playlist")
                
                st.markdown("""
                <div style="background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%); padding: 1rem; border-radius: 8px; margin: 1rem 0; border-left: 4px solid #2196f3;">
                    <p style="margin: 0; color: #0d47a1;">
                        <strong>🎯 Pro Tip:</strong> Create a playlist from missing tracks to easily add them to your YouTube Music library.
                    </p>
                </div>
                """, unsafe_allow_html=True)
                
                playlist_name = st.text_input("Playlist Name", f"Missing Tracks {time.strftime('%Y-%m-%d')}")
                
                col1, col2, col3 = st.columns([1, 2, 1])
                with col2:
                    if st.button("🎵 Create Playlist", type="primary", use_container_width=True):
                        with st.spinner("Creating playlist..."):
                            playlist_result = st.session_state.playlist_manager.create_playlist(
                                playlist_name=playlist_name,
                                tracks=result.missing_tracks,
                                search_fallback=True
                            )
                            
                            if playlist_result['success']:
                                st.success(f"✅ Playlist created! Added {playlist_result['total_added']}/{playlist_result['total_requested']} tracks")
                            else:
                                st.error(f"❌ Failed to create playlist: {playlist_result['error']}")
        else:
            st.info("No missing tracks - perfect match!")
    
    with tabs[2]:
        if HAVE_VISUALIZATION:
            render_comparison_charts(result, stats)


def render_comparison_charts(result, stats):
    """Render comparison visualization charts."""
    col1, col2 = st.columns(2)
    
    with col1:
        # Match type distribution
        match_data = {
            'Exact': stats['exact_matches'],
            'Fuzzy': stats['fuzzy_matches'],
            'ISRC': stats['isrc_matches']
        }
        
        fig = px.pie(
            values=list(match_data.values()),
            names=list(match_data.keys()),
            title='Match Type Distribution'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Overall match rate
        match_rate = stats['match_rate'] / 100
        missing_rate = 1 - match_rate
        
        fig = go.Figure(data=[
            go.Bar(name='Matched', x=[''], y=[match_rate * 100]),
            go.Bar(name='Missing', x=[''], y=[missing_rate * 100])
        ])
        
        fig.update_layout(
            title='Overall Match Rate',
            yaxis_title='Percentage',
            barmode='stack'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Confidence distribution
    if result.matches:
        confidences = [match.confidence * 100 for match in result.matches]
        
        fig = px.histogram(
            x=confidences,
            nbins=20,
            title='Match Confidence Distribution',
            labels={'x': 'Confidence (%)', 'y': 'Number of Matches'}
        )
        st.plotly_chart(fig, use_container_width=True)


def render_analyze_tab():
    """Render the analysis tab."""
    st.header("📊 Multi-Library Analysis")
    
    libraries = SessionManager.list_libraries()
    
    if len(libraries) < 2:
        st.warning("⚠️ Need at least 2 libraries for analysis")
        return
    
    # Select libraries to analyze
    selected_libs = st.multiselect(
        "Select libraries to analyze",
        libraries,
        default=libraries
    )
    
    if len(selected_libs) < 2:
        st.warning("⚠️ Select at least 2 libraries")
        return
    
    # Analysis options
    with st.expander("⚙️ Analysis Options", expanded=False):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            strict_mode = st.checkbox("Strict Matching", value=True, key="analyze_strict")
        with col2:
            use_duration = st.checkbox("Use Duration", value=True, key="analyze_duration")
        with col3:
            use_album = st.checkbox("Use Album", value=False, key="analyze_album")
    
    # Perform analysis
    if st.button("📊 Analyze Libraries", type="primary"):
        with st.spinner("Analyzing libraries..."):
            selected_libraries = [SessionManager.get_library(name) for name in selected_libs]
            
            comparator = LibraryComparator(
                strict_mode=strict_mode,
                enable_duration=use_duration,
                enable_album=use_album
            )
            
            analysis = comparator.analyze_libraries(selected_libraries)
            
            # Store analysis results
            st.session_state.analysis_results = analysis
            
            st.success("✅ Analysis complete!")
    
    # Display analysis results
    if hasattr(st.session_state, 'analysis_results'):
        display_analysis_results(st.session_state.analysis_results)


def display_analysis_results(analysis):
    """Display multi-library analysis results."""
    st.subheader("📈 Analysis Results")
    
    # Universal tracks
    universal_count = len(analysis['universal_tracks'])
    universal_artists = len(analysis['artist_analysis']['universal_artists'])
    total_artists = analysis['artist_analysis']['total_unique_artists']
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Universal Tracks", f"{universal_count:,}")
    with col2:
        st.metric("Universal Artists", f"{universal_artists:,}")
    with col3:
        st.metric("Total Unique Artists", f"{total_artists:,}")
    
    # Tabs for detailed analysis
    tabs = st.tabs(["🔄 Pairwise Comparisons", "🌟 Universal Content", "🎨 Unique Content", "👥 Artist Analysis"])
    
    with tabs[0]:
        st.subheader("📊 Pairwise Comparison Matrix")
        
        comparison_data = []
        for comp in analysis['pairwise_comparisons']:
            comparison_data.append({
                'Source': comp['source'],
                'Target': comp['target'],
                'Match Rate': f"{comp['stats']['match_rate']:.1f}%",
                'Total Matches': comp['stats']['total_matches'],
                'Missing': comp['stats']['missing_tracks']
            })
        
        comp_df = pd.DataFrame(comparison_data)
        st.dataframe(comp_df, use_container_width=True)
    
    with tabs[1]:
        st.subheader("🌟 Universal Content")
        
        if analysis['universal_tracks']:
            universal_df = pd.DataFrame(analysis['universal_tracks'])
            st.dataframe(universal_df, use_container_width=True)
            
            # Download
            csv = universal_df.to_csv(index=False)
            st.download_button(
                "📥 Download Universal Tracks",
                csv,
                f"universal_tracks_{int(time.time())}.csv",
                "text/csv"
            )
        else:
            st.info("No tracks found in all libraries")
    
    with tabs[2]:
        st.subheader("🎨 Unique Content per Library")
        
        for lib_name, unique_tracks in analysis['unique_tracks'].items():
            with st.expander(f"📚 {lib_name} ({len(unique_tracks)} unique tracks)"):
                if unique_tracks:
                    unique_df = pd.DataFrame(unique_tracks)
                    st.dataframe(unique_df, use_container_width=True)
                else:
                    st.info("No unique tracks")
    
    with tabs[3]:
        st.subheader("👥 Artist Analysis")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Universal Artists:**")
            if analysis['artist_analysis']['universal_artists']:
                universal_artists_df = pd.DataFrame(
                    analysis['artist_analysis']['universal_artists'], 
                    columns=['Artist']
                )
                st.dataframe(universal_artists_df)
            else:
                st.info("No universal artists")
        
        with col2:
            st.write("**Top Artists by Total Tracks:**")
            if analysis['artist_analysis']['top_overlap_artists']:
                top_artists_data = []
                for artist, count in analysis['artist_analysis']['top_overlap_artists'][:10]:
                    top_artists_data.append({'Artist': artist, 'Total Tracks': count})
                
                top_artists_df = pd.DataFrame(top_artists_data)
                st.dataframe(top_artists_df)


def render_enrich_tab():
    """Render the enrichment tab."""
    st.header("🔍 Metadata Enrichment")
    
    libraries = SessionManager.list_libraries()
    
    if not libraries:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #fff3cd 0%, #ffeaa7 100%); padding: 2rem; border-radius: 12px; text-align: center; border-left: 4px solid #ffc107;">
            <h4 style="color: #856404; margin-bottom: 1rem;">📚 Enrichment Ready</h4>
            <p style="color: #856404; margin-bottom: 1rem;">Upload some music libraries first to unlock metadata enrichment.</p>
            <p style="color: #856404; margin: 0; font-size: 0.9rem;">Use the sidebar to get started with your library files.</p>
        </div>
        """, unsafe_allow_html=True)
        return
    
    # Select library to enrich
    selected_lib = st.selectbox("Select library to enrich", libraries, help="Choose which loaded library to enrich")
    
    if not selected_lib:
        return
    
    library = SessionManager.get_library(selected_lib)
    
    # Key stats for CTA context
    missing_isrc = sum(1 for t in library.music_tracks if not getattr(t, 'isrc', None))
    st.info(f"📊 {library.name}: {library.music_count:,} music tracks | Missing ISRC: {missing_isrc:,}")
    
    # Clear primary CTAs
    st.markdown(
        """
        <div style="background: linear-gradient(135deg, #e3f2fd 0%, #f1f8ff 100%); padding: 1rem 1.25rem; border-radius: 12px; border: 1px solid #cfe2ff; margin: 0.5rem 0 1rem;">
            <div style="display:flex; align-items:center; gap:10px; margin-bottom: 0.75rem;">
                <span style="font-size: 1.25rem;">🧩</span>
                <div style="font-weight: 600; color: #0d6efd;">Add ISRC Codes via MusicBrainz</div>
            </div>
            <div style="color: #1b4b91; font-size: 0.95rem;">Find and attach official ISRC identifiers to tracks that are missing them. Uses MusicBrainz with safe rate limits.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    cta1, spacer, cta2 = st.columns([2, 1, 2])
    enrich_isrc_clicked = False
    enrich_full_clicked = False
    with cta1:
        enrich_isrc_clicked = st.button(
            "🔐 Add ISRC Codes (MusicBrainz)",
            type="primary",
            use_container_width=True,
            help="Recommended. Adds missing ISRC codes only, leaving other fields unchanged."
        )
    with cta2:
        enrich_full_clicked = st.button(
            "✨ Full Metadata Enrichment",
            use_container_width=True,
            help="Adds ISRC where missing and may fill duration and genre."
        )

    # Advanced options
    with st.expander("⚙️ Advanced Options", expanded=False):
        limit_tracks = st.checkbox("Limit tracks (for testing)")
        if limit_tracks:
            max_tracks = st.number_input("Max tracks to enrich", min_value=1, max_value=1000, value=50)
        else:
            max_tracks = None
    
    # Warning about rate limits
    # Enhanced warning with better styling
    st.markdown("""
    <div style="background: linear-gradient(135deg, #fff3cd 0%, #ffeaa7 100%); padding: 1.5rem; border-radius: 12px; border-left: 4px solid #ffc107; margin: 1rem 0;">
        <h4 style="color: #856404; margin-bottom: 1rem;">⚠️ Rate Limiting Notice</h4>
        <p style="color: #856404; margin-bottom: 0.5rem;"><strong>MusicBrainz API</strong> is rate-limited to 1 request per 1.2 seconds.</p>
        <p style="color: #856404; margin: 0;">Large libraries may take significant time to process. Consider using the limit option for testing.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Perform enrichment (ISRC-only or Full)
    if enrich_isrc_clicked or enrich_full_clicked:
        scope = "isrc_only" if enrich_isrc_clicked else "full"
        with st.spinner("Enriching metadata..."):
            enricher = EnrichmentManager()

            tracks_to_enrich = library.music_tracks
            if max_tracks:
                tracks_to_enrich = tracks_to_enrich[:max_tracks]

            # Progress tracking
            progress_bar = st.progress(0)
            status_text = st.empty()

            def progress_callback(current, total, message):
                progress = current / total if total > 0 else 0
                progress_bar.progress(progress)
                status_text.text(message)

            if scope == "full":
                enriched_results = enricher.bulk_enrich(tracks_to_enrich, progress_callback)
            else:
                # ISRC-only: fetch enrichment but apply only ISRC back to track
                enriched_results = []
                total = len(tracks_to_enrich)
                for idx, t in enumerate(tracks_to_enrich):
                    progress_callback(idx, total, f"Looking up ISRC: {t.title}")
                    data = enricher.enrich_track(t)
                    # Keep original fields, only set ISRC if newly found
                    new_isrc = None
                    if data and 'enriched_fields' in data:
                        new_isrc = data['enriched_fields'].get('isrc')
                    enhanced = Track(
                        title=t.title,
                        artist=t.artist,
                        album=t.album,
                        duration=t.duration,  # unchanged
                        isrc=new_isrc or t.isrc,
                        platform=t.platform,
                        track_id=t.track_id,
                        url=t.url,
                        year=t.year,
                        genre=t.genre,
                        track_number=t.track_number,
                    )
                    enriched_results.append((enhanced, data or {}))
                progress_callback(total, total, "ISRC enrichment complete")

            progress_bar.empty()
            status_text.empty()

            # Store results
            enrich_key = f"{selected_lib}_enriched"
            st.session_state.enrichment_data[enrich_key] = enriched_results

            # Summary
            successful = sum(1 for _, data in enriched_results if data.get('musicbrainz'))
            scope_msg = "ISRC updates" if scope == "isrc_only" else "metadata updates"
            st.success(f"✅ Completed {successful}/{len(enriched_results)} lookups • Applied {scope_msg}")
    
    # Display enrichment results
    enrich_key = f"{selected_lib}_enriched"
    if enrich_key in st.session_state.enrichment_data:
        display_enrichment_results(st.session_state.enrichment_data[enrich_key])


def display_enrichment_results(enriched_results):
    """Display enrichment results."""
    st.subheader("📊 Enrichment Results")
    
    successful = [result for result in enriched_results if result[1].get('musicbrainz')]
    failed = [result for result in enriched_results if not result[1].get('musicbrainz')]
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Processed", len(enriched_results))
    with col2:
        st.metric("Successfully Enriched", len(successful))
    with col3:
        st.metric("Success Rate", f"{len(successful)/len(enriched_results):.1%}")
    
    # Show enriched tracks
    if successful:
        st.subheader("✅ Successfully Enriched Tracks")
        
        enriched_data = []
        for enhanced_track, enrichment_info in successful:
            mb_data = enrichment_info.get('musicbrainz', {})
            
            enriched_data.append({
                'Title': enhanced_track.title,
                'Artist': enhanced_track.artist,
                'Album': enhanced_track.album or '',
                'Original Duration': enhanced_track.duration or '',
                'MusicBrainz ID': mb_data.get('musicbrainz_id', '')[:8] + '...' if mb_data.get('musicbrainz_id') else '',
                'Added ISRC': bool(enrichment_info.get('enriched_fields', {}).get('isrc')),
                'Added Genre': bool(enrichment_info.get('enriched_fields', {}).get('genre'))
            })
        
        enriched_df = pd.DataFrame(enriched_data)
        st.dataframe(enriched_df, use_container_width=True)
        
        # Download enriched data
        if st.button("📥 Download Enriched Data"):
            enrichment_export = []
            for enhanced_track, enrichment_info in successful:
                export_data = enhanced_track.to_dict()
                export_data['enrichment_source'] = 'musicbrainz'
                export_data['enrichment_data'] = enrichment_info.get('musicbrainz', {})
                enrichment_export.append(export_data)
            
            json_str = json.dumps(enrichment_export, indent=2, default=str)
            st.download_button(
                "📥 Download as JSON",
                json_str,
                f"enriched_data_{int(time.time())}.json",
                "application/json"
            )


def main():
    """Main application entry point."""
    # Initialize session
    SessionManager.initialize_session()
    
    # Render header and sidebar
    render_header()
    render_sidebar()
    
    # Enhanced main tabs with better organization
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
        "📊 Overview", 
        "🔍 Compare", 
        "📊 Analyze", 
        "📝 Playlist Audit",
        "🧹 YTM Dedup",
        "🧽 Playlist Cleanup",
        "🔍 Enrich",
        "ℹ️ Help"
    ])
    
    # Check if we have libraries for library-dependent tabs
    has_libraries = bool(SessionManager.list_libraries())
    
    with tab1:
        if has_libraries:
            render_overview_tab()
        else:
            st.markdown("""
            <div style="text-align: center; padding: 3rem; background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); border-radius: 12px; margin: 2rem 0;">
                <h3 style="color: #495057; margin-bottom: 1rem;">📊 Library Overview</h3>
                <p style="color: #6c757d; font-size: 1.1rem; margin-bottom: 2rem;">
                    Upload your music library files to see detailed analytics and insights.
                </p>
                <div style="background: rgba(255, 255, 255, 0.8); padding: 1rem; border-radius: 8px; margin: 1rem 0;">
                    <small style="color: #6c757d;">👈 Use the sidebar to upload files from Apple Music, Spotify, or YouTube Music</small>
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    with tab2:
        if has_libraries:
            render_compare_tab()
        else:
            st.markdown("""
            <div style="text-align: center; padding: 3rem; background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); border-radius: 12px; margin: 2rem 0;">
                <h3 style="color: #495057; margin-bottom: 1rem;">🔍 Library Comparison</h3>
                <p style="color: #6c757d; font-size: 1.1rem; margin-bottom: 2rem;">
                    Compare your music libraries to find matches, duplicates, and missing tracks.
                </p>
                <div style="background: rgba(255, 255, 255, 0.8); padding: 1rem; border-radius: 8px; margin: 1rem 0;">
                    <small style="color: #6c757d;">👈 Upload at least 2 library files to unlock comparison features</small>
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    with tab3:
        if has_libraries:
            render_analyze_tab()
        else:
            st.markdown("""
            <div style="text-align: center; padding: 3rem; background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); border-radius: 12px; margin: 2rem 0;">
                <h3 style="color: #495057; margin-bottom: 1rem;">📊 Multi-Library Analysis</h3>
                <p style="color: #6c757d; font-size: 1.1rem; margin-bottom: 2rem;">
                    Analyze multiple libraries to find universal tracks, unique content, and artist overlaps.
                </p>
                <div style="background: rgba(255, 255, 255, 0.8); padding: 1rem; border-radius: 8px; margin: 1rem 0;">
                    <small style="color: #6c757d;">👈 Upload at least 2 library files to unlock advanced analytics</small>
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    with tab4:
        render_playlist_audit_tab()

    with tab5:
        render_dedup_tab()

    with tab6:
        render_playlist_cleanup_tab()

    with tab7:
        if has_libraries:
            render_enrich_tab()
        else:
            st.markdown("""
            <div style="text-align: center; padding: 3rem; background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); border-radius: 12px; margin: 2rem 0;">
                <h3 style="color: #495057; margin-bottom: 1rem;">🔍 Metadata Enrichment</h3>
                <p style="color: #6c757d; font-size: 1.1rem; margin-bottom: 2rem;">
                    Enhance your library with additional metadata from MusicBrainz.
                </p>
                <div style="background: rgba(255, 255, 255, 0.8); padding: 1rem; border-radius: 8px; margin: 1rem 0;">
                    <small style="color: #6c757d;">👈 Upload library files to unlock metadata enrichment</small>
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    with tab8:
        render_help_tab()


def render_playlist_audit_tab():
    """Render the Playlist Audit tool."""
    st.header("📝 Playlist Audit against Library")
    st.markdown("Upload a playlist text export (Apple Music text/UTF-16 or simple 'Artist - Title' lines) and audit against a loaded library.")

    # Inputs
    c1, c2 = st.columns(2)
    with c1:
        playlist_file = st.file_uploader(
            "Upload playlist text file (txt/csv)",
            type=None,  # accept any; we'll parse bytes
            key="playlist_audit_upload"
        )
        enable_album = st.checkbox("Use album weighting", value=True)
        enable_duration = st.checkbox("Use duration weighting", value=True)
    with c2:
        libs = SessionManager.list_libraries()
        lib_choice = st.selectbox("Library to audit against", libs, help="Choose the Apple Music library you loaded in the sidebar")
        present_threshold = st.slider("Present threshold", 0.70, 0.95, 0.82, 0.01)
        review_threshold = st.slider("Review threshold", 0.60, 0.90, 0.70, 0.01)
    # Alternative inputs
    with st.expander("Alternative input methods"):
        colA, colB = st.columns(2)
        with colA:
            server_path = st.text_input("Or read a playlist file from server path", value="potential missing trax.txt")
        with colB:
            pasted = st.text_area("Or paste playlist text here (optional)")

    if st.button("🔎 Run Playlist Audit", type="primary"):
        # Resolve input source priority: upload -> pasted -> server_path
        data_bytes = None
        if playlist_file is not None:
            data_bytes = playlist_file.getvalue()
        elif pasted.strip():
            data_bytes = pasted.encode("utf-8")
        elif server_path:
            try:
                data_bytes = Path(server_path).read_bytes()
            except Exception as e:
                st.error(f"Failed to read server file: {e}")
                data_bytes = None
        if not data_bytes:
            st.warning("Provide a playlist via upload, paste, or server path.")
            return
        if not lib_choice:
            st.warning("Please select a library to audit against.")
            return
        with st.spinner("Parsing and auditing playlist..."):
            try:
                items = parse_playlist_bytes(data_bytes)
                if not items:
                    st.error("Could not parse any tracks from the playlist file.")
                    return
                lib = SessionManager.get_library(lib_choice)
                res = audit_playlist(
                    items,
                    lib,
                    enable_album=enable_album,
                    enable_duration=enable_duration,
                    present_threshold=present_threshold,
                    review_threshold=review_threshold,
                )
            except Exception as e:
                st.error(f"Audit failed: {e}")
                return

        # Summary
        st.success("✅ Audit complete")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Present", f"{len(res['present']):,}")
        with c2:
            st.metric("Review", f"{len(res['review']):,}")
        with c3:
            st.metric("Missing", f"{len(res['missing']):,}")

        # Tables and downloads
        tabs = st.tabs(["✅ Present", "🧐 Review", "❌ Missing"])
        import pandas as pd
        with tabs[0]:
            df = pd.DataFrame(res['present'])
            st.dataframe(df, use_container_width=True)
            st.download_button("📥 Download Present CSV", df.to_csv(index=False), file_name="playlist_present.csv")
        with tabs[1]:
            df = pd.DataFrame(res['review'])
            st.dataframe(df, use_container_width=True)
            st.download_button("📥 Download Review CSV", df.to_csv(index=False), file_name="playlist_review.csv")
        with tabs[2]:
            df = pd.DataFrame(res['missing'])
            st.dataframe(df, use_container_width=True)
            st.download_button("📥 Download Missing CSV", df.to_csv(index=False), file_name="playlist_missing.csv")
            # Apple Music text playlist export (UTF-16 TSV: Name, Artist, Album, Time)
            def _sec_to_time(x):
                try:
                    s = int(float(x))
                except Exception:
                    return ""
                h, rem = divmod(s, 3600)
                m, ss = divmod(rem, 60)
                return f"{h}:{m:02d}:{ss:02d}" if h else f"{m}:{ss:02d}"
            header = ["Name", "Artist", "Album", "Time"]
            lines = ["\t".join(header)]
            for _, r in df.iterrows():
                title = str(r.get('playlist_title') or r.get('title') or '')
                artist = str(r.get('playlist_artist') or r.get('artist') or '')
                album = str(r.get('playlist_album') or r.get('album') or '')
                dur = r.get('playlist_duration') or r.get('duration') or ''
                time_str = _sec_to_time(dur)
                lines.append("\t".join([title, artist, album, time_str]))
            txt_bytes = ("\n".join(lines)).encode('utf-16')
            st.download_button(
                "📥 Download Apple Music Text (.txt)",
                data=txt_bytes,
                file_name="playlist_missing_apple.txt",
                mime="text/plain"
            )
            # Soundiiz-friendly CSV (Title, Artist, Album, ISRC, Duration)
            szi_cols = {
                'Title': df.get('playlist_title', df.get('title', pd.Series(dtype=str))).fillna(''),
                'Artist': df.get('playlist_artist', df.get('artist', pd.Series(dtype=str))).fillna(''),
                'Album': df.get('playlist_album', df.get('album', pd.Series(dtype=str))).fillna(''),
                'ISRC': df.get('isrc', pd.Series(dtype=str)).fillna(''),
                'Duration': df.get('playlist_duration', df.get('duration', pd.Series(dtype=str))).fillna(''),
            }
            szi_df = pd.DataFrame(szi_cols)
            st.download_button(
                "📥 Download Soundiiz CSV",
                szi_df.to_csv(index=False),
                file_name="playlist_missing_soundiiz.csv",
                mime="text/csv"
            )
            # Optional: Enrich with MusicBrainz to include ISRC codes
            st.markdown("---")
            if EnrichmentManager is not None and st.button("🔎 Enrich Missing with MusicBrainz (add ISRC)"):
                with st.spinner("Querying MusicBrainz for ISRCs (rate-limited)..."):
                    mgr = EnrichmentManager()
                    from musicweb.core.models import Track
                    tracks = []
                    for _, r in df.iterrows():
                        title = r.get('playlist_title') or r.get('title') or ''
                        artist = r.get('playlist_artist') or r.get('artist') or ''
                        album = r.get('playlist_album') or r.get('album') or ''
                        dur = r.get('playlist_duration') or r.get('duration') or ''
                        try:
                            duration = int(float(dur)) if dur not in (None, '') else None
                        except Exception:
                            duration = None
                        t = Track(title=str(title), artist=str(artist), album=str(album) if album else None, duration=duration)
                        tracks.append(t)
                    enriched = mgr.bulk_enrich(tracks)
                # Build ISRC-enriched Soundiiz CSV
                enr_rows = []
                for enhanced_track, _data in enriched:
                    enr_rows.append({
                        'Title': enhanced_track.title,
                        'Artist': enhanced_track.artist,
                        'Album': enhanced_track.album or '',
                        'ISRC': enhanced_track.isrc or '',
                        'Duration': enhanced_track.duration or ''
                    })
                enr_df = pd.DataFrame(enr_rows)
                st.success("✅ Enrichment complete — download enhanced CSV below")
                st.download_button(
                    "📥 Download Soundiiz CSV (with ISRC)",
                    enr_df.to_csv(index=False),
                    file_name="playlist_missing_soundiiz_enriched.csv",
                    mime="text/csv"
                )


def render_dedup_tab():
    """Render the YouTube Music deduplication tab."""
    st.header("🧹 YouTube Music Deduplication")

    # Auth section
    with st.expander("🔐 Authenticate", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            st.write("Use an existing connection from the sidebar or upload headers here.")
            connected = (
                st.session_state.playlist_manager is not None and 
                st.session_state.playlist_manager.is_available()
            )
            st.metric("YT Music Connected", "Yes" if connected else "No")

        with col2:
            headers_upload = st.file_uploader("Upload headers file", type=['json', 'txt', 'i'], key="dedup_headers")
            if headers_upload and st.button("Authenticate (Dedup)"):
                tmp_path = process_headers_upload(headers_upload)
                if tmp_path:
                    st.session_state.ytm_headers_path = tmp_path
                    if not headers_upload.name.endswith('.json'):
                        st.info("📄 Raw headers converted to JSON format")

        # Initialize deduplicator instance
        dedup = st.session_state.ytm_dedup
        if st.button("Initialize Deduplicator"):
            ytmusic = None
            if st.session_state.playlist_manager and st.session_state.playlist_manager.is_available():
                ytmusic = st.session_state.playlist_manager.ytmusic
            headers_path = st.session_state.get('ytm_headers_path')
            dedup = YouTubeMusicDeduplicator(headers_auth_path=headers_path, ytmusic=ytmusic)
            ok = dedup.authenticate()
            if ok:
                st.session_state.ytm_dedup = dedup
                st.success("✅ Deduplicator ready")
            else:
                st.error("❌ Failed to authenticate. Ensure headers are valid.")

    dedup = st.session_state.ytm_dedup
    if not dedup:
        st.info("Connect to YouTube Music and click 'Initialize Deduplicator' to continue.")
        return

    # Scan controls
    st.subheader("🧭 Scan Options")
    col1, col2, col3 = st.columns(3)
    with col1:
        threshold = st.slider("Similarity Threshold", 0.70, 0.95, 0.85, 0.01)
    with col2:
        limit = st.number_input("Limit (optional)", min_value=0, step=100, value=0, help="0 = no limit")
        limit = None if limit == 0 else int(limit)
    with col3:
        playlist_name = st.text_input("Playlist Name", f"YT Music Duplicates {time.strftime('%Y-%m-%d')}")
    prefer_explicit = st.checkbox("Prefer explicit version when available", value=True)
    playlist_mode = st.radio(
        "Playlist Mode",
        options=["All duplicates", "Winners only", "Losers only"],
        index=2,
        help="Choose what to include in the duplicates playlist"
    )
    winners_only = playlist_mode == "Winners only"
    losers_only = playlist_mode == "Losers only"
    dry_run = st.checkbox("Dry run (no playlist created)", value=False)

    if st.button("🔎 Scan for Duplicates", type="primary"):
        with st.spinner("Fetching library and scanning for duplicates..."):
            try:
                total = len(dedup.get_library_songs(limit=limit))
                groups = dedup.find_duplicates(similarity_threshold=threshold)
                # Compute summary
                total_dup_tracks = sum(len(g['duplicates']) for g in groups)
                can_remove = sum(len(g['duplicates']) - 1 for g in groups)
                st.session_state.ytm_dedup_results = {
                    'groups': groups,
                    'total_songs': total,
                    'total_duplicates': total_dup_tracks,
                    'can_remove': can_remove,
                }
                st.success("✅ Scan complete")
            except Exception as e:
                st.error(f"Scan failed: {e}")

    results = st.session_state.get('ytm_dedup_results')
    if results:
        st.subheader("📊 Deduplication Summary")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("Library Songs", f"{results['total_songs']:,}")
        with c2:
            st.metric("Duplicate Groups", f"{len(results['groups']):,}")
        with c3:
            st.metric("Duplicate Tracks", f"{results['total_duplicates']:,}")
        with c4:
            st.metric("Potential Removals", f"{results['can_remove']:,}")

        # Group details table
        table_rows = []
        for g in results['groups']:
            dups = g['duplicates']
            top = dups[0]
            # top can be dataclass RankedDuplicate or dict if coming from JSON
            top_quality = getattr(top, 'quality', None) or (top.get('quality') if isinstance(top, dict) else '')
            table_rows.append({
                'Group ID': g['id'],
                'Title': g['title'],
                'Artist': g['artist'],
                'Duplicates': len(dups),
                'Top Quality': top_quality,
            })
        st.dataframe(pd.DataFrame(table_rows), use_container_width=True)

        st.markdown("---")
        st.subheader("🧩 Select Groups to Include")
        group_ids = [g['id'] for g in results['groups']]

        # Bulk selection controls
        csel1, csel2 = st.columns(2)
        with csel1:
            if st.button("Select All Groups"):
                for gid in group_ids:
                    st.session_state[f"ytm_dedup_group_{gid}"] = True
                st.session_state.ytm_dedup_selected_group_ids = group_ids[:]
        with csel2:
            if st.button("Clear All Groups"):
                for gid in group_ids:
                    st.session_state[f"ytm_dedup_group_{gid}"] = False
                st.session_state.ytm_dedup_selected_group_ids = []

        # Render per-row checkboxes
        current_sel_ids = set(st.session_state.get('ytm_dedup_selected_group_ids', []))
        for g in results['groups']:
            gid = g['id']
            top = g['duplicates'][0]
            top_quality = getattr(top, 'quality', None) or (top.get('quality') if isinstance(top, dict) else '')
            default_checked = st.session_state.get(f"ytm_dedup_group_{gid}", (gid in current_sel_ids) or (len(current_sel_ids) == 0))
            checked = st.checkbox(
                f"Group {gid}: {g['title']} — {g['artist']} ({len(g['duplicates'])} dups, top: {top_quality})",
                key=f"ytm_dedup_group_{gid}",
                value=default_checked
            )
            with st.expander(f"Details for Group {gid}"):
                # Determine preferred index based on preference
                pref_idx = 0
                if prefer_explicit:
                    try:
                        pref_idx = [
                            (getattr(d, 'is_explicit', None) or (d.get('is_explicit') if isinstance(d, dict) else False))
                            for d in g['duplicates']
                        ].index(True)
                    except ValueError:
                        pref_idx = 0
                for idx, d in enumerate(g['duplicates'], start=1):
                    # Support both dataclass and dict entries
                    title = getattr(d, 'title', None) or (d.get('title') if isinstance(d, dict) else '')
                    artists = getattr(d, 'artists', None) or (d.get('artists') if isinstance(d, dict) else [])
                    album = getattr(d, 'album', None) or (d.get('album') if isinstance(d, dict) else '')
                    duration = getattr(d, 'duration', None) or (d.get('duration') if isinstance(d, dict) else '')
                    quality = getattr(d, 'quality', None) or (d.get('quality') if isinstance(d, dict) else '')
                    qscore = getattr(d, 'quality_score', None) or (d.get('quality_score') if isinstance(d, dict) else '')
                    is_explicit = getattr(d, 'is_explicit', None) or (d.get('is_explicit') if isinstance(d, dict) else False)
                    thumb = getattr(d, 'thumbnail', None) or (d.get('thumbnail') if isinstance(d, dict) else '')

                    cimg, cinfo = st.columns([1, 5])
                    with cimg:
                        if thumb:
                            st.image(thumb, width=64)
                        else:
                            st.write("")
                    with cinfo:
                        preferred_flag = " (Preferred)" if (idx - 1) == pref_idx else ""
                        explicit_flag = " | Explicit" if is_explicit else ""
                        # Inclusion label based on mode
                        if winners_only:
                            included = (idx - 1) == pref_idx
                        elif losers_only:
                            included = (idx - 1) != pref_idx
                        else:
                            included = True
                        include_flag = " | Included" if included else " | Excluded"
                        st.write(f"{idx}. {title} — {', '.join(artists)}{preferred_flag}{explicit_flag}{include_flag}")
                        st.caption(f"Album: {album} | Duration: {duration} | Quality: {quality} ({qscore})")
        # Gather selection
        selected_ids = [gid for gid in group_ids if st.session_state.get(f"ytm_dedup_group_{gid}", False)]
        st.session_state.ytm_dedup_selected_group_ids = selected_ids

        # Export JSON
        if st.button("📥 Download JSON Report"):
            serializable = []
            for g in results['groups']:
                serializable.append({
                    'id': g['id'],
                    'title': g['title'],
                    'artist': g['artist'],
                    'similarity_scores': g['similarity_scores'],
                    'duplicates': [
                        (d.__dict__ if hasattr(d, '__dict__') else d) for d in g['duplicates']
                    ]
                })
            json_str = json.dumps({
                'generated': time.strftime('%Y-%m-%d %H:%M:%S'),
                'total_songs': results['total_songs'],
                'duplicate_groups': len(results['groups']),
                'total_duplicates': results['total_duplicates'],
                'can_remove': results['can_remove'],
                'groups': serializable,
            }, indent=2)
            st.download_button("📥 Save Report", json_str, file_name=f"ytm_duplicates_{int(time.time())}.json", mime="application/json")

        # CSV Exports (Winners / Losers)
        def build_group_subset(groups, selected_ids):
            if selected_ids:
                sel = set(selected_ids)
                return [g for g in groups if g['id'] in sel]
            return groups

        subset = build_group_subset(results['groups'], st.session_state.get('ytm_dedup_selected_group_ids'))

        def extract_rows(groups, prefer_explicit_flag, winners):
            rows = []
            for g in groups:
                # determine preferred index
                pref_idx = 0
                if prefer_explicit_flag:
                    try:
                        pref_idx = [
                            (getattr(d, 'is_explicit', None) or (d.get('is_explicit') if isinstance(d, dict) else False))
                            for d in g['duplicates']
                        ].index(True)
                    except ValueError:
                        pref_idx = 0
                for idx, d in enumerate(g['duplicates']):
                    is_pref = idx == pref_idx
                    include = is_pref if winners else (idx != pref_idx)
                    if not include:
                        continue
                    title = getattr(d, 'title', None) or (d.get('title') if isinstance(d, dict) else '')
                    artists = getattr(d, 'artists', None) or (d.get('artists') if isinstance(d, dict) else [])
                    album = getattr(d, 'album', None) or (d.get('album') if isinstance(d, dict) else '')
                    duration = getattr(d, 'duration', None) or (d.get('duration') if isinstance(d, dict) else '')
                    quality = getattr(d, 'quality', None) or (d.get('quality') if isinstance(d, dict) else '')
                    qscore = getattr(d, 'quality_score', None) or (d.get('quality_score') if isinstance(d, dict) else '')
                    is_explicit = getattr(d, 'is_explicit', None) or (d.get('is_explicit') if isinstance(d, dict) else False)
                    thumb = getattr(d, 'thumbnail', None) or (d.get('thumbnail') if isinstance(d, dict) else '')
                    vid = getattr(d, 'id', None) or (d.get('id') if isinstance(d, dict) else '')
                    rows.append({
                        'Group ID': g['id'],
                        'Group Title': g['title'],
                        'Group Artist': g['artist'],
                        'Preferred': is_pref,
                        'Title': title,
                        'Artists': ", ".join(artists) if isinstance(artists, list) else str(artists),
                        'Album': album,
                        'Duration': duration,
                        'Explicit': bool(is_explicit),
                        'Quality': quality,
                        'Quality Score': qscore,
                        'Video ID': vid,
                        'Thumbnail': thumb,
                        'URL': f"https://music.youtube.com/watch?v={vid}" if vid else ''
                    })
            return rows

        col_csv1, col_csv2 = st.columns(2)
        with col_csv1:
            winners_rows = extract_rows(subset, prefer_explicit, winners=True)
            if winners_rows:
                winners_df = pd.DataFrame(winners_rows)
                st.download_button(
                    "📥 Download Winners CSV",
                    winners_df.to_csv(index=False),
                    file_name=f"ytm_winners_{int(time.time())}.csv",
                    mime="text/csv"
                )
        with col_csv2:
            losers_rows = extract_rows(subset, prefer_explicit, winners=False)
            if losers_rows:
                losers_df = pd.DataFrame(losers_rows)
                st.download_button(
                    "📥 Download Losers CSV",
                    losers_df.to_csv(index=False),
                    file_name=f"ytm_losers_{int(time.time())}.csv",
                    mime="text/csv"
                )

        # Cleanup actions
        st.markdown("---")
        st.subheader("🧽 Cleanup Actions (Optional)")
        unlike_losers = st.checkbox("Unlike losers in my library", value=False)
        replace_in_playlists = st.checkbox("Replace losers with winner in my playlists", value=False)
        if st.button("📝 Plan Cleanup"):
            if not (unlike_losers or replace_in_playlists):
                st.info("Select at least one cleanup option.")
            else:
                try:
                    cleaner = YTMusicCleaner(dedup.ytmusic)
                    include_ids = st.session_state.get('ytm_dedup_selected_group_ids') or None
                    plan = cleaner.plan_cleanup(
                        results['groups'],
                        prefer_explicit=prefer_explicit,
                        include_group_ids=include_ids,
                        replace_in_playlists=replace_in_playlists,
                        unlike_losers=unlike_losers,
                    )
                    st.session_state['ytm_cleanup_plan'] = plan
                    # Summary
                    affected_playlists = len([e for e in plan.playlist_edits if e.remove_items or e.add_video_ids])
                    total_removes = sum(len(e.remove_items) for e in plan.playlist_edits)
                    total_adds = sum(len(e.add_video_ids) for e in plan.playlist_edits)
                    st.success("✅ Cleanup plan ready")
                    colp1, colp2, colp3 = st.columns(3)
                    with colp1:
                        st.metric("Will Unlike", len(plan.unlike_video_ids))
                    with colp2:
                        st.metric("Playlists Affected", affected_playlists)
                    with colp3:
                        st.metric("Adds/Removes", f"{total_adds} / {total_removes}")

                    # Verify Plan (preview replacements)
                    with st.expander("🔎 Verify Plan (preview replacements)"):
                        # Build quick lookup maps
                        video_meta = {}
                        for g in results['groups']:
                            for d in g['duplicates']:
                                vid = getattr(d, 'id', None) or (d.get('id') if isinstance(d, dict) else '')
                                if not vid:
                                    continue
                                video_meta[vid] = {
                                    'title': getattr(d, 'title', None) or (d.get('title') if isinstance(d, dict) else ''),
                                    'artists': getattr(d, 'artists', None) or (d.get('artists') if isinstance(d, dict) else []),
                                    'thumb': getattr(d, 'thumbnail', None) or (d.get('thumbnail') if isinstance(d, dict) else ''),
                                    'explicit': bool(getattr(d, 'is_explicit', None) or (d.get('is_explicit') if isinstance(d, dict) else False))
                                }

                        # Reverse map losers -> group id for quick winner lookup
                        loser_to_gid = {}
                        for gid, vids in plan.losers_by_group.items():
                            for v in vids:
                                loser_to_gid[v] = gid

                        # Show playlists with expandable full replacement list
                        expand_all = st.checkbox("Expand all playlists", value=False)
                        for edit in plan.playlist_edits:
                            if not (edit.remove_items or edit.add_video_ids):
                                continue
                            count = len(edit.remove_items)
                            with st.expander(f"🎶 {edit.playlist_name} — {count} replacement(s)", expanded=expand_all):
                                for item in edit.remove_items:
                                    loser_vid = item.get('videoId')
                                    gid = loser_to_gid.get(loser_vid)
                                    winner_vid = plan.winners_by_group.get(gid) if gid is not None else None
                                    lmeta = video_meta.get(loser_vid, {})
                                    wmeta = video_meta.get(winner_vid, {}) if winner_vid else {}
                                    col_l, col_arrow, col_w = st.columns([4, 1, 4])
                                    with col_l:
                                        if lmeta.get('thumb'):
                                            st.image(lmeta['thumb'], width=48)
                                        title = lmeta.get('title', '')
                                        artists = ", ".join(lmeta.get('artists') or [])
                                        eflag = " (Explicit)" if lmeta.get('explicit') else ""
                                        st.write(f"❌ {title}{eflag}")
                                        st.caption(artists)
                                    with col_arrow:
                                        st.write("➡️")
                                    with col_w:
                                        if wmeta.get('thumb'):
                                            st.image(wmeta['thumb'], width=48)
                                        title = wmeta.get('title', '')
                                        artists = ", ".join(wmeta.get('artists') or [])
                                        eflag = " (Explicit)" if wmeta.get('explicit') else ""
                                        st.write(f"✅ {title}{eflag}")
                                        st.caption(artists)
                except Exception as e:
                    st.error(f"Failed to generate cleanup plan: {e}")

        if 'ytm_cleanup_plan' in st.session_state and not dry_run:
            save_undo = st.checkbox("Save undo log for rollback", value=True)
            if st.button("🧹 Apply Cleanup Now", type="primary"):
                try:
                    cleaner = YTMusicCleaner(dedup.ytmusic)
                    plan = st.session_state['ytm_cleanup_plan']
                    summary = cleaner.apply_cleanup(
                        plan,
                        do_unlike=unlike_losers,
                        do_playlists=replace_in_playlists,
                        generate_undo=save_undo
                    )
                    st.success(f"✅ Cleanup applied — Unliked: {summary['unliked']}, Adds: {summary['playlist_adds']}, Removes: {summary['playlist_removes']}")
                    if summary['errors']:
                        with st.expander("Errors"):
                            st.write(summary['errors'])
                    if save_undo and summary.get('undo'):
                        undo_json = json.dumps(summary['undo'], indent=2)
                        st.download_button(
                            "📥 Download Undo Log",
                            undo_json,
                            file_name=f"ytm_cleanup_undo_{int(time.time())}.json",
                            mime="application/json"
                        )
                except Exception as e:
                    st.error(f"Cleanup failed: {e}")

        # Create playlist
        if st.button("🎵 Create Duplicates Playlist"):
            with st.spinner("Creating playlist..."):
                try:
                    if dry_run:
                        st.info("Dry run enabled — no playlist created.")
                    else:
                        include_ids = st.session_state.get('ytm_dedup_selected_group_ids') or None
                        result = dedup.create_duplicates_playlist(
                            name=playlist_name,
                            include_group_ids=include_ids,
                            prefer_explicit=prefer_explicit,
                            losers_only=losers_only,
                            winners_only=winners_only
                        )
                        if result.get('success'):
                            st.success(f"✅ Playlist created: {result['playlist_url']}")
                        else:
                            st.error(f"❌ Failed to create playlist: {result.get('error')}")
                except Exception as e:
                    st.error(f"Playlist creation failed: {e}")


def render_playlist_cleanup_tab():
    """Render the playlist cleanup tab."""
    st.header("🧽 Playlist Cleanup")
    
    st.markdown("""
    Comprehensive playlist cleanup with multiple options:
    - **Remove liked songs** from playlists
    - **Remove library duplicates** with advanced similarity matching
    - **Internal deduplication** to remove duplicate tracks within the playlist
    - **Manual review interface** for uncertain matches
    """)
    
    # Authentication section
    with st.expander("🔐 Authentication", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            # Check if already connected via sidebar
            connected = (
                st.session_state.playlist_manager is not None and 
                st.session_state.playlist_manager.is_available()
            )
            st.metric("YouTube Music Connected", "✅ Yes" if connected else "❌ No")
        
        with col2:
            # Option to upload headers for this tab specifically
            cleanup_headers = st.file_uploader(
                "Upload headers file (if different)",
                type=['json', 'txt', 'i'],
                key="cleanup_headers",
                help="Upload if you want to use different credentials for cleanup"
            )
            
            if cleanup_headers and st.button("Setup for Cleanup"):
                tmp_path = process_headers_upload(cleanup_headers)
                if tmp_path:
                    st.session_state.cleanup_headers_path = tmp_path
                    st.success("✅ Headers uploaded for cleanup")
    
    # Only proceed if we have authentication
    ytmusic_instance = None
    if st.session_state.playlist_manager and st.session_state.playlist_manager.is_available():
        ytmusic_instance = st.session_state.playlist_manager.ytmusic
    elif st.session_state.get('cleanup_headers_path'):
        # Create temporary instance for cleanup
        try:
            from ytmusicapi import YTMusic
            ytmusic_instance = YTMusic(st.session_state.cleanup_headers_path)
        except Exception as e:
            st.error(f"Failed to authenticate: {e}")
            return
    
    if not ytmusic_instance:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #fff3cd 0%, #ffeaa7 100%); padding: 2rem; border-radius: 12px; text-align: center; border-left: 4px solid #ffc107;">
            <h4 style="color: #856404; margin-bottom: 1rem;">🔒 Authentication Required</h4>
            <p style="color: #856404; margin-bottom: 1rem;">Please connect to YouTube Music first to use playlist cleanup features.</p>
            <p style="color: #856404; margin: 0; font-size: 0.9rem;">Use the sidebar or upload headers above to authenticate.</p>
        </div>
        """, unsafe_allow_html=True)
        return
    
    # Playlist URL input
    st.subheader("🎵 Playlist to Clean")
    playlist_url = st.text_input(
        "Playlist URL or ID",
        value="https://music.youtube.com/playlist?list=PL1LO5jourf4MqCSX94juP7bWk2eYTMCQ2&si=-idwc0lg2KK0LYnq",
        help="Paste the full YouTube Music playlist URL or just the playlist ID"
    )
    
    # Cleanup options
    st.subheader("⚙️ Cleanup Options")
    
    # Main cleanup types
    cleanup_tabs = st.tabs(["🎵 Basic Cleanup", "🔍 Advanced Similarity", "🔄 Internal Dedup"])
    
    with cleanup_tabs[0]:
        st.markdown("**Basic cleanup** removes exact matches for liked songs and library tracks.")
        col1, col2 = st.columns(2)
        
        with col1:
            remove_liked = st.checkbox(
                "Remove liked songs", 
                value=True,
                help="Remove songs that are already in your liked songs"
            )
        
        with col2:
            dedupe_library = st.checkbox(
                "Remove songs already in library", 
                value=True,
                help="Remove songs that are already in your main library (exact matches only)"
            )
        
        use_similarity = False
        similarity_threshold = 0.85
        auto_remove_high_confidence = False
        dedupe_internal = False
        auto_remove_internal = False
    
    with cleanup_tabs[1]:
        st.markdown("**Advanced similarity matching** finds library duplicates even with different video IDs.")
        
        use_similarity = st.checkbox(
            "Enable similarity-based library duplicate detection",
            value=False,
            help="Find tracks that are similar but have different video IDs (remasters, different uploads, etc.)"
        )
        
        if use_similarity:
            col1, col2 = st.columns(2)
            
            with col1:
                similarity_threshold = st.slider(
                    "Similarity threshold",
                    min_value=0.70,
                    max_value=0.95,
                    value=0.85,
                    step=0.05,
                    help="Higher values = more strict matching"
                )
            
            with col2:
                auto_remove_high_confidence = st.checkbox(
                    "Auto-remove high confidence matches (>95%)",
                    value=True,
                    help="Automatically remove tracks with very high similarity scores"
                )
            
            st.info("💡 Lower confidence matches will be available for manual review")
        
        remove_liked = False
        dedupe_library = True if use_similarity else False
        dedupe_internal = False
        auto_remove_internal = False
    
    with cleanup_tabs[2]:
        st.markdown("**Internal deduplication** removes duplicate tracks within the playlist itself.")
        
        dedupe_internal = st.checkbox(
            "Remove internal playlist duplicates",
            value=False,
            help="Find and remove duplicate tracks within the same playlist"
        )
        
        if dedupe_internal:
            auto_remove_internal = st.checkbox(
                "Auto-remove high confidence internal duplicates",
                value=True,
                help="Automatically remove obvious duplicates (keeps the best version)"
            )
            
            st.info("💡 Uncertain duplicates will be available for manual review")
        
        st.markdown("""
        <div style="background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%); padding: 1rem; border-radius: 8px; margin: 1rem 0; border-left: 4px solid #2196f3;">
            <p style="margin: 0; color: #0d47a1;">
                <strong>💡 Pro Tip:</strong> To also remove songs already in your main library, use the Basic or Advanced Similarity tabs above.
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        remove_liked = False
        dedupe_library = False
        use_similarity = False
        similarity_threshold = 0.85
        auto_remove_high_confidence = False
    
    # Performance options
    with st.expander("🚀 Performance & Advanced Options", expanded=False):
        st.info("The cleanup process will cache your library and liked songs for better performance")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Clear Cache"):
                # Clear any cached data
                if ytmusic_instance:
                    cleaner = PlaylistCleaner(ytmusic=ytmusic_instance)
                    cleaner.clear_cache()
                st.success("Cache cleared - next cleanup will refresh all data")
        
        with col2:
            save_review_data = st.checkbox(
                "Save review data for manual processing",
                value=True,
                help="Save similarity matches and duplicates for manual review in a separate interface"
            )
    
    # Dry run option (moved outside tabs to apply to all)
    dry_run = st.checkbox("Dry run (preview only)", value=True, help="Preview changes without actually modifying the playlist")
    
    # Execute cleanup
    if st.button("🧽 Clean Playlist", type="primary"):
        if not playlist_url:
            st.error("Please enter a playlist URL")
            return
        
        if not (remove_liked or dedupe_library or use_similarity or dedupe_internal):
            st.warning("Please select at least one cleanup option")
            return
        
        with st.spinner("Cleaning playlist..."):
            try:
                # Create cleaner instance
                cleaner = PlaylistCleaner(ytmusic=ytmusic_instance)
                
                # Show progress
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                status_text.text("Initializing cleanup...")
                progress_bar.progress(0.1)
                
                if dry_run:
                    status_text.text("Running in preview mode - analyzing playlist...")
                    progress_bar.progress(0.3)
                    
                    # Get playlist tracks for preview
                    playlist_id = cleaner.extract_playlist_id(playlist_url)
                    tracks = cleaner.get_playlist_tracks_robust(playlist_id)
                    
                    if not tracks:
                        st.error("Could not retrieve playlist tracks. Check the URL and try again.")
                        return
                    
                    status_text.text("Analyzing what would be removed...")
                    progress_bar.progress(0.6)
                    
                    if use_similarity or dedupe_internal:
                        # Advanced preview with similarity matching or internal dedup
                        if use_similarity:
                            status_text.text("Analyzing library duplicates with similarity matching...")
                            progress_bar.progress(0.6)
                            
                            similarity_matches = cleaner.find_library_duplicates_with_similarity(tracks, similarity_threshold)
                            
                            col1, col2, col3, col4 = st.columns(4)
                            with col1:
                                st.metric("Original Tracks", len(tracks))
                            with col2:
                                st.metric("Total Matches", similarity_matches['total_matches'])
                            with col3:
                                st.metric("High Confidence", len(similarity_matches['high_confidence']))
                            with col4:
                                st.metric("Need Review", len(similarity_matches['needs_review']))
                            
                            # Show similarity match details
                            if similarity_matches['high_confidence']:
                                with st.expander(f"✅ High Confidence Library Duplicates ({len(similarity_matches['high_confidence'])})"):
                                    for match in similarity_matches['high_confidence'][:10]:
                                        track = match['playlist_track']
                                        cimg, cinfo = st.columns([1, 6])
                                        with cimg:
                                            if getattr(track, 'thumbnail', None):
                                                st.image(track.thumbnail, width=48)
                                        with cinfo:
                                            explicit_flag = " (Explicit)" if getattr(track, 'is_explicit', False) else ""
                                            st.write(f"• **{track.title}**{explicit_flag} (confidence: {match['confidence']:.1%})")
                                            st.caption(', '.join(track.artists))
                                    if len(similarity_matches['high_confidence']) > 10:
                                        st.write(f"... and {len(similarity_matches['high_confidence']) - 10} more")
                            
                            if similarity_matches['needs_review']:
                                with st.expander(f"⚠️ Needs Manual Review ({len(similarity_matches['needs_review'])})"):
                                    for match in similarity_matches['needs_review'][:10]:
                                        track = match['playlist_track']
                                        cimg, cinfo = st.columns([1, 6])
                                        with cimg:
                                            if getattr(track, 'thumbnail', None):
                                                st.image(track.thumbnail, width=48)
                                        with cinfo:
                                            explicit_flag = " (Explicit)" if getattr(track, 'is_explicit', False) else ""
                                            st.write(f"• **{track.title}**{explicit_flag} (confidence: {match['confidence']:.1%})")
                                            st.caption(', '.join(track.artists))
                                    if len(similarity_matches['needs_review']) > 10:
                                        st.write(f"... and {len(similarity_matches['needs_review']) - 10} more")
                        
                        if dedupe_internal:
                            status_text.text("Analyzing internal playlist duplicates...")
                            progress_bar.progress(0.7)
                            
                            internal_duplicates = cleaner.find_playlist_internal_duplicates(tracks)
                            auto_remove_candidates = [dup for dup in internal_duplicates if not dup.review_needed]
                            needs_review_internal = [dup for dup in internal_duplicates if dup.review_needed]
                            
                            col1, col2, col3, col4 = st.columns(4)
                            with col1:
                                st.metric("Original Tracks", len(tracks))
                            with col2:
                                st.metric("Duplicate Groups", len(internal_duplicates))
                            with col3:
                                st.metric("Auto-Remove Groups", len(auto_remove_candidates))
                            with col4:
                                st.metric("Review Needed", len(needs_review_internal))
                            
                            # Show internal duplicate details
                            if auto_remove_candidates:
                                with st.expander(f"✅ Auto-Remove Internal Duplicates ({len(auto_remove_candidates)} groups)"):
                                    for dup in auto_remove_candidates[:10]:
                                        st.write(f"• **{dup.signature}** ({dup.duplicate_count} copies, confidence: {dup.confidence:.1%})")
                                    if len(auto_remove_candidates) > 10:
                                        st.write(f"... and {len(auto_remove_candidates) - 10} more groups")
                            
                            if needs_review_internal:
                                with st.expander(f"⚠️ Internal Duplicates Need Review ({len(needs_review_internal)} groups)"):
                                    for dup in needs_review_internal[:10]:
                                        st.write(f"• **{dup.signature}** ({dup.duplicate_count} copies, confidence: {dup.confidence:.1%})")
                                    if len(needs_review_internal) > 10:
                                        st.write(f"... and {len(needs_review_internal) - 10} more groups")
                    
                    else:
                        # Basic preview
                        status_text.text("Analyzing playlist for basic cleanup...")
                        progress_bar.progress(0.6)
                        
                        # Get comparison data
                        liked_songs = set()
                        library_video_ids = set()
                        
                        if remove_liked:
                            liked_songs = cleaner.get_liked_songs_cached()
                        
                        if dedupe_library:
                            library_songs = cleaner.get_library_songs_cached()
                            library_video_ids = {song.get('videoId') for song in library_songs if song.get('videoId')}
                        
                        progress_bar.progress(0.9)
                        
                        # Analyze what would be removed
                        tracks_to_remove_liked = []
                        tracks_to_remove_library = []
                        
                        for track in tracks:
                            if remove_liked and track.video_id in liked_songs:
                                tracks_to_remove_liked.append(track)
                            elif dedupe_library and track.video_id in library_video_ids:
                                tracks_to_remove_library.append(track)
                        
                        # Show basic preview results
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("Original Tracks", len(tracks))
                        with col2:
                            st.metric("Liked to Remove", len(tracks_to_remove_liked))
                        with col3:
                            st.metric("Library Duplicates", len(tracks_to_remove_library))
                        with col4:
                            st.metric("Final Count", len(tracks) - len(tracks_to_remove_liked) - len(tracks_to_remove_library))
                        
                        # Show details
                        if tracks_to_remove_liked:
                            with st.expander(f"🎵 Liked Songs to Remove ({len(tracks_to_remove_liked)})"):
                                for track in tracks_to_remove_liked[:20]:
                                    cimg, cinfo = st.columns([1, 6])
                                    with cimg:
                                        if getattr(track, 'thumbnail', None):
                                            st.image(track.thumbnail, width=48)
                                    with cinfo:
                                        explicit_flag = " (Explicit)" if getattr(track, 'is_explicit', False) else ""
                                        st.write(f"• {track.title}{explicit_flag}")
                                        st.caption(', '.join(track.artists))
                                if len(tracks_to_remove_liked) > 20:
                                    st.write(f"... and {len(tracks_to_remove_liked) - 20} more")
                        
                        if tracks_to_remove_library:
                            with st.expander(f"📚 Library Duplicates to Remove ({len(tracks_to_remove_library)})"):
                                for track in tracks_to_remove_library[:20]:
                                    cimg, cinfo = st.columns([1, 6])
                                    with cimg:
                                        if getattr(track, 'thumbnail', None):
                                            st.image(track.thumbnail, width=48)
                                    with cinfo:
                                        explicit_flag = " (Explicit)" if getattr(track, 'is_explicit', False) else ""
                                        st.write(f"• {track.title}{explicit_flag}")
                                        st.caption(', '.join(track.artists))
                                if len(tracks_to_remove_library) > 20:
                                    st.write(f"... and {len(tracks_to_remove_library) - 20} more")
                    
                    progress_bar.progress(1.0)
                    status_text.text("Preview complete!")
                    
                    st.success("🔍 Preview Complete!")
                    
                    st.info("💡 Uncheck 'Dry run' and click 'Clean Playlist' again to apply these changes")
                
                else:
                    # Actual cleanup
                    status_text.text("Performing cleanup...")
                    progress_bar.progress(0.3)
                    
                    if use_similarity:
                        # Enhanced cleanup with similarity matching
                        result = cleaner.clean_playlist_with_similarity(
                            playlist_url,
                            remove_liked=remove_liked,
                            deduplicate_against_library=True,
                            similarity_threshold=similarity_threshold,
                            auto_remove_high_confidence=auto_remove_high_confidence
                        )
                        
                        progress_bar.progress(1.0)
                        status_text.text("Enhanced cleanup complete!")
                        
                        # Show results
                        st.success("✅ Enhanced Playlist Cleanup Complete!")
                        
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("Original Count", result['original_count'])
                        with col2:
                            st.metric("Total Matches", result['similarity_matches']['total_matches'])
                        with col3:
                            st.metric("Auto-Removed", result['removed_duplicates'])
                        with col4:
                            st.metric("Final Count", result['final_count'])
                        
                        # Show similarity match summary
                        if result['similarity_matches']['needs_review']:
                            st.info(f"💡 {len(result['similarity_matches']['needs_review'])} matches need manual review - use the review interface below")
                        
                        if save_review_data and result['similarity_matches']['needs_review']:
                            # Save review data
                            review_data = {
                                'summary': {
                                    'total_matches': result['similarity_matches']['total_matches'],
                                    'needs_review': len(result['similarity_matches']['needs_review']),
                                    'generated_at': time.strftime('%Y-%m-%d %H:%M:%S')
                                },
                                'needs_review': [{
                                    'playlist_track': {
                                        'videoId': match['playlist_track'].video_id,
                                        'setVideoId': match['playlist_track'].set_video_id,
                                        'title': match['playlist_track'].title,
                                        'artists': match['playlist_track'].artists,
                                        'duration': match['playlist_track'].duration
                                    },
                                    'confidence': match['confidence'],
                                    'library_matches': [{
                                        'title': lib_match['library_track'].get('title'),
                                        'artists': [a.get('name') for a in lib_match['library_track'].get('artists', [])],
                                        'similarity': lib_match['similarity'],
                                        'reason': lib_match['reason']
                                    } for lib_match in match['library_matches']]
                                } for match in result['similarity_matches']['needs_review']]
                            }
                            
                            st.session_state['playlist_review_data'] = review_data
                            st.success("📋 Review data saved for manual processing")
                    
                    elif dedupe_internal:
                        # Internal deduplication
                        result = cleaner.deduplicate_playlist_internal(
                            playlist_url,
                            auto_remove=auto_remove_internal
                        )
                        
                        progress_bar.progress(1.0)
                        status_text.text("Internal deduplication complete!")
                        
                        # Show results
                        st.success("✅ Internal Deduplication Complete!")
                        
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("Original Count", result['original_count'])
                        with col2:
                            st.metric("Duplicate Groups", result['duplicate_groups'])
                        with col3:
                            st.metric("Auto-Removed", result['auto_removed'])
                        with col4:
                            st.metric("Final Count", result['final_count'])
                        
                        if result['needs_review'] > 0:
                            st.info(f"💡 {result['needs_review']} duplicate groups need manual review")
                        
                        if save_review_data and result['duplicates']:
                            st.session_state['internal_dedup_data'] = result
                            st.success("📋 Internal duplicate data saved for manual processing")
                    
                    else:
                        # Basic cleanup
                        result = cleaner.clean_playlist(
                            playlist_url,
                            remove_liked=remove_liked,
                            deduplicate_against_library=dedupe_library
                        )
                        
                        progress_bar.progress(1.0)
                        status_text.text("Basic cleanup complete!")
                        
                        # Show results
                        st.success("✅ Playlist Cleaned!")
                        
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("Original Count", result.original_count)
                        with col2:
                            st.metric("Removed Liked", result.removed_liked)
                        with col3:
                            st.metric("Removed Duplicates", result.removed_duplicates)
                        with col4:
                            st.metric("Final Count", result.final_count)
                        
                        st.info(f"⏱️ Processing time: {result.processing_time:.2f} seconds")
                        
                        if result.errors:
                            with st.expander("⚠️ Errors"):
                                for error in result.errors:
                                    st.error(error)
                    
                    # Show link to cleaned playlist
                    playlist_id = cleaner.extract_playlist_id(playlist_url)
                    st.markdown(f"🎵 **[View Cleaned Playlist](https://music.youtube.com/playlist?list={playlist_id})**")
                
                progress_bar.empty()
                status_text.empty()
                
            except Exception as e:
                st.error(f"❌ Cleanup failed: {e}")
                st.exception(e)
    
    # Manual review interface
    if 'playlist_review_data' in st.session_state or 'internal_dedup_data' in st.session_state:
        st.markdown("---")
        st.subheader("🔍 Manual Review Interface")
        
        if 'playlist_review_data' in st.session_state:
            review_data = st.session_state['playlist_review_data']
            
            st.markdown("**📚 Library Duplicate Candidates for Manual Review**")
            
            with st.expander(f"Review {len(review_data['needs_review'])} potential library duplicates", expanded=True):
                if st.button("🗑️ Clear Library Review Data"):
                    del st.session_state['playlist_review_data']
                    st.rerun()
                
                for i, item in enumerate(review_data['needs_review'][:10]):  # Show first 10
                    track = item['playlist_track']
                    
                    st.markdown(f"**{i+1}. {track['title']}** by {', '.join(track['artists'])}")
                    st.write(f"Confidence: {item['confidence']:.1%}")
                    
                    for match in item['library_matches']:
                        st.write(f"  → Similar to: **{match['title']}** by {', '.join(match['artists'])} ({match['reason']})")
                    
                    if st.button(f"Remove Track {i+1}", key=f"remove_lib_{i}"):
                        st.info(f"Would remove: {track['title']} (feature coming soon)")
                    
                    st.markdown("---")
                
                if len(review_data['needs_review']) > 10:
                    st.info(f"Showing first 10 of {len(review_data['needs_review'])} tracks needing review")
        
        if 'internal_dedup_data' in st.session_state:
            dedup_data = st.session_state['internal_dedup_data']
            
            st.markdown("**🔄 Internal Duplicate Groups for Manual Review**")
            
            needs_review_duplicates = [d for d in dedup_data['duplicates'] if d['review_needed']]
            
            if needs_review_duplicates:
                with st.expander(f"Review {len(needs_review_duplicates)} duplicate groups", expanded=True):
                    if st.button("🗑️ Clear Internal Dedup Data"):
                        del st.session_state['internal_dedup_data']
                        st.rerun()
                    
                    for i, dup in enumerate(needs_review_duplicates[:5]):  # Show first 5 groups
                        st.markdown(f"**Group {i+1}: {dup['signature']}** ({dup['duplicate_count']} copies, confidence: {dup['confidence']:.1%})")
                        
                        st.write("Tracks in this group:")
                        for j, track in enumerate(dup['tracks_to_keep'] + dup['tracks_to_remove']):
                            marker = "✅ Keep" if j == 0 else "❌ Remove"
                            st.write(f"  {marker} **{track['title']}** by {', '.join(track['artists'])}")
                        
                        if st.button(f"Apply Group {i+1} Removals", key=f"remove_group_{i}"):
                            st.info(f"Would remove {len(dup['tracks_to_remove'])} tracks from this group (feature coming soon)")
                        
                        st.markdown("---")
                    
                    if len(needs_review_duplicates) > 5:
                        st.info(f"Showing first 5 of {len(needs_review_duplicates)} groups needing review")


def render_help_tab():
    """Render the help tab."""
    st.header("ℹ️ Help & Documentation")
    
    st.markdown("""
    ## 🎵 MusicWeb - Getting Started
    
    ### 📂 Uploading Libraries
    1. Use the sidebar to upload CSV or JSON files from:
       - **Apple Music**: Export your library as CSV
       - **Spotify**: Use tools like Exportify to get CSV
       - **YouTube Music**: Export from Google Takeout (JSON format)
    
    2. Files are auto-detected based on content and format
    
    ### 🔍 Comparing Libraries
    1. Go to the **Compare** tab
    2. Select source and target libraries
    3. Adjust matching options:
       - **Strict Matching**: Higher precision, fewer false matches
       - **Use Duration**: Include track duration in matching algorithm
       - **Use Album**: Include album information in matching
    4. Click "Compare Libraries" to run the analysis
    
    ### 📊 Multi-Library Analysis
    1. Use the **Analyze** tab for comparing multiple libraries
    2. Select which libraries to include in the analysis
    3. View universal tracks, unique content, and artist overlap
    
    ### 🔍 Metadata Enrichment
    1. Use the **Enrich** tab to enhance your library with MusicBrainz data
    2. **Note**: This process is rate-limited and can take time for large libraries
    3. Enrichment adds missing metadata like ISRC codes, genres, and improved duration data
    
    ### 🎵 YouTube Music Integration
    1. Upload your headers file in the sidebar (supports both formats):
       - **JSON format**: `headers_auth.json` (from `ytmusicapi setup`)
       - **Raw format**: Raw HTTP headers from browser dev tools (auto-converted)
    2. Once connected, you can create playlists from missing tracks
    
    ### 💡 Tips
    - **Large Libraries**: Consider using the "Strict Matching" option for better performance
    - **Duplicates**: The system automatically filters out non-music content
    - **Matching**: The fuzzy matching algorithm handles variations in artist names, featuring artists, and title formats
    - **Exports**: All results can be downloaded as CSV files for further analysis
    
    ### 🛠️ Troubleshooting
    - **CSV Issues**: Ensure your CSV files have proper headers and UTF-8 encoding
    - **YouTube Music**: Make sure your headers file is valid and not expired
    - **Performance**: For very large libraries (>50K tracks), consider comparing in smaller batches
    
    ### 📧 Support
    This is a consolidated version of multiple music library tools. All the advanced matching
    algorithms and features from the original tools have been preserved and enhanced.
    """)


if __name__ == "__main__":
    main()
