"""SQLAlchemy database setup with async engine support."""
import os
from typing import Generator, Optional

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

DATABASE_URL = os.getenv("DATABASE_URL", "") or "sqlite:///./srip.db"

_engine = None
_SessionLocal = None


def get_engine():
    """Get or create the SQLAlchemy engine."""
    global _engine
    if _engine is None and SQLALCHEMY_AVAILABLE and DATABASE_URL:
        engine_kwargs = {
            "pool_pre_ping": True,
            "echo": os.getenv("SQL_ECHO", "false").lower() == "true",
        }
        if DATABASE_URL.startswith("sqlite"):
            engine_kwargs["connect_args"] = {"check_same_thread": False}
        else:
            engine_kwargs["pool_size"] = 10
            engine_kwargs["max_overflow"] = 20

        _engine = create_engine(DATABASE_URL, **engine_kwargs)
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


def get_db() -> Generator:
    """FastAPI dependency to provide a DB session."""
    session = get_session()
    if session is None:
        yield None
        return
    try:
        yield session
    finally:
        session.close()


def init_db():
    """Initialize database tables."""
    engine = get_engine()
    if engine is None:
        print("⚠️  DATABASE_URL not configured. Using in-memory store.")
        return
    try:
        from app.models import db_models  # noqa: F401
    except Exception as exc:
        print(f"⚠️  Failed to import DB models: {exc}")
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created.")


def is_db_available() -> bool:
    """Check if a database connection is configured and available."""
    return bool(SQLALCHEMY_AVAILABLE and DATABASE_URL)
