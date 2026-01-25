"""
Context Manager Agent
Manages user context history in structured markdown files
"""
from typing import Dict, Any, Optional, List
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
        self.db_session = db_session
        self._current_agent_call_log_id = None  # Track current agent call log
        self._tool_calls_log = []  # Track tool calls for logging
        self._tool_results_log = []  # Track tool results for logging

        # Initialize metadata
        self.metadata = {
            "agent_name": "context_manager",
            "agent_type": "context_management",
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
                    "name": "manage_context",
                    "description": "Manage user context: save new information, request additional context, retrieve existing context, or list context files.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "action": {
                                "type": "string",
                                "enum": ["save", "request", "retrieve", "list"],
                                "description": "Context operation: 'save' (save new info), 'request' (ask for specific info), 'retrieve' (read context file), 'list' (list all files)"
                            },
                            "summary": {
                                "type": "string",
                                "description": "Information to save about the user (for 'save' action)"
                            },
                            "query": {
                                "type": "string",
                                "description": "Specific question about ADDITIONAL information not in cached context (for 'request' action)"
                            },
                            "reasoning": {
                                "type": "string",
                                "description": "Why additional context is needed (for 'request' action)"
                            },
                            "filename": {
                                "type": "string",
                                "description": "Filename to retrieve (e.g., 'INDEX.md', 'profile.md', 'goals.md') - for 'retrieve' action"
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

        logger.info(f"Processing message: {self.get_metadata_summary()}")

        # Store user_id for tool execution
        self.current_user_id = user_id
        
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
        import json
        
        # Generate response with tools
        response = await self.model_client.generate_completion(
            messages=self.conversation_history,
            tools=self.tools_openai
        )
        
        # Handle OpenAI response format
        if hasattr(response, 'choices'):
            # OpenAI response object
            message = response.choices[0].message
            
            if message.tool_calls:
                # Execute tool calls
                tool_calls_log = []
                tool_results_log = []
                
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
                    tool_calls_log.append({
                        'id': tc.id,
                        'name': tc.function.name,
                        'arguments': json.loads(tc.function.arguments),
                        'timestamp': datetime.utcnow().isoformat()
                    })
                
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
                
                # Execute tools and collect results
                for tool_call in message.tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = json.loads(tool_call.function.arguments)
                    
                    try:
                        result = await self._execute_tool({"name": tool_name, "arguments": tool_args})
                        tool_result_data = {
                            'tool_call_id': tool_call.id,
                            'result': result,
                            'success': True,
                            'timestamp': datetime.utcnow().isoformat()
                        }
                        tool_results_log.append(tool_result_data)
                        self._tool_results_log.append(tool_result_data)
                    except Exception as tool_error:
                        error_msg = f"Error executing {tool_name}: {str(tool_error)}"
                        tool_result_data = {
                            'tool_call_id': tool_call.id,
                            'result': error_msg,
                            'success': False,
                            'timestamp': datetime.utcnow().isoformat()
                        }
                        tool_results_log.append(tool_result_data)
                        self._tool_results_log.append(tool_result_data)
                        logger.error(error_msg)
                    
                    # Add tool result to history
                    self.add_to_history("tool", result, tool_call.id)
                
                # Get follow-up response after tool execution
                follow_up = await self.model_client.generate_completion(
                    messages=self.conversation_history
                )
                
                # Handle follow-up response
                if hasattr(follow_up, 'choices'):
                    final_response = follow_up.choices[0].message.content
                else:
                    final_response = follow_up
                
                # Note: Don't add to history here - already added with tool_calls above
                return final_response
            else:
                # No tool calls, just return text
                return message.content
        
        # Plain text response fallback
        return str(response)
    
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

        if tool_name == "manage_context":
            # Override user_id with the authenticated user_id from context
            if hasattr(self, 'current_user_id'):
                arguments['user_id'] = self.current_user_id
                logger.debug(f"Enforcing user_id={self.current_user_id} for tool call")
            return await self._handle_manage_context(**arguments)
        
        return f"Unknown tool: {tool_name}"
    
    async def _manage_context_files(
        self,
        action: str,
        user_id: str,
        filename: Optional[str] = None,
        content: Optional[str] = None,
        append: bool = False
    ) -> str:
        """
        Execute context file management operations
        
        Args:
            action: Operation to perform
            user_id: User identifier
            filename: Name of the file (defaults to INDEX.md for create_index action)
            content: Content to write
            append: Whether to append to existing file
            
        Returns:
            Result message
        """
        try:
            ensure_user_context_dir(user_id)
            
            if action == "list_files":
                files = list_user_context_files(user_id)
                if files:
                    return f"Context files for user {user_id}: {', '.join(files)}"
                return f"No context files found for user {user_id}"
            
            elif action == "read_context":
                if not filename:
                    return "Error: filename is required for read_context action"

                # Track file read
                self.metadata["files_read"] += 1

                file_content = read_user_context(user_id, filename)
                if file_content:
                    return f"Content of {filename}:\n{file_content}"
                # Fallback: If INDEX.md is missing, search for other section files
                if filename.upper() == "INDEX.MD":
                    files = list_user_context_files(user_id)
                    # Only consider .md files, skip INDEX.md
                    section_files = [f for f in files if f.lower().endswith('.md') and f.lower() != 'index.md']
                    if not section_files:
                        return f"No information found about this topic. If Index.md does not exist, search in other relevant context files."
                    aggregated = []
                    for section_file in section_files:
                        section_content = read_user_context(user_id, section_file)
                        if section_content:
                            aggregated.append(f"[{section_file}]:\n{section_content.strip()}\n")
                    if aggregated:
                        return "\n".join(aggregated)
                    else:
                        return f"No information found about this topic. If Index.md does not exist, search in other relevant context files."
                return f"File {filename} not found for user {user_id}"
            
            elif action in ["create_index", "update_section"]:
                # Auto-default filename to INDEX.md for create_index action
                if action == "create_index" and not filename:
                    filename = "INDEX.md"
                    logger.info("Auto-defaulting filename to INDEX.md for create_index action")

                if not filename or not content:
                    return f"Error: filename and content are required for {action} action"

                # Check if file exists to determine if this is create or update
                from pathlib import Path
                user_dir = Path(__file__).parent.parent / "user_context" / user_id
                file_exists = (user_dir / filename).exists()

                if append:
                    success = update_user_context(user_id, filename, content)
                    operation = "appended to"
                    if success:
                        self.metadata["files_updated"] += 1
                else:
                    success = write_user_context(user_id, filename, content)
                    operation = "written to"
                    if success:
                        if file_exists:
                            self.metadata["files_updated"] += 1
                        else:
                            self.metadata["files_created"] += 1

                logger.info(
                    f"File operations - created: {self.metadata['files_created']}, "
                    f"updated: {self.metadata['files_updated']}, read: {self.metadata['files_read']}"
                )

                if success:
                    return f"Successfully {operation} {filename} for user {user_id}"
                return f"Failed to write to {filename} for user {user_id}"
            
            else:
                return f"Unknown action: {action}"
                
        except Exception as e:
            logger.error(f"Error managing context files: {e}")
            return f"Error managing context files: {str(e)}"
    
    async def _handle_manage_context(
        self,
        action: str,
        user_id: str,
        summary: Optional[str] = None,
        query: Optional[str] = None,
        reasoning: Optional[str] = None,
        filename: Optional[str] = None
    ) -> str:
        """
        Route manage_context actions to appropriate handlers
        
        Args:
            action: Context operation (save, request, retrieve, list)
            user_id: User identifier
            summary: Information to save (for 'save' action)
            query: Question for additional context (for 'request' action)
            reasoning: Why additional context needed (for 'request' action)
            filename: File to retrieve (for 'retrieve' action)
            
        Returns:
            Result message
        """
        logger.info(f"Handle manage_context action: {action}")
        
        if action == "save":
            # Save new user information to context file
            if not summary:
                return "Error: summary is required for 'save' action"
            
            content = f"# User Information\n\n{summary}\n\nUpdated: {datetime.now(timezone.utc).isoformat()}"
            return await self._manage_context_files(
                action="update_section",
                user_id=user_id,
                filename="user_info.md",
                content=content,
                append=True
            )
        
        elif action == "request":
            # Request additional context information
            if not query:
                return "Error: query is required for 'request' action"
            
            # Return a placeholder indicating that additional context should be requested
            return f"Requesting additional context: {query}" + (f"\nReasoning: {reasoning}" if reasoning else "")
        
        elif action == "retrieve":
            # Retrieve existing context file
            if not filename:
                filename = "INDEX.md"
            
            return await self._manage_context_files(
                action="read_context",
                user_id=user_id,
                filename=filename
            )
        
        elif action == "list":
            # List all context files
            return await self._manage_context_files(
                action="list_files",
                user_id=user_id
            )
        
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
