from __future__ import annotations

from pathlib import Path
import os
from sqlalchemy import create_engine


def get_usda_db_path() -> Path:
    # Allow overriding the USDA SQLite path from an environment variable.
    # Example: export USDA_SQLITE_PATH="/Users/exuan/USDA.sqlite"
    env_path = os.getenv("USDA_SQLITE_PATH")
    if env_path:
        return Path(env_path).expanduser().resolve()

    # Fallback to project-local default
    # Current file is in react-with-flask/api/, so we need to go up 1 level to react-with-flask/
    react_with_flask_root = Path(__file__).resolve().parents[1]
    db_path = react_with_flask_root / "data" / "vendor" / "USDADataBase" / "USDA.sqlite"
    return db_path


def get_usda_engine():
    db_path = get_usda_db_path()
    if not db_path.exists():
        raise FileNotFoundError(
            f"USDA SQLite not found at {db_path}. Please place the built DB there (see USDA_INTEGRATION.md)."
        )
    # Read-only connection: use URI mode with mode=ro
    url = f"sqlite+pysqlite:///{db_path.as_posix()}?mode=ro"
    engine = create_engine(url, connect_args={"uri": True, "check_same_thread": False}, future=True)
    return engine


# Singleton-like engine for app use
try:
    USDA_ENGINE = get_usda_engine()
except FileNotFoundError:
    USDA_ENGINE = None  # Endpoint handlers will return a helpful error until the DB is placed