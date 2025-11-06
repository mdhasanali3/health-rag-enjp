import logging
from fastapi import APIRouter, Depends, HTTPException
from app.core.auth import verify_api_key
from app.models.schemas import (
    RetrieveRequest,
    RetrieveResponse,
    DocumentResult,
    create_snippet
)
from app.storage.embeddings import get_embedding_model
from app.storage.faiss_index import get_index_manager
from app.utils.langdetect import detect_language
from app.utils.translation import translate

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/retrieve", response_model=RetrieveResponse)
async def retrieve_documents(
    request: RetrieveRequest,
    _: str = Depends(verify_api_key)
):
    """
    Retrieve relevant documents for a query.

    Detects query language, performs semantic search,
    and optionally translates results to target language.
    """
    # Detect query language
    query_lang = detect_language(request.query)
    logger.info(f"Query language detected: {query_lang}")

    # Get embedding for query
    embedding_model = get_embedding_model()
    query_embedding = embedding_model.embed_single(request.query)

    # Search index
    index_manager = get_index_manager()
    search_results = index_manager.search(query_embedding, top_k=request.top_k)

    if not search_results:
        return RetrieveResponse(
            query=request.query,
            results=[],
            query_language=query_lang,
            results_translated=False
        )

    # Process results
    results_translated = False
    document_results = []

    for result in search_results:
        text = result["text"]
        original_lang = result["language"]

        # Translate if requested and language differs
        if request.output_language and request.output_language != original_lang:
            text = translate(text, original_lang, request.output_language)
            results_translated = True

        # Create snippet for display
        snippet = create_snippet(text, max_length=300)

        document_results.append(
            DocumentResult(
                doc_id=result["doc_id"],
                text=snippet,
                score=result["score"],
                language=original_lang,
                filename=result["filename"]
            )
        )

    return RetrieveResponse(
        query=request.query,
        results=document_results,
        query_language=query_lang,
        results_translated=results_translated
    )
