# Agent Specifications
# Smart RFQ Intelligence Pipeline — Sub-Agent Definitions

---

## AGENT DESIGN PRINCIPLES

Every agent in SRIP follows the **RLM (Retrieval-augmented Language Model) unit pattern**:

```
Agent Invocation
    ↓
1. RETRIEVE — Pull relevant context from ChromaDB or live APIs
2. AUGMENT — Merge retrieved context with agent's system prompt
3. REASON  — Call Groq LLM with augmented prompt
4. ACT     — Execute tool calls or produce structured output
5. RETURN  — Validated JSON output + confidence score + latency
```

Each agent is implemented as a Python class with a single `.run(input: dict) -> AgentResult` interface.

```python
from dataclasses import dataclass
from typing import Any

@dataclass
class AgentResult:
    agent_name: str
    rfq_id: str
    status: str           # "success" | "partial" | "failed" | "review_needed"
    output: dict
    confidence: float     # 0.0 - 1.0
    latency_ms: int
    error: str | None = None
```

---

## AGENT 0: ORCHESTRATOR AGENT

**File:** `backend/app/agents/orchestrator.py`  
**Model:** `llama3-70b-8192` (Groq)  
**Role:** Master planner. Reads incoming RFQ metadata and produces a dependency-ordered execution plan. Dispatches sub-agents, handles failures, aggregates results.

### System Prompt

```
You are the Orchestrator Agent for an Indian steel RFQ processing pipeline.
Your job is to analyse an incoming RFQ and produce a JSON execution plan.

Available agents: OCRAgent, NERAgent, ValidatorAgent, PricingAgent, GSTAgent, QuoteAgent, CommunicationAgent.

Rules:
- If input is an image or PDF, OCRAgent MUST be step 1.
- If input is raw text, skip OCRAgent and start with NERAgent.
- PricingAgent MUST come after ValidatorAgent.
- GSTAgent MUST come after PricingAgent.
- QuoteAgent is always last before CommunicationAgent.
- Each step must define a fallback action.

Return ONLY valid JSON matching the ExecutionPlan schema. No explanation.
```

### Input Schema

```python
class OrchestratorInput(BaseModel):
    rfq_id: str
    source_channel: str           # whatsapp | email | api
    file_type: str | None         # jpg | png | pdf | text | None
    file_path: str | None
    raw_text: str | None
    sender_contact: str | None
```

### Output Schema

```python
class ExecutionStep(BaseModel):
    step: int
    agent: str
    input_template: dict          # references to prior step outputs via {{stepN.output.field}}
    depends_on: list[int]
    fallback: str

class ExecutionPlan(BaseModel):
    rfq_id: str
    steps: list[ExecutionStep]
    estimated_complexity: str     # simple | standard | complex
```

---

## AGENT 1: OCR AGENT

**File:** `backend/app/agents/ocr_agent.py`  
**Model:** `llama3-70b-8192` with vision OR Tesseract fallback  
**Role:** Converts image/PDF to clean, structured raw text. Handles blurry Pandesara dockets, stamps, handwriting.

### Processing Pipeline

```
Input: image path
    ↓
Preprocess (PIL):
  - Convert to grayscale
  - Increase contrast (factor 2.0)
  - Deskew (Pillow + OpenCV)
  - Resize to min 1200px width
    ↓
Attempt 1: Groq Vision (base64 image)
    ↓ (if OCR confidence < 0.5)
Attempt 2: Tesseract (--psm 6, lang=eng+hin)
    ↓
Post-process:
  - Remove extra whitespace
  - Fix common OCR errors (0→O, 1→I in steel context)
    ↓
Output: raw_text + ocr_confidence
```

### System Prompt

```
You are an OCR and text extraction specialist for Indian steel industry documents.
The image contains a Request for Quotation (RFQ) from a steel buyer.
Documents may be handwritten, stamped, or printed in mixed Hindi-English.

Extract ALL text visible in the image. Do not interpret or classify — just extract.
Pay special attention to: numbers (dimensions, quantities), grade names (Fe 500, IS 2062),
and location names.

Return JSON: { "extracted_text": "...", "confidence": 0.0-1.0, "language_detected": "en|hi|gu|mixed" }
```

### Input Schema

```python
class OCRInput(BaseModel):
    rfq_id: str
    file_path: str                # local path or URL
    file_type: str                # jpg | png | pdf
```

