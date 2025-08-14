"""
Web application for MusicWeb.

This module contains the Streamlit-based web interface for MusicWeb,
providing an intuitive UI for music library management and comparison.
"""

from .app import main
from .config import WebConfig

__all__ = ["main", "WebConfig"]