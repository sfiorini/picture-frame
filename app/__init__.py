"""
Picture Frame Application - Flask app factory.

A web application that displays photos from local folders in a slideshow format,
optimized for Safari on iOS 5.1.1 (iPad 1st gen).
"""
import os
from flask import Flask

from .config import Config
from .routes import bp, init_image_service


def create_app() -> Flask:
    """
    Create and configure the Flask application.

    Returns:
        Flask: Configured Flask application instance
    """
    app = Flask(
        __name__,
        static_folder='static',
        template_folder='static'
    )

    # Load configuration from environment variables
    config = Config.from_env()
    app.config.from_object(config)

    # Initialize image service with config
    init_image_service(
        config.PHOTO_DIRS,
        config.CACHE_DIR,
        config.ENABLE_CACHE
    )

    # Register blueprint
    app.register_blueprint(bp)

    return app
