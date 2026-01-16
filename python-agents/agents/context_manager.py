"""
Context Manager Agent
Manages user context history in structured markdown files
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
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
from storage.context_manager_log import ContextManagerLogger


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
        self.conversation_logger = ContextManagerLogger(db_session) if db_session else None
        self.current_log_id = None  # Track current conversation log
        
        # Add system prompt to conversation history
        self.conversation_history = [
            {"role": "system", "content": CONTEXT_MANAGER_SYSTEM_PROMPT}
        ]
        
        # Define context management tools for OpenAI
        self.tools_openai = [
            {
                "type": "function",
                "function": {
                    "name": "manage_user_context_files",
                    "description": "Manage user context files in markdown format. Create or update the index file and section-specific files to organize user information systematically.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "action": {
                                "type": "string",
                                "enum": ["create_index", "update_section", "read_context", "list_files"],
                                "description": "Action to perform: create_index (create/update INDEX.md - filename defaults to INDEX.md if not provided), update_section (create/update section file - filename required), read_context (read existing files - filename required), list_files (list all context files)"
                            },
                            "user_id": {
                                "type": "string",
                                "description": "User identifier for context storage"
                            },
                            "filename": {
                                "type": "string",
                                "description": "Filename for the context file (e.g., 'INDEX.md', 'profile.md', 'goals.md'). Optional for create_index (defaults to INDEX.md). Required for update_section and read_context actions."
                            },
                            "content": {
                                "type": "string",
                                "description": "Markdown content to write. Required for create_index and update_section actions."
                            },
                            "append": {
                                "type": "boolean",
                                "description": "If true, append content to existing file. If false, overwrite. Default: false",
                                "default": False
                            }
                        },
                        "required": ["action", "user_id"]
                    }
                }
            }
        ]
    
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
        
        # Store user_id for tool execution
        self.current_user_id = user_id
        
        # Create conversation log
        self.current_log_id = str(uuid.uuid4())
        if self.conversation_logger:
            try:
                await self.conversation_logger.create_log(
                    conversation_id=self.current_log_id,
                    user_id=user_id,
                    user_message=user_message,
                    conversation_link_id=user_context.get('conversation_id'),
                    metadata={
                        'model': getattr(self.model_client, 'model_name', 'unknown'),
                        'agent_name': 'context_manager'
                    }
                )
            except Exception as log_error:
                logger.error(f"Failed to create conversation log: {log_error}")
        
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
            
            # Update log with completion
            if self.conversation_logger and self.current_log_id:
                try:
                    await self.conversation_logger.update_log(
                        conversation_id=self.current_log_id,
                        assistant_message=response,
                        status='COMPLETED'
                    )
                except Exception as log_error:
                    logger.error(f"Failed to update conversation log: {log_error}")
            
            return response
            
        except Exception as e:
            logger.error(f"Error in context manager agent for user {user_id}: {e}")
            
            # Log error
            if self.conversation_logger and self.current_log_id:
                try:
                    await self.conversation_logger.update_log(
                        conversation_id=self.current_log_id,
                        status='FAILED',
                        error_message=str(e)
                    )
                except Exception as log_error:
                    logger.error(f"Failed to log error: {log_error}")
            
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
            temperature=0.3,
            max_tokens=2000,
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
                
                # Log tool calls
                for tc in message.tool_calls:
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
                        tool_results_log.append({
                            'tool_call_id': tool_call.id,
                            'result': result,
                            'success': True,
                            'timestamp': datetime.utcnow().isoformat()
                        })
                    except Exception as tool_error:
                        error_msg = f"Error executing {tool_name}: {str(tool_error)}"
                        tool_results_log.append({
                            'tool_call_id': tool_call.id,
                            'result': error_msg,
                            'success': False,
                            'timestamp': datetime.utcnow().isoformat()
                        })
                        logger.error(error_msg)
                    
                    # Add tool result to history
                    self.add_to_history("tool", result, tool_call.id)
                
                # Update log with tool execution
                if self.conversation_logger and self.current_log_id:
                    try:
                        await self.conversation_logger.update_log(
                            conversation_id=self.current_log_id,
                            tool_calls=tool_calls_log,
                            tool_results=tool_results_log,
                            status='IN_PROGRESS'
                        )
                    except Exception as log_error:
                        logger.error(f"Failed to log tool execution: {log_error}")
                
                # Get follow-up response after tool execution
                follow_up = await self.model_client.generate_completion(
                    messages=self.conversation_history,
                    temperature=0.3,
                    max_tokens=800
                )
                
                # Handle follow-up response
                if hasattr(follow_up, 'choices'):
                    final_response = follow_up.choices[0].message.content
                else:
                    final_response = follow_up
                
                self.add_to_history("assistant", final_response)
                return final_response
            else:
                # No tool calls, just return text
                self.add_to_history("assistant", message.content)
                return message.content
        
        # Plain text response fallback
        return str(response)
    
    async def _process_without_tools(self, user_id: str) -> str:
        """Process message without tool-calling (direct context management)"""
        response = await self.model_client.generate_completion(
            messages=self.conversation_history,
            temperature=0.3,
            max_tokens=1500
        )
        
        return response
    
    async def _execute_tool(self, tool_call: Dict[str, Any]) -> str:
        """Execute a context management tool call"""
        tool_name = tool_call.get("name")
        arguments = tool_call.get("arguments", {})
        
        if tool_name == "manage_user_context_files":
            # Override user_id with the authenticated user_id from context
            # This ensures we always use the correct user folder regardless of what the LLM provides
            if hasattr(self, 'current_user_id'):
                arguments['user_id'] = self.current_user_id
                logger.debug(f"Enforcing user_id={self.current_user_id} for tool call")
            return await self._manage_context_files(**arguments)
        
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
                
                file_content = read_user_context(user_id, filename)
                if file_content:
                    return f"Content of {filename}:\n{file_content}"
                return f"File {filename} not found for user {user_id}"
            
            elif action in ["create_index", "update_section"]:
                # Auto-default filename to INDEX.md for create_index action
                if action == "create_index" and not filename:
                    filename = "INDEX.md"
                    logger.info(f"Auto-defaulting filename to INDEX.md for create_index action")
                
                if not filename or not content:
                    return f"Error: filename and content are required for {action} action"
                
                if append:
                    success = update_user_context(user_id, filename, content)
                    operation = "appended to"
                else:
                    success = write_user_context(user_id, filename, content)
                    operation = "written to"
                
                if success:
                    return f"Successfully {operation} {filename} for user {user_id}"
                return f"Failed to write to {filename} for user {user_id}"
            
            else:
                return f"Unknown action: {action}"
                
        except Exception as e:
            logger.error(f"Error managing context files: {e}")
            return f"Error managing context files: {str(e)}"
    
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
