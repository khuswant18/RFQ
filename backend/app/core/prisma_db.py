"""Prisma-based database layer for SRIP."""
import os
import json
from typing import Optional, List, Dict, Any
from datetime import datetime
from prisma import Prisma

# Initialize Prisma client
db = Prisma()


async def connect_db():
    """Connect to database."""
    await db.connect()
    print("✅ Database connected via Prisma")


async def disconnect_db():
    """Disconnect from database."""
    await db.disconnect()
    print("✅ Database disconnected")


# ==================== RFQ Operations ====================

async def create_rfq(
    rfq_id: str,
    source_channel: str,
    file_type: Optional[str] = None,
    file_path: Optional[str] = None,
    raw_text: Optional[str] = None,
    sender_contact: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a new RFQ record."""
    rfq = await db.rfq.create(
        data={
            "rfqId": rfq_id,
            "sourceChannel": source_channel,
            "fileType": file_type,
            "filePath": file_path,
            "rawText": raw_text,
            "senderContact": sender_contact,
            "status": "received",
        }
    )
    return _rfq_to_dict(rfq)


async def get_rfq(rfq_id: str) -> Optional[Dict[str, Any]]:
    """Get RFQ by ID."""
    rfq = await db.rfq.find_unique(where={"rfqId": rfq_id})
    return _rfq_to_dict(rfq) if rfq else None


async def list_rfqs(limit: int = 50, status: Optional[str] = None) -> List[Dict[str, Any]]:
    """List RFQs with optional status filter."""
    where = {}
    if status:
        where["status"] = status
    
    rfqs = await db.rfq.find_many(
        where=where,
        order={"receivedAt": "desc"},
        take=limit,
    )
    return [_rfq_to_dict(rfq) for rfq in rfqs]


async def update_rfq(rfq_id: str, **updates: Any) -> Optional[Dict[str, Any]]:
    """Update RFQ record."""
    update_data = {}
    
    for key, value in updates.items():
        if key == "result":
            update_data["resultJson"] = json.dumps(value) if value else None
        elif key == "file_type":
            update_data["fileType"] = value
        elif key == "file_path":
            update_data["filePath"] = value
        elif key == "raw_file_url":
            update_data["rawFileUrl"] = value
        elif key == "raw_text":
            update_data["rawText"] = value
        elif key == "sender_contact":
            update_data["senderContact"] = value
        else:
            update_data[key] = value
    
    rfq = await db.rfq.update(
        where={"rfqId": rfq_id},
        data=update_data,
    )
    return _rfq_to_dict(rfq) if rfq else None


async def delete_rfq(rfq_id: str) -> bool:
    """Delete RFQ record."""
    result = await db.rfq.delete(where={"rfqId": rfq_id})
    return result is not None


# ==================== RFQ Status ====================

async def update_rfq_status(rfq_id: str, status: str) -> Optional[Dict[str, Any]]:
    """Update RFQ processing status."""
    return await update_rfq(rfq_id, status=status)


# ==================== Helper Functions ====================

def _rfq_to_dict(rfq) -> Dict[str, Any]:
    """Convert RFQ model to dictionary."""
    if not rfq:
        return None
    
    result_json = None
    try:
        result_json = json.loads(rfq.resultJson) if rfq.resultJson else None
    except:
        result_json = None
    
    return {
        "rfq_id": rfq.rfqId,
        "status": rfq.status,
        "source_channel": rfq.sourceChannel,
        "file_type": rfq.fileType,
        "file_path": rfq.filePath,
        "raw_file_url": rfq.rawFileUrl,
        "raw_text": rfq.rawText,
        "sender_contact": rfq.senderContact,
        "created_at": rfq.receivedAt.isoformat() if rfq.receivedAt else None,
        "updated_at": rfq.updatedAt.isoformat() if rfq.updatedAt else None,
        "result": result_json,
        "error": rfq.error,
    }
