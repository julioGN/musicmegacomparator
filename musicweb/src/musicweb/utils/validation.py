"""
Data validation utilities.
"""

from typing import Dict, List, Any, Optional
from ..core.models import Track, Library


def validate_track_data(track_data: Dict[str, Any]) -> List[str]:
    """Validate track data and return list of issues."""
    issues = []
    
    # Required fields
    if not track_data.get('title'):
        issues.append("Missing or empty title")
    
    if not track_data.get('artist'):
        issues.append("Missing or empty artist")
    
    # Data type validation
    duration = track_data.get('duration')
    if duration is not None:
        try:
            duration = int(duration)
            if duration < 0:
                issues.append("Duration cannot be negative")
            elif duration > 7200:  # 2 hours
                issues.append("Duration seems unreasonably long (>2 hours)")
        except (ValueError, TypeError):
            issues.append("Duration must be a number")
    
    # Year validation
    year = track_data.get('year')
    if year is not None:
        try:
            year = int(year)
            if year < 1900 or year > 2030:
                issues.append("Year seems unreasonable")
        except (ValueError, TypeError):
            issues.append("Year must be a number")
    
    # Track number validation
    track_number = track_data.get('track_number')
    if track_number is not None:
        try:
            track_number = int(track_number)
            if track_number < 1:
                issues.append("Track number must be positive")
        except (ValueError, TypeError):
            issues.append("Track number must be a number")
    
    return issues


def validate_library_data(library: Library) -> Dict[str, Any]:
    """Validate library data and return validation report."""
    report = {
        'valid': True,
        'total_tracks': len(library.tracks),
        'issues': [],
        'warnings': [],
        'track_issues': {}
    }
    
    if not library.tracks:
        report['issues'].append("Library contains no tracks")
        report['valid'] = False
        return report
    
    # Validate individual tracks
    tracks_with_issues = 0
    
    for i, track in enumerate(library.tracks):
        track_issues = validate_track_data(track.to_dict())
        if track_issues:
            tracks_with_issues += 1
            report['track_issues'][i] = track_issues
    
    # Summary statistics
    if tracks_with_issues > 0:
        percentage = (tracks_with_issues / len(library.tracks)) * 100
        if percentage > 10:
            report['issues'].append(f"{tracks_with_issues} tracks have validation issues ({percentage:.1f}%)")
            report['valid'] = False
        else:
            report['warnings'].append(f"{tracks_with_issues} tracks have minor issues ({percentage:.1f}%)")
    
    # Check for duplicates
    seen_tracks = set()
    duplicates = 0
    
    for track in library.tracks:
        track_key = (track.normalized_title, track.normalized_artist)
        if track_key in seen_tracks:
            duplicates += 1
        else:
            seen_tracks.add(track_key)
    
    if duplicates > 0:
        percentage = (duplicates / len(library.tracks)) * 100
        if percentage > 5:
            report['warnings'].append(f"{duplicates} potential duplicate tracks ({percentage:.1f}%)")
    
    return report


def validate_comparison_parameters(strict_mode: bool, enable_duration: bool, 
                                 enable_album: bool) -> List[str]:
    """Validate comparison parameters."""
    issues = []
    
    if not isinstance(strict_mode, bool):
        issues.append("strict_mode must be a boolean")
    
    if not isinstance(enable_duration, bool):
        issues.append("enable_duration must be a boolean")
    
    if not isinstance(enable_album, bool):
        issues.append("enable_album must be a boolean")
    
    return issues