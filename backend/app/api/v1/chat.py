"""Chat API endpoint - processes text RFQs synchronously and returns structured replies."""
# pyrefly: ignore [missing-import]
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import uuid
import time
import logging
import traceback

router = APIRouter(tags=["chat"])
logger = logging.getLogger("srip.chat")


class ChatMessage(BaseModel):
    message: str
    rfq_id: Optional[str] = None  # If continuing a conversation


class ChatResponse(BaseModel):
    rfq_id: str
    reply: str
    status: str
    extracted_data: Optional[dict] = None
    cost_breakdown: Optional[dict] = None
    quote_url: Optional[str] = None
    needs_clarification: bool = False
    clarification_questions: list = []
    agent_timings: Optional[dict] = None


@router.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatMessage):
    """
    Main chat endpoint. Accepts a text RFQ and returns a structured reply.
    This is the primary interface for text-based RFQ processing.
    """
    from app.tasks.pipeline_tasks import run_pipeline_sync

    rfq_id = payload.rfq_id or str(uuid.uuid4())

    if not payload.message or not payload.message.strip():
        return ChatResponse(
            rfq_id=rfq_id,
            reply="Please send me your steel RFQ. For example: '12mm Fe500 TMT bars 10 tons delivery Surat'",
            status="awaiting_input",
            needs_clarification=True,
            clarification_questions=[
                "What material do you need? (e.g. TMT bars, MS plate, Angle)",
                "What grade? (e.g. Fe 500, E250)",
                "What quantity? (e.g. 10 tons)",
                "Delivery location?"
            ]
        )

    # Run pipeline synchronously for chat
    try:
        result = run_pipeline_sync(rfq_id, raw_text=payload.message.strip())
    except Exception as e:
        logger.error(f"Pipeline failed for chat: {e}")
        traceback.print_exc()
        return ChatResponse(
            rfq_id=rfq_id,
            reply=f"Sorry, I had trouble processing this RFQ. Error: {str(e)}",
            status="failed",
            needs_clarification=True,
            clarification_questions=["Could you please rephrase your requirements?"]
        )

    # Check if pipeline needs clarification
    if result.get("needs_clarification"):
        return ChatResponse(
            rfq_id=rfq_id,
            reply="I couldn't extract enough details from your message.",
            status="needs_clarification",
            needs_clarification=True,
            clarification_questions=result.get("clarification_questions", [
                "What material do you need?",
                "What grade and size?",
                "How much quantity?",
                "Where should it be delivered?"
            ]),
            agent_timings=result.get("agent_timings")
        )

    # Build human-readable reply
    reply = build_chat_reply(result)

    return ChatResponse(
        rfq_id=rfq_id,
        reply=reply,
        status=result.get("status", "completed"),
        extracted_data=result.get("ner"),
        cost_breakdown=result.get("pricing"),
        quote_url=f"/api/v1/rfq/{rfq_id}/quote" if result.get("quote", {}).get("pdf_path") else None,
        needs_clarification=result.get("needs_clarification", False),
        clarification_questions=result.get("clarification_questions", []),
        agent_timings=result.get("agent_timings")
    )


def build_chat_reply(result: dict) -> str:
    """Convert pipeline result into a natural language reply."""

    ner = result.get("ner", {})
    pricing = result.get("pricing", {})
    gst = result.get("gst", {})
    quote = result.get("quote", {})
    items = ner.get("line_items", [])

    if not items:
        return ("I couldn't extract specific steel items from your message. "
                "Could you please specify: material type, grade (e.g. Fe 500), "
                "size (e.g. 12mm), quantity (e.g. 10 tons), and delivery location?")

    # Build the reply
    lines = ["✅ **Quote Ready!** Here's what I understood:\n"]

    for i, item in enumerate(items, 1):
        mat = (item.get("material_type") or "Steel").replace("_", " ")
        grade = item.get("grade") or ""
        dims = item.get("dimensions", {}) or {}
        qty = item.get("quantity", {}) or {}
        dest = item.get("destination_raw") or item.get("destination_pincode", "")

        # Build dimension string based on material type
        dia = dims.get("diameter_mm")
        width = dims.get("width_mm")
        length = dims.get("length_mm")
        thickness = dims.get("thickness_mm")

        if dia:
            dim_str = f"{dia}mm"
        elif width and length and thickness:
            dim_str = f"{width}×{length}×{thickness}mm"
        elif thickness:
            dim_str = f"{thickness}mm thick"
        else:
            dim_str = ""

        qty_str = f"{qty.get('value', '')} {qty.get('unit', '')}"

        lines.append(f"**Item {i}:** {mat} {grade} {dim_str} — {qty_str} → {dest}")

    # Add cost breakdown
    item_costs = pricing.get("item_costs", [])
    if item_costs:
        total_material = sum(c.get("material_cost", 0) for c in item_costs)
        total_logistics = sum(c.get("logistics_cost", 0) for c in item_costs)
        total_margin = sum(c.get("margin_amount", 0) for c in item_costs)
        total_subtotal = pricing.get("total_subtotal", 0)

        gst_amount = gst.get("total_gst", 0)
        gst_type = gst.get("tax_type", "GST")
        hsn = gst.get("hsn_code", "7213")
        grand_total = total_subtotal + gst_amount

        # Determine price source
        price_source = "fallback"
        if item_costs:
            price_source = item_costs[0].get("price_source", "fallback")
        source_labels = {
            "live": "🟢 Live MCX price",
            "plate_schedule": "🟢 Plate rate card",
            "fallback": "🔴 Fallback price",
        }
        source_label = source_labels.get(price_source, f"📌 {price_source}")

        lines.append(f"\n**Cost Breakdown** ({source_label}):")
        lines.append(f"  Material:  ₹{total_material:,.0f}")
        lines.append(f"  Logistics: ₹{total_logistics:,.0f}")
        lines.append(f"  Margin:    ₹{total_margin:,.0f}")
        lines.append(f"  {gst_type} (18%, HSN {hsn}): ₹{gst_amount:,.0f}")
        lines.append(f"  **Grand Total: ₹{grand_total:,.0f}**")

    if quote.get("pdf_path"):
        lines.append(f"\n📄 Quote PDF ready — click Download Quote below.")
        lines.append(f"⏰ Price valid for 24 hours.")

    # Add timing info
    timings = result.get("agent_timings", {})
    total_ms = result.get("total_pipeline_ms", 0)
    if total_ms:
        lines.append(f"\n⚡ Processed in {total_ms}ms")

    return "\n".join(lines)
