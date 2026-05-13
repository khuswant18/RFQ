"""RFQ API endpoints."""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Any, Dict

from app.core.rfq_store import get_rfq as store_get_rfq, list_rfqs, update_rfq

router = APIRouter(tags=["rfq"])


@router.get("/rfq/feed")
async def get_rfq_feed(limit: int = 50, status: Optional[str] = None):
    """Get live feed of RFQs for the dashboard."""
    rfqs = list_rfqs(limit=limit, status=status)
    return {
        "rfqs": rfqs,
        "total": len(rfqs)
    }


@router.get("/rfq")
async def get_rfq_list(limit: int = 50, status: Optional[str] = None):
    """List all RFQs (alias for /rfq/feed)."""
    return await get_rfq_feed(limit=limit, status=status)


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
