"""Twilio WhatsApp webhook handlers."""
from fastapi import APIRouter, Request, Response
import os
import uuid
import traceback

import httpx
from twilio.request_validator import RequestValidator

from app.core.rfq_store import create_rfq, update_rfq
from app.tasks.pipeline_tasks import process_rfq_pipeline

router = APIRouter(tags=["webhooks"])


def _verify_twilio_signature(request: Request, params: dict) -> bool:
    """Verify Twilio request signature."""
    auth_token = os.getenv("TWILIO_AUTH_TOKEN", "")
    signature = request.headers.get("X-Twilio-Signature", "")
    if not auth_token or not signature:
        return False

    validator = RequestValidator(auth_token)
    url = str(request.url)
    return validator.validate(url, params, signature)


def _twiml_response(message: str) -> Response:
    xml = f"<?xml version=\"1.0\" encoding=\"UTF-8\"?><Response><Message>{message}</Message></Response>"
    return Response(content=xml, media_type="application/xml")


@router.post("/webhook/whatsapp")
async def whatsapp_webhook(request: Request):
    """
    Receive WhatsApp webhook events from Twilio.
    Processes incoming text and media messages and triggers RFQ pipeline.
    """
    try:
        if request.headers.get("content-type", "").startswith("application/json"):
            data = await request.json()
        else:
            form = await request.form()
            data = dict(form)
    except Exception:
        return _twiml_response("Invalid request format.")

    if not _verify_twilio_signature(request, data):
        return Response(status_code=403, content="Invalid Twilio signature")

    # Extract Twilio fields
    twilio_body = data.get("Body", "").strip()
    from_number = data.get("From", "")
    media_url = data.get("MediaUrl0", "")
    media_type = data.get("MediaContentType0", "")
    num_media = int(data.get("NumMedia", "0"))

    if not twilio_body and num_media == 0:
        return _twiml_response("No content to process.")

    # Create RFQ
    rfq_id = str(uuid.uuid4())
    storage_dir = os.getenv("STORAGE_PATH", "storage")
    whatsapp_dir = os.path.join(storage_dir, "whatsapp")
    os.makedirs(whatsapp_dir, exist_ok=True)

    file_path = None
    file_type = "text"
    if num_media > 0 and media_url:
        file_type = "image"

    create_rfq(
        rfq_id=rfq_id,
        source_channel="whatsapp",
        file_type=file_type,
        file_path=None,
        raw_text=twilio_body or "Image RFQ",
        sender_contact=from_number
    )

    if num_media > 0 and media_url:
        ext = ".jpg"
        if media_type == "image/png":
            ext = ".png"
        elif media_type == "image/jpeg":
            ext = ".jpg"
        elif media_type == "application/pdf":
            ext = ".pdf"

        file_path = os.path.join(whatsapp_dir, f"{rfq_id}{ext}")
        try:
            sid = os.getenv("TWILIO_ACCOUNT_SID", "")
            token = os.getenv("TWILIO_AUTH_TOKEN", "")
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(media_url, auth=(sid, token))
                response.raise_for_status()
                with open(file_path, "wb") as f:
                    f.write(response.content)
            file_type = ext.lstrip(".")
            update_rfq(rfq_id, file_type=file_type, file_path=file_path)
        except Exception as e:
            update_rfq(rfq_id, status="failed", error=f"Media download failed: {e}")
            return _twiml_response("Failed to download media.")

    # Trigger pipeline (async)
    try:
        task_kwargs = {
            "sender_contact": from_number,
            "source_channel": "whatsapp",
        }
        if file_path:
            task_kwargs["file_path"] = file_path
        else:
            task_kwargs["raw_text"] = twilio_body

        if hasattr(process_rfq_pipeline, "delay"):
            process_rfq_pipeline.delay(rfq_id, **task_kwargs)
        else:
            import threading
            threading.Thread(
                target=process_rfq_pipeline,
                args=(rfq_id,),
                kwargs=task_kwargs,
                daemon=True
            ).start()
    except Exception as e:
        print(f"Error triggering pipeline for WhatsApp: {e}")
        traceback.print_exc()
        update_rfq(rfq_id, status="failed", error=str(e))
        return _twiml_response("Pipeline trigger failed.")

    return _twiml_response("RFQ received! Processing your quote...")
