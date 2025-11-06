import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
import numpy as np


@pytest.fixture
def client(mock_settings):
    """Create test client with mocked dependencies"""
    # Import after settings are mocked
    from app.main import app
    return TestClient(app)


def test_health_endpoint(client):
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "index_stats" in data


def test_root_endpoint(client):
    """Test root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert "endpoints" in data


def test_auth_required(client, test_api_key):
    """Test that protected endpoints require API key"""
    # Without API key
    response = client.post("/retrieve", json={"query": "test"})
    assert response.status_code == 422  # Missing required header

    # With wrong API key
    response = client.post(
        "/retrieve",
        json={"query": "test"},
        headers={"X-API-Key": "wrong-key"}
    )
    assert response.status_code == 401

    # With correct API key should not fail auth (might fail for other reasons)
    response = client.post(
        "/retrieve",
        json={"query": "test"},
        headers={"X-API-Key": test_api_key}
    )
    # Should not be 401/422 due to auth
    assert response.status_code != 401


@patch('app.storage.embeddings.get_embedding_model')
@patch('app.storage.faiss_index.get_index_manager')
def test_ingest_endpoint(mock_index, mock_embeddings, client, test_api_key, sample_text_files):
    """Test document ingestion"""
    # Mock embedding model
    mock_embed = Mock()
    mock_embed.embed_texts.return_value = np.random.rand(3, 384).astype('float32')
    mock_embeddings.return_value = mock_embed

    # Mock index manager
    mock_idx = Mock()
    mock_idx.add_documents.return_value = ["doc_1", "doc_2", "doc_3"]
    mock_idx.persist.return_value = None
    mock_index.return_value = mock_idx

    # Test file upload
    with open(sample_text_files["en"], "rb") as f:
        response = client.post(
            "/ingest",
            files={"files": ("test.txt", f, "text/plain")},
            headers={"X-API-Key": test_api_key}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] == True
    assert data["files_processed"] >= 1


@patch('app.storage.embeddings.get_embedding_model')
@patch('app.storage.faiss_index.get_index_manager')
def test_retrieve_endpoint(mock_index, mock_embeddings, client, test_api_key):
    """Test document retrieval"""
    # Mock embedding model
    mock_embed = Mock()
    mock_embed.embed_single.return_value = np.random.rand(384).astype('float32')
    mock_embeddings.return_value = mock_embed

    # Mock index manager
    mock_idx = Mock()
    mock_idx.search.return_value = [
        {
            "doc_id": "doc_1",
            "text": "Sample medical text",
            "language": "en",
            "filename": "test.txt",
            "score": 0.95
        }
    ]
    mock_index.return_value = mock_idx

    response = client.post(
        "/retrieve",
        json={"query": "diabetes management", "top_k": 3},
        headers={"X-API-Key": test_api_key}
    )

    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert "query" in data
    assert data["query"] == "diabetes management"


@patch('app.storage.embeddings.get_embedding_model')
@patch('app.storage.faiss_index.get_index_manager')
def test_generate_endpoint(mock_index, mock_embeddings, client, test_api_key):
    """Test response generation"""
    # Mock embedding model
    mock_embed = Mock()
    mock_embed.embed_single.return_value = np.random.rand(384).astype('float32')
    mock_embeddings.return_value = mock_embed

    # Mock index manager with results
    mock_idx = Mock()
    mock_idx.search.return_value = [
        {
            "doc_id": "doc_1",
            "text": "Type 2 diabetes requires careful management.",
            "language": "en",
            "filename": "diabetes.txt",
            "score": 0.92
        }
    ]
    mock_index.return_value = mock_idx

    response = client.post(
        "/generate",
        json={"query": "How to manage diabetes?", "top_k": 3},
        headers={"X-API-Key": test_api_key}
    )

    assert response.status_code == 200
    data = response.json()
    assert "generated_text" in data
    assert "sources" in data
    assert len(data["sources"]) > 0
