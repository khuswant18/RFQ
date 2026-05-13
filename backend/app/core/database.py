"""SQLAlchemy database setup with async engine support."""
import os
from typing import Optional

# SQLAlchemy is optional — graceful fallback to in-memory store
try:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker, DeclarativeBase
    SQLALCHEMY_AVAILABLE = True

    class Base(DeclarativeBase):
        """Base class for all ORM models."""
        pass
except ImportError:
    SQLALCHEMY_AVAILABLE = False
    Base = None  # type: ignore

DATABASE_URL = os.getenv("DATABASE_URL", "")

_engine = None
_SessionLocal = None


def get_engine():
    """Get or create the SQLAlchemy engine."""
    global _engine
    if _engine is None and SQLALCHEMY_AVAILABLE and DATABASE_URL:
        _engine = create_engine(
            DATABASE_URL,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            echo=os.getenv("SQL_ECHO", "false").lower() == "true",
        )
    return _engine


def get_session():
    """Get a new database session."""
    global _SessionLocal
    engine = get_engine()
    if engine is None:
        return None
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    return _SessionLocal()


def init_db():
    """Initialize database tables."""
    engine = get_engine()
    if engine is None:
        print("⚠️  DATABASE_URL not configured. Using in-memory store.")
        return
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created.")


def is_db_available() -> bool:
    """Check if a database connection is configured and available."""
    return bool(SQLALCHEMY_AVAILABLE and DATABASE_URL)
