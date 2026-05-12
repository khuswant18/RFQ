# Product Requirements Document
# Smart RFQ Intelligence Pipeline — PS-05 (SRIP)

**Version:** 2.0 — Hackathon Build  
**Architecture:** Agentic RAG (RLM-Inspired Multi-Agent System)  
**Target Stack:** Python FastAPI · Groq LLMs · Serper Search · ChromaDB · React  
**Domain:** Indian Steel MSMEs, Surat/Gujarat  

---

## 1. PRODUCT VISION

> *"Give Rajeshbhai in Pandesara the procurement intelligence of a Fortune 500 company — accessible from a WhatsApp message."*

The Smart RFQ Intelligence Pipeline (SRIP) transforms the way Indian steel MSMEs respond to purchase enquiries. What currently takes 2–6 hours of manual effort — reading blurry WhatsApp images, computing weights, calling suppliers for rates, calculating GST — is replaced by an **agentic AI system that delivers a professional, accurate quote in under 60 seconds**.

The system is not a chatbot. It is a **multi-agent pipeline** where specialised AI sub-agents collaborate, each owning one part of the intelligence chain. Together they implement a **Retrieval-Augmented Language Model (RLM)** architecture: every agent retrieves domain context before acting, ensuring outputs are grounded in Indian steel standards, live market prices, and GST law.

---

## 2. PROBLEM STATEMENT

### 2.1 The Broken Workflow (Current State)

```
[WhatsApp Image Arrives]
        ↓  (40% ignored / lost)
[Manual re-keying into Excel — 30–60 min]
        ↓  (typos, wrong dims)
[Phone call to check MCX rates — 15 min]
        ↓  (stale data)
[Manual GST calc in head — error prone]
        ↓  (IGST vs CGST confusion)
[Type quote in Word, save as PDF — 20 min]
        ↓  (PDF not branded, no BIS ref)
[Forward on WhatsApp — 2-6 hours total]
        ↓  (Business already moved to competitor)
```

### 2.2 Quantified Pain

| Metric | Current State | Target State |
|--------|--------------|--------------|
| Time per RFQ | 2–6 hours | < 60 seconds |
| RFQs handled/day (single operator) | 3–5 | 25+ (all 10–25 daily) |
| Quote error rate | ~15% (typos, GST) | < 1% |
| RFQ response rate | ~60% | 95%+ |
| Price staleness | Up to 24 hours | Real-time (< 15 min) |

---

## 3. TARGET USERS

### Primary: Rajeshbhai (MSME Mill Owner / Trader)
- Pandesara/Sachin GIDC based re-rolling mill or steel trader
- Receives 10–25 WhatsApp RFQs/day
- Literate in WhatsApp Business; not in ERP systems
- Needs: "Send image, get quote I can forward immediately"

### Secondary: Sales Manager at MSME
- Manages quotation follow-ups
- Needs: Dashboard to track pending RFQs, quote status, conversion rate

### Tertiary: Corporate Procurement (Tata/L&T downstream)
- Wants standardised quote format (JSON API / structured PDF)
- Needs: Machine-readable line items for their internal comparison tools

---

## 4. SYSTEM OVERVIEW: THE IE2W PIPELINE

```
┌─────────────────────────────────────────────────────────────────────┐
│                    SRIP — AGENTIC RFQ PIPELINE                       │
│                                                                       │
│  INPUT          EXTRACT          ESTIMATE          WORKFLOW           │
│                                                                       │
│  WhatsApp  ──►  OCR Agent   ──►  Weight      ──►  PDF Quote          │
│  Email     ──►  NER Agent   ──►  Pricing     ──►  WhatsApp Reply     │
│  Upload    ──►  Validator   ──►  GST Agent   ──►  Task Creator       │
│                     │               │                                 │
│                     ▼               ▼                                 │
│              [Steel RAG DB]   [Live Price RAG]                       │
│              IS Codes, BIS    MCX + Serper Search                    │
└─────────────────────────────────────────────────────────────────────┘
```

