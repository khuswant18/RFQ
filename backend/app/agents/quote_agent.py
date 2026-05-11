"""Quote Agent - Assembles all pipeline results into a professional PDF quote."""
import os
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List, Optional

from app.core.groq_client import GroqClient
from app.models.rfq import QuoteContext, LineItem, CostBreakdown, GSTResult


class QuoteAgent:
    """
    Quote Agent: Assembles all pipeline results into a professional PDF quote.
    """
    
    def __init__(self):
        self.groq = GroqClient()
    
    WHATSAPP_SUMMARY_PROMPT = """Generate a short, professional WhatsApp message (under 200 words) in English 
summarizing the quote. Tone: respectful, business-like.
Include: grade, quantity, final price, validity period.
End with: "Quote PDF attached. Valid for 24 hours."
Do not include detailed breakdowns — just the total.

Quote data: {quote_summary}
"""

    def generate_quote_number(self, rfq_id: str) -> str:
        """Generate a quote number."""
        date_str = datetime.now().strftime("%Y%m%d")
        return f"QT-{rfq_id[:8].upper()}-{date_str}"
    
    def generate_pdf(self, context: QuoteContext) -> str:
        """Generate a PDF quote for an RFQ."""
        from jinja2 import Environment, FileSystemLoader
        from weasyprint import HTML
        
        # Setup Jinja2 environment
        env = Environment(loader=FileSystemLoader("app/templates"))
        template = env.get_template("quote_template.html")
        
        # Generate HTML content
        html_content = template.render(**context.dict())
        
        # Generate PDF
        pdf_path = f"storage/quotes/{context.quote_number}.pdf"
        os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
        HTML(string=html_content).write_pdf(pdf_path)
        
        return pdf_path
    
    def generate_whatsapp_summary(self, quote_summary: dict) -> str:
        """Generate a summary message for WhatsApp."""
        prompt = self.WHATSAPP_SUMMARY_PROMPT.format(quote_summary=quote_summary)
        
        result = self.groq.call(
            system_prompt="You are a professional steel sales assistant.",
            user_prompt=prompt,
            model="llama3-8b-8192",
            temperature=0.7
        )
        
        return result
    
    async def run(self, rfq_id: str, line_items: list, total: float, 
                  buyer_contact: str, buyer_location: str) -> str:
        """Run quote generation."""
        # Generate quote number
        quote_number = self.generate_quote_number(rfq_id)
        
        # Create context
        context = QuoteContext(
            company_name=os.getenv("COMPANY_NAME", "Demo Steel Works"),
            company_gstin=os.getenv("COMPANY_GSTIN", "24XXXXX1234Z5"),
            quote_number=quote_number,
            quote_date=datetime.now().strftime("%Y-%m-%d"),
            valid_until=(datetime.now() + timedelta(hours=24)).strftime("%Y-%m-%d"),
            buyer_contact=buyer_contact,
            buyer_location=buyer_location,
            line_items=line_items,
            subtotal=total,
            logistics_total=0,  # Would be calculated from item costs
            margin_amount=0,
            gst_type="CGST+SGST",
            gst_amount=total * 0.18,
            grand_total=total * 1.18,
            is_codes_referenced=["IS 1786:2008", "IS 2062:2011"],
            notes="Price valid for 24 hours. GST extra as applicable.",
            bank_details="Bank: SBI, Acc: 1234567890, IFSC: SBIN0001234"
        )
        
        # Generate PDF
        pdf_path = self.generate_pdf(context)
        
        # Generate WhatsApp summary
        quote_summary = {
            "quote_number": quote_number,
            "total": total,
            "valid_until": context.valid_until
        }
        whatsapp_summary = self.generate_whatsapp_summary(quote_summary)
        
        return pdf_path
