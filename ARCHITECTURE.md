# System Architecture
# Smart RFQ Intelligence Pipeline — Agentic RAG (RLM-Inspired)

---

## 1. ARCHITECTURAL PHILOSOPHY

### 1.1 Why Agentic RAG?

A plain LLM call with one prompt cannot reliably handle the full RFQ pipeline because:

1. **Domain complexity** — Steel grades, IS codes, weight formulas, HSN codes are dense specialised knowledge that LLMs hallucinate without grounding.
2. **Live data requirements** — MCX prices change every 15 minutes. A static LLM has no access to today's rates.
3. **Multi-step reasoning** — Extract → Validate → Price → Tax → Format requires distinct reasoning contexts; cramming into one prompt degrades each step.
4. **Error recovery** — When OCR confidence is low, a human review trigger must fire without killing the whole pipeline.

### 1.2 RLM-Inspired Design

We draw from the **Retrieval-augmented Language Model (RLM)** architecture pattern:

```
Traditional LLM:  Prompt → LLM → Response

RLM Pattern:
  Prompt
    ↓
  [Retrieve relevant context from knowledge store]
    ↓
  [Augmented Prompt = Original + Retrieved Context]
    ↓
  LLM (with bounded, grounded context)
    ↓
  Response (grounded, accurate)
```

We extend this recursively: **each sub-agent in our pipeline is itself an RLM unit** — it retrieves its own relevant context before acting. The Orchestrator Agent is an RLM over the *other agents' capabilities*.

```
Orchestrator (RLM over agent tools)
    → dispatches to →
    OCR Agent (RLM over image preprocessing knowledge)
    NER Agent (RLM over Steel Domain Vector DB)
    Validator Agent (RLM over IS Code lookup table)
    Pricing Agent (RLM over live web search results)
    GST Agent (RLM over tax rule DB)
    Quote Agent (RLM over template library)
```

---

## 2. FULL SYSTEM ARCHITECTURE

```
╔══════════════════════════════════════════════════════════════════════════╗
║                        SRIP — SYSTEM ARCHITECTURE                        ║
╚══════════════════════════════════════════════════════════════════════════╝

┌─────────────────────────────────────────────────────────────┐
│                      INPUT CHANNELS                          │
│  [WhatsApp Business]  [Email IMAP]  [REST Upload]           │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│               INGESTION LAYER (FastAPI)                      │
│  • Webhook handler (WhatsApp Meta / Twilio)                  │
│  • Email poller (IMAP every 60s)                             │
│  • File upload endpoint                                      │
│  • Assigns rfq_id (UUID v4)                                  │
│  • Stores raw file → MinIO / S3 / local                      │
│  • Emits task → Celery Queue                                 │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ▼ (async Celery task)
┌─────────────────────────────────────────────────────────────┐
│           ★ ORCHESTRATOR AGENT (Groq LLaMA3-70B) ★          │
│                                                              │
│  Role: Task Planner + Sub-Agent Dispatcher                   │
│  RAG: Retrieves agent capability definitions from ChromaDB   │
│                                                              │
│  1. Reads rfq metadata (channel, file type, raw text)        │
│  2. Produces an EXECUTION PLAN (JSON task graph)             │
│  3. Dispatches sub-agents in dependency order                │
│  4. Aggregates results, handles partial failures             │
│  5. Emits final pipeline_result to database                  │
└──────────────────┬──────────────────────────────────────────┘
                   │
       ┌───────────┼───────────────────────┐
       │           │                       │
       ▼           ▼                       ▼
┌──────────┐ ┌──────────┐          ┌──────────────┐
│OCR AGENT │ │  NER      │          │ VALIDATOR    │
│          │ │  AGENT   │          │ AGENT        │
│ Groq     │ │          │          │              │
│ Vision   │ │ Groq     │ ◄──────► │ IS Code      │
│ (or      │ │ LLaMA3   │  RAG     │ Lookup Table │
│ Tesser-  │ │ 70B      │  from    │ (static dict)│
│ act)     │ │          │  ChromaDB│              │
└────┬─────┘ └────┬─────┘          └──────┬───────┘
     │            │                        │
     └────────────┼────────────────────────┘
                  │ (Extracted + Validated Entity JSON)
                  ▼
┌─────────────────────────────────────────────────────────────┐
│                   PRICING AGENT (Groq)                       │
│                                                              │
│  RAG Sources:                                                │
│  • Serper API → "MCX steel price today" search              │
│  • Redis Cache (15-min TTL) → cached rates                   │
│  • Logistics rate table (pincode-distance map)               │
│                                                              │
│  Computes:                                                   │
│  • Weight (shape formula)                                    │
│  • Material cost (base_rate × weight)                        │
│  • Logistics cost (distance × rate/ton)                      │
│  • Grade surcharge                                           │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│                   GST AGENT (Groq Mixtral-8x7B)              │
│                                                              │
│  RAG Source: Tax rule embeddings in ChromaDB                 │
│  Logic:                                                      │
│  • Pincode → state → IGST vs CGST+SGST                       │
│  • HSN code assignment (7213, 7214, 7216)                    │
│  • 18% GST split                                             │
│  • ITC eligibility flag                                      │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│                   QUOTE AGENT                                │
│                                                              │
│  • Populates Jinja2 quote template                           │
│  • Renders PDF (WeasyPrint / ReportLab)                      │
│  • Generates WhatsApp short summary text                     │
│  • Stores PDF → object storage                               │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│              COMMUNICATION AGENT                             │
│                                                              │
│  • Sends PDF back via WhatsApp Business API                  │
│  • Creates internal task in task store                       │
│  • Updates dashboard state                                   │
│  • Triggers review workflow if confidence < 0.7              │
└─────────────────────────────────────────────────────────────┘

                  ┌─────────────────────────────┐
                  │     SHARED INFRASTRUCTURE    │
                  │                              │
                  │  • ChromaDB (vector store)   │
                  │  • PostgreSQL (RFQ records)  │
                  │  • Redis (rate cache)         │
                  │  • Celery (task queue)        │
                  │  • MinIO / Local (files)     │
                  └─────────────────────────────┘
```