Every stage is owned by a **dedicated sub-agent**. The **Orchestrator Agent** (Groq LLaMA3-70B) reads the incoming RFQ, decomposes it into a task plan, and dispatches sub-agents in the correct sequence, collecting results and handling failures.

---

## 5. FUNCTIONAL REQUIREMENTS

### 5.1 Ingestion (FR-ING)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-ING-01 | Accept WhatsApp Business webhook (Meta API) with image/document attachments | P0 |
| FR-ING-02 | Accept email via IMAP polling (Gmail/Outlook) filtering subject "RFQ/Enquiry/Rate" | P0 |
| FR-ING-03 | Accept direct file upload via REST endpoint (multipart/form-data) | P0 |
| FR-ING-04 | Support file types: JPG, PNG, PDF, DOCX, XLSX, plain text | P0 |
| FR-ING-05 | Assign unique `rfq_id` (UUID v4) to every incoming document | P0 |
| FR-ING-06 | Persist raw file to object storage (S3-compatible / local) | P0 |
| FR-ING-07 | Emit ingestion event to async task queue | P0 |

### 5.2 Extraction (FR-EXT)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-EXT-01 | Perform OCR on images; preprocess (grayscale, deskew, contrast) before LLM | P0 |
| FR-EXT-02 | Extract: material type, grade, shape, dimensions, quantity, delivery location, urgency | P0 |
| FR-EXT-03 | Understand Hinglish: "Sariya 12mm" → TMT_Bar IS1786, "Kamach dar" → Fe550 | P0 |
| FR-EXT-04 | Understand Gujarati keywords: "Tax inclusive" → price_inclusive_gst=True | P1 |
| FR-EXT-05 | Support multi-line-item RFQs (up to 20 line items per document) | P0 |
| FR-EXT-06 | Produce structured JSON matching Extracted Entity Schema v2 | P0 |
| FR-EXT-07 | Attach `confidence_score` per extracted field (0.0–1.0) | P0 |
| FR-EXT-08 | Flag fields with `confidence < 0.7` as `REVIEW_NEEDED` | P0 |
| FR-EXT-09 | Retrieve IS code context from Steel RAG DB before extraction prompt | P1 |

### 5.3 Validation (FR-VAL)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-VAL-01 | Cross-reference extracted grade against BIS IS1786 / IS2062 lookup | P0 |
| FR-VAL-02 | Flag impossible combinations: e.g., "Fe999" or "IS1786 + Flat Plate" | P0 |
| FR-VAL-03 | Map material synonyms to canonical types (e.g., Saria→TMT_Bar, Patti→Flat) | P0 |
| FR-VAL-04 | Validate delivery pincode format (6-digit India) | P1 |
| FR-VAL-05 | Detect sub-inquiry (forwarded RFQ) patterns and flag | P2 |

### 5.4 Cost Estimation (FR-EST)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-EST-01 | Fetch live MCX steel base price (Serper search or mock API) | P0 |
| FR-EST-02 | Apply grade-specific surcharge on top of base price | P0 |
| FR-EST-03 | Calculate weight using shape-specific formula (round, flat, angle, channel) | P0 |
| FR-EST-04 | Calculate logistics cost using delivery pincode distance from Surat (395006) | P0 |
| FR-EST-05 | Apply configurable margin percentage (default 5%) | P0 |
| FR-EST-06 | Determine GST jurisdiction (IGST vs CGST+SGST) by pincode | P0 |
| FR-EST-07 | Apply 18% GST and split by jurisdiction | P0 |
| FR-EST-08 | Auto-tag HSN code (7213 for TMT, 7214/7216 for structural) | P0 |
| FR-EST-09 | Add finance cost if credit_period > 30 days (1.5% p.m.) | P1 |
| FR-EST-10 | Flag MSME 15% price preference eligibility for government tenders | P2 |
| FR-EST-11 | Cache MCX rates in Redis; refresh every 15 minutes | P0 |

