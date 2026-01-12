"""
HTTP routes for Picture Frame application.

Provides API endpoints for photo listing, serving, and configuration.
"""
import random
from pathlib import Path
from flask import Blueprint, render_template, jsonify, send_file, current_app, request

from .auth import require_api_key
from .image_service import get_image_service, init_image_service

bp = Blueprint('main', __name__)


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

    Handles HEIC transcoding on-demand and blur generation.

    Args:
        photo_id: Unique photo identifier (hash suffix)

    Query Parameters:
        blur: Set to 'true' to get blurred version for background

    Returns:
        Image file with appropriate MIME type

    Raises:
        404: If photo not found or processing failed
    """
    image_service = get_image_service()
    photo = image_service.get_photo_by_id(photo_id)

    if not photo:
        return jsonify({'error': 'Photo not found'}), 404

    # Check if blur requested
    blur = request.args.get('blur', 'false').lower() == 'true'

    display_path = image_service.get_display_path(photo, blur=blur)

    if display_path is None:
        return jsonify({'error': 'Failed to process photo'}), 500

    # Determine MIME type (blur always returns JPEG)
    if blur:
        mimetype = 'image/jpeg'
    elif photo['is_heic']:
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

    # Cache blur longer (24 hours vs 1 hour for normal)
    max_age = 86400 if blur else 3600

    return send_file(
        display_path,
        mimetype=mimetype,
        max_age=max_age
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
    api_key_query = request.args.get('api_key')
    api_key_header = request.headers.get('X-API-Key')
    return jsonify({
        'query_api_key': api_key_query,
        'header_api_key': api_key_header,
        'full_url': request.url,
        'query_string': request.query_string.decode()
    })
