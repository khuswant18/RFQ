"""Communication Agent - Sends outputs to correct channels."""
import os
from typing import Optional

from app.core.groq_client import GroqClient
from app.models.rfq import CommunicationResult


class CommunicationAgent:
    """Communication Agent: Sends PDF quotes to WhatsApp/Email,
    creates dashboard tasks, and updates RFQ status.
    All methods are synchronous for Celery compatibility."""

    def __init__(self):
        self.groq = GroqClient()
        try:
            from twilio.rest import Client as TwilioClient
            sid = os.getenv("TWILIO_ACCOUNT_SID", "")
            token = os.getenv("TWILIO_AUTH_TOKEN", "")
            if sid and token:
                self.twilio_client = TwilioClient(sid, token)
            else:
                self.twilio_client = None
        except (ImportError, Exception):
            self.twilio_client = None

    def send_whatsapp(self, to: str, text: str, media_url: Optional[str] = None) -> bool:
        if not self.twilio_client:
            print("Twilio not configured. Cannot send WhatsApp message.")
            return False
        try:
            msg_kwargs = {
                "from_": os.getenv("TWILIO_WHATSAPP_NUMBER"),
                "body": text,
                "to": to,
            }
            if media_url:
                msg_kwargs["media_url"] = [media_url]
            self.twilio_client.messages.create(**msg_kwargs)
            return True
        except Exception as e:
            print(f"Failed to send WhatsApp: {e}")
            return False

    def send_email(self, to: str, subject: str, body: str,
                   attachment: Optional[str] = None) -> bool:
        print("Email service not configured. Cannot send email.")
        return False

    def create_task(self, title: str, rfq_id: str, priority: str = "normal") -> bool:
        print("Task system not configured. Skipping task creation.")
        return False

    def run(self, rfq_id: str, pdf_path: str, channel: str,
            recipient: str, summary: str) -> CommunicationResult:
        """Run communication dispatch (synchronous)."""
        # Build public URL for PDF (Twilio needs a publicly accessible URL)
        base_url = os.getenv("BACKEND_PUBLIC_URL", "http://localhost:8000")
        public_pdf_url = f"{base_url}/api/v1/rfq/{rfq_id}/quote"

        success = False
        if channel == "whatsapp" and recipient:
            success = self.send_whatsapp(recipient, summary, public_pdf_url)
        elif channel == "email" and recipient:
            success = self.send_email(recipient, f"Quote: {rfq_id[:8]}", summary, pdf_path)
        else:
            # Dashboard-only — no external send needed
            success = True

        # Create internal task
        self.create_task(
            title=f"Verify inventory for RFQ {rfq_id[:8]}",
            rfq_id=rfq_id,
            priority="high"
        )

        return CommunicationResult(
            sent=success,
            channel=channel or "dashboard",
            error=None if success else "Failed to send message"
        )
