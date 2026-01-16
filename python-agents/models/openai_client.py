"""
OpenAI Client Wrapper
Handles communication with OpenAI API
"""
from typing import List, Dict, AsyncGenerator
from openai import AsyncOpenAI
from config.settings import settings
from utils.logger import logger
from utils.token_counter import count_tokens


class OpenAIClient:
    """Wrapper for OpenAI API interactions"""
    
    def __init__(self, model: str = "gpt-3.5-turbo"):
        """
        Initialize OpenAI client
        
        Args:
            model: Model identifier (gpt-3.5-turbo, gpt-4, etc.)
        """
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = model
        logger.info(f"Initialized OpenAI client with model: {model}")
    
    async def generate_completion(
        self,
        messages: List[Dict[str, str]],
        #temperature: float = 0.7,
        #max_tokens: int = 1000,
        tools: List[Dict] = None,
        **kwargs
    ):
        """
        Generate a completion (non-streaming)
        
        Args:
            messages: Conversation messages
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate
            tools: Optional function definitions for tool calling
            **kwargs: Additional OpenAI parameters
            
        Returns:
            Generated text or full response if tools are used
        """
        try:
            logger.debug(f"Generating completion with {len(messages)} messages")
            
            params = {
                "model": self.model,
                "messages": messages,
                #"temperature": temperature,
                #"max_tokens": max_tokens,
                **kwargs
            }
            
            if tools:
                params["tools"] = tools
                params["tool_choice"] = "auto"
            
            response = await self.client.chat.completions.create(**params)
            
            tokens_used = response.usage.total_tokens
            logger.info(f"Completion generated: {tokens_used} tokens")
            
            # If tools were used, return full response for processing
            if tools:
                return response
            
            content = response.choices[0].message.content
            return content
            
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise
    
    async def stream_completion(
        self,
        messages: List[Dict[str, str]],
        #temperature: float = 0.7,
        #max_tokens: int = 1000,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """
        Stream completion tokens in real-time
        
        Args:
            messages: Conversation messages
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional OpenAI parameters
            
        Yields:
            Generated tokens
        """
        try:
            logger.debug(f"Starting streaming completion with {len(messages)} messages")
            
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                #temperature=temperature,
                #max_tokens=max_tokens,
                stream=True,
                **kwargs
            )
            
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
            
            logger.info("Streaming completion finished")
            
        except Exception as e:
            logger.error(f"OpenAI streaming error: {e}")
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
