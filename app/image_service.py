"""
Image service for Picture Frame application.

Handles photo scanning from local directories, HEIC to JPEG transcoding,
and caching of transcoded images.
"""
import hashlib
import os
from pathlib import Path
from typing import List, Tuple, Optional

from flask import current_app, send_file
from PIL import Image, ImageFilter

try:
    import pillow_heif
    pillow_heif.register_heif_opener()
    HEIC_SUPPORT = True
except ImportError:
    HEIC_SUPPORT = False

# Supported image formats
SUPPORTED_FORMATS = {'.jpg', '.jpeg', '.png', '.heic', '.heif'}

# Formats that need transcoding for iOS 5.1.1 compatibility
TRANSCODE_FORMATS = {'.heic', '.heif'}


class ImageService:
    """
    Service for managing photo files and HEIC transcoding.

    Scans configured directories for photos and handles on-demand
    transcoding of HEIC files to JPEG for compatibility with older browsers.
    """

    def __init__(self, photo_dirs: List[str], cache_dir: str, enable_cache: bool = True):
        """
        Initialize the image service.

        Args:
            photo_dirs: List of directory paths to scan for photos
            cache_dir: Directory for caching transcoded images
            enable_cache: Whether to enable caching of transcoded images
        """
        self.photo_dirs = [Path(d) for d in photo_dirs]
        self.cache_dir = Path(cache_dir)
        self.enable_cache = enable_cache
        self._ensure_cache_dir()

    def _ensure_cache_dir(self):
        """Create cache directory if it doesn't exist."""
        if self.enable_cache:
            try:
                self.cache_dir.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                current_app.logger.warning(f'Failed to create cache directory: {e}')
                self.enable_cache = False

    def _get_cache_path(self, image_path: Path) -> Path:
        """
        Generate a cache path for a transcoded image.

        Uses MD5 hash of the original path to avoid filename collisions.

        Args:
            image_path: Original image path

        Returns:
            Path where transcoded image should be cached
        """
        path_hash = hashlib.md5(str(image_path).encode()).hexdigest()
        return self.cache_dir / f'{path_hash}.jpg'

    def _transcode_heic(self, heic_path: Path) -> Optional[Path]:
        """
        Transcode HEIC/HEIF image to JPEG.

        Args:
            heic_path: Path to the HEIC/HEIF file

        Returns:
            Path to transcoded JPEG file, or None if transcoding failed
        """
        if not HEIC_SUPPORT:
            current_app.logger.error(f'HEIC support not available, cannot transcode {heic_path}')
            return None

        cache_path = self._get_cache_path(heic_path)

        # Check cache first
        if self.enable_cache and cache_path.exists():
            # Verify cache is newer than source
            if cache_path.stat().st_mtime > heic_path.stat().st_mtime:
                return cache_path

        try:
            with Image.open(heic_path) as img:
                # Convert to RGB if needed (HEIC might have alpha channel)
                if img.mode != 'RGB':
                    img = img.convert('RGB')

                # Save as JPEG with high quality
                img.save(cache_path, 'JPEG', quality=95, optimize=True)

            current_app.logger.debug(f'Transcoded {heic_path} to {cache_path}')
            return cache_path

        except Exception as e:
            current_app.logger.error(f'Failed to transcode {heic_path}: {e}')
            return None

    def _generate_blurred_image(self, image_path: Path) -> Optional[Path]:
        """
        Generate a blurred version of an image for background display.

        Creates a downscaled (max 800px dimension) and heavily blurred version
        of the image optimized for use as a background layer.

        Args:
            image_path: Path to the original image

        Returns:
            Path to cached blurred image, or None if generation failed
        """
        # Use separate blur cache directory
        blur_cache_path = self.cache_dir / 'blur' / self._get_cache_path(image_path).name

        # Check cache first
        if self.enable_cache and blur_cache_path.exists():
            if blur_cache_path.stat().st_mtime > image_path.stat().st_mtime:
                return blur_cache_path

        # Ensure blur cache subdirectory exists
        try:
            blur_cache_path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            current_app.logger.warning(f'Failed to create blur cache directory: {e}')
            return None

        try:
            with Image.open(image_path) as img:
                # Convert to RGB if needed
                if img.mode != 'RGB':
                    img = img.convert('RGB')

                # Downscale for performance (max dimension 800px)
                img.thumbnail((800, 800), Image.LANCZOS)

                # Apply heavy blur
                img = img.filter(ImageFilter.GaussianBlur(radius=30))

                # Save as JPEG with lower quality (background doesn't need high quality)
                img.save(blur_cache_path, 'JPEG', quality=70, optimize=True)

                current_app.logger.debug(f'Generated blurred image for {image_path}')
                return blur_cache_path

        except Exception as e:
            current_app.logger.error(f'Failed to generate blur for {image_path}: {e}')
            return None

    def scan_photos(self, order: str = 'random') -> List[dict]:
        """
        Scan photo directories and return list of available photos.

        Args:
            order: 'random' or 'sequential' - determines photo order

        Returns:
            List of photo dictionaries with metadata
        """
        photos = []
        seen_paths = set()

        for photo_dir in self.photo_dirs:
            if not photo_dir.exists():
                current_app.logger.warning(f'Photo directory does not exist: {photo_dir}')
                continue

            if not photo_dir.is_dir():
                current_app.logger.warning(f'Photo path is not a directory: {photo_dir}')
                continue

            # Recursively find supported image files
            for filepath in photo_dir.rglob('*'):
                # Skip if not a file or extension not supported
                if not filepath.is_file():
                    continue

                ext = filepath.suffix.lower()
                if ext not in SUPPORTED_FORMATS:
                    continue

                # Use full path as unique identifier
                full_path = str(filepath.resolve())
                if full_path in seen_paths:
                    continue
                seen_paths.add(full_path)

                # Determine if transcoding needed
                is_heic = ext in TRANSCODE_FORMATS

                # Create relative URL path
                # Use filename as identifier, but need to handle duplicates
                # Use hash of full path for unique identifier
                path_hash = hashlib.md5(full_path.encode()).hexdigest()[:12]
                display_name = filepath.stem

                photos.append({
                    'id': f'{display_name}_{path_hash}',
                    'name': display_name,
                    'path': full_path,
                    'is_heic': is_heic,
                    'url': f'/api/photo/{path_hash}'
                })

        # Sort by path for sequential order
        if order == 'sequential':
            photos.sort(key=lambda p: p['path'])
        # For random, we shuffle in the frontend or can do here
        # Doing it here allows persistent shuffle for the session

        return photos

    def get_photo_by_id(self, photo_id: str) -> Optional[dict]:
        """
        Find a photo by its ID.

        Args:
            photo_id: Photo identifier (hash suffix)

        Returns:
            Photo dict or None if not found
        """
        photos = self.scan_photos()
        for photo in photos:
            # Match by hash suffix (last 12 chars of the id)
            if photo['id'].endswith(photo_id) or photo['id'] == photo_id:
                return photo
        return None

    def get_display_path(self, photo: dict, blur: bool = False) -> Optional[str]:
        """
        Get the path to use for displaying a photo.

        For HEIC files, returns the path to the transcoded JPEG.
        For blur requests, returns the path to the blurred version.
        For other formats, returns the original path.

        Args:
            photo: Photo dictionary from scan_photos()
            blur: Whether to get the blurred version

        Returns:
            Path to use for display, or None if processing failed
        """
        photo_path = Path(photo['path'])

        # Handle blur request
        if blur:
            # For HEIC, we blur the transcoded version
            if photo['is_heic']:
                transcoded = self._transcode_heic(photo_path)
                if transcoded:
                    return self._generate_blurred_image(transcoded)
            else:
                return self._generate_blurred_image(photo_path)
            return None

        # Normal display path
        if photo['is_heic']:
            cached = self._transcode_heic(photo_path)
            if cached:
                return str(cached)
            # Transcoding failed, return None
            return None

        return str(photo_path)


# Global image service instance
_image_service: Optional[ImageService] = None


def init_image_service(photo_dirs: List[str], cache_dir: str, enable_cache: bool = True):
    """
    Initialize the global image service instance.

    Args:
        photo_dirs: List of directory paths to scan for photos
        cache_dir: Directory for caching transcoded images
        enable_cache: Whether to enable caching
    """
    global _image_service
    _image_service = ImageService(photo_dirs, cache_dir, enable_cache)


def get_image_service() -> Optional[ImageService]:
    """
    Get the global image service instance.

    Returns:
        ImageService instance or None if not initialized

    Raises:
        RuntimeError: If image service has not been initialized
    """
    if _image_service is None:
        raise RuntimeError('Image service not initialized. Call init_image_service() first.')
    return _image_service
