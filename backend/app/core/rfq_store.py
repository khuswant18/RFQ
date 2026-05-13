"""
RFQ Store — SQLAlchemy-backed persistence with automatic in-memory fallback.

Priority:
1. If DATABASE_URL is set → SQLAlchemy (SQLite or PostgreSQL).
2. Otherwise → thread-safe in-memory dict (data lost on restart).
"""
import logging
from datetime import datetime
from threading import RLock
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Determine storage backend at import time
# ---------------------------------------------------------------------------
from app.core.database import is_db_available, get_session

_USE_DB = is_db_available()

# In-memory fallback store
_RFQS: Dict[str, Dict[str, Any]] = {}
_LOCK = RLock()


def _now_iso() -> str:
    return datetime.utcnow().isoformat()


def _record_to_dict(record) -> Dict[str, Any]:
    """Convert an SQLAlchemy RFQRecord ORM object to a plain dict."""
    return {
        "rfq_id": record.rfq_id,
        "status": record.status,
        "source_channel": record.source_channel,
        "sender_contact": record.sender_contact,
        "raw_file_url": record.raw_file_url,
        "raw_text": record.raw_text,
        "file_type": None,   # legacy compat (not in ORM)
        "file_path": record.raw_file_url,  # stored as raw_file_url in ORM
        "created_at": record.received_at.isoformat() if record.received_at else None,
        "updated_at": record.updated_at.isoformat() if record.updated_at else None,
        "result": record.result_json,
        "error": record.error,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def create_rfq(
    rfq_id: str,
    source_channel: str,
    file_type: Optional[str] = None,
    file_path: Optional[str] = None,
    raw_text: Optional[str] = None,
    sender_contact: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a new RFQ record. Returns the created record as a dict."""

    if _USE_DB:
        try:
            from app.models.db_models import RFQRecord
            session = get_session()
            if session:
                try:
                    now = datetime.utcnow()
                    record = RFQRecord(
                        rfq_id=rfq_id,
                        source_channel=source_channel,
                        sender_contact=sender_contact,
                        raw_file_url=file_path,
                        raw_text=raw_text,
                        status="received",
                        received_at=now,
                        updated_at=now,
                    )
                    session.add(record)
                    session.commit()
                    session.refresh(record)
                    result = _record_to_dict(record)
                    logger.info("RFQ %s created in DB.", rfq_id)
                    return result
                except Exception as exc:
                    session.rollback()
                    logger.error("DB create_rfq failed: %s. Falling back to memory.", exc)
                finally:
                    session.close()
        except Exception as exc:
            logger.error("DB session error in create_rfq: %s. Using memory.", exc)

    # In-memory fallback
    with _LOCK:
        timestamp = _now_iso()
        record = {
            "rfq_id": rfq_id,
            "status": "received",
            "source_channel": source_channel,
            "file_type": file_type,
            "file_path": file_path,
            "raw_text": raw_text,
            "sender_contact": sender_contact,
            "created_at": timestamp,
            "updated_at": timestamp,
            "result": None,
            "error": None,
        }
        _RFQS[rfq_id] = record
        return record.copy()


def update_rfq(rfq_id: str, **updates: Any) -> Optional[Dict[str, Any]]:
    """Update fields on an existing RFQ record."""

    if _USE_DB:
        try:
            from app.models.db_models import RFQRecord
            session = get_session()
            if session:
                try:
                    record = session.query(RFQRecord).filter_by(rfq_id=rfq_id).first()
                    if record:
                        # Map generic update keys to ORM column names
                        field_map = {
                            "status": "status",
                            "error": "error",
                            "result": "result_json",
                            "result_json": "result_json",
                            "raw_text": "raw_text",
                            "sender_contact": "sender_contact",
                        }
                        for key, value in updates.items():
                            orm_field = field_map.get(key, key)
                            if hasattr(record, orm_field):
                                setattr(record, orm_field, value)
                        record.updated_at = datetime.utcnow()
                        session.commit()
                        session.refresh(record)
                        result = _record_to_dict(record)
                        return result
                    logger.warning("update_rfq: RFQ %s not found in DB.", rfq_id)
                    return None
                except Exception as exc:
                    session.rollback()
                    logger.error("DB update_rfq failed: %s. Falling back to memory.", exc)
                finally:
                    session.close()
        except Exception as exc:
            logger.error("DB session error in update_rfq: %s. Using memory.", exc)

    # In-memory fallback
    with _LOCK:
        record = _RFQS.get(rfq_id)
        if not record:
            return None
        record.update(updates)
        record["updated_at"] = _now_iso()
        return record.copy()


def get_rfq(rfq_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve a single RFQ by ID."""

    if _USE_DB:
        try:
            from app.models.db_models import RFQRecord
            session = get_session()
            if session:
                try:
                    record = session.query(RFQRecord).filter_by(rfq_id=rfq_id).first()
                    if record:
                        return _record_to_dict(record)
                    return None
                except Exception as exc:
                    logger.error("DB get_rfq failed: %s. Falling back to memory.", exc)
                finally:
                    session.close()
        except Exception as exc:
            logger.error("DB session error in get_rfq: %s. Using memory.", exc)

    # In-memory fallback
    with _LOCK:
        record = _RFQS.get(rfq_id)
        return record.copy() if record else None


def list_rfqs(limit: int = 50, status: Optional[str] = None) -> List[Dict[str, Any]]:
    """List RFQs ordered by most recently updated."""

    if _USE_DB:
        try:
            from app.models.db_models import RFQRecord
            from sqlalchemy import desc
            session = get_session()
            if session:
                try:
                    query = session.query(RFQRecord)
                    if status:
                        query = query.filter(RFQRecord.status == status)
                    records = query.order_by(desc(RFQRecord.updated_at)).limit(limit).all()
                    return [_record_to_dict(r) for r in records]
                except Exception as exc:
                    logger.error("DB list_rfqs failed: %s. Falling back to memory.", exc)
                finally:
                    session.close()
        except Exception as exc:
            logger.error("DB session error in list_rfqs: %s. Using memory.", exc)

    # In-memory fallback
    with _LOCK:
        items = list(_RFQS.values())
        if status:
            items = [item for item in items if item.get("status") == status]
        items.sort(key=lambda item: item.get("updated_at", ""), reverse=True)
        return [item.copy() for item in items[:limit]]
