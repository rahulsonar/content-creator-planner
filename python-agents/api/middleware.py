"""
Authentication Middleware
Verifies requests from Next.js service
"""
from fastapi import Header, HTTPException
from config.settings import settings
from utils.logger import logger


async def verify_internal_request(
    x_internal_secret: str = Header(None),
    x_user_id: str = Header(None)
) -> str:
    """
    Verify internal service-to-service request
    
    Args:
        x_internal_secret: Shared secret from Next.js
        x_user_id: User ID from Next.js JWT
        
    Returns:
        Validated user ID
        
    Raises:
        HTTPException: If authentication fails
    """
    # Verify secret
    if not x_internal_secret:
        logger.warning("Missing internal secret header")
        raise HTTPException(
            status_code=401,
            detail="Missing authentication headers"
        )
    
    if x_internal_secret != settings.INTERNAL_API_SECRET:
        logger.warning("Invalid internal secret")
        raise HTTPException(
            status_code=401,
            detail="Unauthorized"
        )
    
    # Verify user ID
    if not x_user_id:
        logger.warning("Missing user ID header")
        raise HTTPException(
            status_code=400,
            detail="Missing user ID"
        )
    
    logger.debug(f"Verified internal request for user: {x_user_id}")
    return x_user_id
