"""NER Agent - Extracts structured steel entities from raw text."""
import json
import re
import logging
from typing import List, Optional

from app.core.groq_client import GroqClient
try:
    from app.core.rag.chroma_client import ChromaClient
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False

from app.models.rfq import NERInput, NEROutput, LineItem

logger = logging.getLogger("srip.ner")


# ─────────────── JSON normalization ───────────────

def normalize_ner_output(raw_response: str) -> dict:
    """
    Normalize LLM output to consistent NER schema.
    Handles all the ways LLMs return malformed JSON.
    """
    # Strip markdown code blocks if present
    text = raw_response.strip()
    text = re.sub(r'^```(?:json)?\s*', '', text)
    text = re.sub(r'\s*```$', '', text)
    text = text.strip()

    # Remove JS-style comments (// comment and /* comment */)
    text = re.sub(r'//[^\n]*', '', text)
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)

    # Remove trailing commas before } or ]
    text = re.sub(r',\s*([}\]])', r'\1', text)

    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        # Last resort: try to extract JSON object from surrounding text
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group())
            except Exception:
                raise ValueError(f"Could not parse LLM output as JSON: {e}\nRaw: {text[:500]}")
        else:
            raise ValueError(f"No JSON object found in LLM output: {e}\nRaw: {text[:500]}")

    # Normalize line_items structure
    items = data.get("line_items", [])
    if not isinstance(items, list):
        items = [items] if items else []

    normalized_items = []
    for item in items:
        if not isinstance(item, dict):
            continue

        # Normalize quantity field (LLM sometimes returns flat number)
        qty = item.get("quantity", {})
        if isinstance(qty, (int, float)):
            qty = {"value": float(qty), "unit": "tons"}
        elif isinstance(qty, str):
            match = re.match(r'([\d.]+)\s*(\w+)?', qty)
            if match:
                raw_unit = (match.group(2) or "tons").lower()
                # Normalize unit aliases
                unit_map = {
                    "kg": "kg", "kgs": "kg", "kilogram": "kg", "kilograms": "kg",
                    "ton": "tons", "tonne": "tons", "tonnes": "tons", "mt": "tons",
                    "piece": "pieces", "pcs": "pieces", "nos": "pieces", "pc": "pieces",
                    "meter": "meters", "metre": "meters", "mtr": "meters", "m": "meters",
                    "bundle": "bundles",
                }
                qty = {"value": float(match.group(1)), "unit": unit_map.get(raw_unit, raw_unit)}
            else:
                qty = {"value": 0, "unit": "tons"}
        elif isinstance(qty, dict):
            # Normalize the unit inside the dict too
            raw_unit = str(qty.get("unit", "tons")).lower().strip()
            unit_map = {
                "kg": "kg", "kgs": "kg", "kilogram": "kg", "kilograms": "kg",
                "ton": "tons", "tonne": "tons", "tonnes": "tons", "mt": "tons",
                "piece": "pieces", "pcs": "pieces", "nos": "pieces",
                "meter": "meters", "metre": "meters", "mtr": "meters",
                "bundle": "bundles",
            }
            qty["unit"] = unit_map.get(raw_unit, raw_unit)
        else:
            qty = {"value": 0, "unit": "tons"}
        item["quantity"] = qty

        # Normalize dimensions field — material-aware defaults
        dims = item.get("dimensions", {})
        if not isinstance(dims, dict):
            dims = {}
        mat_type = item.get("material_type", "Other")
        if mat_type in ("TMT_Bar", "tmt_bar"):
            # TMT bars use diameter + length
            dims.setdefault("diameter_mm", None)
            dims.setdefault("length_ft", 40)
        elif mat_type in ("Structural_Plate", "Plate", "plate"):
            # Plates use width × length × thickness — do NOT set TMT defaults
            dims.setdefault("width_mm", None)
            dims.setdefault("length_mm", None)
            dims.setdefault("thickness_mm", None)
        else:
            # Other materials — set minimal defaults
            dims.setdefault("thickness_mm", None)
        item["dimensions"] = dims

        # Ensure confidence is a float 0-1
        conf = item.get("confidence", 0.8)
        if isinstance(conf, dict):
            conf = sum(conf.values()) / len(conf) if conf else 0.8
        try:
            conf = float(conf)
        except (TypeError, ValueError):
            conf = 0.8
        item["confidence"] = conf

        # needs_review: True if confidence < 0.7 or grade is unknown
        item.setdefault("needs_review", conf < 0.7)
        item.setdefault("review_reason", None)
        item.setdefault("is_code", "unknown")
        item.setdefault("urgency", "not_specified")
        item.setdefault("destination_pincode", None)
        item.setdefault("destination_city", None)
        item.setdefault("material_type", "Other")
        # Only default grade to Fe 500 for TMT bars — plates have their own grades
        if mat_type in ("TMT_Bar", "tmt_bar"):
            item.setdefault("grade", "Fe 500")
        else:
            item.setdefault("grade", None)

        # Normalize material_type naming
        material_aliases = {
            "plate": "Structural_Plate", "Plate": "Structural_Plate",
            "Carbon Steel Plate": "Structural_Plate",
            "MS Plate": "Structural_Plate",
            "tmt_bar": "TMT_Bar", "TMT": "TMT_Bar", "Rebar": "TMT_Bar",
            "angle": "Angle", "channel": "Channel",
            "flat_bar": "Flat_Bar", "flat bar": "Flat_Bar",
            "pipe": "Pipe", "tube": "Pipe",
        }
        item["material_type"] = material_aliases.get(item["material_type"], item["material_type"])

        # Map destination_raw → destination_city if present
        if item.get("destination_raw") and not item.get("destination_city"):
            item["destination_city"] = item["destination_raw"]

        normalized_items.append(item)

    data["line_items"] = normalized_items
    data.setdefault("overall_confidence",
                     sum(i["confidence"] for i in normalized_items) / max(len(normalized_items), 1)
                     if normalized_items else 0.0)
    data.setdefault("language_detected", data.get("language", "mixed"))
    data.setdefault("raw_keywords_found", [])

    return data


