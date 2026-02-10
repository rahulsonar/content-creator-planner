"""
Authentication Middleware
Verifies requests from Next.js service
"""
from fastapi import Header, HTTPException
from config.settings import settings
from utils.logger import logger


async def verify_internal_request(
    x_internal_secret: str = Header(None),
    x_user_id: str = Header(None),
    x_user_name: str = Header(None)
) -> tuple[int, str | None]:
    """
    Verify internal service-to-service request
    
    Args:
        x_internal_secret: Shared secret from Next.js
        x_user_id: User ID from Next.js JWT (as string from header)
        x_user_name: User name from Next.js JWT (optional)
        
    Returns:
        Tuple of (validated user ID as int, user name)
        
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
    
    # Parse user_id to int (headers are always strings)
    try:
        user_id_int = int(x_user_id)
    except ValueError:
        logger.warning(f"Invalid user ID format: {x_user_id}")
        raise HTTPException(
            status_code=400,
            detail="Invalid user ID format"
        )
    
    logger.debug(f"Verified internal request for user: {user_id_int} ({x_user_name})")
    return user_id_int, x_user_name
