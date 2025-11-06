from typing import List, Optional, Literal
from pydantic import BaseModel, Field


class IngestResponse(BaseModel):
    """Response from document ingestion"""
    success: bool
    files_processed: int
    total_chunks_added: int
    details: List[dict] = Field(default_factory=list)
    message: str = ""


class RetrieveRequest(BaseModel):
    """Request to retrieve similar documents"""
    query: str = Field(..., min_length=1, description="Search query text")
    top_k: int = Field(default=3, ge=1, le=10, description="Number of results to return")
    output_language: Optional[Literal["en", "ja"]] = Field(
        None,
        description="Translate results to this language (optional)"
    )


class DocumentResult(BaseModel):
    """Single document result from retrieval"""
    doc_id: str
    text: str = Field(..., description="Document text or snippet")
    score: float = Field(..., description="Similarity score")
    language: str = Field(..., description="Original document language")
    filename: str = Field(..., description="Source filename")


class RetrieveResponse(BaseModel):
    """Response from retrieval endpoint"""
    query: str
    results: List[DocumentResult]
    query_language: str
    results_translated: bool = False


class GenerateRequest(BaseModel):
    """Request to generate response with RAG"""
    query: str = Field(..., min_length=1, description="User query")
    top_k: int = Field(default=3, ge=1, le=10, description="Number of sources to use")
    output_language: Optional[Literal["en", "ja"]] = Field(
        None,
        description="Generate response in this language (optional)"
    )


class SourceReference(BaseModel):
    """Reference to a source document"""
    doc_id: str
    snippet: str
    score: float
    filename: str


class GenerateResponse(BaseModel):
    """Response from generation endpoint"""
    query: str
    generated_text: str
    sources: List[SourceReference]
    query_language: str


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    index_stats: dict


def truncate_text(text: str, max_length: int = 200) -> str:
    """
    Truncate text to max_length, trying to break at sentence boundaries.

    Args:
        text: Text to truncate
        max_length: Maximum character length

    Returns:
        Truncated text with ellipsis if needed
    """
    if len(text) <= max_length:
        return text

    # Try to break at sentence boundary
    truncated = text[:max_length]
    last_period = truncated.rfind('。')  # Japanese period
    if last_period == -1:
        last_period = truncated.rfind('.')

    if last_period > max_length * 0.7:  # Don't truncate too early
        return truncated[:last_period + 1]

    return truncated + "..."


def create_snippet(text: str, max_length: int = 200) -> str:
    """Create a snippet from text for display"""
    return truncate_text(text, max_length)
