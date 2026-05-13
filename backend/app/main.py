"""Entry point for SRIP API server."""
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn

from app.api.v1 import ingestion, rfq, quotes, webhook
from app.core.rag.seed_knowledge import seed_chroma


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup: Seed knowledge base
    seed_chroma()
    yield
    # Shutdown: cleanup if needed


app = FastAPI(
    title="Smart RFQ Intelligence Pipeline",
    description="Agentic RAG system for Indian steel MSME RFQ processing",
    version="2.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(ingestion.router, prefix="/api/v1")
app.include_router(rfq.router, prefix="/api/v1")
app.include_router(quotes.router, prefix="/api/v1")
app.include_router(webhook.router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "2.0.0"}


@app.post("/api/v1/process")
async def process_rfq_legacy(file: UploadFile = File(...)):
    """Legacy direct file upload and process endpoint."""
    content = await file.read()
    # Process logic here (kept for backward compatibility)
    return {"filename": file.filename, "status": "received"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
