import logging
from typing import List
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from app.core.auth import verify_api_key
from app.models.schemas import IngestResponse
from app.storage.embeddings import get_embedding_model
from app.storage.faiss_index import get_index_manager
from app.utils.langdetect import detect_language
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


def chunk_text(text: str, max_size: int = 1000, overlap: int = 200) -> List[str]:
    """
    Split text into overlapping chunks for better context preservation.

    Args:
        text: Input text
        max_size: Max characters per chunk
        overlap: Overlap between chunks

    Returns:
        List of text chunks
    """
    if len(text) <= max_size:
        return [text]

    chunks = []
    start = 0

    while start < len(text):
        end = start + max_size

        # Try to break at sentence boundary
        if end < len(text):
            # Look for sentence endings
            for delimiter in ['。', '.', '！', '!', '？', '?', '\n\n']:
                last_delim = text[start:end].rfind(delimiter)
                if last_delim > max_size * 0.6:  # Don't break too early
                    end = start + last_delim + 1
                    break

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        # Move start position with overlap
        start = end - overlap if end < len(text) else end

    return chunks


@router.post("/ingest", response_model=IngestResponse)
async def ingest_documents(
    files: List[UploadFile] = File(..., description="Text files to ingest (.txt)"),
    _: str = Depends(verify_api_key)
):
    """
    Ingest documents into the vector database.

    Accepts multiple .txt files, detects language, chunks text,
    generates embeddings, and stores in FAISS index.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    embedding_model = get_embedding_model()
    index_manager = get_index_manager()

    total_chunks = 0
    details = []
    processed_count = 0

    for file in files:
        try:
            # Validate file type
            if not file.filename.endswith('.txt'):
                details.append({
                    "filename": file.filename,
                    "status": "skipped",
                    "reason": "Only .txt files supported"
                })
                continue

            # Read file content
            content = await file.read()
            text = content.decode('utf-8', errors='ignore')

            if not text.strip():
                details.append({
                    "filename": file.filename,
                    "status": "skipped",
                    "reason": "Empty file"
                })
                continue

            # Detect language
            language = detect_language(text)

            # Chunk the text
            chunks = chunk_text(
                text,
                max_size=settings.max_chunk_size,
                overlap=settings.chunk_overlap
            )

            # Generate embeddings
            embeddings = embedding_model.embed_texts(chunks)

            # Prepare metadata
            languages = [language] * len(chunks)
            filenames = [file.filename] * len(chunks)
            chunk_indices = list(range(len(chunks)))

            # Add to index
            doc_ids = index_manager.add_documents(
                texts=chunks,
                embeddings=embeddings,
                languages=languages,
                filenames=filenames,
                chunk_indices=chunk_indices
            )

            total_chunks += len(chunks)
            processed_count += 1

            details.append({
                "filename": file.filename,
                "status": "success",
                "chunks_created": len(chunks),
                "language": language,
                "doc_ids": doc_ids[:3]  # Show first 3 IDs
            })

            logger.info(f"Ingested {file.filename}: {len(chunks)} chunks, language: {language}")

        except Exception as e:
            logger.error(f"Failed to process {file.filename}: {e}")
            details.append({
                "filename": file.filename,
                "status": "error",
                "reason": str(e)
            })

    # Persist index after batch ingestion
    try:
        index_manager.persist()
    except Exception as e:
        logger.error(f"Failed to persist index: {e}")

    return IngestResponse(
        success=processed_count > 0,
        files_processed=processed_count,
        total_chunks_added=total_chunks,
        details=details,
        message=f"Successfully processed {processed_count}/{len(files)} files"
    )
