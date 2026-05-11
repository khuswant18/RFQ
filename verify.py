#!/usr/bin/env python
"""
SRIP Project - Verification Script
This script checks if all project files are in place and verifies the build.
"""
import os
import sys

def check_file(path, description):
    """Check if a file exists."""
    exists = os.path.exists(path)
    status = "✅" if exists else "❌"
    print(f"{status} {description}: {path}")
    return exists

def main():
    print("SRIP Project - Verification\n")
    print("=" * 50)

    all_ok = True

    # Check backend files
    backend_files = [
        ("backend/app/main.py", "FastAPI main entry"),
        ("backend/app/agents/orchestrator.py", "Orchestrator Agent"),
        ("backend/app/agents/ocr_agent.py", "OCR Agent"),
        ("backend/app/agents/ner_agent.py", "NER Agent"),
        ("backend/app/agents/validator_agent.py", "Validator Agent"),
        ("backend/app/agents/pricing_agent.py", "Pricing Agent"),
        ("backend/app/agents/gst_agent.py", "GST Agent"),
        ("backend/app/agents/quote_agent.py", "Quote Agent"),
        ("backend/app/agents/communication_agent.py", "Communication Agent"),
        ("backend/app/core/groq_client.py", "Groq Client"),
        ("backend/app/core/rag/chroma_client.py", "ChromaDB Client"),
        ("backend/app/core/rag/seed_knowledge.py", "Knowledge Seeder"),
        ("backend/app/models/rfq.py", "Pydantic Models"),
        ("backend/app/tasks/pipeline_tasks.py", "Celery Tasks"),
        ("backend/app/templates/quote_template.html", "Quote Template"),
        ("backend/requirements.txt", "Backend Requirements"),
        ("backend/Dockerfile", "Backend Dockerfile"),
    ]

    print("Backend Files:")
    for path, desc in backend_files:
        if not check_file(path, desc):
            all_ok = False

    print()

    # Check frontend files
    frontend_files = [
        ("frontend/package.json", "Package JSON"),
        ("frontend/index.html", "Entry HTML"),
        ("frontend/src/main.jsx", "React Entry"),
        ("frontend/src/App.jsx", "App Component"),
        ("frontend/src/pages/Dashboard.jsx", "Dashboard Page"),
        ("frontend/src/pages/RFQDetail.jsx", "RFQ Detail Page"),
        ("frontend/Dockerfile", "Frontend Dockerfile"),
    ]

    print("Frontend Files:")
    for path, desc in frontend_files:
        if not check_file(path, desc):
            all_ok = False

    print()

    # Check infrastructure files
    infra_files = [
        ("docker-compose.yml", "Docker Compose"),
        (".env.example", "Env Example"),
        ("README.md", "Project README"),
    ]

    print("Infrastructure Files:")
    for path, desc in infra_files:
        if not check_file(path, desc):
            all_ok = False

    print()
    print("=" * 50)
    if all_ok:
        print("✅ All project files are in place!")
    else:
        print("❌ Some project files are missing!")
        sys.exit(1)

if __name__ == "__main__":
    os.chdir("srip")
    main()
