"""
Configuration management for Picture Frame application.
Loads settings from environment variables with sensible defaults.
"""
import os
from dataclasses import dataclass
from typing import List


@dataclass
class Config:
    """Application configuration."""
    # Flask settings
    SECRET_KEY: str = 'dev-secret-key-change-in-production'
    DEBUG: bool = False

    # Authentication
    API_KEY: str = 'change-me'

    # Photo settings
    PHOTO_DIRS: List[str] = None
    PHOTO_DELAY_SECONDS: int = 10
    DISPLAY_ORDER: str = 'random'  # 'random' or 'sequential'

    # Fade/transitions
    FADE_DURATION_MS: int = 1000

    # Cache settings
    CACHE_DIR: str = '/tmp/picture-frame-cache'
    ENABLE_CACHE: bool = True

    def __post_init__(self):
        """Validate and normalize configuration after initialization."""
        if self.PHOTO_DIRS is None:
            self.PHOTO_DIRS = ['/photos']
        elif isinstance(self.PHOTO_DIRS, str):
            self.PHOTO_DIRS = [d.strip() for d in self.PHOTO_DIRS.split(',')]

        # Validate display order
        if self.DISPLAY_ORDER not in ('random', 'sequential'):
            self.DISPLAY_ORDER = 'random'

    @classmethod
    def from_env(cls) -> 'Config':
        """Load configuration from environment variables."""
        photo_dirs_str = os.getenv('PHOTO_DIRS', '/photos')

        return cls(
            SECRET_KEY=os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production'),
            DEBUG=os.getenv('DEBUG', 'false').lower() == 'true',
            API_KEY=os.getenv('API_KEY', 'change-me'),
            PHOTO_DIRS=photo_dirs_str,
            PHOTO_DELAY_SECONDS=int(os.getenv('PHOTO_DELAY_SECONDS', '10')),
            DISPLAY_ORDER=os.getenv('DISPLAY_ORDER', 'random'),
            FADE_DURATION_MS=int(os.getenv('FADE_DURATION_MS', '1000')),
            CACHE_DIR=os.getenv('CACHE_DIR', '/tmp/picture-frame-cache'),
            ENABLE_CACHE=os.getenv('ENABLE_CACHE', 'true').lower() == 'true',
        )
