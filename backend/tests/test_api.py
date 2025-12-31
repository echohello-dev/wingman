"""
Basic API tests for Wingman backend
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_root_endpoint():
    """Test the root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Wingman"
    assert "version" in data
    assert data["status"] == "running"


def test_health_endpoint():
    """Test the health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_ask_endpoint_missing_question():
    """Test ask endpoint with missing question"""
    response = client.post("/api/ask", json={})
    assert response.status_code == 422  # Validation error
