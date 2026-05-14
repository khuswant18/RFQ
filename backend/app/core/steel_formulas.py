"""Steel formulas and constants loaded from knowledge files."""
import json
import os
from typing import Dict, Any


def _load_json(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        raise RuntimeError(f"Knowledge file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_weight_formulas() -> Dict[str, Any]:
    rules_path = os.getenv("WEIGHT_FORMULAS_PATH", "app/knowledge/weight_formulas.json")
    rules = _load_json(rules_path)
    return {rule.get("material"): rule for rule in rules if rule.get("material")}


def load_is_code_rules() -> Dict[str, Any]:
    rules_path = os.getenv("IS_CODES_PATH", "app/knowledge/is_codes.json")
    data = _load_json(rules_path)
    return {rule.get("is_code"): rule for rule in data.get("is_codes", []) if rule.get("is_code")}


def load_material_is_code_map() -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    for rule in load_is_code_rules().values():
        for material in rule.get("materials", []) or []:
            mapping[material] = rule.get("is_code")
    return mapping


WEIGHT_FORMULAS = load_weight_formulas()
IS_CODE_RULES = load_is_code_rules()
MATERIAL_IS_CODE_MAP = load_material_is_code_map()
