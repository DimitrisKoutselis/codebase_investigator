"""
FastAPI Application Entry Point.

This is the main entry point for the Codebase Investigator API.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.infrastructure.config.settings import get_settings
from src.presentation.api.routers import ingest_router, chat_router, session_router
from src.presentation.websocket import websocket_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    # Startup
    settings = get_settings()
    print(f"Starting Codebase Investigator on {settings.host}:{settings.port}")
    print(f"Debug mode: {settings.debug}")

    yield

    # Shutdown
    print("Shutting down Codebase Investigator")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="Codebase Investigator",
        description="A RAG chatbot for GitHub repositories",
        version="1.0.0",
        lifespan=lifespan,
        debug=settings.debug,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(ingest_router)
    app.include_router(chat_router)
    app.include_router(session_router)
    app.include_router(websocket_router)

    @app.get("/health", tags=["health"])
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy"}

    @app.get("/", tags=["root"])
    async def root():
        """Root endpoint with API information."""
        return {
            "name": "Codebase Investigator",
            "version": "1.0.0",
            "docs": "/docs",
            "health": "/health",
        }

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "src.presentation.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
