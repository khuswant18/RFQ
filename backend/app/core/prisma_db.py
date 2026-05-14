"""Prisma-based database layer for SRIP."""
import os
import json
from typing import Optional, List, Dict, Any
from datetime import datetime

# Try to import Prisma, fall back to mock if not available
try:
    from prisma import Prisma
    PRISMA_AVAILABLE = True
except (ImportError, RuntimeError) as e:
    print(f"⚠️  Prisma not available: {e}")
    print("⚠️  Using mock database - data will not persist!")
    PRISMA_AVAILABLE = False
    
    # Mock Prisma client - SINGLETON
    class MockPrisma:
        _instance = None
        _data = {}  # Shared data store
        
        def __new__(cls):
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._connected = False
            return cls._instance
        
        def is_connected(self):
            return self._connected
        
        async def connect(self):
            self._connected = True
            print("✅ Mock database connected")
        
        async def disconnect(self):
            self._connected = False
            print("✅ Mock database disconnected")
        
        @property
        def rfq(self):
            return self
        
        async def create(self, data):
            # Create a mock RFQ object with all required fields
            rfq_data = {
                'rfqId': data.get('rfqId'),
                'sourceChannel': data.get('sourceChannel'),
                'fileType': data.get('fileType'),
                'filePath': data.get('filePath'),
                'rawText': data.get('rawText'),
                'senderContact': data.get('senderContact'),
                'status': data.get('status', 'received'),
                'receivedAt': datetime.now(),
                'updatedAt': datetime.now(),
                'resultJson': None,
                'error': None,
                'rawFileUrl': None
            }
            # Store in shared memory
            MockPrisma._data[rfq_data['rfqId']] = rfq_data
            print(f"✅ Mock DB: Created RFQ {rfq_data['rfqId']} (total: {len(MockPrisma._data)})")
            return type('RFQ', (), rfq_data)()
        
        async def find_unique(self, where):
            rfq_id = where.get('rfqId')
            if rfq_id in MockPrisma._data:
                rfq_data = MockPrisma._data[rfq_id]
                return type('RFQ', (), rfq_data)()
            return None
        
        async def find_many(self, **kwargs):
            results = []
            for rfq_data in list(MockPrisma._data.values())[:50]:  # Limit to 50
                results.append(type('RFQ', (), rfq_data)())
            return results
        
        async def find_first(self):
            # Return a mock RFQ for health check
            return type('RFQ', (), {'rfqId': 'mock', 'status': 'mock'})()
        
        async def update(self, where, data):
            rfq_id = where.get('rfqId')
            if rfq_id in MockPrisma._data:
                # Update existing RFQ
                MockPrisma._data[rfq_id].update(data)
                MockPrisma._data[rfq_id]['updatedAt'] = datetime.now()
                print(f"✅ Mock DB: Updated RFQ {rfq_id} - status: {data.get('status', 'N/A')}")
                return type('RFQ', (), MockPrisma._data[rfq_id])()
            return None
        
        async def delete(self, where):
            rfq_id = where.get('rfqId')
            if rfq_id in MockPrisma._data:
                del MockPrisma._data[rfq_id]
                print(f"✅ Mock DB: Deleted RFQ {rfq_id}")
                return True
            return False
    
    Prisma = MockPrisma

# Initialize Prisma client (singleton for mock)
db = Prisma()


async def ensure_connected():
    """Ensure Prisma client is connected."""
    is_connected = getattr(db, "is_connected", None)
    if callable(is_connected):
        if not db.is_connected():
            await db.connect()
        return
    await db.connect()


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
    await ensure_connected()
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
    await ensure_connected()
    rfq = await db.rfq.find_unique(where={"rfqId": rfq_id})
    return _rfq_to_dict(rfq) if rfq else None


async def list_rfqs(limit: int = 50, status: Optional[str] = None) -> List[Dict[str, Any]]:
    """List RFQs with optional status filter."""
    await ensure_connected()
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
    await ensure_connected()
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
    await ensure_connected()
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
