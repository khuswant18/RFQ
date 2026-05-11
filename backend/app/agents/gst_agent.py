"""GST Agent - Determines tax jurisdiction, assigns HSN code, calculates GST."""
from typing import List

from app.models.rfq import GSTResult


class GSTAgent:
    """
    GST Agent: Determines tax jurisdiction, assigns HSN code,
    calculates IGST/CGST/SGST split.
    """
    
    GUJARAT_PINCODE_PREFIXES = ["36", "37", "38", "39"]
    
    HSN_MAP = {
        "TMT_Bar": "7213",
        "Structural_Plate": "7208",
        "Angle": "7216",
        "Channel": "7216",
        "Flat_Bar": "7214",
        "Square_Bar": "7214",
        "Pipe": "7306"
    }
    
    GST_RATE = 0.18  # 18%
    
    def calculate_gst(self, subtotal: float, delivery_pincode: str, material_type: str) -> GSTResult:
        """Calculate GST for a single item."""
        # Determine jurisdiction
        is_gujarat = str(delivery_pincode)[:2] in self.GUJARAT_PINCODE_PREFIXES
        
        # Assign HSN code
        hsn_code = self.HSN_MAP.get(material_type, "7214")
        
        # Calculate GST amount
        gst_amount = subtotal * self.GST_RATE
        
        if is_gujarat:
            # CGST + SGST (intra-state)
            return GSTResult(
                tax_type="CGST+SGST",
                cgst=round(gst_amount / 2, 2),
                sgst=round(gst_amount / 2, 2),
                igst=0.0,
                total_gst=round(gst_amount, 2),
                hsn_code=hsn_code,
                gst_rate_pct=18.0
            )
        else:
            # IGST (inter-state)
            return GSTResult(
                tax_type="IGST",
                cgst=0.0,
                sgst=0.0,
                igst=round(gst_amount, 2),
                total_gst=round(gst_amount, 2),
                hsn_code=hsn_code,
                gst_rate_pct=18.0
            )
    
    def run(self, subtotal: float, pincode: str, material_type: str) -> GSTResult:
        """Run GST calculation."""
        return self.calculate_gst(subtotal, pincode, material_type)
