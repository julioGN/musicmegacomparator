#!/usr/bin/env python3
"""
Web app for manual review of duplicate candidates.
"""

import streamlit as st
import json
import pandas as pd
from pathlib import Path
from ytmusicapi import YTMusic
import time

st.set_page_config(
    page_title="Playlist Duplicate Review",
    page_icon="🎵",
    layout="wide"
)

def load_review_data(file_path: str):
    """Load review data from JSON file."""
    if not Path(file_path).exists():
        return None
    
    with open(file_path, 'r') as f:
        return json.load(f)

def save_review_decisions(decisions: dict, file_path: str):
    """Save user review decisions."""
    with open(file_path, 'w') as f:
        json.dump(decisions, f, indent=2)

def format_track_info(track: dict) -> str:
    """Format track information for display."""
    title = track.get('title', 'Unknown')
    artists = ', '.join(track.get('artists', []))
    duration = track.get('duration', '')
    
    return f"**{title}** by {artists}" + (f" ({duration})" if duration else "")

def main():
    st.title("🎵 Playlist Duplicate Review")
    st.markdown("Review potential duplicates found in your playlist and decide which ones to remove.")
    
    # File upload/selection
    review_file = st.sidebar.text_input(
        "Review data file path:",
        value="/Users/guerrero/Documents/musiccode/duplicate_review.json"
    )
    
    if not Path(review_file).exists():
        st.error(f"Review file not found: {review_file}")
        st.info("Run the advanced_playlist_cleaner.py script first to generate review data.")
        return
    
    # Load data
    data = load_review_data(review_file)
    if not data:
        st.error("Could not load review data")
        return
    
    # Summary
    st.header("📊 Summary")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Duplicates", data['summary']['total_duplicates'])
    
    with col2:
        st.metric("Auto-Remove", data['summary']['auto_remove'])
    
    with col3:
        st.metric("Needs Review", data['summary']['needs_review'])
    
    # Load existing decisions
    decisions_file = review_file.replace('.json', '_decisions.json')
    decisions = {}
    if Path(decisions_file).exists():
        with open(decisions_file, 'r') as f:
            decisions = json.load(f)
    
    # Auto-remove candidates
    st.header("✅ Auto-Remove Candidates")
    if data['auto_remove']:
        st.success(f"Found {len(data['auto_remove'])} high-confidence duplicates that can be safely auto-removed.")
        
        with st.expander(f"View {len(data['auto_remove'])} auto-remove candidates"):
            for i, candidate in enumerate(data['auto_remove']):
                track = candidate['playlist_track']
                st.write(f"{i+1}. {format_track_info(track)} - **{candidate['match_type']}** match (confidence: {candidate['confidence']:.1%})")
    else:
        st.info("No high-confidence auto-remove candidates found.")
    
    # Manual review section
    st.header("🔍 Manual Review Required")
    
    if not data['needs_review']:
        st.success("No manual review needed! All duplicates can be auto-processed.")
        return
    
    st.warning(f"{len(data['needs_review'])} items need manual review due to uncertainty or multiple matches.")
    
    # Review each candidate
    for i, candidate in enumerate(data['needs_review']):
        track = candidate['playlist_track']
        track_id = track['videoId']
        
        st.markdown("---")
        st.subheader(f"Review {i+1}/{len(data['needs_review'])}")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown("### 🎵 Playlist Track")
            st.markdown(format_track_info(track))
            
            if candidate['similar_tracks']:
                st.markdown("### 📚 Similar Library Tracks")
                for j, sim_track in enumerate(candidate['similar_tracks']):
                    similarity = sim_track['similarity']
                    color = "🟢" if similarity > 0.9 else "🟡" if similarity > 0.8 else "🔴"
                    st.markdown(f"{color} {format_track_info(sim_track)} - {similarity:.1%} similar")
        
        with col2:
            st.markdown(f"**Match Type:** {candidate['match_type']}")
            st.markdown(f"**Confidence:** {candidate['confidence']:.1%}")
            
            # Decision buttons
            current_decision = decisions.get(track_id, 'undecided')
            
            decision = st.radio(
                "Decision:",
                ['undecided', 'remove', 'keep'],
                key=f"decision_{track_id}",
                index=['undecided', 'remove', 'keep'].index(current_decision)
            )
            
            decisions[track_id] = decision
            
            # Notes
            note_key = f"note_{track_id}"
            note = st.text_area(
                "Notes (optional):",
                value=decisions.get(note_key, ''),
                key=note_key,
                height=60
            )
            decisions[note_key] = note
    
    # Save decisions
    if st.button("💾 Save Review Decisions", type="primary"):
        save_review_decisions(decisions, decisions_file)
        st.success(f"Decisions saved to {decisions_file}")
    
    # Summary of decisions
    if decisions:
        st.header("📝 Review Summary")
        
        remove_count = sum(1 for k, v in decisions.items() if not k.startswith('note_') and v == 'remove')
        keep_count = sum(1 for k, v in decisions.items() if not k.startswith('note_') and v == 'keep')
        undecided_count = sum(1 for k, v in decisions.items() if not k.startswith('note_') and v == 'undecided')
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("🗑️ Remove", remove_count)
        with col2:
            st.metric("💾 Keep", keep_count)
        with col3:
            st.metric("❓ Undecided", undecided_count)
    
    # Apply decisions
    if st.button("🚀 Apply Removal Decisions", type="secondary"):
        if not decisions:
            st.error("No decisions to apply")
            return
        
        # Get tracks to remove based on decisions
        tracks_to_remove = []
        for candidate in data['needs_review']:
            track_id = candidate['playlist_track']['videoId']
            if decisions.get(track_id) == 'remove':
                tracks_to_remove.append(candidate['playlist_track'])
        
        if not tracks_to_remove:
            st.warning("No tracks selected for removal")
            return
        
        st.warning(f"This will remove {len(tracks_to_remove)} tracks from your playlist. Are you sure?")
        
        if st.button("⚠️ CONFIRM REMOVAL", type="secondary"):
            # Apply removals using ytmusicapi
            headers_path = "/Users/guerrero/Documents/musiccode/headers_auth.json"
            
            if not Path(headers_path).exists():
                st.error("Headers file not found. Cannot apply changes.")
                return
            
            try:
                ytmusic = YTMusic(headers_path)
                playlist_id = "PL1LO5jourf4MqCSX94juP7bWk2eYTMCQ2"  # Should be configurable
                
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
                    
                    for i in range(0, len(removal_items), batch_size):
                        batch = removal_items[i:i + batch_size]
                        ytmusic.remove_playlist_items(playlist_id, batch)
                        
                        progress = (i + len(batch)) / len(removal_items)
                        progress_bar.progress(progress)
                        
                        st.write(f"Removed batch {i//batch_size + 1}: {len(batch)} tracks")
                        time.sleep(1)  # Rate limiting
                    
                    st.success(f"Successfully removed {len(removal_items)} tracks from playlist!")
                else:
                    st.error("No valid tracks to remove (missing videoId or setVideoId)")
                    
            except Exception as e:
                st.error(f"Error applying changes: {e}")

if __name__ == "__main__":
    main()