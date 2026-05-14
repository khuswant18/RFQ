"""Pydantic models for the SRIP system."""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class AgentResult(BaseModel):
    """Output from any sub-agent."""
    agent_name: str
    rfq_id: str
    status: str  # "success" | "partial" | "failed" | "review_needed"
    output: dict
    confidence: float  # 0.0 - 1.0
    latency_ms: int
    error: Optional[str] = None


# ==================== RFQ models ====================

class RFQCreate(BaseModel):
    """Input model for creating a new RFQ."""
    source_channel: str = Field(..., description="Source channel: whatsapp, email, api")
    file_type: Optional[str] = Field(None, description="File type: jpg, png, pdf, text")
    file_path: Optional[str] = Field(None, description="Path to the uploaded file")
    raw_text: Optional[str] = Field(None, description="Raw text of the RFQ")
    sender_contact: Optional[str] = Field(None, description="Contact info of the sender")


class RFQStatus(BaseModel):
    """Model for RFQ status."""
    rfq_id: str
    status: str  # received, processing, extracted, priced, quoted, failed, review_needed
    created_at: datetime
    updated_at: Optional[datetime] = None


# ==================== Orchestrator models ====================

class OrchestratorInput(BaseModel):
    """Input model for the Orchestrator Agent."""
    rfq_id: str
    source_channel: str
    file_type: Optional[str] = None
    file_path: Optional[str] = None
    raw_text: Optional[str] = None
    sender_contact: Optional[str] = None


class ExecutionStep(BaseModel):
    """A single step in the execution plan."""
    step: int
    agent: str
    input_template: Dict[str, Any]
    depends_on: List[int]
    fallback: str


class ExecutionPlan(BaseModel):
    """Complete execution plan for an RFQ."""
    rfq_id: str
    steps: List[ExecutionStep]
    estimated_complexity: str  # simple, standard, complex


# ==================== OCR models ====================

class OCRInput(BaseModel):
    """Input for OCR Agent."""
    rfq_id: str
    file_path: str
    file_type: str


class OCROutput(BaseModel):
    """Output from OCR Agent."""
    raw_text: str
    ocr_confidence: float
    language_detected: str
    page_count: int


# ==================== NER models ====================

class NERInput(BaseModel):
    """Input for NER Agent."""
    rfq_id: str
    raw_text: str
    retrieved_context: Optional[str] = None


class LineItem(BaseModel):
    """A single line item extracted from an RFQ."""
    item_id: Optional[int] = None
    material_type: Optional[str] = None
    is_code: Optional[str] = None
    grade: Optional[str] = None
    shape: Optional[str] = None
    dimensions: Optional[Dict[str, Any]] = None
    quantity: Optional[Dict[str, Any]] = None
    destination_pincode: Optional[str] = None
    destination_raw: Optional[str] = None
    urgency: Optional[str] = None
    confidence_scores: Optional[Dict[str, float]] = None


class NEROutput(BaseModel):
    """Output from NER Agent."""
    rfq_id: str
    line_items: List[LineItem]
    language: str
    is_sub_inquiry: bool
    price_inclusive_gst: bool
    overall_confidence: float


# ==================== Validation models ====================

class ValidationResult(BaseModel):
    """Validation result for a single line item."""
    item: LineItem
    status: str  # valid, invalid
    errors: List[str]
    warnings: List[str]


# ==================== Pricing models ====================

class ValidatedLineItem(LineItem):
    """Line item that has been validated."""
    pass


class WeightResult(BaseModel):
    """Weight calculation result."""
    formula_used: str
    unit_weight_kg: float
    total_weight_ton: float


class PriceResult(BaseModel):
    """Live price fetch result."""
    price_per_ton: float
    source: str
    as_of: str


class CostBreakdown(BaseModel):
    """Cost breakdown for a single line item."""
    material_cost: float
    logistics_cost: float
    loading_cost: float
    margin_amount: float
    subtotal: float


class PricingResult(BaseModel):
    """Complete pricing result."""
    item_costs: List[CostBreakdown]
    total_subtotal: float
    margin_percent: float
    external_context: Optional[str] = None


# ==================== GST models ====================

class GSTResult(BaseModel):
    """GST calculation result."""
    tax_type: str
    cgst: float
    sgst: float
    igst: float
    total_gst: float
    hsn_code: str
    gst_rate_pct: float
    destination_state: Optional[str] = None
    external_context: Optional[str] = None


# ==================== Quote models ====================

class QuoteContext(BaseModel):
    """Context data for generating a quote."""
    company_name: str
    company_gstin: str
    quote_number: str
    quote_date: str
    valid_until: str
    buyer_contact: str
    buyer_location: str
    line_items: List[Dict[str, Any]]
    subtotal: float
    logistics_total: float
    margin_amount: float
    margin_percent: float
    gst_type: str
    gst_amount: float
    grand_total: float
    is_codes_referenced: List[str]
    notes: str
    bank_details: str


# ==================== Communication models ====================

class CommunicationResult(BaseModel):
    """Result of communication dispatch."""
    sent: bool
    channel: str
    error: Optional[str] = None
