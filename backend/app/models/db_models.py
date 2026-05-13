"""SQLAlchemy ORM models for the SRIP database."""
import uuid
from datetime import datetime
from typing import Optional

try:
    from sqlalchemy import (
        Column, String, Integer, Float, Boolean, Text, DateTime,
        ForeignKey, JSON, Numeric
    )
    from sqlalchemy.orm import relationship
    from app.core.database import Base
    MODELS_AVAILABLE = True
except ImportError:
    MODELS_AVAILABLE = False
    # Provide stubs so the module can be imported without SQLAlchemy
    class Base:
        pass


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.utcnow()


if MODELS_AVAILABLE:
    class RFQRecord(Base):
        """RFQ master record."""
        __tablename__ = "rfqs"

        rfq_id = Column(String(36), primary_key=True, default=_uuid)
        source_channel = Column(String(20), nullable=False)
        sender_contact = Column(String(50))
        raw_file_url = Column(Text)
        raw_text = Column(Text)
        received_at = Column(DateTime, default=_now)
        status = Column(String(30), default="received")
        updated_at = Column(DateTime, default=_now, onupdate=_now)
        error = Column(Text)
        result_json = Column(JSON)

        line_items = relationship("RFQLineItemRecord", back_populates="rfq")
        costs = relationship("RFQCostRecord", back_populates="rfq")
        quotes = relationship("RFQQuoteRecord", back_populates="rfq")
        agent_logs = relationship("AgentLogRecord", back_populates="rfq")

    class RFQLineItemRecord(Base):
        """Extracted line items."""
        __tablename__ = "rfq_line_items"

        item_id = Column(Integer, primary_key=True, autoincrement=True)
        rfq_id = Column(String(36), ForeignKey("rfqs.rfq_id"))
        material_type = Column(String(50))
        is_code = Column(String(20))
        grade = Column(String(20))
        shape = Column(String(20))
        diameter_mm = Column(Numeric)
        width_mm = Column(Numeric)
        thickness_mm = Column(Numeric)
        length_ft = Column(Numeric)
        quantity_value = Column(Numeric)
        quantity_unit = Column(String(10))
        destination_pin = Column(String(10))
        confidence = Column(Numeric)
        needs_review = Column(Boolean, default=False)

        rfq = relationship("RFQRecord", back_populates="line_items")

    class RFQCostRecord(Base):
        """Cost records."""
        __tablename__ = "rfq_costs"

        cost_id = Column(Integer, primary_key=True, autoincrement=True)
        rfq_id = Column(String(36), ForeignKey("rfqs.rfq_id"))
        item_id = Column(Integer, ForeignKey("rfq_line_items.item_id"), nullable=True)
        base_price_per_ton = Column(Numeric)
        total_weight_ton = Column(Numeric)
        material_cost = Column(Numeric)
        logistics_cost = Column(Numeric)
        processing_cost = Column(Numeric)
        subtotal = Column(Numeric)
        gst_type = Column(String(10))
        gst_amount = Column(Numeric)
        final_total = Column(Numeric)
        margin_percent = Column(Numeric)
        rate_fetched_at = Column(DateTime)
        hsn_code = Column(String(10))

        rfq = relationship("RFQRecord", back_populates="costs")

    class RFQQuoteRecord(Base):
        """Generated quotes."""
        __tablename__ = "rfq_quotes"

        quote_id = Column(Integer, primary_key=True, autoincrement=True)
        rfq_id = Column(String(36), ForeignKey("rfqs.rfq_id"))
        pdf_url = Column(Text)
        validity_hours = Column(Integer, default=24)
        created_at = Column(DateTime, default=_now)
        sent_at = Column(DateTime)
        sent_via = Column(String(20))

        rfq = relationship("RFQRecord", back_populates="quotes")

    class AgentLogRecord(Base):
        """Agent execution log."""
        __tablename__ = "agent_logs"

        log_id = Column(Integer, primary_key=True, autoincrement=True)
        rfq_id = Column(String(36), ForeignKey("rfqs.rfq_id"))
        agent_name = Column(String(50))
        step_number = Column(Integer)
        input_hash = Column(String(64))
        output_schema = Column(JSON)
        confidence = Column(Numeric)
        latency_ms = Column(Integer)
        status = Column(String(20))
        error_msg = Column(Text)
        executed_at = Column(DateTime, default=_now)

        rfq = relationship("RFQRecord", back_populates="agent_logs")
