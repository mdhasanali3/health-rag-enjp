# Design Notes: Healthcare RAG Assistant

## Architecture Overview

This document outlines the architectural decisions, scalability considerations, and future improvements for the Healthcare RAG Assistant system.

## Core Design Principles

### 1. Modularity and Separation of Concerns

The application follows a clean layered architecture:

- **API Layer** (`app/api/`): Handles HTTP requests/responses, validation, and orchestration
- **Core Layer** (`app/core/`): Configuration and cross-cutting concerns (auth, config)
- **Storage Layer** (`app/storage/`): Data persistence abstractions (FAISS, embeddings)
- **Utilities Layer** (`app/utils/`): Reusable components (translation, language detection)
- **Models Layer** (`app/models/`): Data schemas and validation

This separation enables:
- Independent testing of each layer
- Easy replacement of components (e.g., swap FAISS for another vector DB)
- Clear dependency flow (APIs depend on storage, not vice versa)

### 2. Bilingual Support

Language handling is built into the core architecture:

- **Automatic Detection**: Uses `langdetect` library at ingestion and query time
- **Metadata Storage**: Each document chunk stores its original language
- **Optional Translation**: Users can request results in either language via `output_language` parameter
- **Model Selection**: Uses multilingual sentence transformers to handle both languages in the same embedding space

**Trade-offs:**
- Multilingual models may have slightly lower performance than monolingual models
- Translation quality depends on model capabilities; medical terminology may require specialized models
- Translation adds latency (~1-2s per text depending on length)

### 3. Vector Storage with FAISS

**Why FAISS:**
- Fast similarity search (optimized by Meta AI)
- No external dependencies (embedded in-process)
- Suitable for POC and medium-scale deployments
- Multiple index types available for different scales

**Current Implementation:**
- `IndexFlatIP`: Exact search using inner product (cosine similarity on normalized vectors)
- SQLite for metadata: Allows rich queries on document properties
- Thread-safe operations via locks

**Limitations:**
- In-memory index: Memory grows with document count (~1.5KB per 384-dim vector)
- Single-server: No built-in distribution
- Persistence: Must explicitly save index to disk

## Scalability Considerations

### Current Capacity

With the default configuration:
- **Documents**: Can handle ~100K documents (typical medical guidelines corpus)
- **Memory**: ~150MB for 100K vectors + metadata
- **Latency**: <100ms for search queries on 100K documents
- **Throughput**: ~10-20 QPS on single server (limited by embedding generation)

### Scaling Strategies

#### 1. Vertical Scaling (Short-term)
- Increase server RAM for larger indexes
- Use GPU for faster embedding generation (10-50x speedup)
- Switch to `IndexIVFFlat` for approximate search at scale

#### 2. Horizontal Scaling (Medium-term)

**Approach A: Sharding by Specialty/Category**
```
Load Balancer
    ├─ Service 1: Diabetes & Endocrinology
    ├─ Service 2: Cardiology & Hypertension
    └─ Service 3: General Medicine
```
- Route queries based on detected topic/keywords
- Each service maintains its own FAISS index
- Reduces search space, improves latency

**Approach B: Replicated Read Instances**
```
Write API → Primary (ingestion)
              ├─ Replica 1 (read)
              ├─ Replica 2 (read)
              └─ Replica 3 (read)
```
- Separate ingestion from retrieval
- Periodic index synchronization
- Handles higher query load

#### 3. Enterprise Scaling (Long-term)

**Replace FAISS with Production Vector DB:**
- **Pinecone/Weaviate**: Managed vector databases with built-in scaling
- **Elasticsearch with vector fields**: Hybrid search (keywords + vectors)
- **Milvus/Qdrant**: Self-hosted distributed vector databases

**Benefits:**
- Automatic sharding and replication
- CRUD operations on vectors (FAISS is append-only)
- Advanced filtering and metadata queries
- Multi-tenancy support

### Async Processing for Ingestion

**Current:** Synchronous file upload → blocking embedding generation

**Improvement:**
```python
# Queue-based ingestion
POST /ingest → Job Queue (Redis/RabbitMQ)
                    ↓
            Background Workers
                    ↓
            Update Index + Notify
```

**Benefits:**
- Non-blocking API responses
- Handle large file batches
- Retry failed embeddings
- Progress tracking

## Caching Strategies

### 1. Query Embedding Cache
```python
@lru_cache(maxsize=1000)
def get_cached_embedding(query: str) -> np.ndarray:
    return embed_single(query)
```
- Cache frequently asked questions
- Redis for distributed caching
- TTL: 1 hour

### 2. Translation Cache
```python
translation_cache = {
    (text_hash, source_lang, target_lang): translated_text
}
```
- Medical terminology is repetitive
- Significant latency reduction

### 3. Model Preloading
- Currently: Lazy load on first use
- Improvement: Preload during startup (increases startup time but reduces first-request latency)

## Privacy and Security Considerations

### Protected Health Information (PHI)

**Current Implementation:**
- Basic API key authentication
- No PHI filtering or detection

**Production Requirements:**
1. **Data Sanitization**: Detect and redact/anonymize PHI in documents
   - Patient names, IDs, dates
   - Use NER models trained on medical text

2. **Encryption**:
   - At rest: Encrypt FAISS index and SQLite database
   - In transit: HTTPS only (enforce with middleware)

3. **Access Control**:
   - Role-based access (admin, clinician, viewer)
   - Audit logging for all queries and document access

