#!/usr/bin/env python3
"""
Simple web app to review library duplicate candidates.
"""

import streamlit as st
import json
from pathlib import Path
from ytmusicapi import YTMusic
import time

st.set_page_config(
    page_title="Library Duplicate Review",
    page_icon="🎵",
    layout="wide"
)

def load_review_data():
    """Load review data from JSON file."""
    file_path = "/Users/guerrero/Documents/musiccode/library_duplicates_review.json"
    if not Path(file_path).exists():
        return None
    
    with open(file_path, 'r') as f:
        return json.load(f)

def save_decisions(decisions):
    """Save user decisions."""
    file_path = "/Users/guerrero/Documents/musiccode/library_review_decisions.json"
    with open(file_path, 'w') as f:
        json.dump(decisions, f, indent=2)

def run_fresh_analysis():
    """Run a fresh analysis of the current playlist."""
    import subprocess
    import sys
    
    try:
        with st.spinner("🔄 Running fresh analysis of your current playlist..."):
            # Run the analysis script
            result = subprocess.run([
                sys.executable, 
                "/Users/guerrero/Documents/musiccode/remove_library_duplicates.py"
            ], capture_output=True, text=True, timeout=600)
            
            if result.returncode == 0:
                st.success("✅ Fresh analysis complete!")
                return True
            else:
                st.error(f"Analysis failed: {result.stderr}")
                return False
    except subprocess.TimeoutExpired:
        st.error("Analysis timed out. The playlist might be very large.")
        return False
    except Exception as e:
        st.error(f"Error running analysis: {e}")
        return False

