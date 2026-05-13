#!/usr/bin/env python3
"""
Generate test RFQ data for dashboard testing.
Run this to populate the system with sample RFQs in various states.
"""
import os
import sys
import uuid
from datetime import datetime, timedelta
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.core.rfq_store import create_rfq, update_rfq


def generate_test_rfqs():
    """Generate sample RFQs in various processing states."""
    
    test_rfqs = [
        {
            "status": "received",
            "file_type": "txt",
            "source_channel": "whatsapp",
            "sender_contact": "whatsapp:+919876543210",
            "raw_text": "12mm sariya Fe500 10 ton chahiye, Sachin GIDC Surat",
        },
        {
            "status": "processing",
            "file_type": "txt",
            "source_channel": "email",
            "sender_contact": "buyer@rajkottraders.com",
            "raw_text": "Need 5 ton 16mm Fe550D TMT for Rajkot delivery",
        },
        {
            "status": "completed",
            "file_type": "txt",
            "source_channel": "whatsapp",
            "sender_contact": "whatsapp:+919999000111",
            "raw_text": "12mm TMT Fe500 10 ton Sachin GIDC Surat",
            "result": {
                "line_items": [
                    {
                        "material_type": "TMT_Bar",
                        "grade": "Fe 500",
                        "diameter_mm": 12,
                        "quantity_value": 10,
                        "quantity_unit": "tons"
                    }
                ],
                "cost_breakdown": {
                    "material_cost": 580000,
                    "logistics_cost": 16750,
                    "gst_amount": 112635,
                    "grand_total": 738385
                },
                "quote_path": "storage/quotes/{rfq_id}.pdf"
            }
        },
        {
            "status": "completed",
            "file_type": "txt",
            "source_channel": "email",
            "sender_contact": "buyer@mumbaimetal.com",
            "raw_text": "MS Plate 6mm IS 2062, 2 ton, Mumbai",
            "result": {
                "line_items": [
                    {
                        "material_type": "Structural_Plate",
                        "grade": "E250",
                        "thickness_mm": 6,
                        "quantity_value": 2,
                        "quantity_unit": "tons"
                    }
                ],
                "cost_breakdown": {
                    "material_cost": 112000,
                    "logistics_cost": 5400,
                    "gst_amount": 21132,
                    "grand_total": 138532
                },
                "quote_path": "storage/quotes/{rfq_id}.pdf"
            }
        },
        {
            "status": "failed",
            "file_type": "image",
            "source_channel": "whatsapp",
            "sender_contact": "whatsapp:+916543210987",
            "raw_text": "Blurry image of RFQ",
            "error": "OCR confidence too low (0.25). Could not extract text reliably.",
        }
    ]

    print("=" * 60)
    print("Generating Test RFQ Data")
    print("=" * 60)
    print()

    created_count = 0
    for i, rfq_data in enumerate(test_rfqs, 1):
        rfq_id = str(uuid.uuid4())
        status = rfq_data.pop("status")
        result = rfq_data.pop("result", None)
        error = rfq_data.pop("error", None)

        # Create RFQ
        create_rfq(rfq_id=rfq_id, **rfq_data)

        # Update with status and result
        if isinstance(result, dict):
            result = json.loads(json.dumps(result).replace("{rfq_id}", rfq_id))

        update_rfq(
            rfq_id=rfq_id,
            status=status,
            result=result,
            error=error,
        )

        created_count += 1
        print(f"✓ Created RFQ {i}: {status.upper()}")
        print(f"  ID: {rfq_id}")
        print(f"  Channel: {rfq_data.get('source_channel')}")
        print()

    print("=" * 60)
    print(f"✅ Generated {created_count} test RFQs")
    print("=" * 60)
    print()
    print("Next steps:")
    print("1. Open http://localhost:5173 in your browser")
    print("2. Go to Dashboard to see the test RFQs")
    print("3. Click on any RFQ to see details")
    print("4. Try uploading a new RFQ to test the pipeline")
    print()


if __name__ == "__main__":
    generate_test_rfqs()