4. **Compliance**:
   - HIPAA compliance for US healthcare
   - GDPR for EU patients
   - Data retention policies

### API Security

**Current:**
- Single API key (shared secret)

**Improvements:**
- JWT tokens with expiration
- Rate limiting (per-user/IP)
- Request signing for tamper protection

## Translation Quality

### Current Approach

- MarianMT models from Helsinki-NLP
- General-purpose translation

### Challenges with Medical Text

1. **Terminology**: Drug names, procedures, anatomical terms
2. **Abbreviations**: May not translate correctly
3. **Context**: Medical context crucial for accuracy

### Improvements

1. **Domain-Specific Models**:
   - Fine-tune MarianMT on medical corpora (PubMed, clinical guidelines)
   - Use medical translation services (e.g., AWS Medical Translate)

2. **Terminology Dictionary**:
   ```python
   medical_terms = {
       "en": {"diabetes": "diabetes mellitus"},
       "ja": {"糖尿病": "diabetes"}
   }
   ```
   - Protect medical terms from translation
   - Post-processing term substitution

3. **Human Review Loop**:
   - Flag uncertain translations
   - Clinician validation for critical content

## Mock LLM vs. Real LLM

### Current Implementation

Template-based response generation:
- Predictable, deterministic output
- Low latency, no API costs
- Suitable for POC/demo

### Production LLM Integration

**Architecture:**
```python
def generate_with_llm(query: str, sources: List[Dict]) -> str:
    context = "\n\n".join([s["text"] for s in sources])
    prompt = f"""You are a medical assistant. Answer based only on these sources:

    {context}

    Question: {query}
    Answer:"""

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "system", "content": prompt}]
    )
    return response.choices[0].message.content
```

**LLM Options:**
1. **OpenAI GPT-4**: Best quality, expensive, API dependency
2. **Anthropic Claude**: Strong medical reasoning
3. **Open-source (Llama 3, Mistral)**: Self-hosted, cost-effective at scale
4. **Medical LLMs (Med-PaLM, BioGPT)**: Specialized knowledge

**Considerations:**
- **Hallucination**: LLMs may generate false information; citation forcing critical
- **Latency**: 2-10s per response depending on model/length
- **Cost**: $0.01-0.10 per query depending on model
- **Privacy**: Self-hosted models for PHI compliance

## Future Enhancements

### 1. Multi-Modal Support
- Ingest PDFs with tables and diagrams
- Image analysis (medical charts, X-rays) using vision models
- Extract text from scanned documents (OCR)

### 2. Advanced Retrieval

**Hybrid Search:**
```python
# Combine vector search + keyword search
vector_results = faiss_search(query_embedding)
keyword_results = elasticsearch_search(query_text)
final_results = rerank(vector_results + keyword_results)
```

**Semantic Reranking:**
- Use cross-encoder models to rerank top-K results
- Improves precision for complex queries

### 3. Feedback Loop

```python
POST /feedback
{
    "query": "...",
    "doc_id": "doc_123",
    "helpful": true,
    "comment": "Very relevant"
}
```

- Collect relevance feedback
- Fine-tune embeddings on domain data
- A/B test retrieval strategies

### 4. Structured Output

Instead of free-form text:
```json
{
    "condition": "Type 2 Diabetes",
    "recommendations": [
        {
            "category": "Diet",
            "actions": ["Reduce sugar intake", "..."],
            "evidence_level": "A"
        }
    ],
    "sources": [...]
}
```

Parse medical guidelines into structured knowledge graphs.

### 5. Real-time Updates

- Watch document directories for changes
- Incremental index updates (add/delete documents)
- Versioning for guideline updates

## Performance Benchmarks

### Target SLAs (Production)

| Operation | Latency (p95) | Throughput |
|-----------|---------------|------------|
| Ingestion (per doc) | <5s | 10 docs/min |
| Retrieve | <200ms | 50 QPS |
| Generate (mock) | <500ms | 30 QPS |
| Generate (real LLM) | <5s | 10 QPS |

### Optimization Opportunities

1. **Batch Embedding**: Process multiple queries in parallel
2. **Model Quantization**: Reduce model size (INT8) for faster inference
3. **Connection Pooling**: Reuse HTTP clients for translation APIs
4. **Async I/O**: FastAPI supports async; use for I/O-bound operations

## Monitoring and Observability

**Essential Metrics:**
- Query latency (p50, p95, p99)
- Embedding generation time
- Index size and search performance
- Error rates by endpoint
- API key usage patterns

**Tools:**
- Prometheus + Grafana for metrics
- OpenTelemetry for distributed tracing
- Logging (structured JSON logs)

**Health Indicators:**
- Index age (time since last update)
- Model availability
- Disk space (for index persistence)

## Conclusion

This architecture provides a solid foundation for a healthcare RAG system with room to grow. The modular design allows incremental improvements: start with FAISS for POC, migrate to a production vector DB as scale demands. The bilingual support and translation capabilities address the unique requirements of international medical practices.

Key next steps for production readiness:
1. Implement proper PHI handling and encryption
2. Replace mock LLM with real model + hallucination safeguards
3. Add comprehensive monitoring and alerting
4. Conduct security audit and penetration testing
5. Load testing to validate SLAs

The system balances simplicity (embedded FAISS, no external services) with flexibility (easy to swap components), making it suitable for both small clinics and larger healthcare organizations with different scaling needs.
