from fastapi import APIRouter, File, UploadFile, HTTPException
from typing import Optional
import os
import threading
import uuid

from app.core.rfq_store import create_rfq
from app.tasks.pipeline_tasks import process_rfq_pipeline

router = APIRouter(tags=["ingestion"])


@router.post("/ingest/upload")
async def upload_rfq(file: UploadFile = File(...)):
    """
    Upload an RFQ file (image, PDF, docx, etc.).
    Returns rfq_id and starts the processing pipeline.
    """
    try:
        rfq_id = str(uuid.uuid4())

        # Save file to storage (sanitize filename to prevent path traversal)
        storage_dir = os.getenv("STORAGE_PATH", "storage")
        os.makedirs(storage_dir, exist_ok=True)
        safe_name = os.path.basename(file.filename) if file.filename else "upload.bin"
        if not safe_name or safe_name in (".", ".."):
            safe_name = "upload.bin"
        file_path = os.path.join(storage_dir, f"{rfq_id}_{safe_name}")
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        # Try to create RFQ record in DB; if DB not available, proceed without failing the request
        db_ok = True
        try:
            create_rfq(
                rfq_id=rfq_id,
                source_channel="api",
                file_type=file.filename.rsplit(".", 1)[-1].lower() if file.filename and "." in file.filename else None,
                file_path=file_path,
                sender_contact=None,
            )
        except Exception as exc:
            # Log and continue — background pipeline will handle failures and update DB when available
            print(f"⚠️  Failed to create RFQ record: {exc}")
            db_ok = False

        if hasattr(process_rfq_pipeline, "delay"):
            process_rfq_pipeline.delay(rfq_id, file_path=file_path, source_channel="api")
        else:
            threading.Thread(
                target=process_rfq_pipeline,
                args=(rfq_id,),
                kwargs={"file_path": file_path, "source_channel": "api"},
                daemon=True
            ).start()

        # Return accepted even if DB was unavailable — caller can poll or check logs
        resp = {
            "rfq_id": rfq_id,
            "filename": file.filename,
            "status": "received",
            "db_record_created": db_ok,
            "message": "RFQ uploaded successfully. Processing will begin shortly."
        }
        return resp
    except Exception as exc:
        import traceback
        error_detail = f"{str(exc)}"
        traceback.print_exc()
        print(f"❌ Upload endpoint error: {error_detail}")
        return {
            "status": "error",
            "error": error_detail,
            "message": "File upload failed. Check server logs for details."
        }


@router.post("/ingest/text")
async def ingest_text(text: str, sender_contact: Optional[str] = None):
    """
    Ingest raw text RFQ (from WhatsApp, email, etc.).
    """
    rfq_id = str(uuid.uuid4())

    create_rfq(
        rfq_id=rfq_id,
        source_channel="api",
        file_type="text",
        raw_text=text,
        sender_contact=sender_contact
    )

    if hasattr(process_rfq_pipeline, "delay"):
        process_rfq_pipeline.delay(
            rfq_id,
            raw_text=text,
            sender_contact=sender_contact,
            source_channel="api"
        )
    else:
        threading.Thread(
            target=process_rfq_pipeline,
            args=(rfq_id,),
            kwargs={"raw_text": text, "sender_contact": sender_contact, "source_channel": "api"},
            daemon=True
        ).start()

    return {
        "rfq_id": rfq_id,
        "status": "received",
        "message": "Text RFQ received. Processing will begin shortly."
    }
