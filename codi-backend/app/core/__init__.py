"""Core infrastructure package for Codi backend.

This package provides:
- config: Application settings
- database: SQLAlchemy database connection
"""
from app.core.config import settings
from app.core.database import init_db, get_db, get_db_context, Base

__all__ = [
    # Config
    "settings",
    # Database
    "init_db",
    "get_db",
    "get_db_context",
    "Base",
]
