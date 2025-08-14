"""
File handling utilities.
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional


def detect_encoding(file_path: str) -> str:
    """Detect file encoding."""
    encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']
    
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                f.read()
            return encoding
        except (UnicodeDecodeError, UnicodeError):
            continue
    
    return 'utf-8'  # Fallback


def validate_file_size(file_path: str, max_size_mb: int = 100) -> bool:
    """Validate file size is within limits."""
    try:
        file_size = os.path.getsize(file_path)
        max_size_bytes = max_size_mb * 1024 * 1024
        return file_size <= max_size_bytes
    except OSError:
        return False


def get_file_info(file_path: str) -> Dict[str, Any]:
    """Get comprehensive file information."""
    path = Path(file_path)
    
    info = {
        'name': path.name,
        'stem': path.stem,
        'suffix': path.suffix,
        'size_bytes': 0,
        'size_mb': 0.0,
        'exists': False,
        'is_file': False,
        'encoding': None
    }
    
    if path.exists():
        info['exists'] = True
        info['is_file'] = path.is_file()
        
        if path.is_file():
            info['size_bytes'] = path.stat().st_size
            info['size_mb'] = info['size_bytes'] / (1024 * 1024)
            info['encoding'] = detect_encoding(str(path))
    
    return info


def ensure_directory(dir_path: str) -> None:
    """Ensure directory exists, create if necessary."""
    Path(dir_path).mkdir(parents=True, exist_ok=True)


def clean_filename(filename: str) -> str:
    """Clean filename for safe file system usage."""
    # Remove or replace invalid characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    # Trim whitespace and dots
    filename = filename.strip(' .')
    
    # Ensure not empty
    if not filename:
        filename = 'untitled'
    
    return filename