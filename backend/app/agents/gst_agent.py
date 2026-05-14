"""GST Agent - Determines tax jurisdiction, assigns HSN code, calculates GST."""
import json
import os
from typing import Dict

from app.core.rag.chroma_client import ChromaClient
from app.models.rfq import GSTResult


class GSTAgent:
    """
    GST Agent: Determines tax jurisdiction, assigns HSN code,
    calculates IGST/CGST/SGST split.
    """

    def __init__(self):
        prefixes = os.getenv("GST_GUJARAT_PREFIXES")
        if not prefixes:
            raise RuntimeError("GST_GUJARAT_PREFIXES must be set (comma-separated).")
        self.gujarat_prefixes = [p.strip() for p in prefixes.split(",") if p.strip()]

        rules_path = os.getenv("GST_RULES_PATH", "app/knowledge/hsn_gst_rules.json")
        if not os.path.exists(rules_path):
            raise RuntimeError(f"GST rules not found: {rules_path}")

        with open(rules_path, "r", encoding="utf-8") as f:
            rules = json.load(f)

        self.hsn_map: Dict[str, Dict[str, str]] = {}
        for rule in rules:
            material = rule.get("material")
            if material:
                self.hsn_map[material] = {
                    "hsn_code": rule.get("hsn_code", ""),
                    "gst_rate": rule.get("gst_rate", "")
                }

        self.chroma = ChromaClient()

    def _external_context(self, query: str) -> str:
        try:
            results = self.chroma.query(
                collection="external_rag_files",
                query_texts=[query],
                n_results=3
            )
            return "\n".join([doc for doc in results.get("documents", [[]])[0]])
        except Exception as exc:
            print(f"ChromaDB external_rag_files query failed: {exc}")
            return ""

    def calculate_gst(self, subtotal: float, delivery_pincode: str, material_type: str) -> GSTResult:
        """Calculate GST for a single item."""
        # Determine jurisdiction
        is_gujarat = str(delivery_pincode)[:2] in self.gujarat_prefixes

        external_context = self._external_context(
            f"gst rules material {material_type} pincode {delivery_pincode}"
        )

        rule = self.hsn_map.get(material_type)
        if not rule or not rule.get("hsn_code"):
            ext = self._external_context(f"hsn {material_type} gst")
            raise RuntimeError(f"HSN rule not found for material: {material_type}. External context: {ext}")

        hsn_code = rule["hsn_code"]
        gst_rate_str = rule.get("gst_rate", "").replace("%", "").strip()
        if not gst_rate_str:
            ext = self._external_context(f"gst rate {material_type}")
            raise RuntimeError(f"GST rate missing for material: {material_type}. External context: {ext}")
        gst_rate_pct = float(gst_rate_str)
        gst_rate = gst_rate_pct / 100.0

        gst_amount = subtotal * gst_rate

        if is_gujarat:
            # CGST + SGST (intra-state)
            return GSTResult(
                tax_type="CGST+SGST",
                cgst=round(gst_amount / 2, 2),
                sgst=round(gst_amount / 2, 2),
                igst=0.0,
                total_gst=round(gst_amount, 2),
                hsn_code=hsn_code,
                gst_rate_pct=gst_rate_pct,
                destination_state="Gujarat",
                external_context=external_context
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
                gst_rate_pct=gst_rate_pct,
                destination_state="Other State",
                external_context=external_context
            )

    def run(self, subtotal: float, pincode: str, material_type: str) -> GSTResult:
        """Run GST calculation."""
        result = self.calculate_gst(subtotal, pincode, material_type)
        return result
