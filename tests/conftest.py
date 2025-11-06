import pytest
import tempfile
import os
from pathlib import Path
from fastapi.testclient import TestClient


@pytest.fixture
def temp_dir():
    """Create temporary directory for test data"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def test_api_key():
    """Test API key"""
    return "test-api-key-12345"


@pytest.fixture
def mock_settings(monkeypatch, temp_dir, test_api_key):
    """Mock settings for testing"""
    monkeypatch.setenv("API_KEY", test_api_key)
    monkeypatch.setenv("FAISS_INDEX_PATH", os.path.join(temp_dir, "test_index.bin"))
    monkeypatch.setenv("FAISS_METADATA_PATH", os.path.join(temp_dir, "test_metadata.db"))
    monkeypatch.setenv("LOG_LEVEL", "ERROR")  # Reduce noise in tests


@pytest.fixture
def sample_text_files(temp_dir):
    """Create sample text files for testing"""
    files = {}

    # English file
    en_file = Path(temp_dir) / "diabetes_guide.txt"
    en_file.write_text(
        "Type 2 diabetes management includes lifestyle modifications, "
        "monitoring blood glucose levels, and medication when necessary. "
        "Patients should maintain a healthy diet and regular exercise routine."
    )
    files["en"] = en_file

    # Japanese file
    ja_file = Path(temp_dir) / "hypertension_guide.txt"
    ja_file.write_text(
        "高血圧の管理には、減塩食、適度な運動、ストレス管理が重要です。"
        "定期的な血圧測定を行い、必要に応じて降圧薬を使用します。"
    )
    files["ja"] = ja_file

    return files