def main():
    st.title("🎵 Library Duplicate Review")
    st.markdown("Review tracks in your playlist that might already exist in your library.")
    
    # Refresh analysis button
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown("**Current analysis results:**")
    with col2:
        if st.button("🔄 Refresh Analysis", help="Re-scan playlist for duplicates with current state"):
            # Clear old decisions since playlist has changed
            decisions_file = "/Users/guerrero/Documents/musiccode/library_review_decisions.json"
            if Path(decisions_file).exists():
                Path(decisions_file).unlink()  # Delete old decisions
            
            if run_fresh_analysis():
                st.rerun()  # Refresh the page with new data
    
    # Load data
    data = load_review_data()
    if not data:
        st.error("No review data found.")
        st.info("Click 'Refresh Analysis' to scan your playlist for library duplicates.")
        return
    
    # Summary
    st.header("📊 Summary")
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("Total Potential Duplicates", data['summary']['total_matches'])
    
    with col2:
        st.metric("Need Review", data['summary']['needs_review'])
    
    # Load existing decisions
    decisions_file = "/Users/guerrero/Documents/musiccode/library_review_decisions.json"
    decisions = {}
    if Path(decisions_file).exists():
        with open(decisions_file, 'r') as f:
            decisions = json.load(f)
    
    st.header("🔍 Review Potential Duplicates")
    st.markdown("**Decision Guide:**")
    st.markdown("- **Remove**: The playlist track is the same song as in your library (just different version)")
    st.markdown("- **Keep**: The playlist track is different enough to keep (e.g., live vs studio, acoustic vs electric)")
    
    # Pagination
    items_per_page = 10
    total_items = len(data['needs_review'])
    total_pages = (total_items + items_per_page - 1) // items_per_page
    
    if 'page' not in st.session_state:
        st.session_state.page = 0
    
    # Page navigation
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col1:
        if st.button("◀ Previous") and st.session_state.page > 0:
            st.session_state.page -= 1
    
    with col2:
        st.markdown(f"**Page {st.session_state.page + 1} of {total_pages}**")
    
    with col3:
        if st.button("Next ▶") and st.session_state.page < total_pages - 1:
            st.session_state.page += 1
    
    # Get items for current page
    start_idx = st.session_state.page * items_per_page
    end_idx = min(start_idx + items_per_page, total_items)
    current_items = data['needs_review'][start_idx:end_idx]
    
    # Review items
    for i, item in enumerate(current_items):
        item_idx = start_idx + i
        playlist_track = item['playlist_track']
        video_id = playlist_track['videoId']
        
        st.markdown("---")
        st.subheader(f"Review {item_idx + 1}/{total_items}")
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            # Playlist track
            st.markdown("### 🎵 **Playlist Track**")
            title = playlist_track['title']
            artists = ', '.join(playlist_track['artists'])
            duration = playlist_track.get('duration', '')
            
            st.markdown(f"**{title}**")
            st.markdown(f"by {artists}")
            if duration:
                st.markdown(f"Duration: {duration}")
            
            # Library matches
            st.markdown("### 📚 **Potential Library Matches**")
            for match in item['library_matches']:
                lib_title = match['title']
                lib_artists = ', '.join(match['artists'])
                similarity = match['similarity']
                
                # Color code by similarity
                if similarity >= 0.9:
                    color = "🟢"
                elif similarity >= 0.8:
                    color = "🟡"
                else:
                    color = "🔴"
                
                st.markdown(f"{color} **{lib_title}** by {lib_artists}")
                st.markdown(f"   Similarity: {similarity:.1%} - {match['reason']}")
        
        with col2:
            st.markdown(f"**Confidence:** {item['confidence']:.1%}")
            
            # Decision
            current_decision = decisions.get(video_id, 'undecided')
            
            decision = st.radio(
                "Decision:",
                ['undecided', 'remove', 'keep'],
                key=f"decision_{video_id}",
                index=['undecided', 'remove', 'keep'].index(current_decision),
                help="Remove if it's the same song, Keep if it's different enough"
            )
            
            decisions[video_id] = decision
    
    # Save decisions
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("💾 Save Decisions", type="primary"):
            save_decisions(decisions)
            st.success("Decisions saved!")
    
    # Summary of decisions
    if decisions:
        st.header("📝 Decision Summary")
        
        remove_count = sum(1 for v in decisions.values() if v == 'remove')
        keep_count = sum(1 for v in decisions.values() if v == 'keep')
        undecided_count = sum(1 for v in decisions.values() if v == 'undecided')
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("🗑️ Remove", remove_count)
        with col2:
            st.metric("💾 Keep", keep_count)
        with col3:
            st.metric("❓ Undecided", undecided_count)
    
    # Apply removals section
    st.header("🚀 Apply Removals")
    
    if decisions:
        # Get tracks to remove
        tracks_to_remove = []
        for item in data['needs_review']:
            video_id = item['playlist_track']['videoId']
            if decisions.get(video_id) == 'remove':
                tracks_to_remove.append(item['playlist_track'])
        
        if tracks_to_remove:
            st.warning(f"⚠️ Ready to remove {len(tracks_to_remove)} tracks from your playlist")
            
            # Show what will be removed
            with st.expander(f"Show {len(tracks_to_remove)} tracks to be removed"):
                for track in tracks_to_remove:
                    title = track['title']
                    artists = ', '.join(track['artists'])
                    st.write(f"• {title} by {artists}")
            
            # Confirmation checkbox
            confirm = st.checkbox("I confirm I want to remove these tracks from my playlist")
            
            if confirm:
                if st.button("🗑️ REMOVE TRACKS NOW", type="primary"):
                    # Apply removals
                    headers_path = "/Users/guerrero/Documents/musiccode/headers_auth.json"
                    
                    if not Path(headers_path).exists():
                        st.error("Headers file not found")
                        return
                    
                    try:
                        with st.spinner('Removing tracks...'):
                            ytmusic = YTMusic(headers_path)
                            playlist_id = "PL1LO5jourf4MqCSX94juP7bWk2eYTMCQ2"
                            
                            # Prepare removal data
                            removal_items = []
                            for track in tracks_to_remove:
                                if track.get('videoId') and track.get('setVideoId'):
                                    removal_items.append({
                                        'videoId': track['videoId'],
                                        'setVideoId': track['setVideoId']
                                    })
                            
                            if removal_items:
                                # Remove in batches
                                batch_size = 50
                                progress_bar = st.progress(0)
                                status_text = st.empty()
                                
                                for i in range(0, len(removal_items), batch_size):
                                    batch = removal_items[i:i + batch_size]
                                    ytmusic.remove_playlist_items(playlist_id, batch)
                                    
                                    progress = (i + len(batch)) / len(removal_items)
                                    progress_bar.progress(progress)
                                    status_text.text(f"Removed {i + len(batch)}/{len(removal_items)} tracks...")
                                    
                                    time.sleep(1)  # Rate limiting
                                
                                st.success(f"✅ Successfully removed {len(removal_items)} duplicate tracks!")
                                st.balloons()
                                
                                # Clear the progress indicators
                                progress_bar.empty()
                                status_text.empty()
                            else:
                                st.error("No valid tracks to remove (missing videoId or setVideoId)")
                                
                    except Exception as e:
                        st.error(f"Error removing tracks: {e}")
                        st.write("Please check the error and try again.")
        else:
            st.info("No tracks marked for removal. Mark some tracks as 'remove' first.")
    else:
        st.info("No decisions made yet. Review some tracks first.")

if __name__ == "__main__":
    main()