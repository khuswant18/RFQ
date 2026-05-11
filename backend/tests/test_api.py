"""Integration tests and runner."""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_upload_rfq():
    """Test the RFQ upload endpoint."""
    response = client.post("/api/v1/rfq/upload")
    assert response.status_code == 200
    assert response.json()["status"] == "received"

def test_get_rfq():
    """Test the get RFQ endpoint."""
    # First upload an RFQ
    upload_response = client.post("/api/v1/rfq/upload")
    rfq_id = upload_response.json()["rfq_id"]
    
    # Then get it
    response = client.get(f"/api/v1/rfq/{rfq_id}")
    assert response.status_code == 200
    assert response.json()["rfq_id"] == rfq_id

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