---

## 3. KNOWLEDGE BASES (RAG STORES)

### 3.1 Steel Domain Vector DB (ChromaDB)

Populated at startup from static JSON files. Every NER/Extraction agent call retrieves top-5 relevant chunks before prompting.

**Collections:**

| Collection | Contents | Update Frequency |
|-----------|---------|-----------------|
| `is_codes` | IS1786, IS2062 full grade tables, dimension ranges | Static (re-seed on deploy) |
| `material_synonyms` | Saria→TMT_Bar, Kamach→Fe550, Patti→Flat, etc. | Static + editable by admin |
| `hsn_gst_rules` | HSN codes, GST rates, IGST/SGST trigger rules | Static |
| `weight_formulas` | Shape → formula mapping with examples | Static |
| `agent_capabilities` | Each sub-agent's description, input schema, output schema | Static |

**Embedding Model:** `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`  
(Supports Hindi/Gujarati/English mixed queries)

### 3.2 Live Price RAG (Serper + Redis)

```
Request for current steel price
    ↓
Check Redis key "mcx:Fe500:rate" with TTL=15min
    ↓ (cache miss)
Serper API search: "MCX steel prices today TMT Fe500"
    ↓
Parse top 3 results → extract price + timestamp
    ↓
Store in Redis with 15-min TTL
    ↓
Return to Pricing Agent as grounding context
```

---

## 4. ORCHESTRATOR AGENT — TASK PLANNING

The Orchestrator uses **ReAct-style** (Reason + Act) prompting to produce an execution plan.

### 4.1 Plan Format

```json
{
  "rfq_id": "uuid",
  "execution_plan": [
    {
      "step": 1,
      "agent": "OCRAgent",
      "input": {"file_path": "storage/rfq_001.jpg"},
      "depends_on": [],
      "fallback": "request_clearer_image"
    },
    {
      "step": 2,
      "agent": "NERAgent",
      "input": {"raw_text": "{{step1.output.text}}"},
      "depends_on": [1],
      "fallback": "set_status_incomplete"
    },
    {
      "step": 3,
      "agent": "ValidatorAgent",
      "input": {"entities": "{{step2.output.entities}}"},
      "depends_on": [2],
      "fallback": "flag_for_review"
    },
    {
      "step": 4,
      "agent": "PricingAgent",
      "input": {"validated_items": "{{step3.output}}"},
      "depends_on": [3],
      "fallback": "use_cached_rates"
    },
    {
      "step": 5,
      "agent": "GSTAgent",
      "input": {"cost_data": "{{step4.output}}", "pincode": "{{step2.output.destination_pincode}}"},
      "depends_on": [4],
      "fallback": "use_igst_conservative"
    },
    {
      "step": 6,
      "agent": "QuoteAgent",
      "input": {"full_data": "{{steps1-5.merged}}"},
      "depends_on": [5],
      "fallback": "generate_partial_quote"
    },
    {
      "step": 7,
      "agent": "CommunicationAgent",
      "input": {"pdf_path": "{{step6.output.pdf_path}}", "channel": "whatsapp"},
      "depends_on": [6],
      "fallback": "store_for_manual_send"
    }
  ]
}
```

