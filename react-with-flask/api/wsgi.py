#!/usr/bin/env python3
"""
Production WSGI entry point for Flask application
"""
import os
import sys

# Add the api directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# Set environment variables for production
os.environ.setdefault('FLASK_ENV', 'production')

# Import the Flask app
from api import app

# Configure the application for production
if __name__ != '__main__':
    # Production gunicorn setup
    import logging
    gunicorn_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)

# The WSGI callable
application = app

if __name__ == '__main__':
    # For development/testing only
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5001)))