<div align="center">

<br/>

```
███████╗██████╗ ██╗██████╗
██╔════╝██╔══██╗██║██╔══██╗
███████╗██████╔╝██║██████╔╝
╚════██║██╔══██╗██║██╔═══╝
███████║██║  ██║██║██║
╚══════╝╚═╝  ╚═╝╚═╝╚═╝
```

# Smart RFQ Intelligence Pipeline

**Automated RFQ → Quote for Indian Steel MSMEs**

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18+-61DAFB?style=flat-square&logo=react&logoColor=black)](https://react.dev)
[![Groq](https://img.shields.io/badge/Groq-LLaMA3-F55036?style=flat-square)](https://groq.com)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-RAG-E88C1F?style=flat-square)](https://trychroma.com)
[![License](https://img.shields.io/badge/License-MIT-22C55E?style=flat-square)](LICENSE)

<br/>

> **SRIP** converts incoming RFQs — WhatsApp messages, email attachments, or file uploads — into structured, GST-compliant, BIS-validated PDF quotes in minutes, not hours. Built for the Indian steel supply chain.

<br/>

[Quick Start](#-quick-start) · [Architecture](#-architecture) · [Agents](#-agent-pipeline) · [API Reference](#-api-reference) · [Configuration](#-environment-variables) · [Docs](#-documentation)

</div>

---

## The Problem

Indian steel MSMEs — traders, stockists, and processors in Gujarat's industrial clusters — receive dozens of RFQs daily via WhatsApp, email, and physical uploads. Each one requires a sales operator to manually:

- Parse product descriptions, grades, and dimensions
- Validate against BIS/IS standards
- Compute theoretical weights using product-specific formulas
- Fetch live MCX steel prices
- Apply HSN-based GST rules
- Type out a structured, client-ready PDF quote

**A single RFQ takes 20–40 minutes. At 30 RFQs/day, that's a dedicated headcount — plus compounding pricing and compliance errors.**

SRIP automates this entire pipeline with a multi-agent AI system that encodes real steel domain knowledge.

---

## Architecture

### System Flow

```mermaid
flowchart TD
    subgraph INGESTION["Ingestion Layer"]
        A[📎 Web Upload API<br/>/api/v1/ingest/upload]
        B[📝 Raw Text API<br/>/api/v1/ingest/text]
        C[💬 WhatsApp Webhook<br/>/api/v1/webhook/whatsapp]
    end

    subgraph ORCH["Orchestration Engine"]
        D[OrchestratorAgent<br/>LLM-Driven ExecutionPlan Generator]
    end

    subgraph PIPELINE["Agent Pipeline  —  IE2W Stages"]
        direction LR
        F[OCR Agent<br/>Tesseract]
        G[NER Agent<br/>Groq LLM]
        H[Validator Agent<br/>BIS / IS Codes]
        I[Pricing Agent<br/>MCX + Formulas]
        J[GST Agent<br/>HSN Classification]
        K[Quote Agent<br/>WeasyPrint PDF]
        L[Comms Agent<br/>Twilio]
        F --> G --> H --> I --> J --> K --> L
    end

    subgraph KNOWLEDGE["Knowledge & External Services"]
        M[(ChromaDB<br/>IS Codes · HSN Rules<br/>Weight Formulas)]
        N[Groq API<br/>LLaMA3 / Mixtral]
        O[Serper Search<br/>Live MCX Prices]
        P[Twilio<br/>WhatsApp / SMS]
    end

    subgraph OUTPUT["Output Layer"]
        Q[PDF Quote<br/>/api/v1/rfq/id/quote]
        R[WhatsApp Delivery]
        S[Dashboard<br/>React Frontend]
    end

    A & B & C --> D
    D --> F
    D -.->|RAG queries| M
    G -.->|NER inference| N
    I -.->|Live price lookup| O
    L -.->|Message delivery| P
    K --> Q
    L --> R
    Q --> S

    style INGESTION fill:#EFF6FF,stroke:#3B82F6,stroke-width:2px
    style ORCH fill:#F5F3FF,stroke:#8B5CF6,stroke-width:2px
    style PIPELINE fill:#F0FDF4,stroke:#22C55E,stroke-width:2px
    style KNOWLEDGE fill:#FFFBEB,stroke:#F59E0B,stroke-width:2px
    style OUTPUT fill:#FFF1F2,stroke:#F43F5E,stroke-width:2px
```

---

### High-Level Text Overview

```
                         ┌─────────────────────────────────────────┐
  INGESTION              │           ORCHESTRATION ENGINE           │
  ─────────              │                                          │
  WhatsApp  ─────────►   │   OrchestratorAgent                      │
  Email     ─────────►   │   └─ Receives RFQ context                │
  Upload    ─────────►   │   └─ Calls Groq LLM                      │
                         │   └─ Produces JSON ExecutionPlan          │
                         └─────────────┬───────────────────────────┘
                                       │
           ┌───────────────────────────▼──────────────────────────────┐
           │                    AGENT PIPELINE                        │
           │                                                          │
           │  OCR ──► NER ──► Validator ──► Pricing ──► GST ──► Quote ──► Comms
           │   │        │          │             │          │       │
           │   │        │          │             │          │       └── PDF → WhatsApp/Email
           │   │        └──────────┘             └──────────┘
           │   │         BIS/IS Codes              MCX + HSN Rules
           │   └── Tesseract OCR (image RFQs)
           └──────────────────────────────────────────────────────────┘
                          │                      │
               [ChromaDB RAG Knowledge]   [Serper Live Prices]
               IS Codes · BIS Rules       MCX Steel Market Data
               HSN/GST Mappings
               Weight Formulas
```

---

## Agent Pipeline

Each agent has a **single responsibility**, a defined Pydantic input/output schema, and a **graceful heuristic fallback** when LLM or external services are unavailable.

| # | Agent | File | Input | Output | External Services |
|---|-------|------|-------|--------|-------------------|
| 1 | **OCR Agent** | `ocr_agent.py` | Image/PDF file | Raw extracted text | Tesseract OCR |
| 2 | **NER Agent** | `ner_agent.py` | Raw text | `LineItem[]` (product, grade, dimensions, qty) | Groq LLM · ChromaDB |
| 3 | **Validator Agent** | `validator_agent.py` | `LineItem[]` | `ValidationResult[]` with BIS/IS compliance flags | ChromaDB IS codes |
| 4 | **Pricing Agent** | `pricing_agent.py` | Validated items | `PricingResult` with weight, unit price, logistics | Serper MCX · steel_formulas |
| 5 | **GST Agent** | `gst_agent.py` | Pricing data | `GSTResult` with HSN codes, rates, tax amounts | ChromaDB HSN rules |
| 6 | **Quote Agent** | `quote_agent.py` | Full `QuoteContext` | PDF file via WeasyPrint + Jinja2 template | — |
| 7 | **Comms Agent** | `communication_agent.py` | Quote PDF path | Delivery confirmation | Twilio WhatsApp/Email |

### Orchestrator

`orchestrator.py` — The planning layer. Receives the incoming RFQ context, calls Groq to produce a structured `ExecutionPlan` JSON object (ordered steps with dependencies and fallback flags), then dispatches agents in sequence via Celery tasks.

---

## RFQ Status Lifecycle

```
  RECEIVED ──► PROCESSING ──► EXTRACTED ──► PRICED ──► QUOTED
                                                           │
                          FAILED ◄──────── REVIEW_NEEDED ◄┘
```

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker & Docker Compose (recommended)

### 1. Clone & Configure

```bash
git clone <repo-url>
cd srip
cp .env.example .env
# Fill in your API keys — see Environment Variables below
```

### 2. Docker (Recommended)

```bash
docker compose up --build -d
```

This starts: FastAPI backend · React frontend · Redis · ChromaDB

### 3. Manual Setup

**Backend:**

```bash
cd backend
pip install -r requirements.txt

# Seed the knowledge base (IS codes, HSN rules, weight formulas)
cd app/core/rag
python seed_knowledge.py

# Start API server
cd ../../..
uvicorn app.main:app --reload --port 8000
```

**Frontend:**

```bash
cd frontend
npm install
npm run dev
```

**Celery Worker (for async pipeline):**

```bash
cd backend
celery -A app.tasks.pipeline_tasks worker --loglevel=info
```

---

## Environment Variables

```env
# ── Groq API (5 keys, round-robin rotated for rate management) ─────────────
GROQ_API_KEY_1=gsk_...
GROQ_API_KEY_2=gsk_...
GROQ_API_KEY_3=gsk_...
GROQ_API_KEY_4=gsk_...
GROQ_API_KEY_5=gsk_...

# ── Serper (live MCX steel price search) ───────────────────────────────────
SERPER_API_KEY=...

# ── Twilio (WhatsApp inbound + outbound) ───────────────────────────────────
TWILIO_ACCOUNT_SID=...
TWILIO_AUTH_TOKEN=...
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886

# ── Persistence ────────────────────────────────────────────────────────────
DATABASE_URL=postgresql://srip:srip@localhost:5432/srip
REDIS_URL=redis://localhost:6379/0

# ── Storage ────────────────────────────────────────────────────────────────
STORAGE_PATH=./storage
AWS_S3_BUCKET=srip-rfqs         # optional, for production

# ── Business Config ────────────────────────────────────────────────────────
ORIGIN_PINCODE=395006           # Surat, Gujarat (for freight calc)
DEFAULT_MARGIN_PERCENT=5.0
MCX_CACHE_TTL_SECONDS=900       # 15-minute live price cache
COMPANY_NAME=Demo Steel Works
COMPANY_GSTIN=24XXXXX1234Z5
```

---

## API Reference

### Ingestion

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/ingest/upload` | Upload RFQ file (image, PDF, DOCX). Returns `rfq_id`. |
| `POST` | `/api/v1/ingest/text` | Submit raw text RFQ. Returns `rfq_id`. |
| `POST` | `/api/v1/webhook/whatsapp` | Twilio webhook receiver for WhatsApp RFQs. |

### RFQ Lifecycle

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/rfq/{rfq_id}` | Full RFQ details including line-items and agent outputs. |
| `GET` | `/api/v1/rfq/{rfq_id}/status` | Lightweight status polling (`received` → `quoted`). |
| `GET` | `/api/v1/rfq/{rfq_id}/quote` | Download the generated PDF quote. |

---

## Domain Knowledge Base

The ChromaDB vector store is seeded at startup (`seed_knowledge.py`) with:

| Collection | Contents |
|------------|----------|
| `is_codes` | BIS/IS standard descriptions, material grade definitions, compliance rules for Indian steel products |
| `hsn_gst_rules` | HSN code → GST rate mappings for steel and related products (India GST Council data) |
| `weight_formulas` | Theoretical weight-per-metre formulas for TMT bars, plates, channels, angles, pipes, sheets |
| `product_synonyms` | Regional and trade-language synonyms for steel product names (Surat/Gujarat context) |

Knowledge can be updated without redeployment by modifying and re-running `seed_knowledge.py` — no engineering changes required.

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | React 18 · Vite · TailwindCSS | Operator dashboard · RFQ upload UI · Quote viewer |
| **Backend** | Python 3.11 · FastAPI · Uvicorn | REST API server · agent orchestration layer |
| **Task Queue** | Celery · Redis | Async pipeline execution · worker pool |
| **LLM** | Groq API (LLaMA3, Mixtral) | Orchestration planning · NER · agent reasoning |
| **Vector Store** | ChromaDB | RAG knowledge base: IS codes · HSN rules · formulas |
| **Web Search** | Serper API | Live MCX steel price discovery |
| **OCR** | Tesseract | Text extraction from image/PDF RFQ uploads |
| **PDF** | WeasyPrint · Jinja2 | HTML → PDF quote rendering |
| **Messaging** | Twilio WhatsApp API | Inbound webhook · outbound quote delivery |
| **Database** | PostgreSQL | RFQ persistence · agent result audit trail |
| **Cache** | Redis | MCX price cache · Celery broker |
| **Deployment** | Docker · docker-compose | Containerised multi-service deployment |

---

## Project Structure

```
srip/
├── backend/
│   ├── app/
│   │   ├── agents/
│   │   │   ├── orchestrator.py          # ExecutionPlan generator
│   │   │   ├── ocr_agent.py             # Tesseract OCR
│   │   │   ├── ner_agent.py             # LLM entity extraction
│   │   │   ├── validator_agent.py       # BIS/IS validation
│   │   │   ├── pricing_agent.py         # Weight + MCX pricing
│   │   │   ├── gst_agent.py             # HSN-based GST calc
│   │   │   ├── quote_agent.py           # PDF generation
│   │   │   └── communication_agent.py   # WhatsApp/Email delivery
│   │   ├── api/v1/
│   │   │   ├── ingestion.py             # Upload + text ingest endpoints
│   │   │   ├── rfq.py                   # RFQ detail + status endpoints
│   │   │   ├── quotes.py                # PDF download endpoint
│   │   │   └── webhook.py               # Twilio webhook receiver
│   │   ├── core/
│   │   │   ├── rag/
│   │   │   │   ├── seed_knowledge.py    # ChromaDB seeder
│   │   │   │   └── chroma_client.py     # Vector store wrapper
│   │   │   ├── steel_formulas.py        # Weight calculation formulas
│   │   │   ├── gst_logic.py             # GST heuristics
│   │   │   ├── groq_client.py           # LLM client with key rotation
│   │   │   └── serper_client.py         # Web search client
│   │   ├── models/
│   │   │   └── rfq.py                   # Pydantic domain models
│   │   └── tasks/
│   │       └── pipeline_tasks.py        # Celery task definitions
│   └── templates/
│       └── quote_template.html          # Jinja2 PDF quote template
├── frontend/
│   └── src/
│       ├── pages/
│       │   ├── Dashboard.jsx            # RFQ list + status board
│       │   ├── Upload.jsx               # File upload interface
│       │   └── RFQDetail.jsx            # Quote breakdown view
│       └── App.jsx                      # Router + layout
├── docker-compose.yml
└── .env.example
```

---

## Data Flow: A Single RFQ

```
1.  Operator uploads RFQ image via /api/v1/ingest/upload
      └── rfq_id generated · file saved to storage/

2.  Celery task: process_rfq_pipeline(rfq_id) fires
      └── Status: received → processing

3.  OrchestratorAgent.run(rfq_context)
      └── Calls Groq LLM with system prompt
      └── Returns JSON ExecutionPlan with ordered steps

4.  OCRAgent extracts raw text from image (Tesseract)
      └── Status: processing

5.  NERAgent identifies LineItems
      └── e.g. { product: "TMT Bar", grade: "Fe500", dia: 12mm, qty: 5MT }
      └── ChromaDB queried for product synonym resolution
      └── Status: extracted

6.  ValidatorAgent checks each LineItem
      └── BIS IS 1786:2008 compliance verified for TMT Fe500
      └── Flags any non-standard grades

7.  PricingAgent computes weight + price
      └── Weight: π/4 × d² × L × 7.85 (steel density formula)
      └── Serper fetches live MCX TMT price (cached 15 min)
      └── Adds freight from pin 395006 (configurable)
      └── Status: priced

8.  GSTAgent classifies and computes tax
      └── HSN 7214 → 18% GST for TMT bars
      └── CGST 9% + SGST 9% (within Gujarat)

9.  QuoteAgent renders PDF
      └── Jinja2 template → WeasyPrint → storage/rfq_id_quote.pdf
      └── Status: quoted

10. CommunicationAgent (if Twilio configured)
      └── Sends PDF via WhatsApp to buyer's number
      └── Dashboard updated · /api/v1/rfq/{rfq_id}/quote available
```

---

## Scalability

| Bottleneck | Strategy |
|------------|----------|
| LLM call volume | Key rotation across 5 Groq keys · async Celery workers · response caching |
| OCR throughput | Dedicated Celery queue · GPU-enabled Tesseract workers for image-heavy load |
| PDF generation | WeasyPrint worker pool · CPU-bound dedicated queue with autoscaling |
| Live price lookups | Redis-cached MCX prices with 15-min TTL · rate-limited Serper calls |
| Database reads | PostgreSQL read replicas for dashboard · PgBouncer connection pooling |
| Knowledge updates | ChromaDB seeder runs independently · no redeployment required |

**Target:** 50+ concurrent RFQs/hour with a 4-worker Celery pool on a standard VM.

---

## Roadmap

- [x] Ingestion API (upload, text, WhatsApp webhook)
- [x] Agent implementations (OCR, NER, Validator, Pricing, GST, Quote, Comms)
- [x] Orchestrator ExecutionPlan generation
- [x] ChromaDB knowledge seeding
- [x] React dashboard (demo shell)
- [ ] Wire Celery pipeline (ingestion → task queue → execution)
- [ ] PostgreSQL persistence + SQLAlchemy ORM
- [ ] Agent executor (run plan steps end-to-end, persist AgentResults)
- [ ] JWT authentication + RBAC for dashboard
- [ ] Production Groq/Serper/Twilio error handling + retry logic
- [ ] Real-time dashboard via WebSockets
- [ ] Admin UI for knowledge base management
- [ ] Unit + integration test suite · CI/CD pipeline

---

## Documentation

| Document | Description |
|----------|-------------|
| [PRD.md](PRD.md) | Product Requirements Document — user stories, acceptance criteria |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System Architecture & Design — detailed component specs |
| [AGENTS_SPECIFICATION.md](AGENTS_SPECIFICATION.md) | Agent prompts, schemas, and fallback behaviour |

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit changes: `git commit -m 'feat: description'`
4. Push and open a Pull Request

Please ensure new agents follow the existing `AgentResult` Pydantic schema and include a heuristic fallback path.

---

<div align="center">

**Built for the Indian steel supply chain · Surat / Gujarat**

*SRIP — turning WhatsApp RFQs into professional quotes, automatically.*

</div>