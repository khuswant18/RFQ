"""Celery tasks for pipeline processing."""
try:
    from celery import Celery
    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False

    class Celery:  # type: ignore[no-redef]
        def __init__(self, *args, **kwargs):
            self.conf = type('conf', (), {'update': lambda self, **kw: None})()

    def celery_app_task(*args, **kwargs):
        def decorator(func):
            return func
        return decorator

import os
import asyncio
from pathlib import Path


# Celery configuration
celery_app = None
if CELERY_AVAILABLE:
    celery_app = Celery(
        "srip",
        broker=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        backend=os.getenv("REDIS_URL", "redis://localhost:6379/0")
    )

    celery_app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="Asia/Kolkata",
        enable_utc=True
    )
else:
    # Mock Celery app for when Celery is not installed
    class _MockCeleryApp:
        def __init__(self):
            self.conf = type('conf', (), {'update': lambda self, **kw: None})()
    celery_app = _MockCeleryApp()


def _run_pipeline(rfq_id: str, file_path: str = None, raw_text: str = None,
                  sender_contact: str = None, source_channel: str = "api"):
    """Process an RFQ through the full pipeline."""
    from app.core.rfq_store import update_rfq
    from app.agents.ocr_agent import OCRAgent
    from app.agents.ner_agent import NERAgent
    from app.agents.validator_agent import ValidatorAgent
    from app.agents.pricing_agent import PricingAgent
    from app.agents.gst_agent import GSTAgent
    from app.agents.quote_agent import QuoteAgent
    from app.agents.communication_agent import CommunicationAgent
    from app.models.rfq import OCRInput, NERInput

    results = {"rfq_id": rfq_id}
    update_rfq(rfq_id, status="processing")

    # OCR (optional)
    extracted_text = raw_text or ""
    if file_path:
        file_type = Path(file_path).suffix.lstrip(".").lower()
        ocr_agent = OCRAgent()
        ocr_output = ocr_agent.run(OCRInput(
            rfq_id=rfq_id,
            file_path=file_path,
            file_type=file_type
        ))
        extracted_text = ocr_output.raw_text
        results["ocr"] = ocr_output.model_dump()  # Pydantic v2

    if not extracted_text:
        update_rfq(rfq_id, status="failed", error="No text extracted from RFQ.")
        return {
            "status": "failed",
            "rfq_id": rfq_id,
            "error": "No text extracted from RFQ."
        }

    # NER
    ner_agent = NERAgent()
    ner_output = ner_agent.run(NERInput(
        rfq_id=rfq_id,
        raw_text=extracted_text
    ))
    results["ner"] = ner_output.model_dump()  # Pydantic v2
    update_rfq(rfq_id, status="extracted")

    # Validation
    validator_agent = ValidatorAgent()
    validation_results = validator_agent.run(ner_output.line_items)
    results["validation"] = [res.model_dump() for res in validation_results]

    valid_items = [res.item for res in validation_results if res.status == "valid"]
    if not valid_items:
        update_rfq(rfq_id, status="failed", error="No valid line items after validation.")
        return {
            "status": "failed",
            "rfq_id": rfq_id,
            "error": "No valid line items after validation."
        }

    # Pricing + Quote items
    pricing_agent = PricingAgent()
    margin_percent = float(os.getenv("DEFAULT_MARGIN_PERCENT", "5.0"))
    default_pincode = os.getenv("ORIGIN_PINCODE", "395006")

    async def _price_items():
        item_costs = []
        quote_items = []
        total_subtotal = 0.0

        for item in valid_items:
            price = await pricing_agent.fetch_mcx_price(item.grade)
            weight = pricing_agent.calculate_weight(item)
            delivery_pincode = item.destination_pincode or default_pincode
            material_cost = weight.total_weight_ton * price.price_per_ton
            logistics_cost = pricing_agent.calculate_logistics_cost(delivery_pincode, weight.total_weight_ton)
            margin = material_cost * (margin_percent / 100)
            subtotal = material_cost + logistics_cost + margin

            item_costs.append({
                "material_cost": round(material_cost, 2),
                "logistics_cost": round(logistics_cost, 2),
                "loading_cost": 0.0,
                "margin_amount": round(margin, 2),
                "subtotal": round(subtotal, 2)
            })

            dimensions = item.dimensions or {}
            quantity = item.quantity or {}
            dimensions_str = ", ".join(f"{k}:{v}" for k, v in dimensions.items()) if dimensions else ""
            quantity_str = f"{quantity.get('value', '')} {quantity.get('unit', '')}".strip()

            quote_items.append({
                "material": item.material_type or "",
                "grade": item.grade or "",
                "dimensions": dimensions_str,
                "quantity": quantity_str,
                "rate": price.price_per_ton,
                "amount": round(material_cost, 2)
            })

            total_subtotal += subtotal

        return item_costs, total_subtotal, quote_items

    item_costs, total_subtotal, quote_items = asyncio.run(_price_items())
    logistics_total = sum(item.get("logistics_cost", 0.0) for item in item_costs)
    margin_total = sum(item.get("margin_amount", 0.0) for item in item_costs)
    results["pricing"] = {
        "item_costs": item_costs,
        "total_subtotal": round(total_subtotal, 2),
        "margin_percent": margin_percent
    }
    update_rfq(rfq_id, status="priced")

    # GST
    gst_agent = GSTAgent()
    gst_pincode = valid_items[0].destination_pincode or default_pincode
    gst_material = valid_items[0].material_type or ""
    gst_result = gst_agent.run(total_subtotal, gst_pincode, gst_material)
    results["gst"] = gst_result.model_dump()  # Pydantic v2

    # Quote
    quote_agent = QuoteAgent()
    buyer_contact = sender_contact or ""
    buyer_location = valid_items[0].destination_raw or gst_pincode
    pdf_path = asyncio.run(quote_agent.run(
        rfq_id=rfq_id,
        line_items=quote_items,
        total=total_subtotal,
        buyer_contact=buyer_contact,
        buyer_location=buyer_location,
        logistics_total=logistics_total,
        margin_amount=margin_total,
        margin_percent=margin_percent,
        gst_type=gst_result.tax_type,
        gst_amount=gst_result.total_gst
    ))
    results["quote"] = {"pdf_path": pdf_path}
    update_rfq(rfq_id, status="quoted")

    # Communication (best-effort)
    if sender_contact:
        comms_agent = CommunicationAgent()
        grand_total = total_subtotal + gst_result.total_gst
        summary = f"Quote for RFQ {rfq_id}: total INR {grand_total:.2f}. Quote PDF attached."
        comms_result = asyncio.run(comms_agent.run(
            rfq_id=rfq_id,
            pdf_path=pdf_path,
            channel=source_channel,
            recipient=sender_contact,
            summary=summary
        ))
        results["communication"] = comms_result.model_dump()  # Pydantic v2

    update_rfq(rfq_id, result=results)
    return {
        "status": "success",
        "rfq_id": rfq_id,
        "result": results
    }


if CELERY_AVAILABLE:
    @celery_app.task(name="srip.process_rfq_pipeline")
    def process_rfq_pipeline(rfq_id: str, file_path: str = None, raw_text: str = None,
                             sender_contact: str = None, source_channel: str = "api"):
        return _run_pipeline(
            rfq_id=rfq_id,
            file_path=file_path,
            raw_text=raw_text,
            sender_contact=sender_contact,
            source_channel=source_channel
        )
else:
    def process_rfq_pipeline(rfq_id: str, file_path: str = None, raw_text: str = None,
                             sender_contact: str = None, source_channel: str = "api"):
        return _run_pipeline(
            rfq_id=rfq_id,
            file_path=file_path,
            raw_text=raw_text,
            sender_contact=sender_contact,
            source_channel=source_channel
        )
