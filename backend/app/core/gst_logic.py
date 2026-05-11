"""GST calculation logic."""
from typing import Dict


def determine_gst_type(pincode: str) -> str:
    """Determine GST type (IGST or CGST+SGST) based on pincode."""
    # Gujarat pincode prefixes
    gujarat_prefixes = ["36", "37", "38", "39"]
    
    pin_prefix = str(pincode)[:2]
    
    if pin_prefix in gujarat_prefixes:
        return "CGST+SGST"
    else:
        return "IGST"


def get_hsn_code(material_type: str) -> str:
    """Get HSN code for a material type."""
    hsn_map = {
        "TMT_Bar": "7213",
        "Structural_Plate": "7208",
        "Angle": "7216",
        "Channel": "7216",
        "Flat_Bar": "7214",
        "Square_Bar": "7214",
        "Pipe": "7306"
    }
    
    return hsn_map.get(material_type, "7214")


def calculate_gst(subtotal: float, pincode: str, material_type: str) -> Dict:
    """Calculate GST breakdown."""
    gst_rate = 0.18  # 18%
    gst_amount = subtotal * gst_rate
    
    tax_type = determine_gst_type(pincode)
    
    if tax_type == "CGST+SGST":
        return {
            "tax_type": "CGST+SGST",
            "cgst": round(gst_amount / 2, 2),
            "sgst": round(gst_amount / 2, 2),
            "igst": 0.0,
            "total_gst": round(gst_amount, 2),
            "hsn_code": get_hsn_code(material_type),
            "gst_rate_pct": 18.0
        }
    else:
        return {
            "tax_type": "IGST",
            "cgst": 0.0,
            "sgst": 0.0,
            "igst": round(gst_amount, 2),
            "total_gst": round(gst_amount, 2),
            "hsn_code": get_hsn_code(material_type),
            "gst_rate_pct": 18.0
        }
