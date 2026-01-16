"""
Anthropic Client Wrapper
Handles communication with Anthropic API (Claude)
"""
from typing import List, Dict, AsyncGenerator
from anthropic import AsyncAnthropic
from config.settings import settings
from utils.logger import logger
from utils.token_counter import count_tokens


class AnthropicClient:
    """Wrapper for Anthropic API interactions"""
    
    def __init__(self, model: str = "claude-sonnet-4-20250514"):
        """
        Initialize Anthropic client
        
        Args:
            model: Model identifier
        """
        self.client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = model
        logger.info(f"Initialized Anthropic client with model: {model}")
    
    async def generate_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs
    ) -> str:
        """
        Generate a completion (non-streaming)
        
        Args:
            messages: Conversation messages
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional Anthropic parameters
            
        Returns:
            Generated text
        """
        try:
            logger.debug(f"Generating completion with {len(messages)} messages")
            
            # Extract system message if present
            system_messages = []
            filtered_messages = []
            for msg in messages:
                if msg["role"] == "system":
                    system_messages.append({
                        "type": "text",
                        "text": msg["content"]
                    })
                else:
                    filtered_messages.append(msg)
            
            # Build kwargs conditionally
            api_kwargs = {
                "model": self.model,
                "messages": filtered_messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                **kwargs
            }
            if system_messages:
                api_kwargs["system"] = system_messages
            
            response = await self.client.messages.create(**api_kwargs)
            
            content = response.content[0].text
            tokens_used = response.usage.input_tokens + response.usage.output_tokens
            
            logger.info(f"Completion generated: {tokens_used} tokens")
            return content
            
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            raise
    
    async def stream_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """
        Stream completion tokens in real-time
        
        Args:
            messages: Conversation messages
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional Anthropic parameters
            
        Yields:
            Generated tokens
        """
        try:
            logger.debug(f"Starting streaming completion with {len(messages)} messages")
            
            # Extract system message if present
            system_messages = []
            filtered_messages = []
            for msg in messages:
                if msg["role"] == "system":
                    system_messages.append({
                        "type": "text",
                        "text": msg["content"]
                    })
                else:
                    filtered_messages.append(msg)
            
            # Build kwargs conditionally
            api_kwargs = {
                "model": self.model,
                "messages": filtered_messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                **kwargs
            }
            if system_messages:
                api_kwargs["system"] = system_messages
            
            async with self.client.messages.stream(**api_kwargs) as stream:
                async for text in stream.text_stream:
                    yield text
            
            logger.info("Streaming completion finished")
            
        except Exception as e:
            logger.error(f"Anthropic streaming error: {e}")
            raise
    
    def set_model(self, model: str):
        """
        Change the model
        
        Args:
            model: New model identifier
        """
        self.model = model
        logger.info(f"Switched to model: {model}")
    
    async def count_message_tokens(self, messages: List[Dict[str, str]]) -> int:
        """
        Count tokens in messages (approximate)
        
        Args:
            messages: List of messages
            
        Returns:
            Approximate token count
        """
        total = 0
        for message in messages:
            total += count_tokens(message.get("content", ""))
        return total
