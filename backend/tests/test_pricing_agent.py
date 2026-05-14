"""
Tests for Pricing Agent weight calculation and price fetching.
Run with: pytest tests/test_pricing_agent.py -v
"""
import pytest
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestWeightCalculation:
    """Test weight calculation using BIS standard formulas."""

    @pytest.fixture(autouse=True)
    def setup_env(self, tmp_path, monkeypatch):
        """Set up required env vars and weight formulas file."""
        weight_formulas = [
            {
                "material": "TMT_Bar",
                "type": "tmt_bar",
                "divisor": 162,
                "standard_length_ft": 40
            },
            {
                "material": "Structural_Plate",
                "type": "plate",
                "density_g_cm3": 7.85
            },
        ]
        formulas_path = tmp_path / "weight_formulas.json"
        formulas_path.write_text(json.dumps(weight_formulas))
        monkeypatch.setenv("WEIGHT_FORMULAS_PATH", str(formulas_path))

        # Logistics rates
        logistics_rates = [
            {"destination_pincode_prefix": "39", "rate_per_ton": 500},
            {"destination_pincode_prefix": "40", "rate_per_ton": 1200},
            {"destination_pincode_prefix": "49", "rate_per_ton": 2000},
        ]
        rates_path = tmp_path / "logistics_rates.json"
        rates_path.write_text(json.dumps(logistics_rates))
        monkeypatch.setenv("LOGISTICS_RATES_PATH", str(rates_path))

    def test_tmt_bar_weight_12mm_10_tons(self):
        """12mm TMT Bar @ 10 tons → total_weight_ton = 10"""
        from app.agents.pricing_agent import PricingAgent
        agent = PricingAgent()

        item = {
            "material_type": "TMT_Bar",
            "dimensions": {"diameter_mm": 12, "length_ft": 40},
            "quantity": {"value": 10, "unit": "tons"}
        }
        result = agent.calculate_weight(item)
        assert result.total_weight_ton == 10.0

    def test_tmt_bar_weight_12mm_pieces(self):
        """12mm TMT Bar in pieces → correct weight conversion."""
        from app.agents.pricing_agent import PricingAgent
        agent = PricingAgent()

        item = {
            "material_type": "TMT_Bar",
            "dimensions": {"diameter_mm": 12, "length_ft": 40},
            "quantity": {"value": 100, "unit": "pieces"}
        }
        result = agent.calculate_weight(item)
        # Each 12mm bar: (12^2/162) kg/m * (40ft * 0.3048 m/ft) = 0.888.. * 12.192 = ~10.84 kg
        # 100 pieces: ~1084 kg = ~1.084 ton
        assert 1.0 < result.total_weight_ton < 1.2

    def test_tmt_bar_bis_formula_accuracy(self):
        """Verify BIS formula: weight_kg_per_m = d²/162"""
        from app.agents.pricing_agent import PricingAgent
        agent = PricingAgent()

        item = {
            "material_type": "TMT_Bar",
            "dimensions": {"diameter_mm": 16, "length_ft": 40},
            "quantity": {"value": 1, "unit": "pieces"}
        }
        result = agent.calculate_weight(item)
        # 16mm: (16^2/162) = 1.5802 kg/m
        # 40ft = 12.192m
        # 1 piece = 1.5802 * 12.192 = ~19.26 kg = ~0.01926 ton
        assert 0.019 < result.total_weight_ton < 0.020

    def test_tmt_bar_default_diameter(self):
        """TMT Bar with missing diameter should default to 12mm."""
        from app.agents.pricing_agent import PricingAgent
        agent = PricingAgent()

        item = {
            "material_type": "TMT_Bar",
            "dimensions": {"length_ft": 40},
            "quantity": {"value": 5, "unit": "tons"}
        }
        result = agent.calculate_weight(item)
        assert result.total_weight_ton == 5.0  # Direct conversion for tons

    def test_plate_direct_tons(self):
        """Structural plate with quantity in tons → direct conversion."""
        from app.agents.pricing_agent import PricingAgent
        agent = PricingAgent()

        item = {
            "material_type": "Structural_Plate",
            "dimensions": {"thickness_mm": 6},
            "quantity": {"value": 3, "unit": "tons"}
        }
        result = agent.calculate_weight(item)
        assert result.total_weight_ton == 3.0

    def test_unknown_material_tons_fallback(self):
        """Unknown material with tons → direct conversion fallback."""
        from app.agents.pricing_agent import PricingAgent
        agent = PricingAgent()

        item = {
            "material_type": "Pipe",  # Not in the test formulas
            "dimensions": {},
            "quantity": {"value": 7, "unit": "tons"}
        }
        result = agent.calculate_weight(item)
        assert result.total_weight_ton == 7.0


