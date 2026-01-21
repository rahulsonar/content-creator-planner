"""
Model Factory
Creates appropriate AI client based on model name
"""
from typing import Optional, Dict, Union
from models.openai_client import OpenAIClient
from models.anthropic_client import AnthropicClient
from utils.logger import logger


def create_model_client(
    model: str,
    metadata: Optional[Dict[str, str]] = None
) -> Union[OpenAIClient, AnthropicClient]:
    """
    Create appropriate AI client based on model name
    
    Args:
        model: Model identifier (gpt-4, claude-sonnet-4.5, etc.)
        metadata: Optional metadata for tracking/logging
        
    Returns:
        Initialized OpenAI or Anthropic client
        
    Examples:
        >>> client = create_model_client("gpt-4")
        >>> client = create_model_client("claude-sonnet-4.5")
        >>> client = create_model_client("claude-opus-4")
    """
    # Determine provider based on model name
    if model.startswith("claude-"):
        logger.info(f"Creating Anthropic client for model: {model}")
        return AnthropicClient(model=model, metadata=metadata)
    else:
        logger.info(f"Creating OpenAI client for model: {model}")
        return OpenAIClient(model=model, metadata=metadata)


# Model aliases for convenience
MODEL_ALIASES = {
    # OpenAI models
    "gpt-3.5": "gpt-3.5-turbo",
    "gpt-4": "gpt-4",
    "gpt-5": "gpt-5",
    
    # Anthropic models
    "claude-sonnet": "claude-sonnet-4.5",
    "claude-opus": "claude-opus-4",
    "claude": "claude-sonnet-4.5",  # Default to Sonnet 4.5
}


def get_model_name(alias: str) -> str:
    """
    Resolve model alias to full model name
    
    Args:
        alias: Model alias or full name
        
    Returns:
        Full model identifier
    """
    return MODEL_ALIASES.get(alias, alias)
