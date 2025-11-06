import logging
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.models.schemas import HealthResponse
from app.storage.faiss_index import get_index_manager
from app.api import ingest, retrieve, generate

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events"""
    # Startup
    logger.info("Starting Healthcare RAG Assistant...")
    try:
        # Initialize index manager (lazy loads models)
        index_manager = get_index_manager()
        logger.info(f"Index initialized with {index_manager.get_stats()['total_documents']} documents")
    except Exception as e:
        logger.error(f"Failed to initialize: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down...")
    try:
        index_manager = get_index_manager()
        index_manager.persist()
        logger.info("Index persisted successfully")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


# Create FastAPI app
app = FastAPI(
    title="Healthcare RAG Assistant",
    description="Bilingual RAG-powered medical knowledge retrieval system",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint (no auth required)
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Check API health and index statistics"""
    try:
        index_manager = get_index_manager()
        stats = index_manager.get_stats()
        return HealthResponse(
            status="healthy",
            index_stats=stats
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthResponse(
            status="unhealthy",
            index_stats={"error": str(e)}
        )


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "name": "Healthcare RAG Assistant API",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
            "ingest": "/ingest (POST)",
            "retrieve": "/retrieve (POST)",
            "generate": "/generate (POST)"
        },
        "note": "All endpoints except /health and / require X-API-Key header"
    }


# Include routers
app.include_router(ingest.router, tags=["ingestion"])
app.include_router(retrieve.router, tags=["retrieval"])
app.include_router(generate.router, tags=["generation"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=False,  # Disable in production
        log_level=settings.log_level.lower()
    )
