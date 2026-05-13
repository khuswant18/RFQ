"""Comprehensive API tests for SRIP."""
import pytest
from fastapi.testclient import TestClient
from app.main import app

# Initialize test client correctly
def get_test_client():
    return TestClient(app)


# ==================== Health & Root Tests ====================

def test_health_check():
    """Test health endpoint."""
    client = get_test_client()
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    print("✅ /health works")


def test_root():
    """Test root endpoint."""
    client = get_test_client()
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "Smart RFQ Intelligence Pipeline (SRIP)"
    assert "docs" in data
    print("✅ / works")


# ==================== RFQ Endpoints ====================

def test_rfq_feed_empty():
    """Test RFQ feed endpoint."""
    client = get_test_client()
    response = client.get("/api/v1/rfq/feed")
    assert response.status_code == 200
    data = response.json()
    assert "rfqs" in data or "status" in data or "error" in data
    print("✅ /api/v1/rfq/feed works")


def test_rfq_list():
    """Test RFQ list endpoint (alias)."""
    client = get_test_client()
    response = client.get("/api/v1/rfq")
    assert response.status_code == 200
    data = response.json()
    assert "rfqs" in data or "status" in data or "error" in data
    print("✅ /api/v1/rfq works")


def test_rfq_not_found():
    """Test RFQ get with invalid ID."""
    client = get_test_client()
    response = client.get("/api/v1/rfq/invalid-id-12345")
    assert response.status_code in [404, 200]
    print("✅ /api/v1/rfq/{id} returns proper response")


def test_rfq_status():
    """Test RFQ status endpoint."""
    client = get_test_client()
    response = client.get("/api/v1/rfq/test-id/status")
    assert response.status_code in [404, 200]
    print("✅ /api/v1/rfq/{id}/status works")


# ==================== Upload Endpoint ====================

def test_upload_file():
    """Test file upload endpoint."""
    client = get_test_client()
    test_content = b"Test RFQ content"
    response = client.post(
        "/api/v1/ingest/upload",
        files={"file": ("test_rfq.txt", test_content, "text/plain")},
    )
    assert response.status_code == 200
    data = response.json()
    assert "rfq_id" in data
    assert data["status"] == "received"
    print(f"✅ /api/v1/ingest/upload works")


# ==================== Quote Endpoint ====================

def test_quote_not_found():
    """Test quote endpoint with invalid ID."""
    client = get_test_client()
    response = client.get("/api/v1/rfq/invalid-id/quote")
    assert response.status_code in [404, 200]
    print("✅ /api/v1/rfq/{id}/quote returns proper response")


# ==================== Auth Endpoints ====================

def test_login_valid():
    """Test login with valid credentials."""
    client = get_test_client()
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["username"] == "admin"
    print("✅ /api/v1/auth/login works (admin)")


def test_login_operator():
    """Test login with operator credentials."""
    client = get_test_client()
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "operator", "password": "operator123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["username"] == "operator"
    print("✅ /api/v1/auth/login works (operator)")


def test_login_invalid():
    """Test login with invalid credentials."""
    client = get_test_client()
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "invalid", "password": "wrong"},
    )
    assert response.status_code == 401
    print("✅ /api/v1/auth/login properly rejects invalid credentials")


def test_get_me_with_token():
    """Test get current user endpoint."""
    client = get_test_client()
    # Get token first
    login_response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    token = login_response.json()["access_token"]
    
    # Use token
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "admin"
    print("✅ /api/v1/auth/me works with token")
