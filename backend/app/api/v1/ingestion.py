from fastapi import APIRouter, File, UploadFile, HTTPException
from typing import Optional
import uuid

router = APIRouter(tags=["ingestion"])


@router.post("/ingest/upload")
async def upload_rfq(file: UploadFile = File(...)):
    """
    Upload an RFQ file (image, PDF, docx, etc.).
    Returns rfq_id and starts the processing pipeline.
    """
    rfq_id = str(uuid.uuid4())
    
    # Save file to storage
    file_path = f"storage/{rfq_id}_{file.filename}"
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)
    
    # TODO: Trigger Celery task for pipeline processing
    
    return {
        "rfq_id": rfq_id,
        "filename": file.filename,
        "status": "received",
        "message": "RFQ uploaded successfully. Processing will begin shortly."
    }


@router.post("/ingest/text")
async def ingest_text(text: str, sender_contact: Optional[str] = None):
    """
    Ingest raw text RFQ (from WhatsApp, email, etc.).
    """
    rfq_id = str(uuid.uuid4())
    
    # TODO: Trigger Celery task for pipeline processing
    
    return {
        "rfq_id": rfq_id,
        "status": "received",
        "message": "Text RFQ received. Processing will begin shortly."
    }
