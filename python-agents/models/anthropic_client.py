"""
Anthropic Client Wrapper
Handles communication with Anthropic Claude API
"""
import json
from typing import List, Dict, Any, AsyncGenerator, Optional
from anthropic import AsyncAnthropic
from config.settings import settings
from utils.logger import logger


# Retries classifier refusals on the model Anthropic recommends for the category
REFUSAL_FALLBACK_BETA = "server-side-fallback-2026-07-01"

# OpenAI-style kwargs that current Claude models reject (sampling params 400)
UNSUPPORTED_KWARGS = ("temperature", "top_p", "top_k", "response_format", "tool_choice")

# Key on an OpenAI-format assistant message holding the original Claude content
# blocks, so thinking blocks are passed back unchanged in tool-use loops
RAW_CONTENT_KEY = "_anthropic_content"


class AnthropicRefusalError(Exception):
    """Raised when Claude declines a request (stop_reason == "refusal")."""


class AnthropicClient:
    """Wrapper for Anthropic Claude API interactions"""

    def __init__(self, model: str = "", metadata: Optional[Dict[str, str]] = None):
        """
        Initialize Anthropic client

        Args:
            model: Model identifier (claude-opus-5-5, claude-sonnet-5-5, etc.);
                   empty uses ANTHROPIC_DEFAULT_MODEL
            metadata: Optional metadata dict to be sent with each API call
        """
        self.client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = model or settings.ANTHROPIC_DEFAULT_MODEL
        self.client_type = 'anthropic'
        self.metadata = metadata or {}
        logger.info(f"Initialized Anthropic client with model: {self.model}, metadata: {list(self.metadata.keys())}")

    @staticmethod
    def raw_content(response: Any) -> List[Dict[str, Any]]:
        """Serialize a response's content blocks for RAW_CONTENT_KEY."""
        return [block.model_dump(exclude_none=True) for block in response.content]

    def _convert_messages(self, messages: List[Dict[str, Any]]) -> tuple[Optional[str], List[Dict[str, Any]]]:
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
                # Replay Claude's own blocks verbatim (keeps thinking blocks intact)
                if msg.get(RAW_CONTENT_KEY):
                    anthropic_messages.append({"role": "assistant", "content": msg[RAW_CONTENT_KEY]})
                    continue

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
                tool_result = {
                    "type": "tool_result",
                    "tool_use_id": msg.get("tool_call_id"),
                    "content": msg.get("content", "")
                }
                # Results for parallel tool calls must share one user message
                previous = anthropic_messages[-1] if anthropic_messages else None
                if (
                    previous
                    and previous["role"] == "user"
                    and isinstance(previous["content"], list)
                    and all(b.get("type") == "tool_result" for b in previous["content"])
                ):
                    previous["content"].append(tool_result)
                else:
                    anthropic_messages.append({"role": "user", "content": [tool_result]})
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
                anthropic_tool = {
                    "type": "custom",
                    "name": func["name"],
                    "description": func.get("description", ""),
                    "input_schema": func.get("parameters", {})
                }
                # OpenAI strict mode maps to Claude strict tool use
                if func.get("strict"):
                    anthropic_tool["strict"] = True
                anthropic_tools.append(anthropic_tool)

        return anthropic_tools

    @staticmethod
    def _pop_max_tokens(kwargs: Dict) -> int:
        """
        Resolve the output token limit from kwargs.
        Anthropic requires `max_tokens`; accept OpenAI-style `max_completion_tokens` too.
        """
        max_completion_tokens = kwargs.pop("max_completion_tokens", None)
        max_tokens = kwargs.pop("max_tokens", None)
        return max_tokens or max_completion_tokens or settings.ANTHROPIC_MAX_TOKENS

    def _build_params(self, messages: List[Dict[str, Any]], kwargs: Dict) -> Dict[str, Any]:
        """Request params shared by completion and streaming calls."""
        for key in UNSUPPORTED_KWARGS:
            if kwargs.pop(key, None) is not None:
                logger.debug(f"Dropping unsupported Anthropic param: {key}")

        system_message, anthropic_messages = self._convert_messages(messages)

        params = {
            "model": self.model,
            "messages": anthropic_messages,
            "max_tokens": self._pop_max_tokens(kwargs),
            # Thinking is adaptive (always on); effort controls its depth
            "output_config": {"effort": settings.ANTHROPIC_EFFORT},
            **kwargs
        }

        if system_message:
            params["system"] = system_message

        # Add metadata if available (Anthropic only accepts user_id in metadata,
        # and only as a string - callers may pass an integer ID)
        if self.metadata and self.metadata.get("user_id") is not None:
            params["metadata"] = {"user_id": str(self.metadata["user_id"])}

        if settings.ANTHROPIC_REFUSAL_FALLBACK:
            params["betas"] = [REFUSAL_FALLBACK_BETA]
            params["extra_body"] = {"fallbacks": "default"}

        return params

    def _messages_api(self):
        """Beta namespace is needed for the refusal fallback header."""
        if settings.ANTHROPIC_REFUSAL_FALLBACK:
            return self.client.beta.messages
        return self.client.messages

    @staticmethod
    def _check_stop_reason(response: Any) -> None:
        """Fail loudly instead of returning partial or declined output."""
        if response.stop_reason == "refusal":
            details = getattr(response, "stop_details", None)
            category = getattr(details, "category", None) if details else None
            raise AnthropicRefusalError(f"Claude declined the request (category: {category})")

        if response.stop_reason == "max_tokens" and any(
            block.type == "tool_use" for block in response.content
        ):
            raise ValueError(
                "Claude hit max_tokens while writing a tool call; "
                "raise ANTHROPIC_MAX_TOKENS or lower ANTHROPIC_EFFORT"
            )

    async def generate_completion(
        self,
        messages: List[Dict[str, Any]],
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

            params = self._build_params(messages, kwargs)
            anthropic_tools = self._convert_tools(tools)
            if anthropic_tools:
                params["tools"] = anthropic_tools

            response = await self._messages_api().create(**params)
            self._check_stop_reason(response)

            tokens_used = response.usage.input_tokens + response.usage.output_tokens
            logger.info(f"Completion generated: {tokens_used} tokens (input: {response.usage.input_tokens}, output: {response.usage.output_tokens})")

            # If tools were used, return full response for processing
            if anthropic_tools and response.stop_reason == "tool_use":
                return response

            # Extract text content (thinking blocks are skipped)
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
        messages: List[Dict[str, Any]],
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

            params = self._build_params(messages, kwargs)

            async with self._messages_api().stream(**params) as stream:
                async for text in stream.text_stream:
                    yield text
                final_message = await stream.get_final_message()

            self._check_stop_reason(final_message)
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
        # Rough estimate: 1 token ~= 4 characters
        return len(text) // 4