class TestLogisticsCost:
    """Test logistics cost calculation."""

    @pytest.fixture(autouse=True)
    def setup_env(self, tmp_path, monkeypatch):
        weight_formulas = [{"material": "TMT_Bar", "type": "tmt_bar", "divisor": 162, "standard_length_ft": 40}]
        formulas_path = tmp_path / "weight_formulas.json"
        formulas_path.write_text(json.dumps(weight_formulas))
        monkeypatch.setenv("WEIGHT_FORMULAS_PATH", str(formulas_path))

        logistics_rates = [
            {"destination_pincode_prefix": "39", "rate_per_ton": 500},
            {"destination_pincode_prefix": "40", "rate_per_ton": 1200},
            {"destination_pincode_prefix": "49", "rate_per_ton": 2000},
        ]
        rates_path = tmp_path / "logistics_rates.json"
        rates_path.write_text(json.dumps(logistics_rates))
        monkeypatch.setenv("LOGISTICS_RATES_PATH", str(rates_path))
        monkeypatch.setenv("LOADING_COST_PER_TON", "0")

    def test_surat_delivery(self):
        """Surat (39xxxx) → ₹500/ton"""
        from app.agents.pricing_agent import PricingAgent
        agent = PricingAgent()
        cost = agent.calculate_logistics_cost("395006", 10)
        assert cost == 5000.0

    def test_mumbai_delivery(self):
        """Mumbai (40xxxx) → ₹1200/ton"""
        from app.agents.pricing_agent import PricingAgent
        agent = PricingAgent()
        cost = agent.calculate_logistics_cost("400001", 5)
        assert cost == 6000.0

    def test_unknown_pincode_fallback(self):
        """Unknown pincode → fallback ₹1500/ton"""
        from app.agents.pricing_agent import PricingAgent
        agent = PricingAgent()
        cost = agent.calculate_logistics_cost("110001", 10)
        assert cost == 15000.0  # ₹1500/ton × 10


class TestMCXPriceFetching:
    """Test MCX price fetching and caching."""

    @pytest.fixture(autouse=True)
    def setup_env(self, tmp_path, monkeypatch):
        weight_formulas = [{"material": "TMT_Bar", "type": "tmt_bar", "divisor": 162, "standard_length_ft": 40}]
        formulas_path = tmp_path / "weight_formulas.json"
        formulas_path.write_text(json.dumps(weight_formulas))
        monkeypatch.setenv("WEIGHT_FORMULAS_PATH", str(formulas_path))

        logistics_rates = [{"destination_pincode_prefix": "39", "rate_per_ton": 500}]
        rates_path = tmp_path / "logistics_rates.json"
        rates_path.write_text(json.dumps(logistics_rates))
        monkeypatch.setenv("LOGISTICS_RATES_PATH", str(rates_path))

    def test_fallback_prices_exist(self):
        """All common grades should have fallback prices."""
        from app.agents.pricing_agent import PricingAgent
        agent = PricingAgent()
        for grade in ["Fe 500", "Fe 500D", "Fe 550", "E250", "E350"]:
            assert grade in agent.FALLBACK_PRICES
            assert 30000 < agent.FALLBACK_PRICES[grade] < 100000

    def test_cache_works(self):
        """Manual cache hit should return cached price."""
        from app.agents.pricing_agent import PricingAgent
        import time
        agent = PricingAgent()

        # Pre-seed cache
        cache_key = "mcx:Fe500:rate"
        agent._price_cache[cache_key] = {
            "price_per_ton": 54000,
            "source": "live",
            "as_of": "today",
            "timestamp": time.time(),
        }

        result = agent.fetch_mcx_price("Fe 500")
        assert result.price_per_ton == 54000
        assert result.source == "live"
