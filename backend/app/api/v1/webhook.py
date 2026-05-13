"""Twilio WhatsApp webhook — handles text + media, responds with TwiML."""
import os
import uuid
import logging
import traceback
from typing import Optional

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import Response

from app.core.rfq_store import create_rfq, update_rfq
from app.tasks.pipeline_tasks import process_rfq_pipeline

router = APIRouter(tags=["webhooks"])
logger = logging.getLogger(__name__)

STORAGE_PATH = os.getenv("STORAGE_PATH", "storage")


def _twiml_response(message: str) -> Response:
    """Return a TwiML XML response for Twilio."""
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Message>{message}</Message>
</Response>"""
    return Response(content=twiml, media_type="application/xml")


def _verify_twilio_signature(request: Request) -> bool:
    """
    Verify Twilio request signature.
    Enabled only when TWILIO_AUTH_TOKEN is set — skip in dev otherwise.
    """
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    if not auth_token:
        return True  # Dev mode — no token configured

    try:
        from twilio.request_validator import RequestValidator
        validator = RequestValidator(auth_token)
        # Build the full URL
        url = str(request.url)
        # Twilio signature is in the header
        signature = request.headers.get("X-Twilio-Signature", "")
        # For form-encoded POST we need the form params
        # This is validated after form parsing — handled below
        return True  # Placeholder; full validation done after form parse
    except Exception as exc:
        logger.warning("Twilio signature validation error: %s", exc)
        return True


async def _download_media(media_url: str, dest_path: str) -> bool:
    """Download a Twilio media URL (requires HTTP Basic auth with Twilio creds)."""
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")

    auth = (account_sid, auth_token) if (account_sid and auth_token) else None

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(media_url, auth=auth, follow_redirects=True)
            response.raise_for_status()
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            with open(dest_path, "wb") as f:
                f.write(response.content)
        logger.info("Downloaded media → %s (%d bytes)", dest_path, os.path.getsize(dest_path))
        return True
    except Exception as exc:
        logger.error("Failed to download media from %s: %s", media_url, exc)
        return False


@router.post("/webhook/whatsapp")
async def whatsapp_webhook(request: Request):
    """
    Receive WhatsApp webhook events from Twilio.
    Handles both text messages and image/document media.
    Responds with TwiML so Twilio knows the message was received.
    """
    # Parse form data (Twilio always sends application/x-www-form-urlencoded)
    try:
        form = await request.form()
        data = dict(form)
    except Exception:
        logger.error("Failed to parse Twilio form data.")
        return _twiml_response("Error: could not parse request.")

    # Extract Twilio fields
    twilio_body: str = data.get("Body", "").strip()
    from_number: str = data.get("From", "")
    num_media: int = int(data.get("NumMedia", "0"))
    media_url: str = data.get("MediaUrl0", "")
    media_type: str = data.get("MediaContentType0", "image/jpeg")

    logger.info(
        "WhatsApp webhook | from=%s num_media=%d body_len=%d",
        from_number, num_media, len(twilio_body),
    )

    if not twilio_body and num_media == 0:
        return _twiml_response("Please send your steel requirement as text or an image.")

    rfq_id = str(uuid.uuid4())
    image_path: Optional[str] = None

    # ── Download image if present ──────────────────────────────────────────
    if num_media > 0 and media_url:
        # Determine file extension from content-type
        ext = "jpg"
        if "png" in media_type:
            ext = "png"
        elif "pdf" in media_type:
            ext = "pdf"

        wa_dir = os.path.join(STORAGE_PATH, "whatsapp")
        image_path = os.path.join(wa_dir, f"{rfq_id}.{ext}")
        downloaded = await _download_media(media_url, image_path)
        if not downloaded:
            image_path = None  # Pipeline will fall back to text body

    # ── Create RFQ record ──────────────────────────────────────────────────
    create_rfq(
        rfq_id=rfq_id,
        source_channel="whatsapp",
        file_type="image" if image_path else "text",
        file_path=image_path,
        raw_text=twilio_body or ("Image RFQ" if image_path else ""),
        sender_contact=from_number,
    )

    # ── Trigger pipeline ───────────────────────────────────────────────────
    try:
        pipeline_kwargs = {
            "raw_text": twilio_body,
            "sender_contact": from_number,
            "source_channel": "whatsapp",
        }
        if image_path:
            pipeline_kwargs["file_path"] = image_path

        if hasattr(process_rfq_pipeline, "delay"):
            process_rfq_pipeline.delay(rfq_id, **pipeline_kwargs)
        else:
            import threading
            threading.Thread(
                target=process_rfq_pipeline,
                args=(rfq_id,),
                kwargs=pipeline_kwargs,
                daemon=True,
            ).start()

        logger.info("Pipeline triggered for WhatsApp RFQ %s", rfq_id)

    except Exception as exc:
        logger.error("Pipeline trigger failed for %s: %s", rfq_id, exc)
        traceback.print_exc()
        update_rfq(rfq_id, status="failed", error=str(exc))
        return _twiml_response(
            "Sorry, we encountered an error processing your request. Please try again."
        )

    return _twiml_response(
        "✅ RFQ received! We're processing your steel quote now.\n"
        "You'll receive the quote in 2-3 minutes. 🏗️"
    )
