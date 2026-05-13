from fastapi import APIRouter, HTTPException
from typing import Optional

from app.core.rfq_store import get_rfq as store_get_rfq, list_rfqs

router = APIRouter(tags=["rfq"])


@router.get("/rfq/{rfq_id}")
async def get_rfq(rfq_id: str):
    """Get RFQ details by ID."""
    record = store_get_rfq(rfq_id)
    if not record:
        raise HTTPException(status_code=404, detail="RFQ not found")
    return record


@router.get("/rfq/{rfq_id}/status")
async def get_rfq_status(rfq_id: str):
    """Get the current processing status of an RFQ."""
    record = store_get_rfq(rfq_id)
    if not record:
        raise HTTPException(status_code=404, detail="RFQ not found")
    return {
        "rfq_id": rfq_id,
        "status": record.get("status"),
        "updated_at": record.get("updated_at")
    }


@router.get("/rfq/feed")
async def get_rfq_feed(limit: int = 50, status: Optional[str] = None):
    """Get live feed of RFQs for the dashboard."""
    rfqs = list_rfqs(limit=limit, status=status)
    return {
        "rfqs": rfqs,
        "total": len(rfqs)
    }
