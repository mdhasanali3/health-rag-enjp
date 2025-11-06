import pytest
import numpy as np
from unittest.mock import Mock, patch


@patch('app.storage.embeddings.SentenceTransformer')
def test_embedding_model_lazy_loading(mock_transformer):
    """Test that model is only loaded when first accessed"""
    from app.storage.embeddings import EmbeddingModel

    model = EmbeddingModel()
    # Model should not be loaded yet
    assert model._model is None

    # Access model property
    _ = model.model
    # Now model should be loaded
    mock_transformer.assert_called_once()


@patch('app.storage.embeddings.SentenceTransformer')
def test_embed_texts(mock_transformer):
    """Test text embedding generation"""
    from app.storage.embeddings import EmbeddingModel

    # Mock the transformer
    mock_instance = Mock()
    mock_instance.encode.return_value = np.random.rand(2, 384)
    mock_transformer.return_value = mock_instance

    model = EmbeddingModel()
    texts = ["Sample text 1", "Sample text 2"]
    embeddings = model.embed_texts(texts)

    assert embeddings.shape[0] == 2
    mock_instance.encode.assert_called_once()


@patch('app.storage.embeddings.SentenceTransformer')
def test_embed_single(mock_transformer):
    """Test single text embedding"""
    from app.storage.embeddings import EmbeddingModel

    mock_instance = Mock()
    mock_instance.encode.return_value = np.random.rand(1, 384)
    mock_transformer.return_value = mock_instance

    model = EmbeddingModel()
    embedding = model.embed_single("Test text")

    assert embedding.shape == (384,)


@patch('app.storage.embeddings.SentenceTransformer')
def test_embed_empty_list(mock_transformer):
    """Test embedding empty list"""
    from app.storage.embeddings import EmbeddingModel

    model = EmbeddingModel()
    embeddings = model.embed_texts([])

    assert len(embeddings) == 0
