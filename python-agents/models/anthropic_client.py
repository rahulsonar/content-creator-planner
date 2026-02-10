"""
Anthropic Client Wrapper
Handles communication with Anthropic Claude API
"""
from typing import List, Dict, AsyncGenerator, Optional
from anthropic import AsyncAnthropic
from config.settings import settings
from utils.logger import logger


class AnthropicClient:
    """Wrapper for Anthropic Claude API interactions"""
    
    def __init__(self, model: str = "claude-sonnet-4.5", metadata: Optional[Dict[str, str]] = None):
        """
        Initialize Anthropic client
        
        Args:
            model: Model identifier (claude-sonnet-4.5, claude-opus-4, etc.)
            metadata: Optional metadata dict to be sent with each API call
        """
        self.client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = model
        self.client_type = 'anthropic'
        self.metadata = metadata or {}
        logger.info(f"Initialized Anthropic client with model: {model}, metadata: {list(self.metadata.keys())}")
    
    def _convert_messages(self, messages: List[Dict[str, str]]) -> tuple[Optional[str], List[Dict[str, str]]]:
        """
        Convert OpenAI-style messages to Anthropic format
        Extracts system message and converts remaining messages
        Handles tool calls and tool results
        
        Args:
            messages: OpenAI-style messages with role and content
            
        Returns:
            Tuple of (system_message, anthropic_messages)
        """
        system_message = None
        anthropic_messages = []
        
        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            elif msg["role"] == "assistant":
                # Handle assistant messages with or without tool calls
                content_blocks = []
                
                # Add text content if present
                if msg.get("content"):
                    content_blocks.append({
                        "type": "text",
                        "text": msg["content"]
                    })
                
                # Convert OpenAI tool_calls to Anthropic tool_use blocks
                if msg.get("tool_calls"):
                    import json
                    for tc in msg["tool_calls"]:
                        content_blocks.append({
                            "type": "tool_use",
                            "id": tc["id"],
                            "name": tc["function"]["name"],
                            "input": json.loads(tc["function"]["arguments"])
                        })
                
                anthropic_messages.append({
                    "role": "assistant",
                    "content": content_blocks if content_blocks else msg.get("content", "")
                })
            elif msg["role"] == "tool":
                # Convert tool results to Anthropic format (user message with tool_result)
                anthropic_messages.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": msg.get("tool_call_id"),
                        "content": msg.get("content", "")
                    }]
                })
            else:
                # Regular user messages
                anthropic_messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
        
        return system_message, anthropic_messages
    
    def _convert_tools(self, tools: Optional[List[Dict]]) -> Optional[List[Dict]]:
        """
        Convert OpenAI-style tools to Anthropic format
        
        Args:
            tools: OpenAI function definitions
            
        Returns:
            Anthropic-formatted tools
        """
        if not tools:
            return None
        
        anthropic_tools = []
        for tool in tools:
            if tool.get("type") == "function":
                func = tool["function"]
                anthropic_tools.append({
                    "type": "custom",
                    "name": func["name"],
                    "description": func.get("description", ""),
                    "input_schema": func.get("parameters", {})
                })
        
        return anthropic_tools
    
    async def generate_completion(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict] = None,
        **kwargs
    ):
        """
        Generate a completion (non-streaming)
        
        Args:
            messages: Conversation messages
            tools: Optional function definitions for tool calling
            **kwargs: Additional Anthropic parameters
            
        Returns:
            Generated text or full response if tools are used
        """
        try:
            logger.debug(f"Generating completion with {len(messages)} messages")
            
            # Convert messages and tools to Anthropic format
            system_message, anthropic_messages = self._convert_messages(messages)
            anthropic_tools = self._convert_tools(tools)
            
            params = {
                "model": self.model,
                "messages": anthropic_messages,
                "max_completion_tokens": kwargs.pop("max_completion_tokens", 4096),
                **kwargs
            }
            
            if system_message:
                params["system"] = system_message
            
            if anthropic_tools:
                params["tools"] = anthropic_tools
            
            # Add metadata if available (Anthropic only accepts user_id in metadata)
            if self.metadata and "user_id" in self.metadata:
                params["metadata"] = {"user_id": self.metadata["user_id"]}
            
            response = await self.client.messages.create(**params)
            
            tokens_used = response.usage.input_tokens + response.usage.output_tokens
            logger.info(f"Completion generated: {tokens_used} tokens (input: {response.usage.input_tokens}, output: {response.usage.output_tokens})")
            
            # If tools were used, return full response for processing
            if anthropic_tools and response.stop_reason == "tool_use":
                return response
            
            # Extract text content
            content = ""
            for block in response.content:
                if block.type == "text":
                    content += block.text
            
            return content
            
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            raise
    
    async def stream_completion(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """
        Stream completion tokens in real-time
        
        Args:
            messages: Conversation messages
            **kwargs: Additional Anthropic parameters
            
        Yields:
            Text chunks as they are generated
        """
        try:
            logger.debug(f"Starting stream with {len(messages)} messages")
            
            # Convert messages to Anthropic format
            system_message, anthropic_messages = self._convert_messages(messages)
            
            params = {
                "model": self.model,
                "messages": anthropic_messages,
                "max_completion_tokens": kwargs.pop("max_completion_tokens", 4096),
                "stream": True,
                **kwargs
            }
            
            if system_message:
                params["system"] = system_message
            
            # Add metadata if available (Anthropic only accepts user_id in metadata)
            if self.metadata and "user_id" in self.metadata:
                params["metadata"] = {"user_id": self.metadata["user_id"]}
            
            async with self.client.messages.stream(**params) as stream:
                async for text in stream.text_stream:
                    yield text
            
            # Log final usage
            final_message = await stream.get_final_message()
            tokens_used = final_message.usage.input_tokens + final_message.usage.output_tokens
            logger.info(f"Stream completed: {tokens_used} tokens")
            
        except Exception as e:
            logger.error(f"Anthropic streaming error: {e}")
            raise
    
    async def count_tokens(self, text: str) -> int:
        """
        Estimate token count for text
        
        Args:
            text: Text to count tokens for
            
        Returns:
            Estimated token count
        """
        # Anthropic uses a similar tokenization to OpenAI
        # Rough estimate: 1 token ~= 4 characters
        return len(text) // 4
