"""
Context Manager Agent
Manages user context history in structured markdown files
"""
from typing import Dict, Any, Optional, List
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


class ContextManagerAgent(BaseAgent):
    """Agent for managing user context in structured markdown files"""
    
    def __init__(self, model_client):
        """
        Initialize context manager agent
        
        Args:
            model_client: LLM client (OpenAI or Anthropic)
        """
        super().__init__(model_client, "context_manager")
        
        # Define context management tools for Anthropic
        self.tools_anthropic = [
            {
                "name": "manage_user_context_files",
                "description": "Manage user context files in markdown format. Create or update the index file and section-specific files to organize user information systematically.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["create_index", "update_section", "read_context", "list_files"],
                            "description": "Action to perform: create_index (create/update INDEX.md), update_section (create/update section file), read_context (read existing files), list_files (list all context files)"
                        },
                        "user_id": {
                            "type": "string",
                            "description": "User identifier for context storage"
                        },
                        "filename": {
                            "type": "string",
                            "description": "Filename for the context file (e.g., 'INDEX.md', 'profile.md', 'goals.md'). Required for create_index, update_section, and read_context actions."
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
                                "description": "Action to perform: create_index (create/update INDEX.md), update_section (create/update section file), read_context (read existing files), list_files (list all context files)"
                            },
                            "user_id": {
                                "type": "string",
                                "description": "User identifier for context storage"
                            },
                            "filename": {
                                "type": "string",
                                "description": "Filename for the context file (e.g., 'INDEX.md', 'profile.md', 'goals.md'). Required for create_index, update_section, and read_context actions."
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
        
        # Add user message to history
        self.add_to_history("user", user_message)
        
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
            
            return response
            
        except Exception as e:
            logger.error(f"Error in context manager agent: {e}")
            return f"I encountered an error while managing the context: {str(e)}"
    
    async def _process_with_tools(self, user_id: str) -> str:
        """Process message using tool-calling capabilities"""
        # Determine which tools to use based on model type
        if hasattr(self.model_client, 'client_type'):
            if self.model_client.client_type == 'anthropic':
                tools = self.tools_anthropic
            else:
                tools = self.tools_openai
        else:
            tools = self.tools_openai
        
        # Generate response with tools
        response = await self.model_client.generate_completion(
            messages=self.conversation_history,
            temperature=0.3,
            max_tokens=2000,
            tools=tools
        )
        
        # Check if tool was called
        if isinstance(response, dict) and "tool_calls" in response:
            # Execute tool calls
            tool_results = []
            for tool_call in response["tool_calls"]:
                result = await self._execute_tool(tool_call)
                tool_results.append(result)
            
            return "\n".join(tool_results)
        
        return response
    
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
            filename: Name of the file
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
    
    async def stream_response(
        self,
        user_message: str,
        user_context: Optional[Dict[str, Any]] = None
    ):
        """
        Stream context management response in real-time
        
        Args:
            user_message: Information from other agents
            user_context: User context including user_id
            
        Yields:
            Response tokens
        """
        if not user_context or "user_id" not in user_context:
            yield "Error: user_id is required to manage context"
            return
        
        # Add user message to history
        self.add_to_history("user", user_message)
        
        full_response = ""
        try:
            async for token in self.model_client.stream_completion(
                messages=self.conversation_history,
                temperature=0.3,
                max_tokens=1500
            ):
                full_response += token
                yield token
            
            # Add complete response to history
            self.add_to_history("assistant", full_response)
            
        except Exception as e:
            logger.error(f"Error streaming context manager response: {e}")
            yield f"\n\nError: {str(e)}"
    
    def add_to_history(self, role: str, content: str):
        """Add message to conversation history"""
        self.conversation_history.append({
            "role": role,
            "content": content
        })
    
    def get_history(self) -> List[Dict[str, str]]:
        """Get conversation history"""
        return self.conversation_history
    
    def clear_history(self):
        """Clear conversation history"""
        self.conversation_history = []
