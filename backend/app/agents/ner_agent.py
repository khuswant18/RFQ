"""NER Agent - Extracts structured steel entities from raw text."""
import json
from typing import List, Optional

from app.core.groq_client import GroqClient
try:
    from app.core.rag.chroma_client import ChromaClient
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False
    
from app.models.rfq import NERInput, NEROutput, LineItem


class NERAgent:
    """
    NER Agent: Extracts structured steel entities from raw text.
    Uses RAG (Retrieval-Augmented Generation) with ChromaDB for context.
    """
    
    def __init__(self):
        self.groq = GroqClient()
        try:
            self.chroma = ChromaClient()
        except ImportError:
            self.chroma = None
            print("⚠️  ChromaDB not available. NER agent running without RAG.")
    
    SYSTEM_PROMPT = """You are an expert Indian Steel Metallurgist and procurement specialist.
Your task is to extract structured entities from an RFQ document.

DOMAIN CONTEXT (retrieved from BIS standards database):
{retrieved_is_code_context}

SYNONYM MAP (retrieved):
{retrieved_synonyms}

EXTRACTION RULES:
1. Material Type Mapping:
   - "Sariya", "Saria", "TMT", "Rod", "Rib bar", "Rebar", "Kamach dar" → TMT_Bar
   - "Plate", "Sheet", "Patti (wide)" → Structural_Plate
   - "Angle", "L section" → Angle
   - "Channel", "C section" → Channel
   - "Square bar", "SQ" → Square_Bar
   - "Pipe", "Tube", "Hollow" → Pipe
   - "Flat", "Patti" → Flat_Bar

2. Grade Mapping:
   - Numeric: "500", "500D", "550" → Fe500, Fe500D, Fe550 (IS1786)
   - Structural: "E250", "E350" → grade per IS2062
   - If grade not mentioned for TMT_Bar, default to Fe500 and flag confidence=0.6

3. Dimension Extraction:
   - "12mm", "12 mm", "12 Ø", "12 diameter" → diameter_mm: 12
   - "40ft", "40 feet", "standard" (for TMT = 40ft) → length_ft: 40
   - For plates: extract thickness × width

4. Quantity:
   - "ton", "MT", "metric ton", "tonne" → unit: tons
   - "bundle" → note as bundle; flag for conversion
   - "piece", "no", "nos" → unit: pieces

5. Location: extract delivery address / site name / pincode if mentioned.

6. Urgency: extract if "urgent", "immediate", "by [date]" mentioned.

7. Hinglish/Gujarati handling:
   - "bhai" = ignore (term of address)
   - "chahiye" = "I want/need"
   - "rate batao" = "tell me the rate"
   - "tax free / tax inclusive" → price_inclusive_gst: true

Return ONLY valid JSON matching the ExtractedEntity schema.
Include confidence score (0.0-1.0) for each field.
If a field cannot be determined, set it to null and confidence to 0.
"""

    def retrieve_steel_context(self, raw_text: str) -> tuple:
        """Retrieve relevant IS code context and synonyms from ChromaDB."""
        is_results = self.chroma.query(
            collection="is_codes",
            query_texts=[raw_text],
            n_results=5
        )
        synonym_results = self.chroma.query(
            collection="material_synonyms",
            query_texts=[raw_text],
            n_results=5
        )
        
        is_context = "\n".join([doc for doc in is_results.get("documents", [[]])[0]])
        synonyms = "\n".join([doc for doc in synonym_results.get("documents", [[]])[0]])
        
        return is_context, synonyms

    def run(self, ner_input: NERInput) -> NEROutput:
        """Run NER extraction on the input text."""
        # Retrieve context from ChromaDB
        is_context, synonyms = self.retrieve_steel_context(ner_input.raw_text)
        
        # Augment prompt with retrieved context
        system_prompt = self.SYSTEM_PROMPT.format(
            retrieved_is_code_context=is_context,
            retrieved_synonyms=synonyms
        )
        
        # Call LLM
        result = self.groq.call(
            system_prompt=system_prompt,
            user_prompt=ner_input.raw_text,
            model="llama3-70b-8192",
            temperature=0.1
        )
        
        # Parse JSON output
        try:
            entities = json.loads(result)
        except json.JSONDecodeError:
            entities = {
                "line_items": [],
                "language": "en",
                "is_sub_inquiry": False,
                "price_inclusive_gst": False,
                "overall_confidence": 0.0
            }
        
        return NEROutput(
            rfq_id=ner_input.rfq_id,
            line_items=entities.get("line_items", []),
            language=entities.get("language", "en"),
            is_sub_inquiry=entities.get("is_sub_inquiry", False),
            price_inclusive_gst=entities.get("price_inclusive_gst", False),
            overall_confidence=entities.get("overall_confidence", 0.0)
        )
