"""Quote Agent - Assembles all pipeline results into a professional PDF quote."""
import os
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from app.core.groq_client import GroqClient
from app.models.rfq import QuoteContext


class QuoteAgent:
    """Quote Agent: Assembles pipeline results into a professional PDF quote.
    All methods are synchronous for Celery compatibility."""

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
        date_str = datetime.now().strftime("%Y%m%d")
        return f"QT-{rfq_id[:8].upper()}-{date_str}"

    def generate_pdf(self, context: QuoteContext, rfq_id: str) -> str:
        import pathlib
        base_dir = pathlib.Path(__file__).resolve().parent.parent
        try:
            from jinja2 import Environment, FileSystemLoader
            env = Environment(loader=FileSystemLoader(str(base_dir / "templates")))
            template = env.get_template("quote_template.html")
            html_content = template.render(**context.model_dump())
        except Exception as e:
            print(f"Jinja2 template rendering failed: {e}. Using inline HTML.")
            html_content = self._inline_template(context)

        pdf_path = f"storage/quotes/QT-{rfq_id}.pdf"
        os.makedirs(os.path.dirname(pdf_path), exist_ok=True)

        try:
            from weasyprint import HTML as WeasyHTML
            WeasyHTML(string=html_content).write_pdf(pdf_path)
        except ImportError:
            html_path = f"storage/quotes/QT-{rfq_id}.html"
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            self._create_placeholder_pdf(pdf_path, context)
        except Exception as e:
            print(f"WeasyPrint failed: {e}. Using fallback.")
            self._create_placeholder_pdf(pdf_path, context)
        return pdf_path

    def _inline_template(self, context: QuoteContext) -> str:
        items_rows = ""
        for i, item in enumerate(context.line_items, 1):
            items_rows += f"<tr><td>{i}</td><td>{item.get('material','')}</td><td>{item.get('grade','')}</td><td>{item.get('dimensions','')}</td><td>{item.get('quantity','')}</td><td>₹{item.get('rate',0):,.2f}</td><td>₹{item.get('amount',0):,.2f}</td></tr>"
        return f"""<!DOCTYPE html><html><head><title>Quote {context.quote_number}</title>
<style>body{{font-family:Helvetica,Arial,sans-serif;padding:40px;color:#333}}h1{{color:#2c5aa0}}table{{width:100%;border-collapse:collapse;margin:20px 0}}th,td{{border:1px solid #ddd;padding:10px;text-align:left}}th{{background:#f8f9fa;color:#2c5aa0}}.total{{font-size:18px;font-weight:bold;color:#2c5aa0}}</style></head>
<body><h1>{context.company_name}</h1><p>GSTIN: {context.company_gstin}</p>
<h2>Quote #{context.quote_number}</h2><p>Date: {context.quote_date} | Valid Until: {context.valid_until}</p>
<h3>Buyer: {context.buyer_contact} — {context.buyer_location}</h3>
<table><tr><th>#</th><th>Material</th><th>Grade</th><th>Dims</th><th>Qty</th><th>Rate</th><th>Amount</th></tr>{items_rows}</table>
<p>Subtotal: ₹{context.subtotal:,.2f}</p><p>Logistics: ₹{context.logistics_total:,.2f}</p>
<p>Margin ({context.margin_percent}%): ₹{context.margin_amount:,.2f}</p>
<p>GST ({context.gst_type}): ₹{context.gst_amount:,.2f}</p>
<p class="total">Grand Total: ₹{context.grand_total:,.2f}</p>
<p><em>{context.notes}</em></p></body></html>"""

    def _create_placeholder_pdf(self, pdf_path: str, context: QuoteContext):
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.pdfgen import canvas
            from reportlab.lib.units import mm
            c = canvas.Canvas(pdf_path, pagesize=A4)
            w, h = A4
            c.setFont("Helvetica-Bold", 16)
            c.drawString(20*mm, h-20*mm, context.company_name)
            c.setFont("Helvetica", 12)
            c.drawString(20*mm, h-30*mm, f"Quote #: {context.quote_number}")
            c.drawString(20*mm, h-40*mm, f"Date: {context.quote_date}")
            c.drawString(20*mm, h-50*mm, f"Valid Until: {context.valid_until}")
            y = h - 70*mm
            c.drawString(20*mm, y, f"Subtotal: ₹{context.subtotal:,.2f}")
            y -= 10*mm
            c.drawString(20*mm, y, f"GST ({context.gst_type}): ₹{context.gst_amount:,.2f}")
            y -= 15*mm
            c.setFont("Helvetica-Bold", 14)
            c.drawString(20*mm, y, f"Grand Total: ₹{context.grand_total:,.2f}")
            c.save()
        except ImportError:
            open(pdf_path, "w").close()

    def generate_whatsapp_summary(self, quote_summary: dict) -> str:
        prompt = self.WHATSAPP_SUMMARY_PROMPT.format(quote_summary=quote_summary)
        return self.groq.call(
            system_prompt="You are a professional steel sales assistant.",
            user_prompt=prompt, model="llama3-8b-8192", temperature=0.7
        )

    def run(self, rfq_id: str, line_items: list, total: float,
            buyer_contact: str, buyer_location: str,
            logistics_total: float = 0.0, margin_amount: float = 0.0,
            margin_percent: float = 0.0, gst_type: str = "CGST+SGST",
            gst_amount: float = None) -> dict:
        """Run quote generation (synchronous). Returns dict with pdf_path and summary."""
        quote_number = self.generate_quote_number(rfq_id)
        effective_gst = gst_amount if gst_amount is not None else (total * 0.18)
        context = QuoteContext(
            company_name=os.getenv("COMPANY_NAME", "Demo Steel Works"),
            company_gstin=os.getenv("COMPANY_GSTIN", "24XXXXX1234Z5"),
            quote_number=quote_number,
            quote_date=datetime.now().strftime("%Y-%m-%d"),
            valid_until=(datetime.now() + timedelta(hours=24)).strftime("%Y-%m-%d %H:%M"),
            buyer_contact=buyer_contact or "N/A",
            buyer_location=buyer_location or "N/A",
            line_items=line_items, subtotal=total,
            logistics_total=logistics_total, margin_amount=margin_amount,
            margin_percent=margin_percent, gst_type=gst_type,
            gst_amount=effective_gst,
            grand_total=round(total + effective_gst, 2),
            is_codes_referenced=["IS 1786:2008", "IS 2062:2011"],
            notes="Price valid for 24 hours. GST extra as applicable.",
            bank_details="Bank: SBI, Acc: 1234567890, IFSC: SBIN0001234"
        )
        pdf_path = self.generate_pdf(context, rfq_id)
        summary = self.generate_whatsapp_summary({
            "quote_number": quote_number, "total": total,
            "grand_total": round(total + effective_gst, 2),
            "valid_until": context.valid_until
        })
        return {"pdf_path": pdf_path, "quote_number": quote_number,
                "whatsapp_summary": summary, "grand_total": context.grand_total}
