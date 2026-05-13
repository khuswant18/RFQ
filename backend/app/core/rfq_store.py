"""In-memory RFQ store (placeholder for persistent DB)."""
from datetime import datetime
from threading import RLock
from typing import Any, Dict, List, Optional

_RFQS: Dict[str, Dict[str, Any]] = {}
_LOCK = RLock()


def _now_iso() -> str:
    return datetime.utcnow().isoformat()


def create_rfq(
    rfq_id: str,
    source_channel: str,
    file_type: Optional[str] = None,
    file_path: Optional[str] = None,
    raw_text: Optional[str] = None,
    sender_contact: Optional[str] = None,
) -> Dict[str, Any]:
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
    with _LOCK:
        record = _RFQS.get(rfq_id)
        if not record:
            return None
        record.update(updates)
        record["updated_at"] = _now_iso()
        return record.copy()


def get_rfq(rfq_id: str) -> Optional[Dict[str, Any]]:
    with _LOCK:
        record = _RFQS.get(rfq_id)
        return record.copy() if record else None


def list_rfqs(limit: int = 50, status: Optional[str] = None) -> List[Dict[str, Any]]:
    with _LOCK:
        items = list(_RFQS.values())
        if status:
            items = [item for item in items if item.get("status") == status]
        items.sort(key=lambda item: item.get("updated_at", ""), reverse=True)
        return [item.copy() for item in items[:limit]]
