"""Celery tasks for pipeline processing — fully synchronous execution."""
try:
    from celery import Celery
    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False

import os
import time
import traceback
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
        enable_utc=True,
        task_track_started=True,
        task_acks_late=True,
        worker_prefetch_multiplier=1,
        task_always_eager=os.getenv("CELERY_EAGER", "true").lower() == "true",
    )


def _run_pipeline(rfq_id: str, file_path: str = None, raw_text: str = None,
                  sender_contact: str = None, source_channel: str = "api"):
    """Process an RFQ through the full agent pipeline (fully synchronous)."""
    from app.core.rfq_store import update_rfq
    from app.agents.ocr_agent import OCRAgent
    from app.agents.ner_agent import NERAgent
    from app.agents.validator_agent import ValidatorAgent
    from app.agents.pricing_agent import PricingAgent
    from app.agents.gst_agent import GSTAgent
    from app.agents.quote_agent import QuoteAgent
    from app.agents.communication_agent import CommunicationAgent
    from app.models.rfq import OCRInput, NERInput

    pipeline_start = time.time()
    results = {"rfq_id": rfq_id, "agent_timings": {}}

    try:
        update_rfq(rfq_id, status="processing")

        # ========== Step 1: OCR (if file provided) ==========
        extracted_text = raw_text or ""
        if file_path and os.path.exists(file_path):
            step_start = time.time()
            file_type = Path(file_path).suffix.lstrip(".").lower()
            if file_type in ("jpg", "jpeg", "png", "gif", "bmp", "tiff", "pdf"):
                ocr_agent = OCRAgent()
                ocr_output = ocr_agent.run(OCRInput(
                    rfq_id=rfq_id, file_path=file_path, file_type=file_type
                ))
                extracted_text = ocr_output.raw_text
                results["ocr"] = ocr_output.model_dump()
                results["agent_timings"]["ocr"] = round((time.time() - step_start) * 1000)

                if ocr_output.ocr_confidence < 0.3:
                    update_rfq(rfq_id, status="review_needed",
                               error=f"OCR confidence too low: {ocr_output.ocr_confidence:.0%}")
                    results["status"] = "review_needed"
                    return results

        if not extracted_text:
            update_rfq(rfq_id, status="failed", error="No text extracted from RFQ.")
            return {"status": "failed", "rfq_id": rfq_id, "error": "No text extracted."}

        # ========== Step 2: NER (Entity Extraction) ==========
        step_start = time.time()
        ner_agent = NERAgent()
        ner_output = ner_agent.run(NERInput(rfq_id=rfq_id, raw_text=extracted_text))
        results["ner"] = ner_output.model_dump()
        results["agent_timings"]["ner"] = round((time.time() - step_start) * 1000)
        update_rfq(rfq_id, status="extracted")

        if not ner_output.line_items:
            update_rfq(rfq_id, status="failed", error="No line items extracted from RFQ text.")
            return {"status": "failed", "rfq_id": rfq_id, "error": "No line items extracted."}

        # ========== Step 3: Validation ==========
        step_start = time.time()
        validator_agent = ValidatorAgent()
        validation_results = validator_agent.run(ner_output.line_items)
        results["validation"] = [res.model_dump() for res in validation_results]
        results["agent_timings"]["validator"] = round((time.time() - step_start) * 1000)

        valid_items = [res.item for res in validation_results if res.status == "valid"]
        if not valid_items:
            # If all items invalid, still use them with warnings
            valid_items = [res.item for res in validation_results]
            results["validation_warning"] = "All items had validation errors — proceeding with best-effort."

        # ========== Step 4: Pricing ==========
        step_start = time.time()
        pricing_agent = PricingAgent()
        margin_percent = float(os.getenv("DEFAULT_MARGIN_PERCENT", "5.0"))
        default_pincode = os.getenv("ORIGIN_PINCODE", "395006")

        # Build pricing data synchronously
        item_costs = []
        quote_items = []
        total_subtotal = 0.0

        for item in valid_items:
            price = pricing_agent.fetch_mcx_price(item.grade or "Fe 500")
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
                "subtotal": round(subtotal, 2),
                "weight_ton": round(weight.total_weight_ton, 4),
                "price_per_ton": price.price_per_ton,
                "price_source": price.source,
            })

            dims = item.dimensions or {}
            qty = item.quantity or {}
            dims_str = ", ".join(f"{k}:{v}" for k, v in dims.items()) if dims else ""
            qty_str = f"{qty.get('value', '')} {qty.get('unit', '')}".strip()

            quote_items.append({
                "material": item.material_type or "",
                "grade": item.grade or "",
                "dimensions": dims_str,
                "quantity": qty_str,
                "rate": price.price_per_ton,
                "amount": round(material_cost, 2),
            })
            total_subtotal += subtotal

        logistics_total = sum(ic.get("logistics_cost", 0) for ic in item_costs)
        margin_total = sum(ic.get("margin_amount", 0) for ic in item_costs)

        results["pricing"] = {
            "item_costs": item_costs,
            "total_subtotal": round(total_subtotal, 2),
            "margin_percent": margin_percent,
        }
        results["agent_timings"]["pricing"] = round((time.time() - step_start) * 1000)
        update_rfq(rfq_id, status="priced")

        # ========== Step 5: GST ==========
        step_start = time.time()
        gst_agent = GSTAgent()
        gst_pincode = valid_items[0].destination_pincode or default_pincode
        gst_material = valid_items[0].material_type or "TMT_Bar"
        gst_result = gst_agent.run(total_subtotal, gst_pincode, gst_material)
        results["gst"] = gst_result.model_dump()
        results["agent_timings"]["gst"] = round((time.time() - step_start) * 1000)

        # ========== Step 6: Quote Generation ==========
        step_start = time.time()
        quote_agent = QuoteAgent()
        buyer_contact = sender_contact or ""
        buyer_location = valid_items[0].destination_raw or gst_pincode

        quote_result = quote_agent.run(
            rfq_id=rfq_id,
            line_items=quote_items,
            total=total_subtotal,
            buyer_contact=buyer_contact,
            buyer_location=buyer_location,
            logistics_total=logistics_total,
            margin_amount=margin_total,
            margin_percent=margin_percent,
            gst_type=gst_result.tax_type,
            gst_amount=gst_result.total_gst,
        )
        results["quote"] = quote_result
        results["agent_timings"]["quote"] = round((time.time() - step_start) * 1000)
        update_rfq(rfq_id, status="quoted")

        # ========== Step 7: Communication (best-effort) ==========
        step_start = time.time()
        comms_agent = CommunicationAgent()
        grand_total = total_subtotal + gst_result.total_gst
        summary = quote_result.get("whatsapp_summary", f"Quote for RFQ {rfq_id[:8]}: ₹{grand_total:,.2f}")

        comms_result = comms_agent.run(
            rfq_id=rfq_id,
            pdf_path=quote_result.get("pdf_path", ""),
            channel=source_channel,
            recipient=sender_contact or "",
            summary=summary,
        )
        results["communication"] = comms_result.model_dump()
        results["agent_timings"]["communication"] = round((time.time() - step_start) * 1000)

        # ========== Done ==========
        total_time = round((time.time() - pipeline_start) * 1000)
        results["total_pipeline_ms"] = total_time
        results["status"] = "success"
        update_rfq(rfq_id, result=results)

        print(f"✅ Pipeline complete for {rfq_id} in {total_time}ms")
        return results

    except Exception as e:
        error_msg = f"Pipeline error: {str(e)}"
        print(f"❌ {error_msg}")
        traceback.print_exc()
        update_rfq(rfq_id, status="failed", error=error_msg)
        return {"status": "failed", "rfq_id": rfq_id, "error": error_msg}


# Register as Celery task if available, otherwise plain function
if CELERY_AVAILABLE and celery_app:
    @celery_app.task(name="srip.process_rfq_pipeline", bind=True,
                     max_retries=2, default_retry_delay=5)
    def process_rfq_pipeline(self, rfq_id: str, file_path: str = None,
                             raw_text: str = None, sender_contact: str = None,
                             source_channel: str = "api"):
        try:
            return _run_pipeline(rfq_id, file_path, raw_text, sender_contact, source_channel)
        except Exception as exc:
            print(f"Celery task failed, retrying: {exc}")
            raise self.retry(exc=exc)
else:
    def process_rfq_pipeline(rfq_id: str, file_path: str = None,
                             raw_text: str = None, sender_contact: str = None,
                             source_channel: str = "api"):
        return _run_pipeline(rfq_id, file_path, raw_text, sender_contact, source_channel)
