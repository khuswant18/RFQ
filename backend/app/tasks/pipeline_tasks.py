"""Celery tasks for pipeline processing."""
try:
    from celery import Celery
    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False
    class Celery:
        def __init__(self, *args, **kwargs):
            self.conf = type('conf', (), {'update': lambda self, **kw: None})()
    
    def celery_app_task(*args, **kwargs):
        def decorator(func):
            return func
        return decorator

import os


# Celery configuration
celery_app = None
if CELERY_AVAILABLE:
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
else:
    # Mock Celery app for when Celery is not installed
    class _MockCeleryApp:
        def __init__(self):
            self.conf = type('conf', (), {'update': lambda self, **kw: None})()
    celery_app = _MockCeleryApp()


def process_rfq_pipeline(rfq_id: str, file_path: str = None, raw_text: str = None):
    """
    Main Celery task for processing an RFQ through the entire pipeline."""
    from app.agents.orchestrator import OrchestratorAgent
    from app.models.rfq import OrchestratorInput
    
    orchestrator = OrchestratorAgent()
    
    input_data = OrchestratorInput(
        rfq_id=rfq_id,
        source_channel="api",
        file_type=file_path.split(".")[-1] if file_path else None,
        file_path=file_path,
        raw_text=raw_text,
        sender_contact=None
    )
    
    result = orchestrator.run(input_data)
    
    return {
        "status": "success",
        "rfq_id": rfq_id,
        "result": result
    }
