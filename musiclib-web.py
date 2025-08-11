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

from musiclib import (
    Library, Track, LibraryComparator, PlaylistManager, 
    EnrichmentManager, create_parser, detect_platform
)

# Try to import optional visualization dependencies
try:
    import matplotlib.pyplot as plt
    from matplotlib_venn import venn2, venn3
    import plotly.express as px
    import plotly.graph_objects as go
    HAVE_VISUALIZATION = True
except ImportError:
    HAVE_VISUALIZATION = False


# Page configuration
st.set_page_config(
    page_title="MusicWeb - Library Manager",
    page_icon="🎵",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
.stTabs [data-baseweb="tab-list"] {
    gap: 24px;
}
.stTabs [data-baseweb="tab"] {
    height: 50px;
    padding-left: 20px;
    padding-right: 20px;
}
.metric-container {
    background-color: #f0f2f6;
    padding: 1rem;
    border-radius: 0.5rem;
    margin: 0.5rem 0;
}
</style>
""", unsafe_allow_html=True)


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
    """Render the main header."""
    st.title("🎵 MusicWeb - Library Manager")
    st.markdown("---")


def render_sidebar():
    """Render the sidebar with file uploads and library management."""
    st.sidebar.header("📂 Library Management")
    
    # File upload section
    with st.sidebar.expander("📁 Upload Library Files", expanded=True):
        uploaded_files = st.file_uploader(
            "Choose library files",
            accept_multiple_files=True,
            type=['csv', 'json'],
            help="Upload CSV or JSON files from Apple Music, Spotify, or YouTube Music"
        )
        
        if uploaded_files:
            for uploaded_file in uploaded_files:
                if st.button(f"Load {uploaded_file.name}", key=f"load_{uploaded_file.name}"):
                    with st.spinner(f"Loading {uploaded_file.name}..."):
                        success = load_uploaded_file(uploaded_file)
                        if success:
                            st.success(f"✅ Loaded {uploaded_file.name}")
                            st.rerun()
                        else:
                            st.error(f"❌ Failed to load {uploaded_file.name}")
    
    # Existing libraries
    libraries = SessionManager.list_libraries()
    if libraries:
        st.sidebar.header("📚 Loaded Libraries")
        for lib_name in libraries:
            library = SessionManager.get_library(lib_name)
            with st.sidebar.expander(f"🎵 {lib_name}", expanded=False):
                st.write(f"**Platform:** {library.platform}")
                st.write(f"**Total tracks:** {library.total_tracks:,}")
                st.write(f"**Music tracks:** {library.music_count:,}")
                st.write(f"**Non-music:** {library.non_music_count:,}")
                st.write(f"**Artists:** {len(library.artist_counts):,}")
                
                if st.button(f"Remove {lib_name}", key=f"remove_{lib_name}"):
                    del st.session_state.libraries[lib_name]
                    st.rerun()
    
    # YouTube Music setup
    st.sidebar.header("🎵 YouTube Music")
    headers_file = st.sidebar.file_uploader(
        "Upload headers_auth.json",
        type=['json'],
        help="Required for YouTube Music playlist creation"
    )
    
    if headers_file:
        if st.sidebar.button("Setup YouTube Music"):
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
                tmp.write(headers_file.getvalue().decode())
                tmp_path = tmp.name
            
            try:
                playlist_manager = PlaylistManager(tmp_path)
                if playlist_manager.is_available():
                    st.session_state.playlist_manager = playlist_manager
                    st.sidebar.success("✅ YouTube Music connected")
                else:
                    st.sidebar.error("❌ Failed to connect to YouTube Music")
            except Exception as e:
                st.sidebar.error(f"❌ Setup failed: {e}")
            finally:
                Path(tmp_path).unlink(missing_ok=True)


def load_uploaded_file(uploaded_file) -> bool:
    """Load an uploaded file into session state."""
    try:
        # Save to temporary file
        with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix=Path(uploaded_file.name).suffix) as tmp:
            tmp.write(uploaded_file.getvalue())
            tmp_path = tmp.name
        
        # Detect platform
        platform = detect_platform(tmp_path)
        
        # Create parser and load library
        parser = create_parser(platform)
        library = parser.parse_file(tmp_path)
        
        # Add to session state
        lib_name = f"{platform}_{uploaded_file.name}"
        SessionManager.add_library(lib_name, library)
        
        # Cleanup
        Path(tmp_path).unlink(missing_ok=True)
        
        return True
    
    except Exception as e:
        st.error(f"Error loading file: {e}")
        return False


def render_overview_tab():
    """Render the overview tab."""
    st.header("📊 Library Overview")
    
    libraries = SessionManager.list_libraries()
    
    if not libraries:
        st.info("👆 Upload some library files to get started!")
        return
    
    # Summary metrics
    total_libraries = len(libraries)
    total_tracks = sum(SessionManager.get_library(name).total_tracks for name in libraries)
    total_music = sum(SessionManager.get_library(name).music_count for name in libraries)
    total_artists = len(set().union(*(SessionManager.get_library(name).artist_counts.keys() for name in libraries)))
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Libraries", total_libraries)
    with col2:
        st.metric("Total Tracks", f"{total_tracks:,}")
    with col3:
        st.metric("Music Tracks", f"{total_music:,}")
    with col4:
        st.metric("Unique Artists", f"{total_artists:,}")
    
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
        st.warning("⚠️ Need at least 2 libraries to perform comparison")
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
    
    # Perform comparison
    if st.button("🔍 Compare Libraries", type="primary"):
        if source_lib and target_lib:
            with st.spinner("Comparing libraries..."):
                source_library = SessionManager.get_library(source_lib)
                target_library = SessionManager.get_library(target_lib)
                
                comparator = LibraryComparator(
                    strict_mode=strict_mode,
                    enable_duration=use_duration,
                    enable_album=use_album
                )
                
                # Progress bar
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                def progress_callback(current, total, message):
                    progress = current / total if total > 0 else 0
                    progress_bar.progress(progress)
                    status_text.text(message)
                
                comparator.progress_callback = progress_callback
                
                result = comparator.compare_libraries(source_library, target_library)
                
                # Store result
                comparison_key = f"{source_lib}_vs_{target_lib}"
                st.session_state.comparison_results[comparison_key] = result
                
                progress_bar.empty()
                status_text.empty()
                
                st.success("✅ Comparison complete!")
    
    # Display results
    comparison_key = f"{source_lib}_vs_{target_lib}"
    if comparison_key in st.session_state.comparison_results:
        result = st.session_state.comparison_results[comparison_key]
        display_comparison_results(result)


def display_comparison_results(result):
    """Display comparison results."""
    stats = result.get_stats()
    
    # Summary metrics
    st.subheader("📊 Comparison Results")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Matches", f"{stats['total_matches']:,}")
    with col2:
        st.metric("Match Rate", f"{stats['match_rate']:.1f}%")
    with col3:
        st.metric("Avg Confidence", f"{stats['avg_confidence']:.1f}%")
    with col4:
        st.metric("Missing Tracks", f"{stats['missing_tracks']:,}")
    
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
                matches_data.append({
                    'Source Title': match.source_track.title,
                    'Source Artist': match.source_track.artist,
                    'Target Title': match.target_track.title,
                    'Target Artist': match.target_track.artist,
                    'Confidence': f"{match.confidence:.1%}",
                    'Match Type': match.match_type.title()
                })
            
            matches_df = pd.DataFrame(matches_data)
            st.dataframe(matches_df, use_container_width=True)
            
            # Download button
            csv = matches_df.to_csv(index=False)
            st.download_button(
                "📥 Download Matched Tracks CSV",
                csv,
                f"matched_tracks_{int(time.time())}.csv",
                "text/csv"
            )
        else:
            st.info("No matched tracks found")
    
    with tabs[1]:
        if result.missing_tracks:
            missing_data = []
            for track in result.missing_tracks:
                missing_data.append({
                    'Title': track.title,
                    'Artist': track.artist,
                    'Album': track.album or '',
                    'Duration': f"{track.duration}s" if track.duration else '',
                    'Platform': track.platform or ''
                })
            
            missing_df = pd.DataFrame(missing_data)
            st.dataframe(missing_df, use_container_width=True)
            
            # Download button
            csv = missing_df.to_csv(index=False)
            st.download_button(
                "📥 Download Missing Tracks CSV",
                csv,
                f"missing_tracks_{int(time.time())}.csv",
                "text/csv"
            )
            
            # YouTube Music playlist creation
            if st.session_state.playlist_manager:
                st.subheader("🎵 Create YouTube Music Playlist")
                
                playlist_name = st.text_input("Playlist Name", f"Missing Tracks {time.strftime('%Y-%m-%d')}")
                
                if st.button("🎵 Create Playlist"):
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
        st.warning("⚠️ Upload some libraries first")
        return
    
    # Select library to enrich
    selected_lib = st.selectbox("Select library to enrich", libraries)
    
    if not selected_lib:
        return
    
    library = SessionManager.get_library(selected_lib)
    
    st.info(f"📊 {library.name}: {library.music_count:,} music tracks")
    
    # Enrichment options
    with st.expander("⚙️ Enrichment Options", expanded=False):
        limit_tracks = st.checkbox("Limit tracks (for testing)")
        if limit_tracks:
            max_tracks = st.number_input("Max tracks to enrich", min_value=1, max_value=1000, value=50)
        else:
            max_tracks = None
    
    # Warning about rate limits
    st.warning("⚠️ MusicBrainz enrichment is rate-limited (1 request per 1.2 seconds). Large libraries will take time!")
    
    # Perform enrichment
    if st.button("🔍 Enrich Metadata", type="primary"):
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
            
            enriched_results = enricher.bulk_enrich(tracks_to_enrich, progress_callback)
            
            progress_bar.empty()
            status_text.empty()
            
            # Store results
            enrich_key = f"{selected_lib}_enriched"
            st.session_state.enrichment_data[enrich_key] = enriched_results
            
            # Summary
            successful = sum(1 for _, data in enriched_results if data.get('musicbrainz'))
            st.success(f"✅ Enriched {successful}/{len(enriched_results)} tracks")
    
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
    
    # Main content area
    if not SessionManager.list_libraries():
        st.info("👈 Start by uploading some library files in the sidebar!")
        return
    
    # Main tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Overview", 
        "🔍 Compare", 
        "📊 Analyze", 
        "🔍 Enrich",
        "ℹ️ Help"
    ])
    
    with tab1:
        render_overview_tab()
    
    with tab2:
        render_compare_tab()
    
    with tab3:
        render_analyze_tab()
    
    with tab4:
        render_enrich_tab()
    
    with tab5:
        render_help_tab()


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
    1. Upload your `headers_auth.json` file in the sidebar
    2. Generate this file using: `ytmusicapi setup`
    3. Once connected, you can create playlists from missing tracks
    
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