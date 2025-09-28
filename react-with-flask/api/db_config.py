"""
Database configuration for different environments
"""
import os
from urllib.parse import urlparse

def get_database_url():
    """Get the appropriate database URL for the current environment."""
    
    # Check if we're in production with PostgreSQL
    database_url = os.getenv('DATABASE_URL')
    if database_url:
        # Render provides DATABASE_URL for PostgreSQL
        # Fix for psycopg2 compatibility (Render uses postgres://, psycopg2 expects postgresql://)
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)
        return database_url
    
    # Development/local environment - use SQLite
    return 'sqlite:///./grocery_tracker.db'

def is_production():
    """Check if we're running in production environment."""
    return os.getenv('FLASK_ENV') == 'production' and os.getenv('DATABASE_URL') is not None

def get_usda_db_path():
    """Get USDA database path - for production, this would need to be uploaded or replaced with PostgreSQL tables."""
    if is_production():
        # In production, you might want to import USDA data into PostgreSQL
        # For now, disable USDA features in production
        return None
    else:
        # Local development path
        import os
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        return os.path.join(project_root, 'data', 'vendor', 'USDA.sqlite')