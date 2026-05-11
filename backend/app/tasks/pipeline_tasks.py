"""Celery tasks for pipeline processing."""
from celery import Celery
import os

# Celery configuration
celery_app = Celery(
    "srip",
    broker=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    backend=os.getenv("REDIS_URL", "redis://localhost:6379/0")
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Kolkata",
    enable_utc=True
)


@celery_app.task(bind=True, max_retries=3)
def process_rfq_pipeline(self, rfq_id: str, file_path: str = None, raw_text: str = None):
    """
    Main Celery task for processing an RFQ through the entire pipeline.
    
    This task orchestrates the full pipeline:
    1. OCR (if image/PDF)
    2. NER Extraction
    3. Validation
    4. Pricing
    5. GST Calculation
    6. Quote Generation
    7. Communication
    """
    try:
        from app.agents.orchestrator import OrchestratorAgent
        from app.models.rfq import OrchestratorInput
        
        # Create orchestrator
        orchestrator = OrchestratorAgent()
        
        # Create input
        input_data = OrchestratorInput(
            rfq_id=rfq_id,
            source_channel="api",  # Could be whatsapp, email, etc.
            file_type=file_path.split(".")[-1] if file_path else None,
            file_path=file_path,
            raw_text=raw_text,
            sender_contact=None
        )
        
        # Run orchestrator
        result = orchestrator.run(input_data)
        
        return {
            "status": "success",
            "rfq_id": rfq_id,
            "result": result
        }
    
    except Exception as e:
        # Retry on failure
        self.retry(countdown=60, exc=e)
