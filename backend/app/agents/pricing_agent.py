"""Pricing Agent - Fetches live MCX prices and calculates weight & cost."""
import asyncio
from typing import Optional
import os
import json

from app.core.groq_client import GroqClient
from app.core.serper_client import SerperClient
try:
    from app.core.rag.chroma_client import ChromaClient
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False

from app.models.rfq import (
    ValidatedLineItem, WeightResult, CostBreakdown, 
    PricingResult, PriceResult
)


class PricingAgent:
    """
    Pricing Agent: Fetches live MCX prices, calculates weight,
    logistics, and produces full cost breakdown.
    """
    
    def __init__(self):
        self.groq = GroqClient()
        self.serper = SerperClient()
        try:
            self.chroma = ChromaClient()
        except ImportError:
            self.chroma = None
            print("⚠️  ChromaDB not available. Pricing agent running in standalone mode.")
        self.redis = None  # Will be initialized with actual Redis client
        
        # Mock base prices for fallback
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
    
    async def fetch_mcx_price(self, grade: str) -> PriceResult:
        """Fetch live MCX price for a given grade."""
        cache_key = f"mcx:{grade.replace(' ', '')}:rate"
        
        # Try cache first (simplified - implement with actual Redis)
        # cached = await self.redis.get(cache_key)
        # if cached:
        #     return PriceResult(price=float(cached), source="cache")
        
        # Serper web search
        query = f"MCX steel price today {grade} TMT bar India per ton"
        results = self.serper.search(query, num=5)
        
        # Parse search results with LLM
        prompt = f"""
Extract the current steel price per metric ton (₹/ton) from these search results.
Grade: {grade}
Search Results:
{json.dumps(results)}

Return JSON: {{"price_per_ton": <number>, "source": "<site>", "as_of": "<date>"}}
If you cannot find a reliable price, return {{"price_per_ton": null}}.
"""
        
        try:
            price_data = await self.groq.call_async(
                system_prompt="You are a pricing analyst. Extract steel prices from search results.",
                user_prompt=prompt,
                model="mixtral-8x7b-32768",
                temperature=0.1
            )
            
            price_json = json.loads(price_data)
            
            if price_json.get("price_per_ton"):
                # Cache the result
                # await self.redis.setex(cache_key, int(os.getenv("MCX_CACHE_TTL_SECONDS", 900)), str(price_json["price_per_ton"]))
                return PriceResult(
                    price_per_ton=price_json["price_per_ton"],
                    source=price_json.get("source", "serper"),
                    as_of=price_json.get("as_of", "today")
                )
        except Exception as e:
            print(f"Error fetching MCX price: {e}")
        
        # Fallback to mock price
        fallback_price = self.BASE_FALLBACK_PRICES.get(grade, 60000)
        return PriceResult(
            price_per_ton=fallback_price,
            source="fallback",
            as_of="today"
        )
    
    def calculate_weight(self, item: ValidatedLineItem) -> WeightResult:
        """Calculate weight using BIS standard formulas."""
        
        if item.material_type == "TMT_Bar":
            d = item.dimensions["diameter_mm"]
            weight_kg_per_m = (d ** 2) / 162.28
            total_length_m = item.dimensions.get("length_ft", 40) * 0.3048
            unit_weight_kg = weight_kg_per_m * total_length_m
            
            if item.quantity["unit"] == "tons":
                total_weight_ton = item.quantity["value"]
            elif item.quantity["unit"] == "pieces":
                total_weight_ton = (unit_weight_kg * item.quantity["value"]) / 1000
            elif item.quantity["unit"] == "bundles":
                rods_per_bundle = 7 if d <= 12 else 5
                total_pieces = item.quantity["value"] * rods_per_bundle
                total_weight_ton = (unit_weight_kg * total_pieces) / 1000
            else:
                total_weight_ton = item.quantity["value"]
        
        elif item.material_type == "Structural_Plate":
            t = item.dimensions.get("thickness_mm", 10)
            w = item.dimensions.get("width_mm", 1250)
            l = item.dimensions.get("length_mm", 6000)
            unit_weight_kg = (l * w * t * 7.85) / (1000 * 1000 * 1000) * 1000
            total_weight_ton = (unit_weight_kg * item.quantity["value"]) / 1000 if item.quantity["unit"] == "pieces" else item.quantity["value"]
        
        elif item.material_type == "Angle":
            a = item.dimensions.get("leg_a_mm", 50)
            b = item.dimensions.get("leg_b_mm", a)
            t = item.dimensions.get("thickness_mm", 5)
            weight_kg_per_m = (a + b - t) * t * 0.00785
            total_length_m = item.quantity["value"] if item.quantity["unit"] == "meters" else item.quantity["value"] * 6
            total_weight_ton = (weight_kg_per_m * total_length_m) / 1000
        
        else:
            # Default calculation
            unit_weight_kg = 0
            total_weight_ton = item.quantity["value"]
        
        return WeightResult(
            formula_used=f"Shape:{item.material_type}",
            unit_weight_kg=unit_weight_kg if 'unit_weight_kg' in dir() else 0,
            total_weight_ton=total_weight_ton
        )
    
    def calculate_logistics_cost(self, pincode: str, total_weight_ton: float) -> float:
        """Calculate logistics cost based on pincode distance from Surat (395006)."""
        # Simplified: use a mock distance based on pincode prefix
        pin_prefix = str(pincode)[:2]
        distance_km = self._estimate_distance(pin_prefix)
        logistics_rate = distance_km * 2.5  # ₹2.5 per km per ton (approximate)
        loading_cost = total_weight_ton * 1500  # ₹1500/ton standard
        
        return (logistics_rate + loading_cost)
    
    def _estimate_distance(self, pin_prefix: str) -> int:
        """Estimate distance based on pincode prefix (mock implementation)."""
        # Gujarat
        if pin_prefix == "39":  # Gujarat
            return 100
        # Maharashtra
        elif pin_prefix == "40":
            return 300
        # Rajasthan
        elif pin_prefix == "30":
            return 500
        # Madhya Pradesh
        elif pin_prefix == "45":
            return 600
        # Delhi
        elif pin_prefix == "11":
            return 1200
        # Default
        else:
            return 800
    
    async def run(self, items: list, margin_percent: float = 5.0, pincode: str = "395006") -> PricingResult:
        """Run pricing calculation for all items."""
        total_cost = 0
        item_costs = []
        
        for item in items:
            # Fetch price
            price = await self.fetch_mcx_price(item.grade)
            
            # Calculate weight
            weight = self.calculate_weight(item)
            
            # Calculate costs
            material_cost = weight.total_weight_ton * price.price_per_ton
            logistics_cost = self.calculate_logistics_cost(pincode, weight.total_weight_ton)
            margin = material_cost * (margin_percent / 100)
            
            item_cost = CostBreakdown(
                material_cost=round(material_cost, 2),
                logistics_cost=round(logistics_cost, 2),
                loading_cost=0,  # Included in logistics
                margin_amount=round(margin, 2),
                subtotal=round(material_cost + logistics_cost + margin, 2)
            )
            
            item_costs.append(item_cost)
            total_cost += item_cost.subtotal
        
        return PricingResult(
            item_costs=item_costs,
            total_subtotal=total_cost,
            margin_percent=margin_percent
        )