### Output Schema

```python
class OCROutput(BaseModel):
    raw_text: str
    ocr_confidence: float
    language_detected: str        # en | hi | gu | mixed
    page_count: int               # for PDFs
```

### Failure Handling

```python
if output.ocr_confidence < 0.5:
    # Send WhatsApp message asking for rescan
    return AgentResult(
        status="failed",
        error="Image clarity insufficient. OCR confidence: {:.0%}".format(conf)
    )
```

---

## AGENT 2: NER AGENT (Steel Named Entity Recognition)

**File:** `backend/app/agents/ner_agent.py`  
**Model:** `llama3-70b-8192` (Groq)  
**RAG:** ChromaDB `is_codes` + `material_synonyms` collections  
**Role:** Extracts structured steel entities from raw text. The most critical agent — accuracy here determines everything downstream.

### RAG Retrieval Step

Before calling the LLM, retrieve relevant IS code context:

```python
def retrieve_steel_context(raw_text: str, chroma_client) -> str:
    """Retrieve top-5 IS code chunks relevant to the RFQ text."""
    results = chroma_client.query(
        collection="is_codes",
        query_texts=[raw_text],
        n_results=5
    )
    synonym_results = chroma_client.query(
        collection="material_synonyms",
        query_texts=[raw_text],
        n_results=5
    )
    return format_context(results, synonym_results)
```

### System Prompt (with RAG injection)

```
You are an expert Indian Steel Metallurgist and procurement specialist.
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
   - Structural: "E250", "E350" → grades per IS2062
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
```

### Input Schema

```python
class NERInput(BaseModel):
    rfq_id: str
    raw_text: str
    retrieved_context: str        # from ChromaDB
```

### Output Schema

```python
class LineItem(BaseModel):
    item_id: int
    material_type: str
    is_code: str | None
    grade: str | None
    shape: str | None
    dimensions: dict              # diameter_mm, width_mm, thickness_mm, length_ft
    quantity: dict                # value, unit
    destination_pincode: str | None
    destination_raw: str | None   # "Sachin GIDC" - free text
    urgency: str | None           # "immediate" | "3 days" | None
    confidence_scores: dict       # per-field confidence

class NEROutput(BaseModel):
    rfq_id: str
    line_items: list[LineItem]
    language: str
    is_sub_inquiry: bool          # detected if forwarded RFQ pattern
    price_inclusive_gst: bool
    overall_confidence: float
```

---

## AGENT 3: VALIDATOR AGENT

**File:** `backend/app/agents/validator_agent.py`  
**Model:** `llama3-8b-8192` (Groq — fast model sufficient)  
**RAG:** Static IS code lookup table (Python dict, no vector search needed)  
**Role:** Cross-references extracted entities against BIS standards. Flags impossible combinations. Maps to canonical values.

### Validation Rules Engine

```python
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
    ("TMT_Bar", "E250"),       # E250 is structural, not TMT
    ("TMT_Bar", "E350"),
    ("Structural_Plate", "Fe 500"),  # Fe500 is TMT grade
    ("Structural_Plate", "Fe 550"),
]
```

### Validation Actions

```python
def validate_line_item(item: LineItem) -> ValidationResult:
    errors = []
    warnings = []
    
    # 1. Grade exists?
    if item.grade not in ALL_VALID_GRADES:
        errors.append(f"Unknown grade: {item.grade}")
    
    # 2. Grade + Material combo valid?
    if (item.material_type, item.grade) in IMPOSSIBLE_COMBINATIONS:
        errors.append(f"Impossible: {item.material_type} cannot be {item.grade}")
    
    # 3. Auto-assign IS code
    if not item.is_code:
        item.is_code = VALID_GRADES[item.material_type]["is_code"]
        warnings.append("IS code auto-assigned")
    
    # 4. Dimension sanity check
    if item.material_type == "TMT_Bar" and item.dimensions.diameter_mm:
        valid_range = VALID_GRADES["TMT_Bar"]["diameter_range_mm"]
        if not (valid_range[0] <= item.dimensions.diameter_mm <= valid_range[1]):
            errors.append(f"Diameter {item.dimensions.diameter_mm}mm out of BIS range")
    
    # 5. Auto-assign standard length if missing
    if item.material_type == "TMT_Bar" and not item.dimensions.get("length_ft"):
        item.dimensions["length_ft"] = 40
        warnings.append("Standard 40ft length assumed for TMT")
    
    return ValidationResult(
        item=item,
        status="valid" if not errors else "invalid",
        errors=errors,
        warnings=warnings
    )
```

