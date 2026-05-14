"""
Tests for GST Agent - jurisdiction, HSN code, and tax calculation.
Run with: pytest tests/test_gst_agent.py -v
"""
import pytest
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestGSTAgent:
    """Test GST jurisdiction logic, HSN mapping, and tax calculation."""

    @pytest.fixture(autouse=True)
    def setup_env(self, tmp_path, monkeypatch):
        """Set up required env vars and knowledge files."""
        hsn_rules = [
            {
                "id": "hsn_1",
                "material": "TMT_Bar",
                "hsn_code": "7213",
                "gst_rate": "18%",
                "description": "TMT bars and rods"
            },
            {
                "id": "hsn_2",
                "material": "Structural_Plate",
                "hsn_code": "7208",
                "gst_rate": "18%",
                "description": "Structural steel plates"
            },
            {
                "id": "hsn_3",
                "material": "Angle",
                "hsn_code": "7216",
                "gst_rate": "18%",
                "description": "Angles, shapes, and sections"
            },
            {
                "id": "hsn_4",
                "material": "Pipe",
                "hsn_code": "7304",
                "gst_rate": "18%",
                "description": "Steel pipes and tubes"
            }
        ]
        hsn_path = tmp_path / "hsn_gst_rules.json"
        hsn_path.write_text(json.dumps(hsn_rules))
        monkeypatch.setenv("GST_RULES_PATH", str(hsn_path))
        monkeypatch.setenv("GST_GUJARAT_PREFIXES", "36,37,38,39")

    def test_intra_state_cgst_sgst(self):
        """Gujarat pincode → CGST+SGST"""
        from app.agents.gst_agent import GSTAgent
        agent = GSTAgent()
        result = agent.run(subtotal=100000, pincode="395006", material_type="TMT_Bar")
        assert result.tax_type == "CGST+SGST"
        assert result.cgst == 9000  # 9% of 100000
        assert result.sgst == 9000
        assert result.igst == 0
        assert result.total_gst == 18000

    def test_inter_state_igst(self):
        """Non-Gujarat pincode → IGST"""
        from app.agents.gst_agent import GSTAgent
        agent = GSTAgent()
        result = agent.run(subtotal=100000, pincode="400001", material_type="TMT_Bar")
        assert result.tax_type == "IGST"
        assert result.igst == 18000  # 18% of 100000
        assert result.cgst == 0
        assert result.sgst == 0
        assert result.total_gst == 18000

    def test_hsn_code_tmt_bar(self):
        """TMT_Bar should have HSN 7213"""
        from app.agents.gst_agent import GSTAgent
        agent = GSTAgent()
        result = agent.run(subtotal=100000, pincode="395006", material_type="TMT_Bar")
        assert result.hsn_code == "7213"

    def test_hsn_code_structural_plate(self):
        """Structural_Plate should have HSN 7208"""
        from app.agents.gst_agent import GSTAgent
        agent = GSTAgent()
        result = agent.run(subtotal=100000, pincode="395006", material_type="Structural_Plate")
        assert result.hsn_code == "7208"

    def test_unknown_material_raises(self):
        """Unknown material should raise RuntimeError since no HSN rule exists."""
        from app.agents.gst_agent import GSTAgent
        agent = GSTAgent()
        with pytest.raises(RuntimeError, match="HSN rule not found"):
            agent.run(subtotal=50000, pincode="395006", material_type="Unknown_Material")

    def test_gst_rounding(self):
        """GST amounts should be properly rounded."""
        from app.agents.gst_agent import GSTAgent
        agent = GSTAgent()
        result = agent.run(subtotal=99999, pincode="395006", material_type="TMT_Bar")
        # 18% = 17999.82, each half = 8999.91
        assert result.cgst == pytest.approx(8999.91, abs=0.01)
        assert result.sgst == pytest.approx(8999.91, abs=0.01)
        assert result.total_gst == pytest.approx(17999.82, abs=0.01)

    def test_zero_subtotal(self):
        """Zero subtotal should give zero GST."""
        from app.agents.gst_agent import GSTAgent
        agent = GSTAgent()
        result = agent.run(subtotal=0, pincode="395006", material_type="TMT_Bar")
        assert result.total_gst == 0

    def test_delhi_is_igst(self):
        """Delhi (110xxx) → IGST since not Gujarat."""
        from app.agents.gst_agent import GSTAgent
        agent = GSTAgent()
        result = agent.run(subtotal=200000, pincode="110001", material_type="TMT_Bar")
        assert result.tax_type == "IGST"
        assert result.igst == 36000
