"""Orchestrator Agent - Master task planner and sub-agent dispatcher."""
from dataclasses import dataclass
from typing import List, Optional
import json

from app.core.groq_client import GroqClient
from app.models.rfq import OrchestratorInput, ExecutionPlan, ExecutionStep


class OrchestratorAgent:
    """
    The Orchestrator Agent is the master planner.
    It reads incoming RFQ metadata, produces an execution plan,
    and dispatches sub-agents in the correct sequence.
    """
    
    def __init__(self):
        try:
            self.groq = GroqClient()
        except ValueError:
            self.groq = None  # Allow use without API keys (demo mode)
    
    SYSTEM_PROMPT = """You are the Orchestrator Agent for an Indian steel RFQ processing pipeline.
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
"""

    def create_plan(self, rfq_input: OrchestratorInput) -> ExecutionPlan:
        """Create an execution plan based on the RFQ input."""
        steps = []
        step_num = 1
        
        # Determine if OCR is needed
        if rfq_input.file_type in ("jpg", "png", "pdf"):
            steps.append(ExecutionStep(
                step=step_num,
                agent="OCRAgent",
                input_template={"file_path": rfq_input.file_path, "file_type": rfq_input.file_type},
                depends_on=[],
                fallback="request_clearer_image"
            ))
            step_num += 1
        
        # NER Agent
        ner_input = "{{step1.output.raw_text}}" if step_num > 1 else rfq_input.raw_text
        steps.append(ExecutionStep(
            step=step_num,
            agent="NERAgent",
            input_template={"raw_text": ner_input},
            depends_on=[step_num - 1] if step_num > 1 else [],
            fallback="set_status_incomplete"
        ))
        step_num += 1
        
        # Validator Agent
        steps.append(ExecutionStep(
            step=step_num,
            agent="ValidatorAgent",
            input_template={"entities": "{{step2.output.entities}}"},
            depends_on=[step_num - 1],
            fallback="flag_for_review"
        ))
        step_num += 1
        
        # Pricing Agent
        steps.append(ExecutionStep(
            step=step_num,
            agent="PricingAgent",
            input_template={"validated_items": "{{step3.output}}"},
            depends_on=[step_num - 1],
            fallback="use_cached_rates"
        ))
        step_num += 1
        
        # GST Agent
        steps.append(ExecutionStep(
            step=step_num,
            agent="GSTAgent",
            input_template={
                "cost_data": "{{step4.output}}",
                "pincode": "{{step2.output.destination_pincode}}"
            },
            depends_on=[step_num - 1],
            fallback="use_igst_conservative"
        ))
        step_num += 1
        
        # Quote Agent
        steps.append(ExecutionStep(
            step=step_num,
            agent="QuoteAgent",
            input_template={"full_data": "{{steps1-5.merged}}"},
            depends_on=[step_num - 1],
            fallback="generate_partial_quote"
        ))
        step_num += 1
        
        # Communication Agent
        steps.append(ExecutionStep(
            step=step_num,
            agent="CommunicationAgent",
            input_template={
                "pdf_path": "{{step6.output.pdf_path}}",
                "channel": rfq_input.source_channel
            },
            depends_on=[step_num - 1],
            fallback="store_for_manual_send"
        ))
        
        return ExecutionPlan(
            rfq_id=rfq_input.rfq_id,
            steps=steps,
            estimated_complexity="standard"
        )
    
    def run(self, rfq_input: OrchestratorInput) -> dict:
        """Run the orchestrator and return the execution plan."""
        plan = self.create_plan(rfq_input)
        return {
            "status": "success",
            "rfq_id": rfq_input.rfq_id,
            "plan": plan.dict()
        }
