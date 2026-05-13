"""Pricing Agent - Fetches live MCX prices and calculates weight & cost."""
import os
import json
import time
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


class PricingAgent:
    """
    Pricing Agent: Fetches live MCX prices, calculates weight,
    logistics, and produces full cost breakdown.
    All methods are synchronous for Celery compatibility.
    """

    def __init__(self):
        self.groq = GroqClient()
        self.serper = SerperClient()
        try:
            self.chroma = ChromaClient()
        except (ImportError, Exception):
            self.chroma = None
            print("Warning: ChromaDB not available. Pricing agent running in standalone mode.")
        self.redis = None  # Will be initialized with actual Redis client
        self._price_cache = {}

        # Fallback base prices (₹/MT) when live pricing unavailable
        self.BASE_FALLBACK_PRICES = {
            "Fe 415": 55000,
            "Fe 500": 58000,
            "Fe 500D": 60000,
            "Fe 550": 62000,
            "Fe 600": 65000,
            "E250": 52000,
            "E350": 54000,
            "E410": 56000
        }

    def fetch_mcx_price(self, grade: str) -> PriceResult:
        """Fetch live MCX price for a given grade (synchronous)."""
        cache_key = f"mcx:{grade.replace(' ', '')}:rate"
        cache_ttl = int(os.getenv("MCX_CACHE_TTL_SECONDS", "900"))

        cached = self._price_cache.get(cache_key)
        if cached:
            age_seconds = time.time() - cached["timestamp"]
            if age_seconds <= cache_ttl:
                return PriceResult(
                    price_per_ton=cached["price_per_ton"],
                    source=cached["source"],
                    as_of=cached.get("as_of", "today")
                )

        # TODO: Check Redis cache when available
        # if self.redis:
        #     cached = self.redis.get(cache_key)
        #     if cached:
        #         return PriceResult(price_per_ton=float(cached), source="cache", as_of="today")

        try:
            # Serper web search (synchronous call)
            query = "MCX steel TMT price today"
            results = self.serper.search(query, num=5)

            # Parse search results with LLM (synchronous call)
            prompt = f"""
Extract the current steel price per metric ton (₹/ton) from these search results.
Grade: {grade}
Search Results:
{json.dumps(results)}

Return JSON: {{"price_per_ton": <number>, "source": "<site>", "as_of": "<date>"}}
If you cannot find a reliable price, return {{"price_per_ton": null}}.
"""

            price_data = self.groq.call(
                system_prompt="You are a pricing analyst. Extract steel prices from search results. Return ONLY valid JSON.",
                user_prompt=prompt,
                model="mixtral-8x7b-32768",
                temperature=0.1
            )

            price_json = json.loads(price_data)

            if price_json.get("price_per_ton"):
                self._price_cache[cache_key] = {
                    "price_per_ton": price_json["price_per_ton"],
                    "source": price_json.get("source", "serper"),
                    "as_of": price_json.get("as_of", "today"),
                    "timestamp": time.time(),
                }
                return PriceResult(
                    price_per_ton=price_json["price_per_ton"],
                    source=price_json.get("source", "serper"),
                    as_of=price_json.get("as_of", "today")
                )
        except Exception as e:
            print(f"Error fetching MCX price for {grade}: {e}")

        if cached:
            return PriceResult(
                price_per_ton=cached["price_per_ton"],
                source=cached["source"],
                as_of=cached.get("as_of", "today")
            )

        # Fallback to base price
        fallback_price = self.BASE_FALLBACK_PRICES.get(grade, 60000)
        self._price_cache[cache_key] = {
            "price_per_ton": fallback_price,
            "source": "fallback",
            "as_of": "today",
            "timestamp": time.time(),
        }
        return PriceResult(
            price_per_ton=fallback_price,
            source="fallback",
            as_of="today"
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
            quantity = {"value": 1, "unit": "tons"}

        if material_type == "TMT_Bar":
            d = dimensions.get("diameter_mm", 12)
            weight_kg_per_m = (d ** 2) / 162.28
            total_length_m = dimensions.get("length_ft", 40) * 0.3048
            unit_weight_kg = weight_kg_per_m * total_length_m

            qty_unit = quantity.get("unit", "tons")
            qty_value = quantity.get("value", 1)

            if qty_unit == "tons":
                total_weight_ton = qty_value
            elif qty_unit == "pieces":
                total_weight_ton = (unit_weight_kg * qty_value) / 1000
            elif qty_unit == "bundles":
                rods_per_bundle = 7 if d <= 12 else 5
                total_pieces = qty_value * rods_per_bundle
                total_weight_ton = (unit_weight_kg * total_pieces) / 1000
            else:
                total_weight_ton = qty_value

        elif material_type == "Structural_Plate":
            t = dimensions.get("thickness_mm", 10)
            w = dimensions.get("width_mm", 1250)
            l = dimensions.get("length_mm", 6000)
            unit_weight_kg = (l * w * t * 7.85) / 1000000
            qty_unit = quantity.get("unit", "tons")
            qty_value = quantity.get("value", 1)
            if qty_unit == "pieces":
                total_weight_ton = (unit_weight_kg * qty_value) / 1000
            else:
                total_weight_ton = qty_value

        elif material_type == "Angle":
            a = dimensions.get("leg_a_mm", 50)
            b = dimensions.get("leg_b_mm", a)
            t = dimensions.get("thickness_mm", 5)
            weight_kg_per_m = (a + b - t) * t * 0.00785
            unit_weight_kg = weight_kg_per_m
            qty_unit = quantity.get("unit", "tons")
            qty_value = quantity.get("value", 1)
            if qty_unit == "meters":
                total_weight_ton = (weight_kg_per_m * qty_value) / 1000
            elif qty_unit == "pieces":
                total_weight_ton = (weight_kg_per_m * 6 * qty_value) / 1000  # assume 6m lengths
            else:
                total_weight_ton = qty_value

        elif material_type == "Flat_Bar":
            w = dimensions.get("width_mm", 50)
            t = dimensions.get("thickness_mm", 6)
            weight_kg_per_m = w * t * 7.85 / 1000
            unit_weight_kg = weight_kg_per_m
            qty_unit = quantity.get("unit", "tons")
            qty_value = quantity.get("value", 1)
            if qty_unit == "meters":
                total_weight_ton = (weight_kg_per_m * qty_value) / 1000
            else:
                total_weight_ton = qty_value

        else:
            # Default: treat quantity as tonnage
            total_weight_ton = quantity.get("value", 1)

        return WeightResult(
            formula_used=f"Shape:{material_type}",
            unit_weight_kg=round(unit_weight_kg, 4),
            total_weight_ton=round(total_weight_ton, 4)
        )

    def calculate_logistics_cost(self, pincode: str, total_weight_ton: float) -> float:
        """Calculate logistics cost based on pincode distance from Surat (395006)."""
        pin_prefix = str(pincode)[:2] if pincode else "39"
        distance_km = self._estimate_distance(pin_prefix)
        logistics_rate = distance_km * 2.5  # ₹2.5 per km per ton
        loading_cost = total_weight_ton * 1500  # ₹1500/ton standard loading

        return round(logistics_rate + loading_cost, 2)

    def _estimate_distance(self, pin_prefix: str) -> int:
        """Estimate distance from Surat based on pincode prefix."""
        distance_map = {
            "36": 50,   # South Gujarat
            "37": 150,  # Central Gujarat
            "38": 250,  # North Gujarat
            "39": 100,  # Surat region
            "40": 300,  # Maharashtra
            "41": 400,  # Maharashtra
            "30": 500,  # Rajasthan
            "31": 600,  # Rajasthan
            "32": 700,  # Rajasthan
            "45": 600,  # Madhya Pradesh
            "46": 700,  # Madhya Pradesh
            "11": 1200, # Delhi
            "12": 1100, # Haryana
            "20": 1300, # UP
            "50": 1000, # Telangana
            "56": 1200, # Karnataka
            "60": 1400, # Tamil Nadu
        }
        return distance_map.get(pin_prefix, 800)

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

        return PricingResult(
            item_costs=item_costs,
            total_subtotal=round(total_cost, 2),
            margin_percent=margin_percent
        )
