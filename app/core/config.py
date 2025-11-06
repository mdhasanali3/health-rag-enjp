import os
from pathlib import Path
from typing import Literal
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application configuration loaded from environment variables"""

    # Security
    api_key: str = "dev-key-change-in-production"

    # Storage
    faiss_index_path: str = "./data/faiss_index.bin"
    faiss_metadata_path: str = "./data/faiss_metadata.db"

    # Model configuration
    embedding_model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    embedding_dimension: int = 384  # for the default model

    # Translation backend: "transformers" is more reliable
    translation_backend: Literal["transformers", "none"] = "transformers"
    translation_model_en_ja: str = "Helsinki-NLP/opus-mt-en-jap"
    translation_model_ja_en: str = "Helsinki-NLP/opus-mt-jap-en"

    # Retrieval defaults
    default_top_k: int = 3
    max_top_k: int = 10

    # Chunking
    max_chunk_size: int = 1000  # characters
    chunk_overlap: int = 200

    # Logging
    log_level: str = "INFO"

    # API
    host: str = "0.0.0.0"
    port: int = 8000

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Singleton instance
settings = Settings()

# Ensure data directory exists
data_dir = Path(settings.faiss_index_path).parent
data_dir.mkdir(parents=True, exist_ok=True)
