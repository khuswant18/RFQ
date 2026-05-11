from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse
import os
import uuid

# Mock data for testing
MOCK_RFQS = [
    {
        "rfq_id": "test-001",
        "status": "quoted",
        "source_channel": "whatsapp",
        "sender_contact": "+919999999999",
        "items": ["12mm Sariya Fe500 10 ton"],
        "total_amount": 680000,
        "created_at": "2024-05-10T10:00:00"
    },
    {
        "rfq_id": "test-002", 
        "status": "processing",
        "source_channel": "email",
        "sender_contact": "buyer@example.com",
        "items": ["8mm TMT Bar 5 ton", "10mm TMT Bar 3 ton"],
        "total_amount": None,
        "created_at": "2024-05-10T11:30:00"
    },
    {
        "rfq_id": "test-003",
        "status": "failed",
        "source_channel": "api",
        "sender_contact": None,
        "items": ["Invalid grade Fe999"],
        "total_amount": None,
        "created_at": "2024-05-10T09:15:00"
    }
]

# In-memory storage
rfqs = {}
for rfq in MOCK_RFQS:
    rfqs[rfq["rfq_id"]] = rfq

app = FastAPI()

@app.get("/api/v1/rfq/{rfq_id}")
async def get_rfq(rfq_id: str):
    if rfq_id not in rfqs:
        raise HTTPException(status_code=404, detail="RFQ not found")
    return rfqs[rfq_id]

@app.post("/api/v1/rfq/upload")
async def upload_rfq(file: UploadFile = File(...)):
    rfq_id = str(uuid.uuid4())
    rfqs[rfq_id] = {
        "rfq_id": rfq_id,
        "status": "received",
        "filename": file.filename,
        "message": "RFQ uploaded successfully."
    }
    return rfqs[rfq_id]

@app.get("/api/v1/rfq/{rfq_id}/status")
async def get_rfq_status(rfq_id: str):
    if rfq_id not in rfqs:
        raise HTTPException(status_code=404, detail="RFQ not found")
    return {"rfq_id": rfq_id, "status": rfqs[rfq_id]["status"]}
