"""Validator Agent - Cross-references extracted entities against BIS standards."""
from typing import List, Optional

from app.models.rfq import LineItem, ValidationResult


class ValidatorAgent:
    """
    Validator Agent: Cross-references extracted entities against BIS standards.
    Flags impossible combinations and maps to canonical values.
    """

    VALID_GRADES = {
        "TMT_Bar": {
            "grades": ["Fe 415", "Fe 500", "Fe 500D", "Fe 550", "Fe 600"],
            "is_code": "IS 1786:2008",
            "diameter_range_mm": (6, 40),
            "standard_lengths_ft": [20, 40]
        },
        "Structural_Plate": {
            "grades": ["E250", "E350", "E410"],
            "is_code": "IS 2062:2011",
            "thickness_range_mm": (5, 100),
            "width_range_mm": (600, 3000)
        },
        "Angle": {
            "grades": ["E250", "E350"],
            "is_code": "IS 2062:2011",
            "size_range_mm": (20, 200)
        },
        "Channel": {
            "grades": ["E250", "E350"],
            "is_code": "IS 2062:2011"
        },
        "Flat_Bar": {
            "grades": ["E250", "E350"],
            "is_code": "IS 2062:2011"
        }
    }

    IMPOSSIBLE_COMBINATIONS = [
        ("TMT_Bar", "E250"),
        ("TMT_Bar", "E350"),
        ("Structural_Plate", "Fe 500"),
        ("Structural_Plate", "Fe 550"),
    ]

    ALL_VALID_GRADES = set()
    for material, data in VALID_GRADES.items():
        ALL_VALID_GRADES.update(data["grades"])

    def validate_line_item(self, item: LineItem) -> ValidationResult:
        """Validate a single line item."""
        errors = []
        warnings = []

        # 1. Grade exists?
        if item.grade not in self.ALL_VALID_GRADES:
            errors.append(f"Unknown grade: {item.grade}")

        # 2. Grade + Material combo valid?
        if (item.material_type, item.grade) in self.IMPOSSIBLE_COMBINATIONS:
            errors.append(f"Impossible: {item.material_type} cannot be {item.grade}")

        # 3. Auto-assign IS code
        if not item.is_code:
            item.is_code = self.VALID_GRADES.get(item.material_type, {}).get("is_code", "")
            if item.is_code:
                warnings.append("IS code auto-assigned")

        # 4. Dimension sanity check
        if item.material_type == "TMT_Bar" and item.dimensions and item.dimensions.get("diameter_mm"):
            valid_range = self.VALID_GRADES["TMT_Bar"]["diameter_range_mm"]
            diameter = item.dimensions["diameter_mm"]
            if not (valid_range[0] <= diameter <= valid_range[1]):
                errors.append(f"Diameter {diameter}mm out of BIS range")

        # 5. Auto-assign standard length if missing
        if item.material_type == "TMT_Bar" and item.dimensions:
            if not item.dimensions.get("length_ft"):
                item.dimensions["length_ft"] = 40
                warnings.append("Standard 40ft length assumed for TMT")

        return ValidationResult(
            item=item,
            status="valid" if not errors else "invalid",
            errors=errors,
            warnings=warnings
        )

    def run(self, entities: List[LineItem]) -> List[ValidationResult]:
        """Run validation on all extracted entities."""
        results = []
        for entity in entities:
            result = self.validate_line_item(entity)
            results.append(result)
        return results
