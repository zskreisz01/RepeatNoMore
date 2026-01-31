"""Main FastAPI application for RepeatNoMore."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.api.routes import router as api_router
from app.api.workflow_routes import router as workflow_router
from app.utils.logging import setup_logging, get_logger

# Setup logging
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.

    Handles startup and shutdown events.
    """
    # Startup
    logger.info("starting_repeatnomore")
    settings = get_settings()
    logger.info(
        "application_configured",
        environment=settings.environment,
        log_level=settings.log_level
    )

    # Initialize event handlers (includes index handler for auto-indexing)
    from app.events.setup import setup_event_handlers
    from app.events.handlers import get_index_handler

    setup_event_handlers()
    logger.info("event_handlers_initialized")

    # Ensure vector store is initialized (triggers initial indexing if empty)
    index_handler = get_index_handler()
    await index_handler.ensure_initialized()
    logger.info("vector_store_initialized")

    yield

    # Shutdown
    logger.info("shutting_down_repeatnomore")


# Create FastAPI application
app = FastAPI(
    title="RepeatNoMore API",
    description="AI-powered framework assistant with RAG and LLM capabilities",
    version="0.1.0",
    lifespan=lifespan
)

# Configure CORS
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(
    api_router,
    prefix=settings.api_prefix,
    tags=["api"]
)

# Include workflow routes
app.include_router(
    workflow_router,
    prefix=settings.api_prefix,
    tags=["workflow"]
)

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "RepeatNoMore API",
        "version": "0.1.0",
        "status": "running",
        "docs": "/docs",
        "health": f"{settings.api_prefix}/health"
    }


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Handle uncaught exceptions."""
    logger.error(
        "unhandled_exception",
        error=str(exc),
        error_type=type(exc).__name__,
        path=request.url.path
    )

    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred",
            "detail": str(exc) if settings.is_development else None
        }
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8080,
        reload=settings.is_development,
        log_level=settings.log_level.lower()
    )
