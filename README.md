# Healthcare RAG Assistant

A bilingual (English/Japanese) Retrieval-Augmented Generation system for medical knowledge retrieval, built with FastAPI, FAISS, and Sentence Transformers.

## Overview

This system enables clinicians to upload medical guidelines and research documents in English or Japanese, then query them using natural language. The system automatically detects languages, generates embeddings, performs semantic search, and can translate results between languages.

## Features

- **Bilingual Support**: Handles English and Japanese documents and queries
- **Document Ingestion**: Upload `.txt` files with automatic language detection and chunking
- **Semantic Search**: Vector similarity search using multilingual sentence embeddings
- **Translation**: Optional translation of results between EN/JA
- **Mock LLM Generation**: Template-based response generation with source citations
- **API Authentication**: Secure endpoints with API key validation
- **CI/CD**: Automated testing and Docker builds via GitHub Actions

## Architecture

```
healthcare-rag/
├── app/
│   ├── main.py              # FastAPI application
│   ├── api/                 # API endpoints
│   │   ├── ingest.py       # Document ingestion
│   │   ├── retrieve.py     # Semantic search
│   │   └── generate.py     # RAG response generation
│   ├── core/               # Core functionality
│   │   ├── config.py       # Configuration management
│   │   └── auth.py         # API key authentication
│   ├── storage/            # Data persistence
│   │   ├── embeddings.py   # Sentence transformer wrapper
│   │   └── faiss_index.py  # FAISS vector store + SQLite metadata
│   ├── utils/              # Utilities
│   │   ├── langdetect.py   # Language detection
│   │   └── translation.py  # EN/JA translation
│   └── models/
│       └── schemas.py      # Pydantic models
├── tests/                  # Unit tests
├── Dockerfile             # Multi-stage container build
├── .github/workflows/     # CI/CD pipeline
└── requirements.txt       # Python dependencies
```

## Setup

### Prerequisites

- Python 3.10+
- 4GB+ RAM (for embedding models)
- Git

### Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd health_acme
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment**
```bash
cp .env.example .env
# Edit .env and set your API_KEY
```

### Environment Variables

Create a `.env` file with the following:

```bash
# Security
API_KEY=your-secure-api-key-here

# Storage
FAISS_INDEX_PATH=./data/faiss_index.bin
FAISS_METADATA_PATH=./data/faiss_metadata.db

# Models
EMBEDDING_MODEL_NAME=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
TRANSLATION_BACKEND=transformers

# Server
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=INFO
```

## Running the Application

### Local Development

```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Or using the main module:

```bash
python app/main.py
```

### Docker

**Build the image:**
```bash
docker build -t healthcare-rag:latest .
```

**Run the container:**
```bash
docker run -d \
  -p 8000:8000 \
  -e API_KEY=your-secret-key \
  -v $(pwd)/data:/app/data \
  --name healthcare-rag \
  healthcare-rag:latest
```

### Access the API

- API: http://localhost:8000
- Interactive Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

## API Usage

### 1. Ingest Documents

Upload medical documents (`.txt` files):

```bash
curl -X POST "http://localhost:8000/ingest" \
  -H "X-API-Key: your-secret-key" \
  -F "files=@diabetes_guidelines.txt" \
  -F "files=@hypertension_guide.txt"
```

**Response:**
```json
{
  "success": true,
  "files_processed": 2,
  "total_chunks_added": 15,
  "details": [
    {
      "filename": "diabetes_guidelines.txt",
      "status": "success",
      "chunks_created": 8,
      "language": "en"
    }
  ],
  "message": "Successfully processed 2/2 files"
}
```

### 2. Retrieve Similar Documents

Search for relevant documents:

```bash
curl -X POST "http://localhost:8000/retrieve" \
  -H "X-API-Key: your-secret-key" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the latest recommendations for Type 2 diabetes?",
    "top_k": 3,
    "output_language": "ja"
  }'
