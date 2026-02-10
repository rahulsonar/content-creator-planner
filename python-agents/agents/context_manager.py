"""
Context Manager Agent
Manages user context history in structured markdown files
"""
from typing import Dict, Any, Optional, List
import asyncio
from datetime import datetime, timezone
import uuid
from agents.base import BaseAgent
from config.prompts import CONTEXT_MANAGER_SYSTEM_PROMPT
from utils.logger import logger
from utils.user_context_manager import (
    read_user_context,
    write_user_context,
    update_user_context,
    list_user_context_files,
    ensure_user_context_dir
)
from storage.agent_call_log import agent_call_logger


class ContextManagerAgent(BaseAgent):
    """Agent for managing user context in structured markdown files"""
    
    def __init__(self, model_client, db_session=None):
        """
        Initialize context manager agent
        
        Args:
            model_client: LLM client (OpenAI)
            db_session: Optional database session for logging
        """
        super().__init__(model_client, "context_manager")
        self.current_user_id = None  # Will be set during process_message
        self.current_user_name = None  # Will be set during process_message
        self.db_session = db_session
        # Track current agent call log
        self._current_agent_call_log_id: Optional[int] = None
        self._tool_calls_log = []  # Track tool calls for logging
        self._tool_results_log = []  # Track tool results for logging
        self._tool_calls_detailed = []  # Track detailed tool execution info

        # Initialize metadata
        self.metadata = {
            "agent_name": "context_manager",
            "conversation_id": None,
            "user_id": None,
            "session_id": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_activity_at": None,
            "total_messages": 0,
            "total_user_messages": 0,
            "tool_calls_count": 0,
            "tools_by_type": {},  # Track count per tool type
            "enable_tools": True,  # Context manager always uses tools
            "model_name": getattr(model_client, 'model', 'unknown'),
            "files_created": 0,
            "files_updated": 0,
            "files_read": 0,
            "agent_version": "1.0.0"
        }

        logger.info(f"ContextManagerAgent initialized: {self.get_metadata_summary()}")

        # Add system prompt to conversation history
        self.conversation_history = [
            {"role": "system", "content": CONTEXT_MANAGER_SYSTEM_PROMPT}
        ]
        
        # Define unified context management tool with action parameter
        self.tools_openai = [
            {
                "type": "function",
                "function": {
                    "name": "manage_context_files",
                    "description": "Manage user context files with a simple file API (list, read, write, append).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "action": {
                                "type": "string",
                                "enum": ["list", "read", "write", "append"],
                                "description": "Context operation:\n- 'list': List all context files\n- 'read': Read a specific file\n- 'write': Overwrite a specific file\n- 'append': Append to a specific file"
                            },
                            "content": {
                                "type": "string",
                                "description": "Content to write or append (required for 'write' and 'append' actions)"
                            },
                            "filename": {
                                "type": "string",
                                "description": "Filename to read/write/append (required for 'read', 'write', and 'append' actions)"
                            }
                        },
                        "required": ["action"]
                    }
                }
            }
        ]

    def update_metadata(self, **kwargs):
        """Update metadata fields and track last activity, also sync with model client"""
        self.metadata.update(kwargs)
        self.metadata["last_activity_at"] = datetime.now(timezone.utc).isoformat()
        
        # Sync metadata with OpenAI client for API logging
        if hasattr(self.model_client, 'update_metadata'):
            client_metadata = {
                "conversation_id": self.metadata.get("conversation_id"),
                "user_id": self.metadata.get("user_id"),
                "session_id": self.metadata.get("session_id"),
                "agent_name": self.metadata.get("agent_name")
            }
            # Remove None values to avoid setting empty headers
            client_metadata = {k: v for k, v in client_metadata.items() if v is not None}
            if client_metadata:
                self.model_client.update_metadata(client_metadata)

    def get_metadata(self) -> Dict[str, Any]:
        """Get current metadata snapshot"""
        return self.metadata.copy()

    def get_metadata_summary(self) -> str:
        """Get formatted metadata summary for logging"""
        m = self.metadata
        return (
            f"agent={m['agent_name']}, conv={m['conversation_id']}, "
            f"user={m['user_id']}, msgs={m['total_messages']}, "
            f"tools={m['tool_calls_count']}, files={m['files_created']+m['files_updated']+m['files_read']}"
        )

    async def process_message(
        self,
        user_message: str,
        user_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Process information from other agents and manage user context files
        
        Args:
            user_message: Information about user from other agents
            user_context: User context including user_id
            
        Returns:
            Confirmation message about context management
        """
        if not user_context or "user_id" not in user_context:
            return "Error: user_id is required to manage context"

        user_id = user_context["user_id"]
        logger.info(f"Context manager processing message for user_id: {user_id}")

        # Update metadata at start of message processing
        self.update_metadata(
            conversation_id=user_context.get('conversation_id'),
            user_id=user_id,
            session_id=user_context.get('session_id')
        )

        # Increment message counters
        self.metadata["total_messages"] += 1
        self.metadata["total_user_messages"] += 1
        
        # Reset tool tracking for this message
        self._tool_calls_log = []
        self._tool_results_log = []
        self._tool_calls_detailed = []

        logger.info(f"Processing message: {self.get_metadata_summary()}")

        # Store user_id and user_name for tool execution
        self.current_user_id = user_id
        self.current_user_name = user_context.get('user_name')  # Store user name for context
        
        # Prepend user's name to system prompt if available and not already added
        if self.current_user_name and len(self.conversation_history) > 0:
            system_prompt = self.conversation_history[0]['content']
            user_name_prefix = f"You are assisting: {self.current_user_name}\n\n"
            
            # Only add if not already present
            if not system_prompt.startswith("You are assisting:"):
                self.conversation_history[0]['content'] = user_name_prefix + system_prompt
                logger.info(f"Prepended user name to system prompt: {self.current_user_name}")
        
        # START AGENT CALL LOGGING
        try:
            self._current_agent_call_log_id = await agent_call_logger.start_agent_call(
                user_id=user_id,
                agent_name="context_manager",
                model_name=self.metadata.get("model_name", "unknown"),
                message_id=user_context.get('message_id') or agent_call_logger.generate_message_id(),
                conversation_id=user_context.get('conversation_id'),
                session_id=user_context.get('session_id'),
                agent_type="context_management",
                agent_version=self.metadata.get("agent_version", "1.0.0"),
                input_message=user_message,
                tools_enabled=True,
                metadata={
                    "conversation_history_length": len(self.conversation_history),
                    "has_context": bool(user_context)
                },
                tags=["context_manager", "context_management"]
            )
            logger.info(f"Started agent call log: {self._current_agent_call_log_id}")
        except Exception as e:
            logger.error(f"Failed to start agent call logging: {e}")
        
        # Add user message with user_id context to history
        enhanced_message = f"[User ID: {user_id}]\n\n{user_message}"
        self.add_to_history("user", enhanced_message)
        
        try:
            # Check if model supports tools
            if hasattr(self.model_client, 'supports_tools') and self.model_client.supports_tools():
                # Use tool-based approach
                response = await self._process_with_tools(user_id)
            else:
                # Use standard text-based approach
                response = await self._process_without_tools(user_id)
            
            # Add assistant response to history
            self.add_to_history("assistant", response)
            
            # COMPLETE AGENT CALL LOGGING
            try:
                await agent_call_logger.complete_agent_call(
                    log_id=self._current_agent_call_log_id,
                    output_message=response,
                    tool_calls=self._tool_calls_log if self._tool_calls_log else None,
                    tool_results=self._tool_results_log if self._tool_results_log else None,
                    tool_calls_detailed=self._tool_calls_detailed if self._tool_calls_detailed else None,
                    metadata={
                        "final_history_length": len(self.conversation_history),
                        "files_created": self.metadata.get("files_created", 0),
                        "files_updated": self.metadata.get("files_updated", 0),
                        "files_read": self.metadata.get("files_read", 0),
                        "tool_calls_count": len(self._tool_calls_log)
                    }
                )
                logger.info(f"Completed agent call log: {self._current_agent_call_log_id}")
            except Exception as log_error:
                logger.error(f"Failed to complete agent call logging: {log_error}")
            
            return response
            
        except Exception as e:
            logger.error(f"Error in context manager agent for user {user_id}: {e}")
            
            # FAIL AGENT CALL LOGGING
            try:
                import traceback
                await agent_call_logger.fail_agent_call(
                    log_id=self._current_agent_call_log_id,
                    error=str(e),
                    error_type="processing_error",
                    stack_trace=traceback.format_exc(),
                    metadata={"error_location": "process_message"}
                )
                logger.error(f"Failed agent call log: {self._current_agent_call_log_id}")
            except Exception as log_error:
                logger.error(f"Failed to log agent call failure: {log_error}")
            
            return f"I encountered an error while managing the context: {str(e)}"
    
    async def _process_with_tools(self, user_id: str) -> str:
        """Process message using tool-calling capabilities"""
        # Check if OpenAI client
        if hasattr(self.model_client, 'client') and hasattr(self.model_client.client, 'chat'):
            return await self._process_with_tools_openai(user_id)
        else:
            # Fallback to non-tools processing
            logger.warning(f"Unknown client type, falling back to non-tools processing")
            return await self._process_without_tools(user_id)
    
    async def _process_with_tools_openai(self, user_id: str) -> str:
        """Process message using OpenAI tool-calling"""
        max_tool_rounds = 5
        for _ in range(max_tool_rounds):
            response = await self.model_client.generate_completion(
                messages=self.conversation_history,
                tools=self.tools_openai
            )

            if not hasattr(response, 'choices'):
                return str(response)

            message = response.choices[0].message

            if not message.tool_calls:
                return message.content

            # Track tool calls for final logging
            for tc in message.tool_calls:
                tool_call_data = {
                    'id': tc.id,
                    'type': tc.type,
                    'function': {
                        'name': tc.function.name,
                        'arguments': tc.function.arguments
                    }
                }
                self._tool_calls_log.append(tool_call_data)

            # Add assistant message with tool calls to history
            self.add_to_history("assistant", {
                "content": message.content,
                "tool_calls": [{
                    "id": tc.id,
                    "type": tc.type,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    }
                } for tc in message.tool_calls]
            })

            # Execute tools and collect results (wait for all to finish)
            tool_results = await self._execute_tools_openai(message.tool_calls)
            self._tool_results_log.extend(tool_results)

            # Add tool results to history (must follow tool_calls)
            for tool_call, result in zip(message.tool_calls, tool_results):
                self.add_to_history("tool", result["result"], tool_call.id)

        logger.warning("Reached max tool-call rounds without final response")
        return "I completed the requested context operations but need further instructions to continue."

    async def _execute_tools_openai(self, tool_calls) -> List[Dict[str, Any]]:
        """Execute tool calls concurrently and return structured results"""
        import json
        import traceback

        async def _run_tool(tool_call):
            tool_name = tool_call.function.name
            tool_args = json.loads(tool_call.function.arguments)
            
            # Track detailed execution
            detailed_call = {
                "tool_call_id": tool_call.id,
                "name": tool_name,
                "input": tool_args,
                "output": None,
                "exception": None,
                "started_at": datetime.utcnow().isoformat(),
                "completed_at": None,
                "duration_ms": None,
                "success": False
            }
            
            start_time = datetime.utcnow()
            try:
                result = await self._execute_tool({"name": tool_name, "arguments": tool_args})
                end_time = datetime.utcnow()
                
                # Update detailed tracking
                detailed_call["output"] = result
                detailed_call["completed_at"] = end_time.isoformat()
                detailed_call["duration_ms"] = int((end_time - start_time).total_seconds() * 1000)
                detailed_call["success"] = True
                
                self._tool_calls_detailed.append(detailed_call)
                
                return {
                    "tool_call_id": tool_call.id,
                    "result": result,
                    "success": True,
                    "timestamp": datetime.utcnow().isoformat()
                }
            except Exception as tool_error:
                end_time = datetime.utcnow()
                error_msg = f"Error executing {tool_name}: {str(tool_error)}"
                logger.error(error_msg)
                
                # Update detailed tracking with exception
                detailed_call["output"] = error_msg
                detailed_call["exception"] = f"{type(tool_error).__name__}: {str(tool_error)}\n{traceback.format_exc()}"
                detailed_call["completed_at"] = end_time.isoformat()
                detailed_call["duration_ms"] = int((end_time - start_time).total_seconds() * 1000)
                detailed_call["success"] = False
                
                self._tool_calls_detailed.append(detailed_call)
                
                return {
                    "tool_call_id": tool_call.id,
                    "result": error_msg,
                    "success": False,
                    "timestamp": datetime.utcnow().isoformat()
                }

        tasks = [_run_tool(tc) for tc in tool_calls]
        return await asyncio.gather(*tasks)
    
    async def _process_without_tools(self, user_id: str) -> str:
        """Process message without tool-calling (direct context management)"""
        response = await self.model_client.generate_completion(
            messages=self.conversation_history
        )
        
        return response
    
    async def _execute_tool(self, tool_call: Dict[str, Any]) -> str:
        """Execute a context management tool call"""
        # Increment tool calls counter
        self.metadata["tool_calls_count"] += 1

        tool_name = tool_call.get("name")
        arguments = tool_call.get("arguments", {})

        # Track tool usage by type
        tools_by_type = self.metadata["tools_by_type"]
        tools_by_type[tool_name] = tools_by_type.get(tool_name, 0) + 1

        logger.info(f"Executing tool: {tool_name} (total: {tools_by_type[tool_name]})")

        if tool_name == "manage_context_files":
            # Override user_id with the authenticated user_id from context
            if hasattr(self, 'current_user_id'):
                arguments['user_id'] = self.current_user_id
                logger.debug(f"Enforcing user_id={self.current_user_id} for tool call")
            # Also pass user_name if available
            if hasattr(self, 'current_user_name') and self.current_user_name:
                arguments['user_name'] = self.current_user_name
                logger.debug(f"Including user_name={self.current_user_name} for context")
            return await self._handle_manage_context(**arguments)
        
        return f"Unknown tool: {tool_name}"
    
    
    
    async def _handle_manage_context(
        self,
        action: str,
        user_id: str,
        user_name: Optional[str] = None,
        content: Optional[str] = None,
        filename: Optional[str] = None
    ) -> str:
        """
        Route manage_context_files actions to appropriate handlers
        
        Args:
            action: Context operation (list, read, write, append)
            user_id: User identifier
            user_name: User's name (optional, for context)
            content: Content to write (for 'write' or 'append')
            filename: File to read/write/append
            
        Returns:
            Result message
        """
        logger.info(f"Handle manage_context_files action: {action}")
        
        if action == "list":
            ensure_user_context_dir(user_id)
            files = list_user_context_files(user_id)
            return f"Context files for user {user_id}: {', '.join(files)}" if files else f"No context files found for user {user_id}"

        if action == "read":
            if not filename:
                return "Error: filename is required for 'read' action"
            self.metadata["files_read"] += 1
            file_content = read_user_context(user_id, filename)
            if file_content is None:
                return f"File {filename} not found for user {user_id}"
            return f"Content of {filename}:\n{file_content}"

        if action == "write":
            if not filename:
                return "Error: filename is required for 'write' action"
            if content is None:
                return "Error: content is required for 'write' action"
            ensure_user_context_dir(user_id)
            from pathlib import Path
            user_dir = Path(__file__).parent.parent / "agent_context" / str(user_id)
            file_exists = (user_dir / filename).exists()
            success = write_user_context(user_id, filename, content)
            if success:
                if file_exists:
                    self.metadata["files_updated"] += 1
                else:
                    self.metadata["files_created"] += 1
                return f"Successfully written to {filename} for user {user_id}"
            return f"Failed to write to {filename} for user {user_id}"

        if action == "append":
            if not filename:
                return "Error: filename is required for 'append' action"
            if content is None:
                return "Error: content is required for 'append' action"
            success = update_user_context(user_id, filename, content)
            if success:
                self.metadata["files_updated"] += 1
                return f"Successfully appended to {filename} for user {user_id}"
            return f"Failed to append to {filename} for user {user_id}"
        
        else:
            return f"Unknown action: {action}"
    
    def add_to_history(self, role: str, content, tool_call_id: str = None):
        """
        Add message to conversation history
        
        Args:
            role: Message role (user/assistant/system/tool)
            content: Message content (string or dict for assistant with tool_calls)
            tool_call_id: Optional tool call ID for tool role messages
        """
        message = {"role": role}
        
        # Handle different content types
        if isinstance(content, dict):
            # Assistant message with tool calls
            message.update(content)
        elif role == "tool":
            # Tool result message for OpenAI
            message["content"] = str(content)
            if tool_call_id:
                message["tool_call_id"] = tool_call_id
        else:
            # Standard text message
            message["content"] = str(content)
        
        self.conversation_history.append(message)
    
    def get_history(self) -> List[Dict[str, str]]:
        """Get conversation history"""
        return self.conversation_history
    
    def clear_history(self):
        """Clear conversation history"""
        self.conversation_history = []
