"""
Logging Configuration
Centralized logging setup
"""
import logging
import sys
from config.settings import settings


# Create logger
logger = logging.getLogger("agent_service")

# Set level based on environment
log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
logger.setLevel(log_level)

# Create console handler
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(log_level)

# Create formatter
formatter = logging.Formatter(
    fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
handler.setFormatter(formatter)

# Add handler to logger
logger.addHandler(handler)

# Prevent duplicate logs
logger.propagate = False


def get_logger(name: str = None) -> logging.Logger:
    """
    Get a logger instance
    
    Args:
        name: Optional logger name (defaults to agent_service)
        
    Returns:
        Logger instance
    """
    if name:
        return logging.getLogger(f"agent_service.{name}")
    return logger