---

## AGENT 4: PRICING AGENT

**File:** `backend/app/agents/pricing_agent.py`  
**Model:** `mixtral-8x7b-32768` (Groq — strong math reasoning)  
**RAG:** Serper search results + Redis cache + logistics rate table  
**Role:** Fetches live MCX prices, calculates weight, logistics, and produces full cost breakdown.

### Step 1: Live Price Fetch (Serper + Redis)

```python
async def fetch_mcx_price(grade: str, redis_client, serper_client) -> PriceResult:
    cache_key = f"mcx:{grade.replace(' ', '')}:rate"
    
    # Try Redis cache first
    cached = await redis_client.get(cache_key)
    if cached:
        return PriceResult(price=float(cached), source="cache", age_seconds=...)
    
    # Serper web search
    query = f"MCX steel price today {grade} TMT bar India per ton"
    results = await serper_client.search(query, num=5)
    
    # LLM to parse search results and extract price
    prompt = f"""
    Extract the current steel price per metric ton (₹/ton) from these search results.
    Grade: {grade}
    Search Results:
    {format_serper_results(results)}
    
    Return JSON: {{"price_per_ton": <number>, "source": "<site>", "as_of": "<date>"}}
    If you cannot find a reliable price, return {{"price_per_ton": null}}.
    """
    
    price_data = await groq_call(prompt, model="mixtral-8x7b-32768")
    
    if price_data["price_per_ton"]:
        await redis_client.setex(cache_key, MCX_CACHE_TTL, price_data["price_per_ton"])
    else:
        # Fallback: use base mock price
        price_data["price_per_ton"] = BASE_FALLBACK_PRICES.get(grade, 60000)
        price_data["source"] = "fallback"
    
    return PriceResult(**price_data)
```

### Step 2: Weight Calculation Formulas

```python
def calculate_weight(item: ValidatedLineItem) -> WeightResult:
    """
    Standard BIS/industry formulas for weight calculation.
    All outputs in kg per meter, then scaled to quantity.
    """
    
    if item.material_type == "TMT_Bar":
        # Formula: D² / 162.28 (kg/m) — BIS standard for round bars
        d = item.dimensions["diameter_mm"]
        weight_kg_per_m = (d ** 2) / 162.28
        total_length_m = item.dimensions.get("length_ft", 40) * 0.3048
        unit_weight_kg = weight_kg_per_m * total_length_m
        # Convert quantity
        if item.quantity["unit"] == "tons":
            total_weight_ton = item.quantity["value"]
        elif item.quantity["unit"] == "pieces":
            total_weight_ton = (unit_weight_kg * item.quantity["value"]) / 1000
        elif item.quantity["unit"] == "bundles":
            # 1 bundle = 7 rods for 12mm, 5 rods for 16mm+ (industry standard)
            rods_per_bundle = 7 if d <= 12 else 5
            total_pieces = item.quantity["value"] * rods_per_bundle
            total_weight_ton = (unit_weight_kg * total_pieces) / 1000
    
    elif item.material_type == "Structural_Plate":
        # Formula: L × W × T × 7.85 (density of steel g/cm³) / 1000
        t = item.dimensions.get("thickness_mm", 10)
        w = item.dimensions.get("width_mm", 1250)
        l = item.dimensions.get("length_mm", 6000)
        unit_weight_kg = (l * w * t * 7.85) / (1000 * 1000 * 1000) * 1000
        total_weight_ton = (unit_weight_kg * item.quantity["value"]) / 1000 \
            if item.quantity["unit"] == "pieces" else item.quantity["value"]
    
    elif item.material_type == "Angle":
        # Formula: (A + B - T) × T × 0.00785 (kg/mm²/m)
        a = item.dimensions.get("leg_a_mm", 50)
        b = item.dimensions.get("leg_b_mm", a)   # equal angle
        t = item.dimensions.get("thickness_mm", 5)
        weight_kg_per_m = (a + b - t) * t * 0.00785
        total_length_m = item.quantity["value"] if item.quantity["unit"] == "meters" else \
                         item.quantity["value"] * 6  # assume 6m lengths
        total_weight_ton = (weight_kg_per_m * total_length_m) / 1000
    
    return WeightResult(
        formula_used=f"Shape:{item.material_type}",
        unit_weight_kg=unit_weight_kg,
        total_weight_ton=total_weight_ton
    )
```

