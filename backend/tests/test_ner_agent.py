"""
Tests for NER Agent JSON normalization and extraction accuracy.
Run with: pytest tests/test_ner_agent.py -v
"""
import pytest
import json
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.agents.ner_agent import normalize_ner_output


class TestNERNormalization:
    """Test that normalize_ner_output handles all LLM output variants."""

    def test_clean_json(self):
        raw = json.dumps({
            "line_items": [{
                "material_type": "TMT_Bar",
                "grade": "Fe 500",
                "dimensions": {"diameter_mm": 12, "length_ft": 40},
                "quantity": {"value": 10, "unit": "tons"},
                "destination_pincode": "395006",
                "confidence": 0.95,
                "urgency": "immediate"
            }],
            "overall_confidence": 0.95
        })
        result = normalize_ner_output(raw)
        assert len(result["line_items"]) == 1
        assert result["line_items"][0]["material_type"] == "TMT_Bar"
        assert result["line_items"][0]["quantity"]["value"] == 10

    def test_json_with_markdown_fences(self):
        raw = '```json\n{"line_items": [{"material_type": "TMT_Bar", "grade": "Fe 500", "dimensions": {"diameter_mm": 12, "length_ft": 40}, "quantity": {"value": 5, "unit": "tons"}, "confidence": 0.9}], "overall_confidence": 0.9}\n```'
        result = normalize_ner_output(raw)
        assert result["line_items"][0]["material_type"] == "TMT_Bar"

    def test_json_with_comments(self):
        raw = '{"line_items": [{"material_type": "TMT_Bar", /* steel rod */ "grade": "Fe 500", "dimensions": {"diameter_mm": 16, "length_ft": 40}, "quantity": {"value": 20, "unit": "tons"}, "confidence": 0.85}], "overall_confidence": 0.85}'
        result = normalize_ner_output(raw)
        assert result["line_items"][0]["dimensions"]["diameter_mm"] == 16

    def test_flat_quantity_normalized(self):
        """LLM returns quantity as a number, not {"value": x, "unit": y}"""
        raw = json.dumps({
            "line_items": [{
                "material_type": "TMT_Bar",
                "grade": "Fe 500",
                "dimensions": {"diameter_mm": 12, "length_ft": 40},
                "quantity": 15,  # Flat number
                "confidence": 0.8
            }],
            "overall_confidence": 0.8
        })
        result = normalize_ner_output(raw)
        assert result["line_items"][0]["quantity"]["value"] == 15
        assert result["line_items"][0]["quantity"]["unit"] == "tons"

    def test_quantity_as_string(self):
        """LLM returns quantity as string like '10 tons'"""
        raw = json.dumps({
            "line_items": [{
                "material_type": "TMT_Bar",
                "grade": "Fe 500",
                "dimensions": {"diameter_mm": 12},
                "quantity": "10 tons",
                "confidence": 0.8
            }],
            "overall_confidence": 0.8
        })
        result = normalize_ner_output(raw)
        assert result["line_items"][0]["quantity"]["value"] == 10
        assert result["line_items"][0]["quantity"]["unit"] == "tons"

    def test_confidence_as_dict_normalized(self):
        """LLM returns confidence as per-field dict"""
        raw = json.dumps({
            "line_items": [{
                "material_type": "TMT_Bar",
                "grade": "Fe 550",
                "dimensions": {"diameter_mm": 20, "length_ft": 40},
                "quantity": {"value": 5, "unit": "tons"},
                "confidence": {"grade": 1.0, "diameter": 0.9, "quantity": 1.0}
            }],
            "overall_confidence": 0.9
        })
        result = normalize_ner_output(raw)
        conf = result["line_items"][0]["confidence"]
        assert isinstance(conf, float)
        assert 0 <= conf <= 1

    def test_trailing_comma_handled(self):
        raw = '{"line_items": [{"material_type": "TMT_Bar", "grade": "E250", "dimensions": {"diameter_mm": 12, "length_ft": 20}, "quantity": {"value": 2, "unit": "tons"}, "confidence": 0.9,}], "overall_confidence": 0.9,}'
        result = normalize_ner_output(raw)
        assert result["line_items"][0]["material_type"] == "TMT_Bar"

    def test_multi_item_rfq(self):
        raw = json.dumps({
            "line_items": [
                {"material_type": "TMT_Bar", "grade": "Fe 500", "dimensions": {"diameter_mm": 12, "length_ft": 40}, "quantity": {"value": 10, "unit": "tons"}, "confidence": 0.95},
                {"material_type": "TMT_Bar", "grade": "Fe 500", "dimensions": {"diameter_mm": 8, "length_ft": 40}, "quantity": {"value": 5, "unit": "tons"}, "confidence": 0.95}
            ],
            "overall_confidence": 0.95
        })
        result = normalize_ner_output(raw)
        assert len(result["line_items"]) == 2
        assert result["line_items"][1]["dimensions"]["diameter_mm"] == 8

    def test_needs_review_auto_set(self):
        """Items with confidence < 0.7 should have needs_review=True"""
        raw = json.dumps({
            "line_items": [{"material_type": "Other", "grade": "unknown", "dimensions": {}, "quantity": {"value": 1, "unit": "tons"}, "confidence": 0.5}],
            "overall_confidence": 0.5
        })
        result = normalize_ner_output(raw)
        assert result["line_items"][0]["needs_review"] == True

    def test_missing_dimensions_defaults(self):
        """Missing dimensions should get default values"""
        raw = json.dumps({
            "line_items": [{"material_type": "TMT_Bar", "grade": "Fe 500", "quantity": {"value": 10, "unit": "tons"}, "confidence": 0.9}],
            "overall_confidence": 0.9
        })
        result = normalize_ner_output(raw)
        dims = result["line_items"][0]["dimensions"]
        assert dims["length_ft"] == 40
        assert dims["diameter_mm"] is None

    def test_json_embedded_in_text(self):
        """JSON embedded in surrounding text should be extracted"""
        raw = 'Here is the extracted data:\n\n{"line_items": [{"material_type": "TMT_Bar", "grade": "Fe 500", "dimensions": {"diameter_mm": 12}, "quantity": {"value": 5, "unit": "tons"}, "confidence": 0.8}]}\n\nI hope this helps!'
        result = normalize_ner_output(raw)
        assert len(result["line_items"]) == 1

    def test_invalid_json_raises(self):
        """Completely invalid input should raise ValueError"""
        with pytest.raises(ValueError):
            normalize_ner_output("This is not JSON at all")

    def test_empty_line_items(self):
        raw = json.dumps({"line_items": [], "overall_confidence": 0.0})
        result = normalize_ner_output(raw)
        assert len(result["line_items"]) == 0
        assert result["overall_confidence"] == 0.0

    def test_overall_confidence_auto_calculated(self):
        raw = json.dumps({
            "line_items": [
                {"material_type": "TMT_Bar", "grade": "Fe 500", "quantity": {"value": 5, "unit": "tons"}, "confidence": 0.9},
                {"material_type": "TMT_Bar", "grade": "Fe 500", "quantity": {"value": 5, "unit": "tons"}, "confidence": 0.7},
            ]
        })
        result = normalize_ner_output(raw)
        assert abs(result["overall_confidence"] - 0.8) < 0.01

    def test_line_comment_handling(self):
        """Test that // line comments are removed"""
        raw = '{"line_items": [{"material_type": "TMT_Bar", // this is TMT\n"grade": "Fe 500", "quantity": {"value": 5, "unit": "tons"}, "confidence": 0.9}]}'
        result = normalize_ner_output(raw)
        assert result["line_items"][0]["material_type"] == "TMT_Bar"
