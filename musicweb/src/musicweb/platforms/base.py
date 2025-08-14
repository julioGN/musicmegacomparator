"""
Base platform parser with common functionality.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from ..core.models import Library


class BasePlatformParser(ABC):
    """Base class for platform-specific parsers."""
    
    def __init__(self, platform_name: str):
        self.platform_name = platform_name
    
    @abstractmethod
    def parse_file(self, file_path: str) -> Library:
        """Parse a file and return a Library object."""
        pass
    
    def _detect_encoding(self, file_path: str) -> str:
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