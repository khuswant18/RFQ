# Smart RFQ Intelligence Pipeline (SRIP)

**Version:** 2.0 — Hackathon Build  
**Architecture:** Agentic RAG (RLM-Inspired Multi-Agent System)  
**Target Stack:** Python FastAPI · Groq LLMs · Serper Search · ChromaDB · React  
**Domain:** Indian Steel MSMEs, Surat/Gujarat

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker & Docker Compose

### 1. Clone & Setup

```bash
git clone <repo-url>
cd srip
cp .env.example .env
# Edit .env with your API keys
docker compose up --build -d
```

### 2. Install Backend Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 3. Seed Knowledge Base & Run

```bash
cd backend/app/core/rag
python seed_knowledge.py
cd backend
uvicorn app.main:app --reload
```

### 4. Run Frontend

```bash
cd frontend
npm install
npm run dev
```

---

## System Overview: The IE2W Pipeline

```
INPUT      EXTRACT       ESTIMATE       WORKFLOW
WhatsApp  ──► OCR      ──► Weight   ──► PDF Quote
Email     ──► NER      ──► Pricing  ──► WhatsApp Reply
Upload    ──► Validator──► GST Agent──► Task Creator
                    │             │
                    ▼             ▼
              [Steel RAG DB] [Live Price RAG]
              IS Codes, BIS  MCX + Serper Search
```

---

## Documentation

- **[PRD.md](PRD.md)** — Product Requirements Document
- **[ARCHITECTURE.md](ARCHITECTURE.md)** — System Architecture & Design
- **[AGENTS_SPECIFICATION.md](AGENTS_SPECIFICATION.md)** — Agent Prompts & Schemas

---

## Environment Variables

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
STORAGE_PATH=./storage
AWS_S3_BUCKET=srip-rfqs  # optional for production

# App
ORIGIN_PINCODE=395006
DEFAULT_MARGIN_PERCENT=5.0
MCX_CACHE_TTL_SECONDS=900
COMPANY_NAME=Demo Steel Works
COMPANY_GSTIN=24XXXXX1234Z5
```

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/ingest/upload` | POST | Upload RFQ file (image, PDF, etc.) |
| `/api/v1/ingest/whatsapp` | POST | Receive WhatsApp webhook |
| `/api/v1/rfq/{rfq_id}` | GET | Get RFQ details |
| `/api/v1/rfq/{rfq_id}/quote` | GET | Download generated quote PDF |
| `/api/v1/rfq/{rfq_id}/status` | GET | Check pipeline status |

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | Python, FastAPI, Celery |
| LLMs | Groq API (LLaMA3, Mixtral) |
| Vector DB | ChromaDB |
| Cache | Redis |
| Database | PostgreSQL |
| Storage | MinIO / Local |
| Frontend | React, Vite |
| PDF | WeasyPrint |
