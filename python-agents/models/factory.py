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
        model: Model identifier (gpt-4, claude-opus-5-5, etc.)
        metadata: Optional metadata for tracking/logging
        
    Returns:
        Initialized OpenAI or Anthropic client
        
    Examples:
        >>> client = create_model_client("gpt-4")
        >>> client = create_model_client("claude-opus-5-5")
        >>> client = create_model_client("claude-sonnet-5-5")
    """
    # Determine provider based on model name
    if model.startswith("claude-"):
        logger.info(f"Creating Anthropic client for model: {model}")
        return AnthropicClient(model=model, metadata=metadata)
    else:
        logger.info(f"Creating OpenAI client for model: {model}")
        return OpenAIClient(model=model, metadata=metadata)