### 4.2 Failure Handling Policy

| Failure Type | Behaviour |
|-------------|-----------|
| OCR confidence < 50% | Ask user to resend; halt pipeline |
| Grade confidence < 0.7 | Continue with `REVIEW_NEEDED` flag; quote generated but not auto-sent |
| Pricing API failure | Use last Redis-cached rate + add warning to quote |
| GST pincode unknown | Default to IGST (conservative); flag in quote |
| PDF generation failure | Return JSON quote + notify sales manager |

---

## 5. GROQ API USAGE STRATEGY

With 5 Groq API keys available, we implement **round-robin key rotation** with per-key rate limit tracking:

```python
GROQ_KEYS = [KEY_1, KEY_2, KEY_3, KEY_4, KEY_5]

class GroqKeyRotator:
    """Round-robin key rotation with per-key request count tracking."""
    
    def __init__(self, keys: list):
        self.keys = keys
        self.current_index = 0
        self.request_counts = {k: 0 for k in keys}
    
    def get_key(self) -> str:
        key = self.keys[self.current_index % len(self.keys)]
        self.current_index += 1
        self.request_counts[key] += 1
        return key
```

### Agent-to-Model Assignment

| Agent | Groq Model | Reason |
|-------|-----------|--------|
| Orchestrator | `llama3-70b-8192` | Complex task planning, tool calling |
| NER Agent | `llama3-70b-8192` | High accuracy entity extraction |
| Validator | `llama3-8b-8192` | Simple lookup augmentation (fast/cheap) |
| Pricing Agent | `mixtral-8x7b-32768` | Math reasoning, long context for search results |
| GST Agent | `llama3-8b-8192` | Rule-based reasoning (fast) |
| Quote Agent | `llama3-70b-8192` | Structured output generation |
| Communication Agent | `llama3-8b-8192` | Simple message formatting |

---

## 6. DATA FLOW DIAGRAM

```
WhatsApp Image (rfq.jpg)
        │
        ▼
[INGEST] → rfq_id assigned → file saved → Celery task emitted
        │
        ▼
[ORCHESTRATE] → produce execution_plan JSON
        │
        ▼
[OCR] → base64 image → Groq Vision prompt → raw_text extracted
        │
        ▼
[CHROMA RETRIEVE] → query: "TMT Bar, 12mm, Fe500" → top-5 IS code chunks
        │
        ▼
[NER] → (raw_text + retrieved IS chunks) → Groq LLaMA3 → entities JSON
        │
        ▼
[VALIDATE] → entities vs IS code lookup → validated_entities + confidence scores
        │
        ▼
[SERPER SEARCH] → "MCX steel prices today" → parse → cache in Redis
        │
        ▼
[PRICE] → validated_entities + live rates → cost breakdown JSON
        │
        ▼
[GST] → cost + pincode → jurisdiction → tax JSON
        │
        ▼
[QUOTE BUILD] → full data → Jinja2 → WeasyPrint → quote.pdf
        │
        ▼
[COMMUNICATE] → WhatsApp API → send PDF → update DB → notify dashboard
```

---

## 7. DATABASE SCHEMA

### PostgreSQL Tables

