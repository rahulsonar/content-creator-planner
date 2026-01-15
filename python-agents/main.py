"""
FastAPI Application Entry Point
Content Creator Agent Service
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import router
from api.websocket import websocket_endpoint
from config.settings import settings
from utils.logger import logger

app = FastAPI(
    title="Content Creator Agent Service",
    version="1.0.0",
    description="AI Agent service for content creator planning and onboarding",
    docs_url="/docs" if settings.ENVIRONMENT == "development" else None,
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

# WebSocket endpoint
app.add_websocket_route("/ws", websocket_endpoint)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    logger.info("Health check requested")
    return {
        "status": "healthy",
        "service": "python-agent",
        "version": "1.0.0"
    }

@app.on_event("startup")
async def startup_event():
    """Execute on application startup"""
    logger.info("Starting Content Creator Agent Service")
    logger.info(f"Environment: {settings.ENVIRONMENT}")

@app.on_event("shutdown")
async def shutdown_event():
    """Execute on application shutdown"""
    logger.info("Shutting down Content Creator Agent Service")
