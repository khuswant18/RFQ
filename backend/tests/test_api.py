"""Integration tests and runner."""
from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_ingest_text_and_get_rfq():
    """Test text ingestion and RFQ retrieval."""
    response = client.post("/api/v1/ingest/text", params={"text": "12mm TMT Bar 5 tons"})
    assert response.status_code == 200
    rfq_id = response.json()["rfq_id"]

    rfq_response = client.get(f"/api/v1/rfq/{rfq_id}")
    assert rfq_response.status_code == 200
    assert rfq_response.json()["rfq_id"] == rfq_id


def test_ingest_upload_and_status():
    """Test file upload ingestion and status endpoint."""
    files = {
        "file": ("rfq.txt", BytesIO(b"8mm TMT Bar Fe500 3 tons"), "text/plain")
    }
    response = client.post("/api/v1/ingest/upload", files=files)
    assert response.status_code == 200
    rfq_id = response.json()["rfq_id"]

    status_response = client.get(f"/api/v1/rfq/{rfq_id}/status")
    assert status_response.status_code == 200
    assert status_response.json()["rfq_id"] == rfq_id


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
