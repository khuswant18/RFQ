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
            raise RuntimeError("WeasyPrint is required to generate PDFs.")
        except Exception as e:
            raise RuntimeError(f"WeasyPrint failed: {e}")
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


    def generate_whatsapp_summary(self, quote_summary: dict) -> str:
        # Simple template-based summary (skip LLM to avoid API issues)
        return f"""📋 Quote #{quote_summary.get('quote_number', 'N/A')}

💰 Total: ₹{quote_summary.get('grand_total', 0):,.2f} (incl. GST)

✅ Valid until: {quote_summary.get('valid_until', '7 days')}

Thank you for your inquiry!"""

    def run(self, rfq_id: str, line_items: list, total: float,
            buyer_contact: str, buyer_location: str,
            logistics_total: float = 0.0, margin_amount: float = 0.0,
            margin_percent: float = 0.0, gst_type: str = "CGST+SGST",
            gst_amount: float = None) -> dict:
        """Run quote generation (synchronous). Returns dict with pdf_path and summary."""
        quote_number = self.generate_quote_number(rfq_id)
        effective_gst = gst_amount if gst_amount is not None else (total * 0.18)
        company_name = os.getenv("COMPANY_NAME")
        company_gstin = os.getenv("COMPANY_GSTIN")
        if not company_name or not company_gstin:
            raise RuntimeError("COMPANY_NAME and COMPANY_GSTIN must be set.")

        context = QuoteContext(
            company_name=company_name,
            company_gstin=company_gstin,
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
            bank_details=os.getenv("BANK_DETAILS", "")
        )
        pdf_path = self.generate_pdf(context, rfq_id)
        summary = self.generate_whatsapp_summary({
            "quote_number": quote_number, "total": total,
            "grand_total": round(total + effective_gst, 2),
            "valid_until": context.valid_until
        })
        return {"pdf_path": pdf_path, "quote_number": quote_number,
                "whatsapp_summary": summary, "grand_total": context.grand_total}
