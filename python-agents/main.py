"""
FastAPI Application Entry Point
Content Creator Agent Service
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import router
from config.settings import settings
from utils.logger import logger

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events"""
    # Startup
    logger.info("Starting Content Creator Agent Service")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    
    # Clean up orphaned agent logs from previous runs
    try:
        from utils.cleanup_orphaned_agents import orphaned_cleaner
        logger.info("Cleaning up orphaned agent logs from previous runs...")
        cleaned_count = await orphaned_cleaner.cleanup_orphaned_logs(hours_threshold=1)
        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} orphaned agent logs")
        else:
            logger.info("No orphaned agent logs found")
    except Exception as e:
        logger.error(f"Failed to clean up orphaned agent logs on startup: {e}")
    
    yield
    # Shutdown
    logger.info("Shutting down Content Creator Agent Service")

app = FastAPI(
    title="Content Creator Agent Service",
    version="1.0.0",
    description="AI Agent service for content creator planning and onboarding",
    docs_url="/docs" if settings.ENVIRONMENT == "development" else None,
    lifespan=lifespan,
)

# CORS middleware for Next.js communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router, prefix="/api")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    logger.info("Health check requested")
    return {
        "status": "healthy",
        "service": "python-agent",
        "version": "1.0.0"
    }
