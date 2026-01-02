"""
Main FastAPI application.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging
import asyncio

from app.core.config import get_settings
from app.core.exceptions import AppException
from app.core.error_handlers import (
    app_exception_handler,
    http_exception_handler,
    validation_exception_handler,
    general_exception_handler,
)
from app.middleware.logging_middleware import LoggingMiddleware
from app.api.v1.router import api_router
from app.services.task_service import cleanup_expired_tasks_periodically, get_task_executor
from app.core.database import init_db, close_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)

# Get settings
settings = get_settings()


def create_application() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application instance
    """
    # Initialize FastAPI app
    app = FastAPI(
        title=settings.PROJECT_NAME,
        description=settings.DESCRIPTION,
        version=settings.VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add custom middleware
    app.add_middleware(LoggingMiddleware)

    # Register exception handlers
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)

    # Include routers
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    # Lifecycle management
    cleanup_task = None
    startup_called = False

    @app.on_event("startup")
    async def startup_event():
        """Start background tasks on application startup."""
        nonlocal cleanup_task, startup_called

        # Prevent multiple cleanup tasks from being created
        if startup_called:
            logger.warning("Startup event called multiple times, skipping duplicate initialization")
            return

        startup_called = True

        # Initialize database
        logger.info("Initializing database")
        await init_db()

        logger.info("Starting background task cleanup")
        cleanup_task = asyncio.create_task(cleanup_expired_tasks_periodically())

    @app.on_event("shutdown")
    async def shutdown_event():
        """Cleanup on application shutdown."""
        nonlocal cleanup_task
        logger.info("Shutting down application")

        # Cancel cleanup task
        if cleanup_task:
            cleanup_task.cancel()
            try:
                await cleanup_task
            except asyncio.CancelledError:
                logger.info("Cleanup task cancelled")

        # Shutdown task executor
        executor = get_task_executor()
        executor.shutdown()
        logger.info("Task executor shutdown complete")

        # Close database connections
        await close_db()
        logger.info("Database connections closed")

    # Root endpoint
    @app.get(
        "/",
        tags=["Root"],
        summary="Root endpoint",
        description="Returns basic API information",
    )
    async def root():
        """Root endpoint with API information."""
        return {
            "name": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "description": settings.DESCRIPTION,
            "docs": "/docs",
            "redoc": "/redoc",
        }

    # Health check endpoint
    @app.get(
        "/health",
        tags=["Health"],
        summary="Application health check",
        description="Check if the application is running",
    )
    async def health_check():
        """Application-level health check."""
        return {
            "status": "healthy",
            "service": settings.PROJECT_NAME,
            "version": settings.VERSION,
        }

    logger.info(f"Application '{settings.PROJECT_NAME}' initialized successfully")

    return app


# Create the application instance
app = create_application()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info",
    )