### Step 3: Full Cost Assembly

```python
def assemble_cost(item, weight, price, margin_pct, pincode) -> CostBreakdown:
    material_cost = weight.total_weight_ton * price.price_per_ton
    
    # Logistics: base rate per ton + loading
    distance_km = estimate_distance(pincode, ORIGIN_PINCODE)
    logistics_rate = get_logistics_rate(distance_km)  # ₹/ton from rate table
    logistics_cost = weight.total_weight_ton * logistics_rate
    loading_cost = weight.total_weight_ton * 1500  # ₹1500/ton standard
    
    subtotal = material_cost + logistics_cost + loading_cost
    
    # Apply margin
    margin_amount = subtotal * (margin_pct / 100)
    subtotal_with_margin = subtotal + margin_amount
    
    return CostBreakdown(
        material_cost=round(material_cost, 2),
        logistics_cost=round(logistics_cost, 2),
        loading_cost=round(loading_cost, 2),
        margin_amount=round(margin_amount, 2),
        subtotal=round(subtotal_with_margin, 2)
    )
```

---

## AGENT 5: GST AGENT

**File:** `backend/app/agents/gst_agent.py`  
**Model:** `llama3-8b-8192` (Groq)  
**RAG:** HSN/GST rules from ChromaDB  
**Role:** Determines tax jurisdiction, assigns HSN code, calculates GST split.

### Core Logic

```python
GUJARAT_PINCODE_PREFIXES = ["36", "37", "38", "39"]
HSN_MAP = {
    "TMT_Bar":          "7213",
    "Structural_Plate": "7208",
    "Angle":            "7216",
    "Channel":          "7216",
    "Flat_Bar":         "7214",
    "Square_Bar":       "7214",
    "Pipe":             "7306",
}
GST_RATE = 0.18

def calculate_gst(subtotal: float, delivery_pincode: str, material_type: str) -> GSTResult:
    # Determine jurisdiction
    is_gujarat = delivery_pincode[:2] in GUJARAT_PINCODE_PREFIXES
    hsn_code = HSN_MAP.get(material_type, "7214")
    gst_amount = subtotal * GST_RATE
    
    if is_gujarat:
        return GSTResult(
            tax_type="CGST+SGST",
            cgst=round(gst_amount / 2, 2),
            sgst=round(gst_amount / 2, 2),
            igst=0.0,
            total_gst=round(gst_amount, 2),
            hsn_code=hsn_code,
            gst_rate_pct=18.0
        )
    else:
        return GSTResult(
            tax_type="IGST",
            cgst=0.0,
            sgst=0.0,
            igst=round(gst_amount, 2),
            total_gst=round(gst_amount, 2),
            hsn_code=hsn_code,
            gst_rate_pct=18.0
        )
```

---

## AGENT 6: QUOTE AGENT

**File:** `backend/app/agents/quote_agent.py`  
**Model:** `llama3-70b-8192` (Groq — for any LLM-generated text fields)  
**Role:** Assembles all pipeline results into a professional PDF quote.

### Template Variables

```python
@dataclass
class QuoteContext:
    # Header
    company_name: str
    company_gstin: str
    quote_number: str           # QT-{rfq_id[:8].upper()}-{date}
    quote_date: str
    valid_until: str            # date + 24 hours
    
    # Buyer
    buyer_contact: str
    buyer_location: str
    
    # Line Items (list)
    line_items: list[dict]      # material, grade, dims, qty, weight, rate, amount
    
    # Totals
    subtotal: float
    logistics_total: float
    margin_amount: float
    gst_type: str
    gst_amount: float
    grand_total: float
    
    # Footer
    is_codes_referenced: list[str]  # ["IS 1786:2008", "IS 2062:2011"]
    notes: str
    bank_details: str
```

### PDF Generation

```python
async def generate_pdf(context: QuoteContext) -> str:
    """Render Jinja2 HTML template → WeasyPrint → PDF file."""
    template = env.get_template("quote_template.html")
    html_content = template.render(**asdict(context))
    
    pdf_path = f"storage/quotes/QT-{context.quote_number}.pdf"
    HTML(string=html_content).write_pdf(pdf_path)
    
    return pdf_path
```