```sql
-- RFQ master record
CREATE TABLE rfqs (
    rfq_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_channel  VARCHAR(20) NOT NULL,  -- 'whatsapp'|'email'|'api'
    sender_contact  VARCHAR(20),
    raw_file_url    TEXT,
    raw_text        TEXT,
    received_at     TIMESTAMPTZ DEFAULT NOW(),
    status          VARCHAR(30) DEFAULT 'received',
    -- status: received|processing|extracted|priced|quoted|failed|review_needed
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Extracted line items
CREATE TABLE rfq_line_items (
    item_id         SERIAL PRIMARY KEY,
    rfq_id          UUID REFERENCES rfqs(rfq_id),
    material_type   VARCHAR(50),
    is_code         VARCHAR(20),
    grade           VARCHAR(20),
    shape           VARCHAR(20),
    diameter_mm     NUMERIC,
    width_mm        NUMERIC,
    thickness_mm    NUMERIC,
    length_ft       NUMERIC,
    quantity_value  NUMERIC,
    quantity_unit   VARCHAR(10),
    destination_pin VARCHAR(10),
    confidence      NUMERIC,
    needs_review    BOOLEAN DEFAULT FALSE
);

-- Cost records
CREATE TABLE rfq_costs (
    cost_id             SERIAL PRIMARY KEY,
    rfq_id              UUID REFERENCES rfqs(rfq_id),
    item_id             INTEGER REFERENCES rfq_line_items(item_id),
    base_price_per_ton  NUMERIC,
    total_weight_ton    NUMERIC,
    material_cost       NUMERIC,
    logistics_cost      NUMERIC,
    processing_cost     NUMERIC,
    subtotal            NUMERIC,
    gst_type            VARCHAR(10),
    gst_amount          NUMERIC,
    final_total         NUMERIC,
    margin_percent      NUMERIC,
    rate_fetched_at     TIMESTAMPTZ,
    hsn_code            VARCHAR(10)
);

-- Generated quotes
CREATE TABLE rfq_quotes (
    quote_id    SERIAL PRIMARY KEY,
    rfq_id      UUID REFERENCES rfqs(rfq_id),
    pdf_url     TEXT,
    validity_hours INTEGER DEFAULT 24,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    sent_at     TIMESTAMPTZ,
    sent_via    VARCHAR(20)
);

-- Agent execution log
CREATE TABLE agent_logs (
    log_id      SERIAL PRIMARY KEY,
    rfq_id      UUID,
    agent_name  VARCHAR(50),
    step_number INTEGER,
    input_hash  VARCHAR(64),
    output_schema JSONB,
    confidence  NUMERIC,
    latency_ms  INTEGER,
    status      VARCHAR(20),
    error_msg   TEXT,
    executed_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 8. PROJECT DIRECTORY STRUCTURE

```
srip/
├── .kiro/
│   ├── steering/
│   │   ├── project.md          # Main Kiro context
│   │   └── tech_stack.md       # Stack specifics
│   └── specs/
│       └── rfq_pipeline.md     # Feature spec + tasks
│
├── backend/
│   ├── app/
│   │   ├── main.py             # FastAPI app init
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── ingestion.py
│   │   │       ├── rfq.py
│   │   │       ├── quotes.py
│   │   │       └── webhook.py
│   │   ├── agents/
│   │   │   ├── orchestrator.py
│   │   │   ├── ocr_agent.py
│   │   │   ├── ner_agent.py
│   │   │   ├── validator_agent.py
│   │   │   ├── pricing_agent.py
│   │   │   ├── gst_agent.py
│   │   │   ├── quote_agent.py
│   │   │   └── communication_agent.py
│   │   ├── core/
│   │   │   ├── groq_client.py      # Key rotator + Groq wrapper
│   │   │   ├── rag/
│   │   │   │   ├── chroma_client.py
│   │   │   │   ├── embedder.py
│   │   │   │   └── seed_knowledge.py
│   │   │   ├── steel_formulas.py
│   │   │   ├── gst_logic.py
│   │   │   └── serper_client.py
│   │   ├── knowledge/
│   │   │   ├── is_codes.json
│   │   │   ├── material_synonyms.json
│   │   │   ├── hsn_gst_rules.json
│   │   │   ├── weight_formulas.json
│   │   │   └── logistics_rates.json
│   │   ├── models/
│   │   │   ├── rfq.py          # Pydantic schemas
│   │   │   ├── entities.py
│   │   │   └── costs.py
│   │   ├── tasks/
│   │   │   └── pipeline_tasks.py   # Celery tasks
│   │   └── templates/
│   │       └── quote_template.html # Jinja2 PDF template
│   ├── Dockerfile
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── pages/
│   │   │   ├── Dashboard.jsx
│   │   │   └── RFQDetail.jsx
│   │   └── components/
│   │       ├── RFQFeed.jsx
│   │       ├── CostBreakdown.jsx
│   │       └── AgentTrace.jsx
│   └── package.json
│
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## 9. ENVIRONMENT VARIABLES

```env
# Groq API Keys (5 keys, round-robin rotated)
GROQ_API_KEY_1=gsk_...
GROQ_API_KEY_2=gsk_...
GROQ_API_KEY_3=gsk_...
GROQ_API_KEY_4=gsk_...
GROQ_API_KEY_5=gsk_...

# Serper (web search for live MCX prices)
SERPER_API_KEY=...

# WhatsApp (Twilio Sandbox for hackathon)
TWILIO_ACCOUNT_SID=...
TWILIO_AUTH_TOKEN=...
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886

# Database
DATABASE_URL=postgresql://srip:srip@localhost:5432/srip
REDIS_URL=redis://localhost:6379/0

# Storage
STORAGE_PATH=./storage          # local for hackathon
# AWS_S3_BUCKET=srip-rfqs       # for production

# App
ORIGIN_PINCODE=395006           # Surat, Gujarat
DEFAULT_MARGIN_PERCENT=5.0
MCX_CACHE_TTL_SECONDS=900       # 15 minutes
COMPANY_NAME=Demo Steel Works
COMPANY_GSTIN=24XXXXX1234Z5
```
