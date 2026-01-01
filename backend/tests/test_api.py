"""
Basic API tests for Wingman backend
"""
import pytest
from app.database import init_db
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


@pytest.fixture(scope="session", autouse=True)
def setup_db():
    """Initialize database for all tests"""
    init_db()


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


def test_ask_endpoint_with_question():
    """Test ask endpoint with a valid question"""
    response = client.post("/api/ask", json={"question": "What is RAG?"})
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert isinstance(data["answer"], str)


def test_ask_endpoint_includes_confidence():
    """Test that ask endpoint returns confidence score"""
    response = client.post("/api/ask", json={"question": "What is the API?"})
    assert response.status_code == 200
    data = response.json()
    assert "confidence" in data
    assert data["confidence"] in ["high", "low"]


def test_ask_endpoint_includes_sources():
    """Test that ask endpoint returns source information"""
    response = client.post("/api/ask", json={"question": "Tell me about the system"})
    assert response.status_code == 200
    data = response.json()
    assert "sources" in data
    assert isinstance(data["sources"], list)


def test_documents_endpoint_list():
    """Test listing documents"""
    response = client.get("/api/documents")
    assert response.status_code == 200
    data = response.json()
    assert "documents" in data
    assert isinstance(data["documents"], list)


def test_documents_endpoint_create():
    """Test creating a document"""
    doc_data = {
        "title": "Test Document",
        "content": "This is test content for indexing.",
        "source": "test"
    }
    response = client.post("/api/documents", json=doc_data)
    assert response.status_code in [200, 201]


def test_messages_endpoint():
    """Test retrieving messages"""
    response = client.get("/api/messages")
    assert response.status_code == 200
    data = response.json()
    assert "messages" in data
    assert isinstance(data["messages"], list)


def test_messages_endpoint_with_channel_filter():
    """Test retrieving messages with channel filter"""
    response = client.get("/api/messages?channel_id=C123456")
    assert response.status_code == 200
    data = response.json()
    assert "messages" in data


class TestErrorHandling:
    """Tests for error handling in API endpoints"""
    
    def test_invalid_json_request(self):
        """Test handling of invalid JSON"""
        response = client.post("/api/ask", content="not json", headers={"Content-Type": "application/json"})
        assert response.status_code in [400, 422]
    
    def test_empty_question_string(self):
        """Test handling of empty question"""
        response = client.post("/api/ask", json={"question": ""})
        # Should either reject or handle gracefully
        assert response.status_code in [200, 400, 422]
    
    def test_very_long_question(self):
        """Test handling of very long question"""
        long_question = "Why " * 1000  # Create a very long string
        response = client.post("/api/ask", json={"question": long_question})
        # Should process or reject gracefully
        assert response.status_code in [200, 413]


class TestDocumentOperations:
    """Tests for document operations"""
    
    def test_create_and_retrieve_document(self):
        """Test creating a document and verifying it can be retrieved"""
        doc_data = {
            "title": "Integration Test Doc",
            "content": "Integration test content with specific keywords.",
            "source": "integration_test"
        }
        
        # Create document
        create_response = client.post("/api/documents", json=doc_data)
        assert create_response.status_code in [200, 201]
        
        # List documents
        list_response = client.get("/api/documents")
        assert list_response.status_code == 200
        data = list_response.json()
        assert len(data["documents"]) > 0
    
    def test_document_with_special_characters(self):
        """Test creating document with special characters"""
        doc_data = {
            "title": "Special Chars: !@#$%^&*()",
            "content": "Content with emojis 🎉 and symbols → ← ↑ ↓",
            "source": "test"
        }
        response = client.post("/api/documents", json=doc_data)
        assert response.status_code in [200, 201]
    
    def test_document_with_markdown(self):
        """Test creating document with markdown content"""
        doc_data = {
            "title": "Markdown Documentation",
            "content": """# Header
## Subheader
- Bullet point 1
- Bullet point 2

Code example:
```python
def hello():
    return "world"
```
""",
            "source": "markdown_test"
        }
        response = client.post("/api/documents", json=doc_data)
        assert response.status_code in [200, 201]

