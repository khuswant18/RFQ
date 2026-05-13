"""SQLAlchemy-backed RFQ store."""
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import desc

from app.core.database import get_session
from app.models.db_models import RFQRecord


def _now() -> datetime:
    return datetime.utcnow()


def _to_dict(record: RFQRecord) -> Dict[str, Any]:
    return {
        "rfq_id": record.rfq_id,
        "status": record.status,
        "source_channel": record.source_channel,
        "file_type": record.file_type,
        "file_path": record.file_path,
        "raw_file_url": record.raw_file_url,
        "raw_text": record.raw_text,
        "sender_contact": record.sender_contact,
        "created_at": record.received_at.isoformat() if record.received_at else None,
        "updated_at": record.updated_at.isoformat() if record.updated_at else None,
        "result": record.result_json,
        "error": record.error,
    }


def create_rfq(
    rfq_id: str,
    source_channel: str,
    file_type: Optional[str] = None,
    file_path: Optional[str] = None,
    raw_text: Optional[str] = None,
    sender_contact: Optional[str] = None,
) -> Dict[str, Any]:
    session = get_session()
    if session is None:
        raise RuntimeError("Database session not available")
    try:
        record = RFQRecord(
            rfq_id=rfq_id,
            status="received",
            source_channel=source_channel,
            file_type=file_type,
            file_path=file_path,
            raw_text=raw_text,
            sender_contact=sender_contact,
            received_at=_now(),
            updated_at=_now(),
            result_json=None,
            error=None,
        )
        session.add(record)
        session.commit()
        session.refresh(record)
        return _to_dict(record)
    finally:
        session.close()


def update_rfq(rfq_id: str, **updates: Any) -> Optional[Dict[str, Any]]:
    session = get_session()
    if session is None:
        raise RuntimeError("Database session not available")
    try:
        record = session.query(RFQRecord).filter_by(rfq_id=rfq_id).first()
        if not record:
            return None
        for key, value in updates.items():
            if key == "result":
                setattr(record, "result_json", value)
            else:
                setattr(record, key, value)
        record.updated_at = _now()
        session.commit()
        session.refresh(record)
        return _to_dict(record)
    finally:
        session.close()


def update_rfq_status(rfq_id: str, status: str) -> Optional[Dict[str, Any]]:
    return update_rfq(rfq_id, status=status)


def get_rfq(rfq_id: str) -> Optional[Dict[str, Any]]:
    session = get_session()
    if session is None:
        raise RuntimeError("Database session not available")
    try:
        record = session.query(RFQRecord).filter_by(rfq_id=rfq_id).first()
        return _to_dict(record) if record else None
    finally:
        session.close()


def list_rfqs(limit: int = 50, status: Optional[str] = None) -> List[Dict[str, Any]]:
    session = get_session()
    if session is None:
        raise RuntimeError("Database session not available")
    try:
        query = session.query(RFQRecord)
        if status:
            query = query.filter(RFQRecord.status == status)
        records = query.order_by(desc(RFQRecord.received_at)).limit(limit).all()
        return [_to_dict(record) for record in records]
    finally:
        session.close()
