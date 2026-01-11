"""
HTTP routes for Picture Frame application.

Provides API endpoints for photo listing, serving, and configuration.
"""
import os
import random
from flask import Blueprint, render_template, jsonify, send_file, current_app

from .auth import require_api_key
from .image_service import get_image_service

bp = Blueprint('main', __name__)


def init_image_service(photo_dirs, cache_dir, enable_cache):
    """
    Initialize the image service (called from app factory).

    Args:
        photo_dirs: List of photo directory paths
        cache_dir: Cache directory path
        enable_cache: Whether to enable caching
    """
    from .image_service import init_image_service as _init
    _init(photo_dirs, cache_dir, enable_cache)


@bp.route('/')
def index():
    """
    Serve the main H5 slideshow page.

    This page is compatible with Safari on iOS 5.1.1 and uses ES5 JavaScript.
    """
    return render_template('index.html')


@bp.route('/api/config')
def get_config():
    """
    Get client-side configuration.

    Returns delay, fade duration, and display order settings.
    This endpoint does not require authentication as it only returns
    public display settings.
    """
    return jsonify({
        'delay': current_app.config.get('PHOTO_DELAY_SECONDS', 10) * 1000,
        'fadeDuration': current_app.config.get('FADE_DURATION_MS', 1000),
        'displayOrder': current_app.config.get('DISPLAY_ORDER', 'random')
    })


@bp.route('/api/photos')
@require_api_key
def list_photos():
    """
    Get list of all available photos.

    Requires authentication via API key (query param or header).

    Query parameters:
        order: 'random' or 'sequential' - determines photo order

    Returns:
        JSON with 'photos' list and 'count'
    """
    order = request.args.get('order', current_app.config.get('DISPLAY_ORDER', 'random'))

    if order not in ('random', 'sequential'):
        order = 'random'

    image_service = get_image_service()
    photos = image_service.scan_photos(order=order)

    # Shuffle if random order requested
    if order == 'random':
        random.shuffle(photos)

    # Remove internal 'path' field from response
    response_photos = [
        {
            'id': p['id'],
            'name': p['name'],
            'is_heic': p['is_heic'],
            'url': p['url']
        }
        for p in photos
    ]

    return jsonify({
        'photos': response_photos,
        'count': len(response_photos)
    })


@bp.route('/api/photo/<photo_id>')
def get_photo(photo_id):
    """
    Serve a single photo file.

    Handles HEIC transcoding on-demand - HEIC files are converted to JPEG
    before being sent to the client for iOS 5.1.1 compatibility.

    Args:
        photo_id: Unique photo identifier (hash suffix)

    Returns:
        Image file with appropriate MIME type

    Raises:
        404: If photo not found or transcoding failed
    """
    image_service = get_image_service()
    photo = image_service.get_photo_by_id(photo_id)

    if not photo:
        return jsonify({'error': 'Photo not found'}), 404

    display_path = image_service.get_display_path(photo)

    if display_path is None:
        return jsonify({'error': 'Failed to process photo'}), 500

    # Determine MIME type
    if photo['is_heic']:
        mimetype = 'image/jpeg'
    else:
        # Get extension from original path
        ext = Path(photo['path']).suffix.lower()
        if ext in ('.jpg', '.jpeg'):
            mimetype = 'image/jpeg'
        elif ext == '.png':
            mimetype = 'image/png'
        else:
            mimetype = 'image/jpeg'

    return send_file(
        display_path,
        mimetype=mimetype,
        max_age=3600  # Cache for 1 hour
    )


@bp.route('/health')
def health():
    """
    Health check endpoint for Docker/container monitoring.

    Returns:
        JSON with 'status': 'ok'
    """
    return jsonify({'status': 'ok'})


@bp.route('/debug')
def debug():
    """
    Debug endpoint to see what API key is being received.
    """
    from flask import request
    api_key_query = request.args.get('api_key')
    api_key_header = request.headers.get('X-API-Key')
    return jsonify({
        'query_api_key': api_key_query,
        'header_api_key': api_key_header,
        'full_url': request.url,
        'query_string': request.query_string.decode()
    })


# Import request here to avoid circular dependency
from flask import request
from pathlib import Path
