from __future__ import annotations

from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session, DeclarativeBase


class Base(DeclarativeBase):
    pass


def get_db_path() -> Path:
    # Project root is two levels up from this file: react-with-flask/api -> 2025_hackgt
    project_root = Path(__file__).resolve().parents[2]
    data_dir = project_root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "foodtracker.sqlite3"


def get_engine(echo: bool = False):
    db_path = get_db_path()
    url = f"sqlite:///{db_path}"
    engine = create_engine(url, echo=echo, future=True)
    return engine


# Scoped session for use in Flask handlers
engine = get_engine(echo=False)
SessionLocal = scoped_session(sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True))


def init_db():
    """Create all tables if they don't exist."""
    # Support both package and script execution
    try:
        from .models import FoodItem, NutritionFacts, InventoryItem  # noqa: F401
    except ImportError:
        import os, sys
        sys.path.append(os.path.dirname(__file__))
        from models import FoodItem, NutritionFacts, InventoryItem  # type: ignore  # noqa: F401

    Base.metadata.create_all(bind=engine)
