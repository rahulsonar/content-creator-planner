"""
Rate Limiter
Implements rate limiting for API endpoints
"""
from typing import Dict
from datetime import datetime, timedelta
from config.settings import settings
from utils.logger import logger


class RateLimiter:
    """Simple in-memory rate limiter"""
    
    def __init__(self):
        """Initialize rate limiter"""
        self.user_requests: Dict[str, list] = {}
        logger.info("Initialized rate limiter")
    
    def is_rate_limited(
        self,
        user_id: str,
        limit_per_minute: int = None,
        limit_per_day: int = None
    ) -> tuple[bool, str]:
        """
        Check if user is rate limited
        
        Args:
            user_id: User identifier
            limit_per_minute: Requests per minute (optional)
            limit_per_day: Requests per day (optional)
            
        Returns:
            Tuple of (is_limited, reason)
        """
        now = datetime.now()
        
        # Use default limits if not specified
        limit_per_minute = limit_per_minute or settings.RATE_LIMIT_PER_MINUTE
        limit_per_day = limit_per_day or settings.RATE_LIMIT_PER_DAY
        
        # Get user's request history
        if user_id not in self.user_requests:
            self.user_requests[user_id] = []
        
        requests = self.user_requests[user_id]
        
        # Remove old requests
        one_day_ago = now - timedelta(days=1)
        one_minute_ago = now - timedelta(minutes=1)
        
        requests = [r for r in requests if r > one_day_ago]
        self.user_requests[user_id] = requests
        
        # Check daily limit
        if len(requests) >= limit_per_day:
            logger.warning(f"User {user_id} exceeded daily limit")
            return True, f"Daily limit of {limit_per_day} requests exceeded"
        
        # Check per-minute limit
        recent_requests = [r for r in requests if r > one_minute_ago]
        if len(recent_requests) >= limit_per_minute:
            logger.warning(f"User {user_id} exceeded per-minute limit")
            return True, f"Rate limit of {limit_per_minute} requests per minute exceeded"
        
        return False, ""
    
    def record_request(self, user_id: str):
        """
        Record a request for rate limiting
        
        Args:
            user_id: User identifier
        """
        if user_id not in self.user_requests:
            self.user_requests[user_id] = []
        
        self.user_requests[user_id].append(datetime.now())
        logger.debug(f"Recorded request for user: {user_id}")
    
    def get_user_stats(self, user_id: str) -> Dict[str, int]:
        """
        Get user's request statistics
        
        Args:
            user_id: User identifier
            
        Returns:
            Dictionary with request counts
        """
        if user_id not in self.user_requests:
            return {
                "requests_today": 0,
                "requests_last_minute": 0
            }
        
        now = datetime.now()
        requests = self.user_requests[user_id]
        
        one_day_ago = now - timedelta(days=1)
        one_minute_ago = now - timedelta(minutes=1)
        
        requests_today = len([r for r in requests if r > one_day_ago])
        requests_last_minute = len([r for r in requests if r > one_minute_ago])
        
        return {
            "requests_today": requests_today,
            "requests_last_minute": requests_last_minute,
            "daily_limit": settings.RATE_LIMIT_PER_DAY,
            "minute_limit": settings.RATE_LIMIT_PER_MINUTE
        }
    
    def clear_user_limits(self, user_id: str):
        """
        Clear rate limits for a user (admin function)
        
        Args:
            user_id: User identifier
        """
        if user_id in self.user_requests:
            del self.user_requests[user_id]
            logger.info(f"Cleared rate limits for user: {user_id}")