### 5.5 Quote Generation (FR-QTE)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-QTE-01 | Generate branded PDF quote (company logo, letterhead, IS code refs) | P0 |
| FR-QTE-02 | Include: line items, unit price, total weight, logistics, GST breakdown, final total | P0 |
| FR-QTE-03 | Stamp "Price Valid for 24 Hours" on quote | P0 |
| FR-QTE-04 | Generate WhatsApp-ready summary message (short text + PDF attachment) | P0 |
| FR-QTE-05 | Expose quote as downloadable PDF via `/rfq/{id}/quote` endpoint | P0 |

### 5.6 Workflow & Communication (FR-WFL)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-WFL-01 | Send PDF quote back via WhatsApp Business API (session message) | P0 |
| FR-WFL-02 | Create internal task: "Verify inventory for [grade] [qty]" | P1 |
| FR-WFL-03 | Notify sales manager dashboard of new quote generated | P1 |
| FR-WFL-04 | Send follow-up reminder if quote not acknowledged in 6 hours | P2 |

### 5.7 Dashboard (FR-DASH)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-DASH-01 | Live feed of RFQs: status (received, processing, quoted, failed) | P0 |
| FR-DASH-02 | Per-RFQ detail view: extracted JSON, cost breakdown, PDF preview | P0 |
| FR-DASH-03 | Configurable margin and rate override UI | P1 |
| FR-DASH-04 | Analytics: quote volume, avg response time, conversion rate | P2 |

---

## 6. NON-FUNCTIONAL REQUIREMENTS

| Category | Requirement |
|----------|-------------|
| **Performance** | End-to-end pipeline (image to PDF) < 60 seconds for single item RFQ |
| **Accuracy** | Grade + dimension extraction accuracy ≥ 95% on clean PDFs, ≥ 85% on handwritten |
| **Availability** | 99% uptime during business hours (8am–8pm IST) |
| **Concurrency** | Handle 10 simultaneous RFQs without queue backup |
| **Security** | No raw RFQ images stored beyond 30 days; no PII in logs |
| **Scalability** | Stateless agents; horizontally scalable via Celery workers |
| **Observability** | Every agent invocation logged with input hash, output schema, latency, confidence |

---

## 7. SUCCESS METRICS (DEMO + PRODUCTION)

| Metric | Demo Target | Production Target |
|--------|------------|-------------------|
| Time-to-Quote | < 30 seconds (live demo) | < 60 seconds (P99) |
| Extraction Accuracy (Grade) | 100% on prepared test set | ≥ 95% |
| GST Calc Accuracy | 100% on test cases | 100% |
| Quote PDF professionalism | Judged "professional" by evaluators | Usable without edits |
| WhatsApp round-trip | Demo in under 1 minute | < 2 minutes |

---

## 8. OUT OF SCOPE (HACKATHON V1)

- Training custom NER models (use prompt engineering + RAG instead)
- Live WhatsApp Business API (use Twilio sandbox or mock)
- Real-time MCX streaming (use Serper search + 15-min cache)
- Multi-tenant SaaS billing
- Inventory management integration
- SAIL / GeM API live integration (architecture planned, not implemented)

---

## 9. GLOSSARY

| Term | Definition |
|------|-----------|
| RFQ | Request for Quotation — a buyer's document requesting price for specific materials |
| TMT | Thermo-Mechanically Treated steel bar (reinforcement bar / "Sariya") |
| IS Code | Indian Standard code published by BIS (Bureau of Indian Standards) |
| MCX | Multi Commodity Exchange of India — steel futures price benchmark |
| HSN | Harmonized System Nomenclature code — determines GST tax category |
| IGST | Integrated GST — applied on inter-state supply |
| CGST+SGST | Central + State GST — applied on intra-state (Gujarat) supply |
| BOQ | Bill of Quantities — detailed itemized material list in a tender |
| MSME | Micro, Small and Medium Enterprise |
| BIS | Bureau of Indian Standards — regulatory body for IS codes |
| Hinglish | Hindi-English mixed language used in trade communications |
| Sub-inquiry | An RFQ forwarded by a middleman who hasn't confirmed stock |
| RAG | Retrieval Augmented Generation — LLM augmented with retrieved context |
| RLM | Retrieval-augmented Language Model architecture (multi-agent recursive variant) |