```

**Response:**
```json
{
  "query": "What are the latest recommendations for Type 2 diabetes?",
  "results": [
    {
      "doc_id": "doc_1",
      "text": "Type 2 diabetes management includes...",
      "score": 0.89,
      "language": "en",
      "filename": "diabetes_guidelines.txt"
    }
  ],
  "query_language": "en",
  "results_translated": true
}
```

### 3. Generate RAG Response

Get a generated response with sources:

```bash
curl -X POST "http://localhost:8000/generate" \
  -H "X-API-Key: your-secret-key" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "糖尿病の管理方法は？",
    "top_k": 3
  }'
```

**Response:**
```json
{
  "query": "糖尿病の管理方法は？",
  "generated_text": "ご質問「糖尿病の管理方法は？」について...",
  "sources": [
    {
      "doc_id": "doc_1",
      "snippet": "Type 2 diabetes requires...",
      "score": 0.92,
      "filename": "diabetes.txt"
    }
  ],
  "query_language": "ja"
}
```

## Testing

Run the test suite:

```bash
# All tests
pytest tests/ -v

# Specific test file
pytest tests/test_api.py -v

# With coverage
pytest tests/ --cov=app --cov-report=html
```

## CI/CD Pipeline

The GitHub Actions workflow automatically:

1. **Tests** - Runs pytest on all code
2. **Linting** - Checks code quality with flake8 and black
3. **Build** - Creates Docker image
4. **Security** - Scans dependencies for vulnerabilities

Triggered on:
- Push to `main` or `develop`
- Pull requests to `main`

## Project Structure Details

### Data Flow

1. **Ingestion**: Text file → Language detection → Chunking → Embedding → FAISS + SQLite
2. **Retrieval**: Query → Embedding → FAISS search → Metadata lookup → (Optional translation)
3. **Generation**: Query → Retrieval → Mock LLM template → Response with citations

### Storage

- **FAISS Index**: Stores 384-dim vectors (cosine similarity via inner product on normalized vectors)
- **SQLite**: Stores document metadata (text, language, filename, chunk index)
- **Thread-safe**: Uses locks for concurrent access

### Models

- **Embeddings**: `paraphrase-multilingual-MiniLM-L12-v2` (384 dimensions)
- **Translation**: Helsinki-NLP MarianMT models for EN↔JA

## Troubleshooting

### Model Download Issues

If models fail to download, set cache directory:
```bash
export TRANSFORMERS_CACHE=/path/to/cache
export SENTENCE_TRANSFORMERS_HOME=/path/to/cache
```

### Memory Issues

For systems with limited RAM:
1. Reduce `max_chunk_size` in config
2. Use smaller embedding model
3. Process fewer files per batch

### Port Already in Use

Change port in `.env`:
```bash
PORT=8080
```

## Development

### Adding New Endpoints

1. Create router in `app/api/`
2. Add schemas to `app/models/schemas.py`
3. Include router in `app/main.py`
4. Add tests in `tests/`

### Code Style

- Follow PEP 8
- Max line length: 100 characters
- Use type hints
- Document functions with docstrings

## AI Usage Disclosure

This project was developed with assistance from AI coding tools to accelerate development. All code has been reviewed, tested, and validated for correctness, security, and functionality. Key areas where AI assistance was used:

- Initial project scaffolding and structure
- Boilerplate code for FastAPI endpoints
- Unit test templates and fixtures
- Documentation structure and examples

The developer takes full responsibility for all code in this repository, including proper testing, security review, and validation of AI-generated content.

## License

This project is provided as-is for educational and evaluation purposes.

## References

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [FAISS: Facebook AI Similarity Search](https://github.com/facebookresearch/faiss)
- [Sentence Transformers](https://www.sbert.net/)
- [Helsinki-NLP Translation Models](https://huggingface.co/Helsinki-NLP)

## Contact

For questions or issues, please open a GitHub issue or contact the development team.
