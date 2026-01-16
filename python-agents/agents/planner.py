"""
Planning Agent
Generates content project plans and task breakdowns
"""
from typing import Dict, Any, Optional
from agents.base import BaseAgent
from config.prompts import (
    PLANNING_SYSTEM_PROMPT
)
from utils.logger import logger
from utils.task_inserter import insert_tasks_to_db


class PlanningAgent(BaseAgent):
    """Agent for content planning and task generation"""
    
    def __init__(self, model_client, enable_openai_tools: bool = True, context_manager_agent=None, conversation_storage=None):
        """
        Initialize planning agent with tool support for OpenAI.
        
        Args:
            model_client: LLM client (OpenAI)
            enable_openai_tools: Whether to enable tool usage for OpenAI models (default: True)
            context_manager_agent: Context manager agent instance for saving user context
            conversation_storage: Conversation storage instance for checking conversation history
        """
        super().__init__(model_client, "planning")
        self.enable_openai_tools = enable_openai_tools
        self.context_manager_agent = context_manager_agent
        self.conversation_storage = conversation_storage
        self.is_first_conversation = False
        
        # Define task insertion tool (OpenAI format)
        self.tools_openai = [
            {
                "type": "function",
                "function": {
                    "name": "request_user_context",
                    "description": "Request information about the user from their context history.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "A clear, specific question or request for information about the user. Examples: 'What are the user's content goals?', 'What platforms does the user create content for?', 'Has the user mentioned any target audience details?', 'What content topics has the user worked on previously?'"
                            },
                            "reasoning": {
                                "type": "string",
                                "description": "Brief explanation of why you need this information to help with the current task"
                            }
                        },
                        "required": ["query", "reasoning"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "insert_tasks_to_db",
                    "description": "Insert generated tasks into the PostgreSQL database. The tasks will be marked as AI-generated and assigned TODO status.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "action": {
                                "type": "string",
                                "enum": ["create_tasks"],
                                "description": "Must be 'create_tasks'"
                            },
                            "tasks": {
                                "type": "array",
                                "description": "Array of task objects to insert",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "title": {
                                            "type": "string",
                                            "description": "Task title (concise, actionable)"
                                        },
                                        "description": {
                                            "type": "string",
                                            "description": "Detailed task description with steps"
                                        },
                                        "priority": {
                                            "type": "string",
                                            "enum": ["LOW", "MEDIUM", "HIGH", "URGENT"],
                                            "description": "Task priority level"
                                        },
                                        "estimatedHours": {
                                            "type": "number",
                                            "description": "Estimated hours to complete"
                                        },
                                        "researchNotes": {
                                            "type": "string",
                                            "description": "Research findings or reference materials"
                                        },
                                        "aiReasoning": {
                                            "type": "string",
                                            "description": "Your reasoning for including this task"
                                        },
                                        "dependencies": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                            "description": "List of task titles this depends on"
                                        }
                                    },
                                    "required": ["title", "description", "priority", "estimatedHours"]
                                }
                            }
                        },
                        "required": ["action", "tasks"]
                    }
                }
            }
        ]
        
        # Initialize with comprehensive system prompt
        self._initialize_system_prompt()
    def _initialize_system_prompt(self):
        """Initialize the agent with system prompts and instructions"""
        self.add_to_history("system", PLANNING_SYSTEM_PROMPT)
        self.add_to_history("system", "Markdown supported.")
    
    # ============================================================================
    # PUBLIC METHODS - Message Processing
    # ============================================================================
    
    async def process_message(
        self,
        user_message: str,
        user_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Process planning-related questions with tool support
        
        Args:
            user_message: User's question or request
            user_context: User's profile context
            
        Returns:
            Agent's response
        """
        # Store user_id and conversation_id for tool execution
        if user_context and 'user_id' in user_context:
            self._current_user_id = user_context['user_id']
            self._current_conversation_id = user_context.get('conversation_id')
        
        # Check if this is user's first conversation (excluding current one)
        if user_context and self.conversation_storage:
            self.is_first_conversation = await self._is_first_conversation(
                user_context.get('user_id'),
                user_context.get('conversation_id')
            )
            if self.is_first_conversation:
                logger.info(f"First conversation detected for user {user_context.get('user_id')}")
                # Add system message to inform the agent
                self.add_to_history("system", "NOTE: This is the user's first conversation with you. All relevant information about the user is contained in this current conversation history. DO NOT use the request_user_context tool - you already have all available information.")
        
        # Let context manager agent decide if user context should be saved
        if self.context_manager_agent and user_context:
            await self._save_user_context(user_message, user_context)
        
        # Only add user message if not already in history (from loaded conversation)
        if not self.conversation_history or self.conversation_history[-1].get("content") != user_message:
            self.add_to_history("user", user_message)
        
        try:
            # Check if OpenAI client
            if hasattr(self.model_client, 'client') and hasattr(self.model_client.client, 'chat'):
                # Only use tools if enabled for OpenAI
                if self.enable_openai_tools:
                    response = await self._generate_with_tools_openai()
                else:
                    response = await self.model_client.generate_completion(
                        messages=self.conversation_history,
                        #temperature=0.7,
                        #max_tokens=2000
                    )
                    # Create a mock response object matching OpenAI's structure
                    class MockChoice:
                        def __init__(self, content):
                            self.message = type('obj', (object,), {
                                'content': content,
                                'tool_calls': None
                            })()
                    class MockResponse:
                        def __init__(self, content):
                            self.choices = [MockChoice(content)]
                    response = MockResponse(response)
                
                message = response.choices[0].message
                
                # Handle tool calls (only if tools were enabled)
                if message.tool_calls and self.enable_openai_tools:
                    tool_results = await self._execute_tools_openai(message.tool_calls)
                    
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
                    
                    # Add tool results
                    for tool_call, result in zip(message.tool_calls, tool_results):
                        self.add_to_history("tool", result, tool_call.id)
                    
                    # Get follow-up response
                    follow_up = await self.model_client.generate_completion(
                        messages=self.conversation_history,
                        #temperature=0.7,
                        #max_tokens=800
                    )
                    
                    self.add_to_history("assistant", follow_up)
                    return follow_up
                else:
                    # Regular text response
                    self.add_to_history("assistant", message.content)
                    return message.content
            else:
                # Fallback for clients without tool support
                response = await self.model_client.generate_completion(
                    messages=self.conversation_history,
                    #temperature=0.7,
                    #max_tokens=800
                )
                
                self.add_to_history("assistant", response)
                return response
            
        except Exception as e:
            logger.error(f"Error in planning agent: {e}")
            return "I encountered an error while processing your request. Please try again."
    
    # ============================================================================
    # PRIVATE METHODS - Tool Generation (OpenAI)
    # ============================================================================
    
    async def _generate_with_tools_openai(self):
        """Generate response with tool support for OpenAI"""
        # Only include tools if enabled
        kwargs = {
            "messages": self.conversation_history,
            #"temperature": 0.7,
            #"max_tokens": 2000
        }
        
        if self.enable_openai_tools:
            # Filter out context retrieval tool for first-time conversations
            tools = self.tools_openai
            if self.is_first_conversation:
                tools = [tool for tool in self.tools_openai 
                        if tool["function"]["name"] != "request_user_context"]
            kwargs["tools"] = tools
        
        response = await self.model_client.generate_completion(**kwargs)
        
        return response
    
    # ============================================================================
    # PRIVATE METHODS - Tool Execution
    # ============================================================================
    
    async def _execute_tools_openai(self, tool_calls) -> list:
        """Execute tool calls and return results for OpenAI"""
        import json
        results = []
        
        for tool_call in tool_calls:
            tool_name = tool_call.function.name
            tool_input = json.loads(tool_call.function.arguments)
            
            logger.info(f"Executing tool: {tool_name}")
            
            if tool_name == "request_user_context":
                try:
                    # Get current user_id from context
                    user_id = getattr(self, '_current_user_id', None)
                    if not user_id:
                        raise ValueError("No user_id available for context retrieval")
                    
                    context_info = await self._request_context_from_manager(
                        query=tool_input.get('query'),
                        reasoning=tool_input.get('reasoning'),
                        user_id=user_id
                    )
                    results.append(context_info)
                except Exception as e:
                    logger.error(f"Error executing request_user_context tool: {e}")
                    results.append(f"Error retrieving context: {str(e)}")
            elif tool_name == "insert_tasks_to_db":
                try:
                    task_ids = await insert_tasks_to_db(tool_input)
                    results.append(f"Successfully created {len(task_ids)} tasks with IDs: {', '.join(task_ids)}")
                except Exception as e:
                    logger.error(f"Error executing tool: {e}")
                    results.append(f"Error: {str(e)}")
        
        return results
    
    # ============================================================================
    # PRIVATE METHODS - Context Management
    # ============================================================================
    
    async def _save_user_context(
        self,
        user_message: str,
        user_context: Dict[str, Any]
    ):
        """
        Call context manager agent to analyze and potentially save user information.
        The context manager agent decides whether the information is worth saving.
        
        Args:
            user_message: User's message from the planning conversation
            user_context: User context including user_id
        """
        try:
            logger.debug(f"Sending message to context manager for analysis for user: {user_context.get('user_id', 'unknown')}")
            
            # Prepare context information for context manager
            # The context manager will decide if this contains information worth saving
            context_message = f"""Analyze the following user message from a planning conversation and determine if it contains information about the user that should be saved to their context files (profile, goals, content preferences, etc.).

If the message contains relevant user information, extract and save it to the appropriate context files. If not, simply acknowledge without taking action.

User Message: {user_message}
"""
            
            # Call context manager agent - it will decide whether to save
            result = await self.context_manager_agent.process_message(
                user_message=context_message,
                user_context=user_context
            )
            
            logger.debug(f"Context manager response: {result}")
        except Exception as e:
            # Log error but don't fail the main flow
            logger.error(f"Error in context manager communication (non-blocking): {e}")
    
    async def _request_context_from_manager(
        self,
        query: str,
        reasoning: str,
        user_id: str
    ) -> str:
        """
        Request specific information about the user from the context manager agent.
        This allows the planner to retrieve user context as needed.
        
        Args:
            query: The specific question or information request
            reasoning: Why this information is needed
            user_id: The user identifier
            
        Returns:
            Context information from the context manager agent
        """
        try:
            logger.info(f"Requesting context from context manager: {query}")
            logger.debug(f"Reasoning: {reasoning}")
            
            if not self.context_manager_agent:
                return "Context manager agent is not available. Unable to retrieve user context."
            
            # Prepare the request message for the context manager
            context_request = f"""Retrieve information from the user's context files to answer the following query:

**Query:** {query}

**Why this is needed:** {reasoning}

Please search through the user's context files (INDEX.md and any section-specific files) and provide the relevant information. If no information is found, respond with 'No information found about this topic.'
"""
            
            # Call context manager agent
            result = await self.context_manager_agent.process_message(
                user_message=context_request,
                user_context={'user_id': user_id}
            )
            
            logger.debug(f"Context manager returned: {result[:200]}...")  # Log first 200 chars
            return result
            
        except Exception as e:
            logger.error(f"Error requesting context from context manager: {e}")
            return f"Error retrieving context: {str(e)}"
    
    async def _is_first_conversation(
        self,
        user_id: str,
        current_conversation_id: str
    ) -> bool:
        """
        Check if this is the user's first conversation (excluding the current one).
        
        Args:
            user_id: User identifier
            current_conversation_id: Current conversation ID to exclude from count
            
        Returns:
            True if user has no other conversations, False otherwise
        """
        try:
            if not user_id or not current_conversation_id:
                return False
            
            # Get all user conversations
            conversations = await self.conversation_storage.get_user_conversations(
                user_id=user_id,
                limit=100  # Check more than just recent ones
            )
            
            # Filter out the current conversation
            other_conversations = [
                conv for conv in conversations 
                if conv.get('id') != current_conversation_id
            ]
            
            # If no other conversations exist, this is the first one
            return len(other_conversations) == 0
            
        except Exception as e:
            logger.error(f"Error checking first conversation status: {e}")
            # On error, assume it's not first conversation (safer default)
            return False
