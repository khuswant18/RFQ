"""Twilio WhatsApp webhook handlers."""
from fastapi import APIRouter, Request, Form, HTTPException
from typing import Optional
import os
import uuid
import traceback

from app.core.rfq_store import create_rfq, update_rfq
from app.tasks.pipeline_tasks import process_rfq_pipeline

router = APIRouter(tags=["webhooks"])


def _verify_twilio_signature(request: Request) -> bool:
    """Verify Twilio request signature (placeholder - implement fully in production)."""
    # In production, validate X-Twilio-Signature header against raw body
    return True


@router.post("/webhook/whatsapp")
async def whatsapp_webhook(request: Request):
    """
    Receive WhatsApp webhook events from Twilio.
    Processes incoming text and media messages and triggers RFQ pipeline.
    """
    try:
        # Twilio sends form data, not JSON
        if request.headers.get("content-type", "").startswith("application/json"):
            data = await request.json()
        else:
            # Parse form data
            form = await request.form()
            data = dict(form)
    except Exception:
        return {"status": "error", "message": "Invalid request format"}

    # Extract Twilio fields
    twilio_body = data.get("Body", "").strip()
    from_number = data.get("From", "")
    media_url = data.get("MediaUrl0", "")
    num_media = int(data.get("NumMedia", "0"))

    if not twilio_body and num_media == 0:
        return {"status": "ignored", "message": "No content to process"}

    # Create RFQ
    rfq_id = str(uuid.uuid4())
    create_rfq(
        rfq_id=rfq_id,
        source_channel="whatsapp",
        file_type="text" if not media_url else "image",
        raw_text=twilio_body or "Image RFQ",
        sender_contact=from_number
    )

    # Trigger pipeline (async)
    try:
        if hasattr(process_rfq_pipeline, "delay"):
            process_rfq_pipeline.delay(
                rfq_id,
                raw_text=twilio_body,
                sender_contact=from_number,
                source_channel="whatsapp"
            )
        else:
            import threading
            threading.Thread(
                target=process_rfq_pipeline,
                args=(rfq_id,),
                kwargs={
                    "raw_text": twilio_body,
                    "sender_contact": from_number,
                    "source_channel": "whatsapp"
                },
                daemon=True
            ).start()
    except Exception as e:
        print(f"Error triggering pipeline for WhatsApp: {e}")
        traceback.print_exc()
        update_rfq(rfq_id, status="failed", error=str(e))
        return {"status": "failed", "message": "Pipeline trigger failed"}

    return {
        "status": "received",
        "rfq_id": rfq_id,
        "message": "WhatsApp message received. RFQ processing started."
    }
