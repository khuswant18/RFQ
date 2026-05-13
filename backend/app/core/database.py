"""SQLAlchemy database setup — supports SQLite (dev) and PostgreSQL (prod)."""
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

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

# Resolve DATABASE_URL — default to SQLite so dev works without Postgres
_RAW_URL = os.getenv("DATABASE_URL", "")
if not _RAW_URL:
    # Auto-default: SQLite file next to this module
    _db_file = os.path.join(os.path.dirname(__file__), "..", "..", "srip.db")
    _db_file = os.path.normpath(_db_file)
    DATABASE_URL = f"sqlite:///{_db_file}"
    logger.info("DATABASE_URL not set — defaulting to SQLite at %s", _db_file)
else:
    DATABASE_URL = _RAW_URL

_engine = None
_SessionLocal = None


def get_engine():
    """Get or create the SQLAlchemy engine (lazy singleton)."""
    global _engine
    if _engine is None and SQLALCHEMY_AVAILABLE:
        is_sqlite = DATABASE_URL.startswith("sqlite")

        if is_sqlite:
            # SQLite doesn't support pool_size / max_overflow
            _engine = create_engine(
                DATABASE_URL,
                connect_args={"check_same_thread": False},
                echo=os.getenv("SQL_ECHO", "false").lower() == "true",
            )
        else:
            _engine = create_engine(
                DATABASE_URL,
                pool_size=10,
                max_overflow=20,
                pool_pre_ping=True,
                echo=os.getenv("SQL_ECHO", "false").lower() == "true",
            )
        logger.info("DB engine created: %s", DATABASE_URL.split("@")[-1])  # hide creds
    return _engine


def get_session():
    """Get a new database session (caller is responsible for close)."""
    global _SessionLocal
    engine = get_engine()
    if engine is None:
        return None
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    return _SessionLocal()


def init_db():
    """Create all tables defined in ORM models (idempotent)."""
    engine = get_engine()
    if engine is None:
        logger.warning("⚠️  No database engine — skipping table creation.")
        return
    try:
        # Import models so their metadata is registered on Base
        import app.models.db_models  # noqa: F401
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database tables created/verified.")
    except Exception as exc:
        logger.error("DB init failed: %s", exc)
        raise


def is_db_available() -> bool:
    """True if SQLAlchemy is installed and an engine can be created."""
    return SQLALCHEMY_AVAILABLE