class NERAgent:
    """
    NER Agent: Extracts structured steel entities from raw text.
    Uses RAG (Retrieval-Augmented Generation) with ChromaDB for context.
    """

    def __init__(self):
        self.groq = GroqClient()
        self.chroma = ChromaClient()

    SYSTEM_PROMPT = """You are an expert Indian steel procurement analyst. Extract entities from RFQ text.
You handle ALL steel product types — not just TMT bars. Pay close attention to what the document actually says.

DOMAIN CONTEXT (from BIS standards database):
{retrieved_is_code_context}

SYNONYM MAP (Hinglish/Gujarati terms):
{retrieved_synonyms}

EXTERNAL CONTEXT (from steel specifications):
{retrieved_external_context}

MATERIAL IDENTIFICATION RULES:
- "Sariya" / "saria" / "rod" / "rebar" / "TMT" → material_type: "TMT_Bar", is_code: "IS 1786:2008"
- "plate" / "MS plate" / "Carbon Steel Plate" / "CS plate" / "sheet" / "HR plate" → material_type: "Structural_Plate", is_code: "IS 2062:2011"
- "SS plate" / "stainless steel plate" / "SS 410" / "SS 304" / "SS 316" → material_type: "Structural_Plate", grade: the SS grade stated
- "patti" / "flat" → material_type: "Flat_Bar"
- "angle" / "kona" / "L section" → material_type: "Angle"
- "channel" / "C section" / "ISMC" → material_type: "Channel"
- "pipe" / "tube" / "hollow" → material_type: "Pipe", is_code: "IS 1239"

DIMENSION RULES:
- For plates: extract width_mm, length_mm, thickness_mm (e.g. "1500×6300×25" = width 1500mm, length 6300mm, thickness 25mm)
- For TMT bars: extract diameter_mm (e.g. "12mm") and length_ft (default 40ft if not stated)
- For angles: extract leg_a_mm, leg_b_mm, thickness_mm
- Size patterns: "1500x6300x25" or "1500×6300×25" or "1500*6300*25" are all Width×Length×Thickness in mm

QUANTITY RULES:
- "MT" / "ton" / "tonne" / "टन" → unit: "tons"
- "KG" / "Kg" / "kgs" / "kilogram" → unit: "kg" (DO NOT convert to tons — keep as kg)
- "piece" / "pcs" / "nos" / "Nos" → unit: "pieces"
- "meter" / "mtr" / "RM" / "running meter" → unit: "meters"
- If a table lists quantities per item, create one line_item per row

FORMAL RFQ RULES:
- If the document contains a tender/reference number, extract it into raw_keywords_found
- If the document mentions a delivery location (site, plant, city), extract destination_raw AND destination_pincode
- Known pincodes: Surat→395006, Mumbai→400001, Ahmedabad→380001, Rajkot→360001, Pune→411001, Delhi→110001, Raipur→492001, Nagpur→440001, Dibrugarh→786006, Kolkata→700001, Chennai→600001, Bangalore→560001, Hyderabad→500001
- IS 2062 grades: E250 (most common structural), E350, E410, E450
- IS 1786 grades: Fe 415, Fe 500, Fe 500D, Fe 550, Fe 550D, Fe 600

HINGLISH/GUJARATI:
- "Kamach dar" / "Fe550" → grade: "Fe 550"
- "bhai" = ignore (term of address), "chahiye" = "I want/need"
- Grade mapping: "500" or "Fe500" → "Fe 500", "500D" → "Fe 500D"
- If grade not mentioned for TMT_Bar, default to "Fe 500" and set confidence=0.6
- For plates: if IS 2062 mentioned but no specific grade, use "E250" with confidence=0.7

CONFIDENCE:
- 1.0 = explicitly stated in document
- 0.8 = clearly inferred from context
- 0.5 = guessed/assumed

OUTPUT: Return ONLY a JSON object. No markdown. No explanation. No comments. Strictly valid JSON.

SCHEMA:
{{
  "line_items": [
    {{
      "material_type": "TMT_Bar | Flat_Bar | Angle | Channel | Structural_Plate | Pipe | Other",
      "grade": "Fe 500 | Fe 500D | E250 | E350 | SS 410 | Carbon Steel | other_string | null",
      "is_code": "IS 1786:2008 | IS 2062:2011 | IS 1239 | unknown",
      "dimensions": {{
        "diameter_mm": null_or_number,
        "width_mm": null_or_number,
        "length_mm": null_or_number,
        "thickness_mm": null_or_number,
        "length_ft": null_or_number
      }},
      "quantity": {{
        "value": number,
        "unit": "tons | kg | pieces | meters | bundles"
      }},
      "destination_pincode": "6_digit_string_or_null",
      "destination_raw": "city_or_location_or_null",
      "urgency": "immediate | this_week | this_month | not_specified",
      "confidence": 0.0_to_1.0,
      "needs_review": true_or_false,
      "review_reason": "reason_or_null"
    }}
  ],
  "overall_confidence": 0.0_to_1.0,
  "language": "en | hi | gu | mixed",
  "is_sub_inquiry": false,
  "price_inclusive_gst": false,
  "raw_keywords_found": ["list", "of", "key", "terms", "tender_numbers"]
}}
"""

    def retrieve_steel_context(self, raw_text: str) -> tuple:
        """Retrieve relevant IS code context, synonyms, and external RAG context from ChromaDB."""
        try:
            is_results = self.chroma.query(
                collection="is_codes",
                query_texts=[raw_text],
                n_results=5
            )
            is_context = "\n".join([doc for doc in is_results.get("documents", [[]])[0]])
        except Exception as e:
            logger.warning(f"ChromaDB is_codes query failed: {e}")
            is_context = ""

        try:
            synonym_results = self.chroma.query(
                collection="material_synonyms",
                query_texts=[raw_text],
                n_results=5
            )
            synonyms = "\n".join([doc for doc in synonym_results.get("documents", [[]])[0]])
        except Exception as e:
            logger.warning(f"ChromaDB material_synonyms query failed: {e}")
            synonyms = ""

        try:
            external_results = self.chroma.query(
                collection="external_rag_files",
                query_texts=[raw_text],
                n_results=5
            )
            external_context = "\n".join([doc for doc in external_results.get("documents", [[]])[0]])
        except Exception as e:
            logger.warning(f"ChromaDB external_rag_files query failed: {e}")
            external_context = ""

        return is_context, synonyms, external_context

    def run(self, ner_input: NERInput) -> NEROutput:
        """Run NER extraction on the input text."""
        # Retrieve context from ChromaDB (synonyms first to ground grade/alias mapping)
        is_context, synonyms, external_context = self.retrieve_steel_context(ner_input.raw_text)

        system_prompt = self.SYSTEM_PROMPT.format(
            retrieved_is_code_context=is_context or "No IS code context available",
            retrieved_synonyms=synonyms or "No synonym context available",
            retrieved_external_context=external_context or "No external context available"
        )

        user_prompt = f"""Extract all steel entities from this RFQ:

INPUT TEXT:
{ner_input.raw_text}

Remember: Return ONLY valid JSON. No explanation. No markdown."""

        # Try up to 3 times with increasing temperature if JSON fails
        raw_output = ""
        last_error = None
        entities: dict = {"line_items": [], "overall_confidence": 0.0}
        for attempt in range(3):
            try:
                raw_output = self.groq.call(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    model="llama-3.3-70b-versatile",
                    temperature=0.1 + (attempt * 0.1),
                    max_tokens=2000
                )
                entities = normalize_ner_output(raw_output)
                logger.info(f"NER extraction succeeded on attempt {attempt + 1}, "
                            f"found {len(entities.get('line_items', []))} items")
                break
            except (ValueError, json.JSONDecodeError) as e:
                last_error = e
                logger.warning(f"NER JSON parse failed on attempt {attempt + 1}: {e}")
                if attempt == 2:
                    # All retries failed — return a minimal valid structure
                    logger.error(f"NER extraction failed after 3 attempts: {e}")
                    entities = {
                        "line_items": [],
                        "overall_confidence": 0.0,
                        "language": "mixed",
                        "is_sub_inquiry": False,
                        "price_inclusive_gst": False,
                        "raw_keywords_found": [],
                        "_error": str(e),
                        "_raw_response": raw_output[:500] if raw_output else "no response"
                    }

        # Convert line_items dicts to LineItem models for type safety
        raw_items: list = entities.get("line_items", [])
        line_items = []
        for item_dict in raw_items:
            try:
                line_items.append(LineItem(
                    material_type=item_dict.get("material_type"),
                    is_code=item_dict.get("is_code"),
                    grade=item_dict.get("grade"),
                    dimensions=item_dict.get("dimensions"),
                    quantity=item_dict.get("quantity"),
                    destination_pincode=item_dict.get("destination_pincode"),
                    destination_raw=item_dict.get("destination_raw") or item_dict.get("destination_city"),
                    urgency=item_dict.get("urgency"),
                    confidence_scores={"overall": item_dict.get("confidence", 0.8)},
                ))
            except Exception as e:
                logger.warning(f"Failed to create LineItem from dict: {e}")
                continue

        return NEROutput(
            rfq_id=ner_input.rfq_id,
            line_items=line_items,
            language=entities.get("language") or entities.get("language_detected", "en"),
            is_sub_inquiry=bool(entities.get("is_sub_inquiry")),
            price_inclusive_gst=bool(entities.get("price_inclusive_gst")),
            overall_confidence=float(entities.get("overall_confidence") or 0.0)
        )