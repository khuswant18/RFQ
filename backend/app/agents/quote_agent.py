"""Quote Agent - Assembles all pipeline results into a professional PDF quote."""
import os
from datetime import datetime, timedelta
from typing import List, Optional

from app.core.groq_client import GroqClient
from app.models.rfq import QuoteContext


class QuoteAgent:
    """
    Quote Agent: Assembles all pipeline results into a professional PDF quote.
    Falls back to a simple HTML file if WeasyPrint is not installed.
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
        return f"QT-{rfq_id}"

    def generate_pdf(self, context: QuoteContext, rfq_id: str) -> str:
        """Generate a PDF quote for an RFQ."""
        import pathlib

        # Setup Jinja2 environment — templates live inside app/templates
        base_dir = pathlib.Path(__file__).resolve().parent.parent
        env = None
        try:
            from jinja2 import Environment, FileSystemLoader
            env = Environment(loader=FileSystemLoader(str(base_dir / "templates")))
            template = env.get_template("quote_template.html")
            html_content = template.render(**context.dict())
        except Exception as e:
            print(f"Jinja2 template rendering failed: {e}. Using inline HTML.")
            html_content = self._inline_template(context)

        # Generate PDF file path
        pdf_path = f"storage/quotes/QT-{rfq_id}.pdf"
        os.makedirs(os.path.dirname(pdf_path), exist_ok=True)

        # Try WeasyPrint first, fall back to HTML-only
        try:
            from weasyprint import HTML as WeasyHTML
            WeasyHTML(string=html_content).write_pdf(pdf_path)
        except ImportError:
            print("WeasyPrint not installed. Saving HTML as fallback.")
            html_path = f"storage/quotes/QT-{rfq_id}.html"
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            # Create a placeholder PDF
            self._create_placeholder_pdf(pdf_path, context)

        return pdf_path

    def _inline_template(self, context: QuoteContext) -> str:
        """Generate a simple inline HTML template as fallback."""
        items_html = ""
        for i, item in enumerate(context.line_items, 1):
            items_html += f"""
            <tr>
                <td>{i}</td>
                <td>{item.get('material', '')}</td>
                <td>{item.get('grade', '')}</td>
                <td>{item.get('dimensions', '')}</td>
                <td>{item.get('quantity', '')}</td>
                <td>₹{item.get('rate', 0):,.2f}</td>
                <td>₹{item.get('amount', 0):,.2f}</td>
            </tr>
            """

        return f"""
        <!DOCTYPE html>
        <html>
        <head><title>Quote {context.quote_number}</title></head>
        <body>
            <h1>{context.company_name}</h1>
            <h2>Quote #{context.quote_number}</h2>
            <p>Date: {context.quote_date} | Valid Until: {context.valid_until}</p>
            <h3>Line Items</h3>
            <table border="1">
                <tr><th>#</th><th>Material</th><th>Grade</th><th>Dimensions</th><th>Qty</th><th>Rate</th><th>Amount</th></tr>
                {items_html}
            </table>
            <p>Subtotal: ₹{context.subtotal:,.2f}</p>
            <p>GST ({context.gst_type}): ₹{context.gst_amount:,.2f}</p>
            <p><strong>Grand Total: ₹{context.grand_total:,.2f}</strong></p>
            <p>{context.notes}</p>
        </body>
        </html>
        """

    def _create_placeholder_pdf(self, pdf_path: str, context: QuoteContext):
        """Create a minimal placeholder PDF if WeasyPrint is not available."""
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.pdfgen import canvas
            from reportlab.lib.units import mm
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont

            c = canvas.Canvas(pdf_path, pagesize=A4)
            width, height = A4

            # Company name
            c.setFont("Helvetica-Bold", 16)
            c.drawString(20 * mm, height - 20 * mm, context.company_name)

            # Quote info
            c.setFont("Helvetica", 12)
            c.drawString(20 * mm, height - 30 * mm, f"Quote #: {context.quote_number}")
            c.drawString(20 * mm, height - 40 * mm, f"Date: {context.quote_date}")
            c.drawString(20 * mm, height - 50 * mm, f"Valid Until: {context.valid_until}")

            # Totals
            y = height - 80 * mm
            c.drawString(20 * mm, y, f"Subtotal: ₹{context.subtotal:,.2f}")
            c.drawString(20 * mm, y - 10 * mm, f"GST ({context.gst_type}): ₹{context.gst_amount:,.2f}")
            c.setFont("Helvetica-Bold", 14)
            c.drawString(20 * mm, y - 30 * mm, f"Grand Total: ₹{context.grand_total:,.2f}")

            c.save()
        except ImportError:
            # Just touch the file as a placeholder
            open(pdf_path, "w").close()

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
                  buyer_contact: str, buyer_location: str,
                  logistics_total: float = 0.0, margin_amount: float = 0.0,
                  margin_percent: float = 0.0, gst_type: str = "CGST+SGST",
                  gst_amount: float = None) -> str:
        """Run quote generation."""
        # Generate quote number
        quote_number = self.generate_quote_number(rfq_id)

        # Create context
        effective_gst_amount = gst_amount if gst_amount is not None else (total * 0.18)
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
            logistics_total=logistics_total,
            margin_amount=margin_amount,
            margin_percent=margin_percent,
            gst_type=gst_type,
            gst_amount=effective_gst_amount,
            grand_total=total + effective_gst_amount,
            is_codes_referenced=["IS 1786:2008", "IS 2062:2011"],
            notes="Price valid for 24 hours. GST extra as applicable.",
            bank_details="Bank: SBI, Acc: 1234567890, IFSC: SBIN0001234"
        )

        # Generate PDF
        pdf_path = self.generate_pdf(context, rfq_id)

        # Generate WhatsApp summary
        quote_summary = {
            "quote_number": quote_number,
            "total": total,
            "valid_until": context.valid_until
        }
        whatsapp_summary = self.generate_whatsapp_summary(quote_summary)

        return pdf_path
