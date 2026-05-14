"""Validator Agent - Cross-references extracted entities against BIS standards."""
import json
import os
from typing import List, Dict, Any

from app.core.rag.chroma_client import ChromaClient

from app.models.rfq import LineItem, ValidationResult


class ValidatorAgent:
    """
    Validator Agent: Cross-references extracted entities against BIS standards.
    Flags impossible combinations and maps to canonical values.
    """

    def __init__(self):
        rules_path = os.getenv("IS_CODES_PATH", "app/knowledge/is_codes.json")
        if not os.path.exists(rules_path):
            raise RuntimeError(f"IS codes rules not found: {rules_path}")

        with open(rules_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.is_code_rules: Dict[str, Dict[str, Any]] = {}
        for rule in data.get("is_codes", []):
            is_code = rule.get("is_code")
            if is_code:
                self.is_code_rules[is_code] = rule

        self.material_is_code: Dict[str, str] = {}
        for rule in self.is_code_rules.values():
            for material in rule.get("materials", []) or []:
                self.material_is_code[material] = rule.get("is_code")

        self.all_valid_grades = set()
        for rule in self.is_code_rules.values():
            self.all_valid_grades.update(rule.get("grades", []))

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

    def validate_line_item(self, item: LineItem) -> ValidationResult:
        """Validate a single line item."""
        errors = []
        warnings = []

        # 1. Grade exists?
        if item.grade not in self.all_valid_grades:
            errors.append(f"Unknown grade: {item.grade}")
            ext = self._external_context(f"grade {item.grade} material {item.material_type}")
            if ext:
                warnings.append(f"External RAG context: {ext}")

        # 2. Auto-assign IS code
        if not item.is_code:
            item.is_code = self.material_is_code.get(item.material_type, "")
            if item.is_code:
                warnings.append("IS code auto-assigned")

        if not item.is_code:
            errors.append("IS code could not be resolved from material type")
            ext = self._external_context(f"material {item.material_type} is code")
            if ext:
                warnings.append(f"External RAG context: {ext}")
            return ValidationResult(
                item=item,
                status="invalid",
                errors=errors,
                warnings=warnings
            )

        rule = self.is_code_rules.get(item.is_code)
        if not rule:
            errors.append(f"No rules found for IS code: {item.is_code}")
            ext = self._external_context(f"is code {item.is_code} grades")
            if ext:
                warnings.append(f"External RAG context: {ext}")
            return ValidationResult(
                item=item,
                status="invalid",
                errors=errors,
                warnings=warnings
            )

        # 3. Grade + Material combo valid?
        if item.grade not in rule.get("grades", []):
            errors.append(f"Grade {item.grade} not valid for {item.is_code}")
            ext = self._external_context(f"grade {item.grade} is code {item.is_code}")
            if ext:
                warnings.append(f"External RAG context: {ext}")

        # 4. Dimension sanity check
        if item.material_type == "TMT_Bar" and item.dimensions and item.dimensions.get("diameter_mm"):
            diameter = item.dimensions["diameter_mm"]
            diameter_range = rule.get("diameter_range_mm")
            if diameter_range and not (diameter_range[0] <= diameter <= diameter_range[1]):
                errors.append(f"Diameter {diameter}mm out of BIS range")

        # 5. Auto-assign standard length if missing
        if item.material_type == "TMT_Bar" and item.dimensions:
            if not item.dimensions.get("length_ft"):
                standard_lengths = rule.get("standard_lengths_ft")
                if standard_lengths:
                    item.dimensions["length_ft"] = standard_lengths[-1]
                    warnings.append("Standard length assumed from BIS rules")

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
