"""Communication Agent - Sends outputs to correct channels."""
import os
from typing import Optional

from app.core.groq_client import GroqClient
from app.models.rfq import CommunicationResult


class CommunicationAgent:
    """
    Communication Agent: Sends PDF quotes to WhatsApp/Email,
    creates dashboard tasks, and updates RFQ status.
    """
    
    def __init__(self):
        self.groq = GroqClient()
        # Import twilio only if configured
        try:
            from twilio.rest import Client
            self.twilio_client = Client(
                os.getenv("TWILIO_ACCOUNT_SID"),
                os.getenv("TWILIO_AUTH_TOKEN")
            )
        except ImportError:
            self.twilio_client = None
    
    def send_whatsapp(self, to: str, text: str, media_url: Optional[str] = None) -> bool:
        """Send a WhatsApp message with optional media."""
        if not self.twilio_client:
            print("Twilio not configured. Mock sending WhatsApp message.")
            return True
        
        try:
            message = self.twilio_client.messages.create(
                from_=os.getenv("TWILIO_WHATSAPP_NUMBER"),
                body=text,
                to=to,
                media_url=[media_url] if media_url else None
            )
            return True
        except Exception as e:
            print(f"Failed to send WhatsApp message: {e}")
            return False
    
    def send_email(self, to: str, subject: str, body: str, 
                   attachment: Optional[str] = None) -> bool:
        """Send an email with optional attachment."""
        # Implement email sending logic here (e.g., using smtplib)
        print(f"Mock sending email to {to}: {subject}")
        return True
    
    def create_task(self, title: str, rfq_id: str, priority: str = "normal") -> bool:
        """Create an internal task in the task store."""
        # Implement task creation logic here
        print(f"Mock creating task: {title} (RFQ: {rfq_id})")
        return True
    
    async def run(self, rfq_id: str, pdf_path: str, channel: str,
                  recipient: str, summary: str) -> CommunicationResult:
        """Run communication dispatch."""
        
        if channel == "whatsapp":
            success = self.send_whatsapp(recipient, summary, pdf_path)
        elif channel == "email":
            success = self.send_email(recipient, f"Quote: {rfq_id[:8]}", summary, pdf_path)
        else:
            success = False
        
        # Create internal task
        self.create_task(
            title=f"Verify inventory for RFQ {rfq_id}",
            rfq_id=rfq_id,
            priority="high"
        )
        
        return CommunicationResult(
            sent=success,
            channel=channel,
            error=None if success else "Failed to send message"
        )
