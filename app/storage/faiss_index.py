import logging
import sqlite3
import threading
import pickle
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import faiss
from app.core.config import settings

logger = logging.getLogger(__name__)


class FaissIndexManager:
    """
    Manages FAISS index and associated metadata.
    Uses SQLite for metadata storage and thread-safe operations.
    """

    def __init__(self, index_path: str, metadata_path: str, dimension: int):
        self.index_path = Path(index_path)
        self.metadata_path = Path(metadata_path)
        self.dimension = dimension
        self.index: Optional[faiss.Index] = None
        self.lock = threading.Lock()
        self._doc_counter = 0

        # Initialize
        self._ensure_directories()
        self._init_metadata_db()
        self._load_or_create_index()

    def _ensure_directories(self):
        """Create necessary directories"""
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self.metadata_path.parent.mkdir(parents=True, exist_ok=True)

    def _init_metadata_db(self):
        """Initialize SQLite database for metadata"""
        conn = sqlite3.connect(str(self.metadata_path))
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY,
                doc_id TEXT UNIQUE,
                text TEXT,
                language TEXT,
                filename TEXT,
                chunk_index INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()
        logger.info(f"Metadata database initialized at {self.metadata_path}")

    def _load_or_create_index(self):
        """Load existing index or create new one"""
        with self.lock:
            if self.index_path.exists():
                try:
                    self.index = faiss.read_index(str(self.index_path))
                    logger.info(f"Loaded existing FAISS index with {self.index.ntotal} vectors")

                    # Restore counter from DB
                    conn = sqlite3.connect(str(self.metadata_path))
                    cursor = conn.cursor()
                    cursor.execute("SELECT MAX(id) FROM documents")
                    max_id = cursor.fetchone()[0]
                    self._doc_counter = max_id if max_id else 0
                    conn.close()
                except Exception as e:
                    logger.warning(f"Failed to load index: {e}. Creating new one.")
                    self._create_new_index()
            else:
                self._create_new_index()

    def _create_new_index(self):
        """Create a new FAISS index"""
        # Using IndexFlatIP for inner product (cosine similarity with normalized vectors)
        self.index = faiss.IndexFlatIP(self.dimension)
        logger.info(f"Created new FAISS index with dimension {self.dimension}")

    def add_documents(
        self,
        texts: List[str],
        embeddings: np.ndarray,
        languages: List[str],
        filenames: List[str],
        chunk_indices: List[int]
    ) -> List[str]:
        """
        Add documents to the index.

        Args:
            texts: Document texts
            embeddings: Pre-computed embeddings
            languages: Language codes for each doc
            filenames: Source filenames
            chunk_indices: Chunk index within file

        Returns:
            List of assigned document IDs
        """
        if len(texts) != len(embeddings):
            raise ValueError("Texts and embeddings length mismatch")

        with self.lock:
            doc_ids = []
            conn = sqlite3.connect(str(self.metadata_path))
            cursor = conn.cursor()

            try:
                for i, (text, lang, fname, chunk_idx) in enumerate(
                    zip(texts, languages, filenames, chunk_indices)
                ):
                    self._doc_counter += 1
                    doc_id = f"doc_{self._doc_counter}"
                    doc_ids.append(doc_id)

                    # Store metadata
                    cursor.execute(
                        """
                        INSERT INTO documents (id, doc_id, text, language, filename, chunk_index)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (self._doc_counter, doc_id, text, lang, fname, chunk_idx)
                    )

                # Add embeddings to FAISS
                embeddings_array = np.array(embeddings).astype('float32')
                self.index.add(embeddings_array)

                conn.commit()
                logger.info(f"Added {len(doc_ids)} documents to index")

            except Exception as e:
                conn.rollback()
                logger.error(f"Failed to add documents: {e}")
                raise
            finally:
                conn.close()

            return doc_ids

    def search(
        self,
        query_embedding: np.ndarray,
        top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Search for similar documents.

        Args:
            query_embedding: Query vector
            top_k: Number of results to return

        Returns:
            List of dicts with keys: doc_id, text, language, filename, score
        """
        with self.lock:
            if self.index.ntotal == 0:
                return []

            # Ensure query is 2D
            if query_embedding.ndim == 1:
                query_embedding = query_embedding.reshape(1, -1)

            query_embedding = query_embedding.astype('float32')

            # Search
            scores, indices = self.index.search(query_embedding, min(top_k, self.index.ntotal))

            # Fetch metadata
            conn = sqlite3.connect(str(self.metadata_path))
            cursor = conn.cursor()

            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx == -1:  # FAISS returns -1 for empty slots
                    continue

                # FAISS index is 0-based, our DB IDs are 1-based
                db_id = int(idx) + 1
                cursor.execute(
                    "SELECT doc_id, text, language, filename FROM documents WHERE id = ?",
                    (db_id,)
                )
                row = cursor.fetchone()

                if row:
                    results.append({
                        "doc_id": row[0],
                        "text": row[1],
                        "language": row[2],
                        "filename": row[3],
                        "score": float(score)
                    })

            conn.close()
            return results

    def persist(self):
        """Save index to disk"""
        with self.lock:
            if self.index and self.index.ntotal > 0:
                faiss.write_index(self.index, str(self.index_path))
                logger.info(f"Persisted FAISS index with {self.index.ntotal} vectors")

    def get_stats(self) -> Dict[str, Any]:
        """Get index statistics"""
        with self.lock:
            conn = sqlite3.connect(str(self.metadata_path))
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM documents")
            doc_count = cursor.fetchone()[0]
            conn.close()

            return {
                "total_documents": doc_count,
                "total_vectors": self.index.ntotal if self.index else 0,
                "dimension": self.dimension
            }


# Global singleton
_index_manager: Optional[FaissIndexManager] = None


def get_index_manager() -> FaissIndexManager:
    """Get or create the global index manager"""
    global _index_manager
    if _index_manager is None:
        from app.storage.embeddings import get_embedding_model
        embedding_model = get_embedding_model()
        dimension = embedding_model.dimension

        _index_manager = FaissIndexManager(
            index_path=settings.faiss_index_path,
            metadata_path=settings.faiss_metadata_path,
            dimension=dimension
        )
    return _index_manager
