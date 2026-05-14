"""Pricing Agent - Fetches live MCX prices and calculates weight & cost."""
import os
import json
import re
import time
import logging
from typing import Optional, List

from app.core.groq_client import GroqClient
from app.core.serper_client import SerperClient
try:
    from app.core.rag.chroma_client import ChromaClient
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False

from app.models.rfq import (
    ValidatedLineItem, WeightResult,
    PricingResult, PriceResult, CostBreakdown
)

logger = logging.getLogger("srip.pricing")


class PricingAgent:
    """
    Pricing Agent: Fetches live MCX prices, calculates weight,
    logistics, and produces full cost breakdown.
    All methods are synchronous for Celery compatibility.
    """

    def __init__(self):
        self.groq = GroqClient()
        self.serper = SerperClient()
        self.chroma = ChromaClient()
        self.redis = None  # Will be initialized with actual Redis client
        self._price_cache = {}
        self._cache_ttl = int(os.getenv("MCX_CACHE_TTL_SECONDS", "900"))

        # Fallback MCX prices (₹/ton) - updated May 2026 approximate values
        self.FALLBACK_PRICES = {
            "Fe 415": 52000,
            "Fe 500": 54000,
            "Fe 500D": 55000,
            "Fe 550": 57000,
            "Fe 550D": 58000,
            "Fe 600": 59000,
            "E250": 53000,
            "E350": 56000,
            "E410": 58000,
            "default": 54000,
        }

        # Plate pricing (₹/kg by thickness range)
        self.PLATE_PRICES_PER_KG = {
            "thin": 65.0,     # <6mm
            "medium": 62.0,   # 6-25mm
            "thick": 60.0,    # >25mm
        }
        # SS plate pricing (₹/kg) - significantly more expensive
        self.SS_PLATE_PRICES_PER_KG = {
            "SS 410": 180.0,
            "SS 304": 220.0,
            "SS 316": 280.0,
            "default": 180.0,
        }

        rules_path = os.getenv("WEIGHT_FORMULAS_PATH", "app/knowledge/weight_formulas.json")
        if not os.path.exists(rules_path):
            raise RuntimeError(f"Weight formulas not found: {rules_path}")
        with open(rules_path, "r", encoding="utf-8") as f:
            rules = json.load(f)
        self.weight_rules = {rule.get("material"): rule for rule in rules if rule.get("material")}

    def _external_context(self, query: str) -> str:
        try:
            results = self.chroma.query(
                collection="external_rag_files",
                query_texts=[query],
                n_results=3
            )
            return "\n".join([doc for doc in results.get("documents", [[]])[0]])
        except Exception as exc:
            logger.warning(f"ChromaDB external_rag_files query failed: {exc}")
            return ""

    def get_material_price(self, material_type: str, grade: Optional[str] = None, thickness_mm: Optional[float] = None) -> PriceResult:
        """Get the correct price based on material type.
        
        - TMT bars: Use MCX live price or fallback per ton
        - Plates (CS): Use per-kg pricing based on thickness
        - SS plates: Use SS-specific per-kg pricing
        - Other: Fall back to TMT pricing
        """
        if material_type in ("Structural_Plate", "Plate"):
            grade_str = str(grade or "").strip()
            # Stainless steel plates
            if grade_str.upper().startswith("SS") or "stainless" in grade_str.lower():
                price_per_kg = self.SS_PLATE_PRICES_PER_KG.get(
                    grade_str, self.SS_PLATE_PRICES_PER_KG["default"]
                )
                price_per_ton = price_per_kg * 1000
                logger.info(f"🟢 SS Plate price for {grade_str}: ₹{price_per_kg}/kg (₹{price_per_ton}/ton)")
                return PriceResult(
                    price_per_ton=price_per_ton,
                    source="plate_schedule",
                    as_of="rate_card"
                )
            # Carbon steel plates — price by thickness
            t = thickness_mm or 10  # default if unknown
            if t < 6:
                price_per_kg = self.PLATE_PRICES_PER_KG["thin"]
            elif t <= 25:
                price_per_kg = self.PLATE_PRICES_PER_KG["medium"]
            else:
                price_per_kg = self.PLATE_PRICES_PER_KG["thick"]
            price_per_ton = price_per_kg * 1000
            logger.info(f"🟢 CS Plate price ({t}mm): ₹{price_per_kg}/kg (₹{price_per_ton}/ton)")
            return PriceResult(
                price_per_ton=price_per_ton,
                source="plate_schedule",
                as_of="rate_card"
            )

        # TMT bars and everything else: use MCX or fallback
        return self.fetch_mcx_price(grade or "Fe 500")

    def fetch_mcx_price(self, grade: str) -> PriceResult:
        """Fetch live MCX price for a given grade (synchronous)."""
        cache_key = f"mcx:{grade.replace(' ', '')}:rate"

        # Check in-memory cache first
        cached = self._price_cache.get(cache_key)
        if cached:
            age_seconds = time.time() - cached["timestamp"]
            if age_seconds <= self._cache_ttl:
                logger.info(f"MCX price cache hit for {grade}: ₹{cached['price_per_ton']}/ton")
                return PriceResult(
                    price_per_ton=cached["price_per_ton"],
                    source=cached["source"],
                    as_of=cached.get("as_of", "today")
                )

        # Try Serper search + Groq extraction
        try:
            search_query = f"MCX steel TMT {grade} price per ton India today 2026"
            results = self.serper.search(search_query, num=3)

            # Extract just the snippet text (max 500 chars) to avoid Groq 400
            snippets = []
            for r in results[:3]:
                snippet = r.get("snippet", "")[:150]
                if snippet:
                    snippets.append(snippet)
            context_text = " | ".join(snippets)[:500]

            if not context_text.strip():
                raise ValueError("Empty Serper results")

            # Ask Groq to extract price from snippets (small prompt, small response)
            extract_prompt = f"""From this text, extract the current TMT steel price per metric ton in INR.
Text: {context_text}
Grade: {grade}
Return ONLY: {{"price_per_ton": NUMBER}} where NUMBER is an integer. No other text."""

            groq_response = self.groq.call(
                system_prompt="You are a pricing analyst. Extract the steel price per metric ton in INR. Return ONLY valid JSON.",
                user_prompt=extract_prompt,
                model="llama-3.1-8b-instant",  # Use fast small model for extraction
                temperature=0.0,
                max_tokens=50
            )

            raw = groq_response.strip()
            # Strip markdown if present
            raw = re.sub(r'^```(?:json)?\s*', '', raw)
            raw = re.sub(r'\s*```$', '', raw)
            raw = re.sub(r'[^0-9{}":,\s.]', '', raw)  # Strip everything except JSON chars
            parsed = json.loads(raw)
            price = int(parsed.get("price_per_ton", 0))

            if 30000 < price < 150000:  # Sanity check: valid steel price range
                self._price_cache[cache_key] = {
                    "price_per_ton": price,
                    "source": "live",
                    "as_of": "today",
                    "timestamp": time.time(),
                }
                logger.info(f"🟢 MCX live price for {grade}: ₹{price}/ton")
                return PriceResult(
                    price_per_ton=price,
                    source="live",
                    as_of="today"
                )
            else:
                raise ValueError(f"Price {price} outside valid range 30000-150000")

        except Exception as e:
            # Use fallback price with proper logging
            fallback_price = self.FALLBACK_PRICES.get(grade, self.FALLBACK_PRICES["default"])
            logger.warning(f"🔴 MCX price fetch failed for {grade}: {e}. Using fallback ₹{fallback_price}/ton")
            return PriceResult(
                price_per_ton=fallback_price,
                source="fallback",
                as_of="cached"
            )

    def calculate_weight(self, item) -> WeightResult:
        """Calculate weight using BIS standard formulas."""
        unit_weight_kg = 0.0
        total_weight_ton = 0.0

        material_type = item.material_type if hasattr(item, 'material_type') else item.get("material_type", "")
        dimensions = item.dimensions if hasattr(item, 'dimensions') else item.get("dimensions", {})
        quantity = item.quantity if hasattr(item, 'quantity') else item.get("quantity", {})

        if not dimensions:
            dimensions = {}
        if not quantity:
            raise RuntimeError("Missing quantity for weight calculation.")

        rule = self.weight_rules.get(material_type)
        if not rule:
            # Fallback: if quantity is in tons or kg, just convert directly
            qty_unit = quantity.get("unit", "tons")
            qty_value = float(quantity.get("value", 0))
            if qty_unit == "tons":
                return WeightResult(
                    formula_used=f"DirectTons:{material_type}",
                    unit_weight_kg=0.0,
                    total_weight_ton=round(qty_value, 4)
                )
            elif qty_unit == "kg":
                return WeightResult(
                    formula_used=f"DirectKg:{material_type}",
                    unit_weight_kg=qty_value,
                    total_weight_ton=round(qty_value / 1000.0, 4)
                )
            raise RuntimeError(f"Weight formula not found for material: {material_type}")

        rule_type = rule.get("type")
        qty_unit = quantity.get("unit")
        qty_value = quantity.get("value")
        if qty_unit is None or qty_value is None:
            raise RuntimeError("Quantity must include value and unit.")

        if rule_type == "tmt_bar":
            d = dimensions.get("diameter_mm")
            if d is None:
                # Default to 12mm if not specified
                d = 12
                logger.warning(f"TMT_Bar diameter not specified, defaulting to {d}mm")
            divisor = rule.get("divisor")
            if not divisor:
                raise RuntimeError("TMT_Bar divisor missing in weight rules.")

            length_ft = dimensions.get("length_ft")
            if length_ft is None:
                length_ft = rule.get("standard_length_ft")
            if length_ft is None:
                length_ft = 40  # Default 40ft
                logger.warning("TMT_Bar length not specified, defaulting to 40ft")

            weight_kg_per_m = (d ** 2) / float(divisor)
            total_length_m = float(length_ft) * 0.3048
            unit_weight_kg = weight_kg_per_m * total_length_m

            if qty_unit == "tons":
                total_weight_ton = float(qty_value)
            elif qty_unit == "kg":
                total_weight_ton = float(qty_value) / 1000.0
            elif qty_unit == "pieces":
                total_weight_ton = (unit_weight_kg * float(qty_value)) / 1000
            elif qty_unit == "bundles":
                rods_per_bundle = quantity.get("rods_per_bundle")
                if rods_per_bundle is None:
                    raise RuntimeError("bundles require rods_per_bundle in quantity.")
                total_pieces = float(qty_value) * float(rods_per_bundle)
                total_weight_ton = (unit_weight_kg * total_pieces) / 1000
            else:
                raise RuntimeError(f"Unsupported quantity unit for TMT_Bar: {qty_unit}")

        elif rule_type == "plate":
            t = dimensions.get("thickness_mm")
            w = dimensions.get("width_mm")
            l = dimensions.get("length_mm")

            # If quantity is in kg, use directly — no formula needed
            if qty_unit == "kg":
                total_weight_ton = float(qty_value) / 1000.0
                return WeightResult(
                    formula_used=f"DirectKg:Structural_Plate",
                    unit_weight_kg=float(qty_value),
                    total_weight_ton=round(total_weight_ton, 4)
                )
            if qty_unit == "tons":
                total_weight_ton = float(qty_value)
                return WeightResult(
                    formula_used=f"DirectTons:Structural_Plate",
                    unit_weight_kg=0.0,
                    total_weight_ton=round(total_weight_ton, 4)
                )

            # Calculate from dimensions if quantity is in pieces
            if t is None or w is None or l is None:
                raise RuntimeError("Structural_Plate with 'pieces' quantity requires thickness_mm, width_mm, length_mm.")
            density = rule.get("density_g_cm3")
            if not density:
                raise RuntimeError("Structural_Plate density missing in weight rules.")
            unit_weight_kg = (float(l) * float(w) * float(t) * float(density)) / 1000000

            if qty_unit == "pieces":
                total_weight_ton = (unit_weight_kg * float(qty_value)) / 1000
            else:
                raise RuntimeError(f"Unsupported quantity unit for Structural_Plate: {qty_unit}")

        elif rule_type == "angle":
            a = dimensions.get("leg_a_mm")
            b = dimensions.get("leg_b_mm")
            t = dimensions.get("thickness_mm")
            if a is None or b is None or t is None:
                if qty_unit == "tons":
                    total_weight_ton = float(qty_value)
                    return WeightResult(
                        formula_used=f"DirectTons:Angle",
                        unit_weight_kg=0.0,
                        total_weight_ton=round(total_weight_ton, 4)
                    )
                raise RuntimeError("Angle requires leg_a_mm, leg_b_mm, thickness_mm.")
            density_factor = rule.get("density_factor")
            if not density_factor:
                raise RuntimeError("Angle density_factor missing in weight rules.")
            weight_kg_per_m = (float(a) + float(b) - float(t)) * float(t) * float(density_factor)
            unit_weight_kg = weight_kg_per_m

            length_m = dimensions.get("length_m")
            length_mm = dimensions.get("length_mm")
            if length_m is None and length_mm is None:
                raise RuntimeError("Angle requires length_m or length_mm.")
            length_total_m = float(length_m) if length_m is not None else (float(length_mm) / 1000.0)

            if qty_unit == "meters":
                total_weight_ton = (weight_kg_per_m * float(qty_value)) / 1000
            elif qty_unit == "pieces":
                total_weight_ton = (weight_kg_per_m * length_total_m * float(qty_value)) / 1000
            elif qty_unit == "tons":
                total_weight_ton = float(qty_value)
            else:
                raise RuntimeError(f"Unsupported quantity unit for Angle: {qty_unit}")

        elif rule_type == "flat_bar":
            w = dimensions.get("width_mm")
            t = dimensions.get("thickness_mm")
            if w is None or t is None:
                if qty_unit == "tons":
                    total_weight_ton = float(qty_value)
                    return WeightResult(
                        formula_used=f"DirectTons:Flat_Bar",
                        unit_weight_kg=0.0,
                        total_weight_ton=round(total_weight_ton, 4)
                    )
                raise RuntimeError("Flat_Bar requires width_mm and thickness_mm.")
            density = rule.get("density_g_cm3")
            divisor = rule.get("divisor")
            if not density or not divisor:
                raise RuntimeError("Flat_Bar density/divisor missing in weight rules.")
            weight_kg_per_m = float(w) * float(t) * float(density) / float(divisor)
            unit_weight_kg = weight_kg_per_m

            length_m = dimensions.get("length_m")
            length_mm = dimensions.get("length_mm")
            if length_m is None and length_mm is None:
                raise RuntimeError("Flat_Bar requires length_m or length_mm.")
            length_total_m = float(length_m) if length_m is not None else (float(length_mm) / 1000.0)

            if qty_unit == "meters":
                total_weight_ton = (weight_kg_per_m * float(qty_value)) / 1000
            elif qty_unit == "pieces":
                total_weight_ton = (weight_kg_per_m * length_total_m * float(qty_value)) / 1000
            elif qty_unit == "tons":
                total_weight_ton = float(qty_value)
            else:
                raise RuntimeError(f"Unsupported quantity unit for Flat_Bar: {qty_unit}")

        elif rule_type == "channel":
            section_weight = dimensions.get("section_weight_kg_m")
            if section_weight is None:
                if qty_unit == "tons":
                    total_weight_ton = float(qty_value)
                    return WeightResult(
                        formula_used=f"DirectTons:Channel",
                        unit_weight_kg=0.0,
                        total_weight_ton=round(total_weight_ton, 4)
                    )
                raise RuntimeError("Channel requires section_weight_kg_m.")
            unit_weight_kg = float(section_weight)

            length_m = dimensions.get("length_m")
            length_mm = dimensions.get("length_mm")
            if length_m is None and length_mm is None:
                raise RuntimeError("Channel requires length_m or length_mm.")
            length_total_m = float(length_m) if length_m is not None else (float(length_mm) / 1000.0)

            if qty_unit == "meters":
                total_weight_ton = (unit_weight_kg * float(qty_value)) / 1000
            elif qty_unit == "pieces":
                total_weight_ton = (unit_weight_kg * length_total_m * float(qty_value)) / 1000
            elif qty_unit == "tons":
                total_weight_ton = float(qty_value)
            else:
                raise RuntimeError(f"Unsupported quantity unit for Channel: {qty_unit}")
        else:
            raise RuntimeError(f"Unsupported weight rule type: {rule_type}")

        return WeightResult(
            formula_used=f"Shape:{material_type}",
            unit_weight_kg=round(unit_weight_kg, 4),
            total_weight_ton=round(total_weight_ton, 4)
        )

    def calculate_logistics_cost(self, pincode: str, total_weight_ton: float) -> float:
        """Calculate logistics cost based on pincode distance from Surat (395006)."""
        pin_prefix = str(pincode)[:2] if pincode else ""
        rates_path = os.getenv("LOGISTICS_RATES_PATH", "app/knowledge/logistics_rates.json")
        if not os.path.exists(rates_path):
            raise RuntimeError(f"Logistics rates not found: {rates_path}")

        with open(rates_path, "r", encoding="utf-8") as f:
            rates = json.load(f)

        matched = None
        for row in rates:
            if row.get("destination_pincode_prefix") == pin_prefix:
                matched = row
                break

        if not matched:
            logger.warning(f"No logistics rate for pincode prefix {pin_prefix}, using fallback ₹1500/ton")
            fallback_rate = 1500  # Default ₹1500/ton for unknown pincodes
            rate_per_ton = fallback_rate
        else:
            rate_per_ton = float(matched.get("rate_per_ton"))

        loading_cost_per_ton = float(os.getenv("LOADING_COST_PER_TON", "0"))
        logistics_cost = (rate_per_ton + loading_cost_per_ton) * total_weight_ton
        return round(logistics_cost, 2)

    def run(self, items: list, margin_percent: float = 5.0, pincode: str = "395006") -> PricingResult:
        """Run pricing calculation for all items (synchronous)."""
        total_cost = 0
        item_costs = []

        for item in items:
            # Get grade from item (supports both Pydantic model and dict)
            grade = item.grade if hasattr(item, 'grade') else item.get("grade", "Fe 500")

            # Fetch price (synchronous)
            price = self.fetch_mcx_price(grade)

            # Calculate weight
            weight = self.calculate_weight(item)

            # Get delivery pincode
            delivery_pin = pincode
            if hasattr(item, 'destination_pincode') and item.destination_pincode:
                delivery_pin = item.destination_pincode
            elif isinstance(item, dict) and item.get("destination_pincode"):
                delivery_pin = item["destination_pincode"]

            # Calculate costs
            material_cost = weight.total_weight_ton * price.price_per_ton
            logistics_cost = self.calculate_logistics_cost(delivery_pin, weight.total_weight_ton)
            margin = material_cost * (margin_percent / 100)
            subtotal = material_cost + logistics_cost + margin

            item_costs.append(CostBreakdown(
                material_cost=round(material_cost, 2),
                logistics_cost=round(logistics_cost, 2),
                loading_cost=0,  # Included in logistics
                margin_amount=round(margin, 2),
                subtotal=round(subtotal, 2)
            ))
            total_cost += subtotal

        external_context = self._external_context("pricing pipeline summary")
        return PricingResult(
            item_costs=item_costs,
            total_subtotal=round(total_cost, 2),
            margin_percent=margin_percent,
            external_context=external_context
        )
