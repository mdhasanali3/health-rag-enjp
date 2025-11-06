import logging
from typing import List, Dict
from fastapi import APIRouter, Depends
from app.core.auth import verify_api_key
from app.models.schemas import (
    GenerateRequest,
    GenerateResponse,
    SourceReference,
    create_snippet
)
from app.storage.embeddings import get_embedding_model
from app.storage.faiss_index import get_index_manager
from app.utils.langdetect import detect_language
from app.utils.translation import translate

logger = logging.getLogger(__name__)
router = APIRouter()


def generate_mock_response(
    query: str,
    sources: List[Dict],
    language: str
) -> str:
    """
    Generate a mock clinical assistant response.

    This simulates an LLM response by creating a structured answer
    based on retrieved sources. In production, this would call
    an actual LLM with the context.

    Args:
        query: User's question
        sources: Retrieved source documents
        language: Target language for response

    Returns:
        Generated response text
    """
    if language == "ja":
        # Japanese response template
        intro = f"ご質問「{query}」について、医療ガイドラインを基に回答いたします。\n\n"

        body_parts = []
        for idx, source in enumerate(sources, 1):
            snippet = create_snippet(source["text"], max_length=150)
            score_percent = int(source["score"] * 100)
            body_parts.append(
                f"{idx}. {snippet}\n   (関連度: {score_percent}%、出典: {source['filename']})"
            )

        body = "【関連情報】\n" + "\n\n".join(body_parts)

        conclusion = "\n\n【推奨事項】\n上記の情報を総合的に考慮し、個別の症例に応じた適切な判断が必要です。詳細については担当医師にご相談ください。"

        references = "\n\n【参考文献】\n" + "\n".join(
            f"- {source['doc_id']} ({source['filename']})"
            for source in sources
        )

    else:
        # English response template
        intro = f"Based on the available medical guidelines, here's what I found regarding your query: \"{query}\"\n\n"

        body_parts = []
        for idx, source in enumerate(sources, 1):
            snippet = create_snippet(source["text"], max_length=150)
            score_percent = int(source["score"] * 100)
            body_parts.append(
                f"{idx}. {snippet}\n   (Relevance: {score_percent}%, Source: {source['filename']})"
            )

        body = "**Key Information:**\n" + "\n\n".join(body_parts)

        conclusion = "\n\n**Clinical Recommendation:**\nThe above information should be considered in conjunction with individual patient factors. Please consult with the treating physician for specific clinical guidance."

        references = "\n\n**References:**\n" + "\n".join(
            f"- {source['doc_id']} ({source['filename']})"
            for source in sources
        )

    return intro + body + conclusion + references


@router.post("/generate", response_model=GenerateResponse)
async def generate_response(
    request: GenerateRequest,
    _: str = Depends(verify_api_key)
):
    """
    Generate a RAG-powered response to a query.

    Retrieves relevant sources and creates a structured response
    using a mock LLM (template-based). Supports bilingual output.
    """
    # Detect query language
    query_lang = detect_language(request.query)
    logger.info(f"Generating response for query in {query_lang}")

    # Get embedding for query
    embedding_model = get_embedding_model()
    query_embedding = embedding_model.embed_single(request.query)

    # Search index
    index_manager = get_index_manager()
    search_results = index_manager.search(query_embedding, top_k=request.top_k)

    if not search_results:
        # No sources found
        no_results_msg = (
            "申し訳ございませんが、関連する情報が見つかりませんでした。"
            if query_lang == "ja"
            else "I'm sorry, but I couldn't find any relevant information for your query."
        )

        return GenerateResponse(
            query=request.query,
            generated_text=no_results_msg,
            sources=[],
            query_language=query_lang
        )

    # Determine output language
    output_lang = request.output_language or query_lang

    # Generate response using mock LLM
    generated_text = generate_mock_response(
        query=request.query,
        sources=search_results,
        language=output_lang
    )

    # Prepare source references
    source_refs = []
    for result in search_results:
        snippet = create_snippet(result["text"], max_length=200)

        # Translate snippet if needed
        if output_lang != result["language"]:
            snippet = translate(snippet, result["language"], output_lang)

        source_refs.append(
            SourceReference(
                doc_id=result["doc_id"],
                snippet=snippet,
                score=result["score"],
                filename=result["filename"]
            )
        )

    return GenerateResponse(
        query=request.query,
        generated_text=generated_text,
        sources=source_refs,
        query_language=query_lang
    )
