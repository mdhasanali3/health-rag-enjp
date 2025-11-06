import pytest
import numpy as np
from pathlib import Path


def test_faiss_index_creation(temp_dir):
    """Test FAISS index initialization"""
    from app.storage.faiss_index import FaissIndexManager

    index_path = Path(temp_dir) / "test.bin"
    metadata_path = Path(temp_dir) / "meta.db"

    manager = FaissIndexManager(
        index_path=str(index_path),
        metadata_path=str(metadata_path),
        dimension=384
    )

    assert manager.index is not None
    assert manager.index.ntotal == 0
    assert metadata_path.exists()


def test_add_and_search_documents(temp_dir):
    """Test adding and searching documents"""
    from app.storage.faiss_index import FaissIndexManager

    index_path = Path(temp_dir) / "test.bin"
    metadata_path = Path(temp_dir) / "meta.db"

    manager = FaissIndexManager(
        index_path=str(index_path),
        metadata_path=str(metadata_path),
        dimension=384
    )

    # Add documents
    embeddings = np.random.rand(3, 384).astype('float32')
    # Normalize for cosine similarity
    embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)

    doc_ids = manager.add_documents(
        texts=["Text 1", "Text 2", "Text 3"],
        embeddings=embeddings,
        languages=["en", "en", "ja"],
        filenames=["file1.txt", "file1.txt", "file2.txt"],
        chunk_indices=[0, 1, 0]
    )

    assert len(doc_ids) == 3
    assert manager.index.ntotal == 3

    # Search
    query_embedding = np.random.rand(384).astype('float32')
    query_embedding = query_embedding / np.linalg.norm(query_embedding)

    results = manager.search(query_embedding, top_k=2)

    assert len(results) <= 2
    if len(results) > 0:
        assert "doc_id" in results[0]
        assert "text" in results[0]
        assert "score" in results[0]


def test_persist_and_load(temp_dir):
    """Test saving and loading index"""
    from app.storage.faiss_index import FaissIndexManager

    index_path = Path(temp_dir) / "test.bin"
    metadata_path = Path(temp_dir) / "meta.db"

    # Create and populate index
    manager1 = FaissIndexManager(
        index_path=str(index_path),
        metadata_path=str(metadata_path),
        dimension=384
    )

    embeddings = np.random.rand(2, 384).astype('float32')
    embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)

    manager1.add_documents(
        texts=["Text A", "Text B"],
        embeddings=embeddings,
        languages=["en", "ja"],
        filenames=["a.txt", "b.txt"],
        chunk_indices=[0, 0]
    )

    manager1.persist()
    assert index_path.exists()

    # Load in new manager
    manager2 = FaissIndexManager(
        index_path=str(index_path),
        metadata_path=str(metadata_path),
        dimension=384
    )

    assert manager2.index.ntotal == 2
    stats = manager2.get_stats()
    assert stats["total_documents"] == 2
