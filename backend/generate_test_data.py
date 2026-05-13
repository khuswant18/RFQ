"""
generate_test_data.py — Seed realistic RFQ records into SRIP.

Run from the backend/ directory:
    python generate_test_data.py

Seeds 5 realistic RFQ records covering all pipeline states so the dashboard
is not empty on first launch.
"""
import os
import sys
import uuid
import json
from datetime import datetime, timedelta

# ── Bootstrap path so app imports work ──────────────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))

# Load .env before importing app modules
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# ── Trigger DB init ──────────────────────────────────────────────────────────
from app.core.database import init_db, is_db_available
init_db()

from app.core.rfq_store import create_rfq, update_rfq


# ── Helpers ──────────────────────────────────────────────────────────────────

def _ts(minutes_ago: int = 0) -> str:
    return (datetime.utcnow() - timedelta(minutes=minutes_ago)).isoformat()


# ── Test RFQ definitions ─────────────────────────────────────────────────────

SEED_RFQS = [
    # 1. Just arrived — Surat buyer, text RFQ
    {
        "rfq_id": str(uuid.uuid4()),
        "source_channel": "whatsapp",
        "raw_text": "bhai 10 ton 12mm Fe500 sariya chahiye surat sachin gidc delivery by next week",
        "sender_contact": "whatsapp:+919898001001",
        "status": "received",
        "result": None,
        "error": None,
        "minutes_ago": 2,
    },

    # 2. Currently processing — Rajkot buyer
    {
        "rfq_id": str(uuid.uuid4()),
        "source_channel": "whatsapp",
        "raw_text": "5 ton 16mm Fe550D TMT Rajkot urgent",
        "sender_contact": "whatsapp:+919898002002",
        "status": "processing",
        "result": None,
        "error": None,
        "minutes_ago": 5,
    },

    # 3. Completed — Sachin GIDC Surat, 10T 12mm Fe500
    {
        "rfq_id": str(uuid.uuid4()),
        "source_channel": "whatsapp",
        "raw_text": "10 ton 12mm Fe500 surat sachin",
        "sender_contact": "whatsapp:+919898003003",
        "status": "completed",
        "minutes_ago": 30,
        "error": None,
        "result": {
            "status": "success",
            "total_pipeline_ms": 7420,
            "ner": {
                "rfq_id": "",
                "overall_confidence": 0.93,
                "language": "mixed",
                "line_items": [
                    {
                        "item_id": 1,
                        "material_type": "TMT_Bar",
                        "is_code": "IS 1786:2008",
                        "grade": "Fe 500",
                        "shape": "Round",
                        "dimensions": {"diameter_mm": 12, "length_ft": 40},
                        "quantity": {"value": 10, "unit": "tons"},
                        "destination_pincode": "394230",
                        "destination_raw": "Sachin GIDC, Surat",
                        "urgency": None,
                        "confidence_scores": {
                            "material_type": 0.96,
                            "grade": 0.93,
                            "quantity": 0.95,
                        },
                    }
                ],
            },
            "pricing": {
                "item_costs": [
                    {
                        "material_cost": 580000.0,
                        "logistics_cost": 16750.0,
                        "loading_cost": 0.0,
                        "margin_amount": 29000.0,
                        "subtotal": 625750.0,
                        "weight_ton": 10.0,
                        "price_per_ton": 58000,
                        "price_source": "serper",
                    }
                ],
                "total_subtotal": 625750.0,
                "margin_percent": 5.0,
            },
            "gst": {
                "tax_type": "IGST",
                "cgst": 0,
                "sgst": 0,
                "igst": 112635.0,
                "total_gst": 112635.0,
                "hsn_code": "7214",
                "gst_rate_pct": 18,
            },
            "quote": {
                "pdf_path": "storage/quotes/sachin_surat_fe500.pdf",
                "grand_total": 738385.0,
                "whatsapp_summary": (
                    "Quote for 10T Fe500 12mm TMT Bar\n"
                    "Material: ₹5,80,000 | Logistics: ₹16,750\n"
                    "GST (18% IGST): ₹1,12,635\n"
                    "Grand Total: ₹7,38,385\nValid 24 hrs."
                ),
            },
            "agent_timings": {
                "ner": 1840,
                "validator": 210,
                "pricing": 3200,
                "gst": 80,
                "quote": 1900,
                "communication": 190,
            },
        },
    },

    # 4. Completed — Mumbai buyer, MS Plate
    {
        "rfq_id": str(uuid.uuid4()),
        "source_channel": "api",
        "raw_text": "Need 2 MT MS Plate 6mm IS 2062 E250 Mumbai Andheri site",
        "sender_contact": "sales@mumbaiinfra.co.in",
        "status": "completed",
        "minutes_ago": 90,
        "error": None,
        "result": {
            "status": "success",
            "total_pipeline_ms": 9110,
            "ner": {
                "rfq_id": "",
                "overall_confidence": 0.88,
                "language": "en",
                "line_items": [
                    {
                        "item_id": 1,
                        "material_type": "Structural_Plate",
                        "is_code": "IS 2062:2011",
                        "grade": "E250",
                        "shape": "Flat",
                        "dimensions": {
                            "thickness_mm": 6,
                            "width_mm": 1500,
                            "length_mm": 6000,
                        },
                        "quantity": {"value": 2, "unit": "tons"},
                        "destination_pincode": "400053",
                        "destination_raw": "Andheri, Mumbai",
                        "urgency": None,
                        "confidence_scores": {
                            "material_type": 0.91,
                            "grade": 0.88,
                            "quantity": 0.94,
                        },
                    }
                ],
            },
            "pricing": {
                "item_costs": [
                    {
                        "material_cost": 104000.0,
                        "logistics_cost": 9500.0,
                        "loading_cost": 0.0,
                        "margin_amount": 5200.0,
                        "subtotal": 118700.0,
                        "weight_ton": 2.0,
                        "price_per_ton": 52000,
                        "price_source": "serper",
                    }
                ],
                "total_subtotal": 118700.0,
                "margin_percent": 5.0,
            },
            "gst": {
                "tax_type": "IGST",
                "cgst": 0,
                "sgst": 0,
                "igst": 21366.0,
                "total_gst": 21366.0,
                "hsn_code": "7208",
                "gst_rate_pct": 18,
            },
            "quote": {
                "pdf_path": "storage/quotes/mumbai_ms_plate.pdf",
                "grand_total": 140066.0,
                "whatsapp_summary": (
                    "Quote for 2T MS Plate 6mm IS2062 E250\n"
                    "Material: ₹1,04,000 | Logistics: ₹9,500\n"
                    "GST (18% IGST): ₹21,366\n"
                    "Grand Total: ₹1,40,066\nValid 24 hrs."
                ),
            },
            "agent_timings": {
                "ner": 2100,
                "validator": 250,
                "pricing": 4200,
                "gst": 90,
                "quote": 2200,
                "communication": 270,
            },
        },
    },

    # 5. Failed — bad/unreadable RFQ
    {
        "rfq_id": str(uuid.uuid4()),
        "source_channel": "whatsapp",
        "raw_text": "hello bhai rate batao",
        "sender_contact": "whatsapp:+919898005005",
        "status": "failed",
        "minutes_ago": 120,
        "result": None,
        "error": "No line items extracted: RFQ text too vague — no material, grade, or quantity found.",
    },
]


def seed():
    print("🌱 Seeding test RFQ data...")
    created = 0

    for seed_data in SEED_RFQS:
        rfq_id = seed_data["rfq_id"]

        # Create base record
        create_rfq(
            rfq_id=rfq_id,
            source_channel=seed_data["source_channel"],
            file_type="text",
            raw_text=seed_data["raw_text"],
            sender_contact=seed_data["sender_contact"],
        )

        # Advance to target status
        update_kwargs: dict = {"status": seed_data["status"]}
        if seed_data.get("result"):
            update_kwargs["result"] = seed_data["result"]
        if seed_data.get("error"):
            update_kwargs["error"] = seed_data["error"]

        update_rfq(rfq_id, **update_kwargs)

        status_icon = {
            "received": "📥",
            "processing": "⚙️",
            "completed": "✅",
            "failed": "❌",
        }.get(seed_data["status"], "•")

        print(f"  {status_icon}  {rfq_id[:8]}... [{seed_data['status']}] — {seed_data['raw_text'][:50]}")
        created += 1

    print(f"\n✅ Seeded {created} RFQ records.")
    print("   Run the backend and visit GET /api/v1/rfq/feed to confirm.")


if __name__ == "__main__":
    seed()
