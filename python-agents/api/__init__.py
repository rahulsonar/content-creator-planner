"""API module initialization"""
from .routes import router
from .middleware import verify_internal_request

__all__ = [
    "router",
    "verify_internal_request",
]
