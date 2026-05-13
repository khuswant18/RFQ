"""Entry point for SRIP API server."""
import os
import time
import uuid
from fastapi import FastAPI, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn

from app.api.v1 import ingestion, rfq, quotes, webhook, auth
from app.core.rag.seed_knowledge import seed_chroma


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    print("🚀 Starting SRIP API Server...")
    seed_chroma()
    # Initialize database if configured
    try:
        from app.core.database import init_db, is_db_available
        if is_db_available():
            yield
    except ImportError:
        pass
    print("✅ SRIP API Server ready.")
    yield
    print("👋 SRIP API Server shutting down.")


app = FastAPI(
    title="Smart RFQ Intelligence Pipeline",
    description="Agentic RAG system for Indian steel MSME RFQ processing",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — allow frontend origins. Support wildcard via env var CORS_ORIGINS='*'
cors_env = os.getenv("CORS_ORIGINS", "*")
if cors_env.strip() == "*":
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    allowed_origins = [o.strip() for o in cors_env.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Add a unique request ID and timing to every response."""
    request_id = str(uuid.uuid4())[:8]
    start_time = time.time()
    response = await call_next(request)
    process_time = round((time.time() - start_time) * 1000, 2)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time-Ms"] = str(process_time)
    return response


# Include routers
app.include_router(auth.router, prefix="/api/v1")
app.include_router(ingestion.router, prefix="/api/v1")
app.include_router(rfq.router, prefix="/api/v1")
app.include_router(quotes.router, prefix="/api/v1")
app.include_router(webhook.router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    """Health check endpoint for load balancers and monitoring."""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "service": "srip-api",
        "mock_mode": os.getenv("MOCK_GROQ", "true"),
    }


@app.get("/")
async def root():
    """Root endpoint — redirect to docs."""
    return {
        "service": "Smart RFQ Intelligence Pipeline (SRIP)",
        "version": "2.0.0",
        "docs": "/docs",
        "health": "/health",
    }


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=["app"],
    )
