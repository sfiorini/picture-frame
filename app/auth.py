"""
Simple API key authentication for Picture Frame application.

API key can be provided via:
- Query parameter: ?api_key=your-key
- Request header: X-API-Key: your-key
"""
import os
from functools import wraps
from flask import request, jsonify, current_app


def require_api_key(f):
    """
    Decorator to require API key authentication for a route.

    The API key can be provided via:
    - Query parameter 'api_key'
    - Request header 'X-API-Key'

    Args:
        f: The view function to wrap

    Returns:
        Decorated function that returns 401 if API key is invalid or missing
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check query parameter first
        api_key = request.args.get('api_key')

        # Fall back to header
        if not api_key:
            api_key = request.headers.get('X-API-Key')

        # Get configured API key from app config
        expected_key = current_app.config.get('API_KEY', 'change-me')

        if not api_key or api_key != expected_key:
            return jsonify({
                'error': 'Invalid or missing API key',
                'message': 'Provide API key via ?api_key= parameter or X-API-Key header'
            }), 401

        return f(*args, **kwargs)

    return decorated_function