---

## AGENT 7: COMMUNICATION AGENT

**File:** `backend/app/agents/communication_agent.py`  
**Model:** `llama3-8b-8192` (Groq)  
**Role:** Sends outputs to correct channels. Creates internal tasks. Updates RFQ status.

### WhatsApp Message Template

```python
WHATSAPP_SUMMARY_PROMPT = """
Generate a short, professional WhatsApp message (under 200 words) in English 
summarizing the quote. Tone: respectful, business-like.
Include: grade, quantity, final price, validity period.
End with: "Quote PDF attached. Valid for 24 hours."
Do not include detailed breakdowns — just the total.

Quote data: {quote_summary}
"""
```

### Channel Routing

```python
async def dispatch_quote(rfq: RFQ, pdf_path: str, summary_text: str):
    if rfq.source_channel == "whatsapp" and rfq.sender_contact:
        await send_whatsapp(
            to=rfq.sender_contact,
            text=summary_text,
            media_url=pdf_path
        )
    elif rfq.source_channel == "email":
        await send_email_reply(
            to=rfq.sender_email,
            subject=f"Quote: {rfq.rfq_id[:8]}",
            body=summary_text,
            attachment=pdf_path
        )
    
    # Always: create internal task
    await create_task(
        title=f"Verify inventory: {rfq.summary_line}",
        rfq_id=rfq.rfq_id,
        priority="high" if rfq.urgency == "immediate" else "normal"
    )
    
    # Update DB status
    await update_rfq_status(rfq.rfq_id, "quoted")
```

---

## AGENT INTERACTION MATRIX

```
          OCR  NER  VAL  PRC  GST  QTE  COM
OCR        —   feeds  —    —    —    —    —
NER        —    —   feeds  —    —    —    —
VAL        —    —    —   feeds feeds  —    —
PRC        —    —    —    —   feeds feeds  —
GST        —    —    —    —    —   feeds  —
QTE        —    —    —    —    —    —   feeds
COM        —    —    —    —    —    —    —

Legend: "feeds" = output of row agent is input to column agent
```

---

## KNOWLEDGE SEEDING (at startup)

```python
# backend/app/core/rag/seed_knowledge.py

def seed_chroma():
    """Run once at startup to populate ChromaDB with steel domain knowledge."""
    
    # 1. IS Codes
    with open("knowledge/is_codes.json") as f:
        is_codes = json.load(f)
    chroma.add_documents(
        collection="is_codes",
        documents=[format_is_code_doc(code) for code in is_codes],
        ids=[code["id"] for code in is_codes]
    )
    
    # 2. Material synonyms
    with open("knowledge/material_synonyms.json") as f:
        synonyms = json.load(f)
    chroma.add_documents(
        collection="material_synonyms",
        documents=[f"{s['alias']} means {s['canonical']}: {s['context']}" 
                   for s in synonyms],
        ids=[s["id"] for s in synonyms]
    )
    
    # 3. HSN/GST rules
    # ... similar pattern
    
    # 4. Weight formula documentation
    # ... similar pattern

    print("ChromaDB seeded with steel domain knowledge.")
```

---

## AGENT TESTING STRATEGY

Each agent has its own test file in `backend/tests/agents/`.

### Test Cases per Agent

| Agent | Test Case | Input | Expected Output |
|-------|-----------|-------|----------------|
| OCR | Clean printed RFQ | Clear JPG | confidence > 0.9 |
| OCR | Blurry handwritten | Noisy image | confidence < 0.5 → status: failed |
| NER | "12mm sariya 10 ton" | Hinglish text | TMT_Bar, Fe500, 12mm, 10 tons |
| NER | Multi-item BOQ | Excel-like text | 3 line items extracted |
| VAL | "Fe999" grade | Extracted entity | error: unknown grade |
| VAL | "TMT E250" combo | Extracted entity | error: impossible combination |
| PRG | TMT 12mm 10T | Validated entity | weight ≈ 8.9 tons (D²/162 × 40ft × 10T / unit_wt) |
| GST | Gujarat pincode | subtotal + 380001 | CGST+SGST, 18% |
| GST | Non-Gujarat pincode | subtotal + 110001 | IGST, 18% |
