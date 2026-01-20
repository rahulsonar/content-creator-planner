"""
Planning Agent
Generates content project plans and task breakdowns
"""
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import json
import traceback
from agents.base import BaseAgent
from config.prompts import (
    PLANNING_SYSTEM_PROMPT
)
from utils.logger import logger
from storage.agent_call_log import agent_call_logger


class PlanningAgent(BaseAgent):
    """Agent for content planning and task generation"""
    
    def __init__(self, model_client, enable_openai_tools: bool = True, context_manager_agent=None, task_manager_agent=None, conversation_storage=None):
        """
        Initialize planning agent with tool support for OpenAI.
        
        Args:
            model_client: LLM client (OpenAI)
            enable_openai_tools: Whether to enable tool usage for OpenAI models (default: True)
            context_manager_agent: Context manager agent instance for saving user context
            task_manager_agent: Task manager agent instance for delegating task operations
            conversation_storage: Conversation storage instance for checking conversation history
        """
        super().__init__(model_client, "planning")
        self.enable_openai_tools = enable_openai_tools
        self.context_manager_agent = context_manager_agent
        self.task_manager_agent = task_manager_agent
        self.conversation_storage = conversation_storage
        self.is_first_conversation = False
        self._context_cached = False  # Track if context already cached in this session
        self._current_user_id = None
        self._current_conversation_id = None
        self._current_message_id = None
        self._current_log_id = None  # Track current agent call log

        # Initialize metadata
        self.metadata = {
            "agent_name": "planner",
            "agent_type": "planning",
            "conversation_id": None,
            "user_id": None,
            "session_id": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_activity_at": None,
            "total_messages": 0,
            "total_user_messages": 0,
            "tool_calls_count": 0,
            "tools_by_type": {},  # Track count per tool type
            "enable_tools": enable_openai_tools,
            "model_name": getattr(model_client, 'model', 'unknown'),
            "is_first_conversation": None,
            "context_cached": False,
            "tasks_created": 0,
            "agent_version": "1.0.0"
        }

        logger.info(f"PlanningAgent initialized: {self.get_metadata_summary()}")

        # Define tools for planning (OpenAI format)
        self.tools_openai = [
            {
                "type": "function",
                "function": {
                    "name": "manage_tasks",
                    "description": "Delegate task management operations to the UserTaskManager agent. Provide a clear natural language request describing what task operation you need (create, search, update, retrieve, or any other task-related operation).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "request": {
                                "type": "string",
                                "description": "Natural language request describing the task operation. Examples: 'Create 5 tasks for video production', 'Search for tasks related to editing', 'Update task X to completed status', 'Get details of task with ID Y'"
                            }
                        },
                        "required": ["request"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "manage_context",
                    "description": "Manage user context: save new information about user goals/preferences, request additional context, retrieve existing context, or list context files.",
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
                                "description": "Filename to retrieve (e.g., 'INDEX.md', 'profile.md', 'goals.md') - for 'retrieve' action. Optional."
                            }
                        },
                        "required": ["action"]
                    }
                }
            }
        ]
        
        # Initialize with comprehensive system prompt
        self._initialize_system_prompt()

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
            f"tools={m['tool_calls_count']}, tasks={m['tasks_created']}"
        )
    
    def _initialize_system_prompt(self):
        """Initialize the agent with system prompts and instructions"""
        self.add_to_history("system", PLANNING_SYSTEM_PROMPT)
        self.add_to_history("system", "Markdown formatting is supported in your responses.")
       
        
    
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
        # Update metadata at start of message processing
        if user_context:
            self.update_metadata(
                conversation_id=user_context.get('conversation_id'),
                user_id=user_context.get('user_id'),
                session_id=user_context.get('session_id')
            )

        # Increment message counters
        self.metadata["total_messages"] += 1
        self.metadata["total_user_messages"] += 1

        logger.info(f"Processing message: {self.get_metadata_summary()}")

        # Store user_id and conversation_id for tool execution
        if user_context and 'user_id' in user_context:
            self._current_user_id = user_context['user_id']
            self._current_conversation_id = user_context.get('conversation_id')
            self._current_message_id = user_context.get('message_id')
        
        # START AGENT CALL LOGGING
        try:
            self._current_log_id = await agent_call_logger.start_agent_call(
                user_id=self._current_user_id or "unknown",
                agent_name="planner",
                model_name=self.metadata.get("model_name", "unknown"),
                message_id=self._current_message_id or agent_call_logger.generate_message_id(),
                conversation_id=self._current_conversation_id,
                session_id=user_context.get('session_id') if user_context else None,
                agent_type="planning",
                agent_version=self.metadata.get("agent_version", "1.0.0"),
                input_message=user_message,
                tools_enabled=self.enable_openai_tools,
                metadata={
                    "conversation_history_length": len(self.conversation_history),
                    "has_context": bool(user_context),
                    "is_first_conversation": None,  # Will be updated below
                    "tools_enabled": self.enable_openai_tools
                },
                tags=["planner", "planning", "content_planning"]
            )
            logger.info(f"[PLANNER] Started agent call log: {self._current_log_id}")
        except Exception as e:
            logger.error(f"[PLANNER] Failed to start agent call logging: {e}")

        # Check if this is user's first conversation (excluding current one)
        if user_context and self.conversation_storage:
            self.is_first_conversation = await self._is_first_conversation(
                user_context.get('user_id'),
                user_context.get('conversation_id')
            )

            self.update_metadata(is_first_conversation=self.is_first_conversation)

            logger.info(f"is_first_conversation={self.is_first_conversation} for user {user_context.get('user_id')}")

            if self.is_first_conversation:
                logger.info(f"First conversation detected for user {user_context.get('user_id')}")
                self.add_to_history("system", "NOTE: This is the user's first conversation. All relevant information is in the current conversation history. DO NOT use the request_user_context tool.")
            else:
                # Returning user - check if this is their first message in THIS conversation
                is_first_message_in_conversation = await self._is_first_user_message_in_conversation(
                    user_context.get('conversation_id')
                )

                logger.info(f"is_first_message_in_conversation={is_first_message_in_conversation} for conversation {user_context.get('conversation_id')}")
                
                if is_first_message_in_conversation and not self._context_cached:
                    logger.info(f"Returning user's first message - loading basic context for user {user_context.get('user_id')}")
                    await self._load_basic_user_context(user_context)
                    self._context_cached = True
                    self.update_metadata(context_cached=True)

        # Only add user message if not already in history (from loaded conversation)
        if not self.conversation_history or self.conversation_history[-1].get("content") != user_message:
            self.add_to_history("user", user_message)

        # Update system prompt to instruct model about context saving tool
        if self.is_first_conversation:
            self.add_to_history(
                "system",
                "NOTE: This is the user's first conversation with you. You may use the context saving tool to store any valuable new information about the user, their goals, or preferences."
            )
        else:
            self.add_to_history(
                "system",
                "If you encounter any valuable new information about the user, their goals, or preferences during this conversation, use the context saving tool to store it."
            )

        try:
            # Check if OpenAI client
            if hasattr(self.model_client, 'client') and hasattr(self.model_client.client, 'chat'):
                # Only use tools if enabled for OpenAI
                if self.enable_openai_tools:
                    response = await self._generate_with_tools_openai()
                else:
                    response = await self.model_client.generate_completion(
                        messages=self.conversation_history,
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
                    logger.info(f"Tool calls detected: {[tc.function.name for tc in message.tool_calls]}")
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
                    )
                    
                    self.add_to_history("assistant", follow_up)
                    
                    # COMPLETE AGENT CALL LOGGING
                    try:
                        await agent_call_logger.complete_agent_call(
                            log_id=self._current_log_id,
                            output_message=follow_up,
                            metadata={
                                "tool_calls_made": len(message.tool_calls) if message.tool_calls else 0,
                                "is_first_conversation": self.is_first_conversation,
                                "context_cached": self._context_cached,
                                "final_history_length": len(self.conversation_history)
                            }
                        )
                        logger.info(f"[PLANNER] Completed agent call log: {self._current_log_id}")
                    except Exception as log_error:
                        logger.error(f"[PLANNER] Failed to complete agent call logging: {log_error}")
                    
                    return follow_up
                else:
                    # Regular text response
                    self.add_to_history("assistant", message.content)
                    
                    # COMPLETE AGENT CALL LOGGING
                    try:
                        await agent_call_logger.complete_agent_call(
                            log_id=self._current_log_id,
                            output_message=message.content,
                            metadata={
                                "no_tool_calls": True,
                                "is_first_conversation": self.is_first_conversation,
                                "context_cached": self._context_cached
                            }
                        )
                        logger.info(f"[PLANNER] Completed agent call log: {self._current_log_id}")
                    except Exception as log_error:
                        logger.error(f"[PLANNER] Failed to complete agent call logging: {log_error}")
                    
                    return message.content
            else:
                # Fallback for clients without tool support
                response = await self.model_client.generate_completion(
                    messages=self.conversation_history,
                )
                
                self.add_to_history("assistant", response)
                
                # COMPLETE AGENT CALL LOGGING
                try:
                    await agent_call_logger.complete_agent_call(
                        log_id=self._current_log_id,
                        output_message=response,
                        metadata={"fallback_path": True, "no_tool_support": True}
                    )
                    logger.info(f"[PLANNER] Completed agent call log (fallback): {self._current_log_id}")
                except Exception as log_error:
                    logger.error(f"[PLANNER] Failed to complete agent call logging: {log_error}")
                
                return response
            
        except Exception as e:
            logger.error(f"[PLANNER] Error in planning agent: {e}", exc_info=True)
            error_msg = "I encountered an error while processing your request. Please try again."
            
            # FAIL AGENT CALL LOGGING
            try:
                await agent_call_logger.fail_agent_call(
                    log_id=self._current_log_id,
                    error=str(e),
                    error_type="processing_error",
                    stack_trace=traceback.format_exc(),
                    metadata={"error_location": "process_message"}
                )
                logger.error(f"[PLANNER] Failed agent call log: {self._current_log_id}")
            except Exception as log_error:
                logger.error(f"[PLANNER] Failed to log agent call failure: {log_error}")
            
            return error_msg
    
    # ============================================================================
    # PRIVATE METHODS - Conversation Checks
    # ============================================================================
    
    async def _is_first_conversation(self, user_id: str, current_conversation_id: str) -> bool:
        """
        Check if this is the user's first conversation (excluding the current one).
        
        Args:
            user_id: User identifier
            current_conversation_id: Current conversation ID to exclude from count
            
        Returns:
            True if this is the user's first conversation
        """
        try:
            if not self.conversation_storage:
                return True
            
            # Get all conversations for this user
            conversations = await self.conversation_storage.get_user_conversations(
                user_id=user_id,
                limit=100
            )
            
            # Filter out the current conversation
            previous_conversations = [
                conv for conv in conversations 
                if conv.get('id') != current_conversation_id
            ]
            
            is_first = len(previous_conversations) == 0
            logger.info(f"User {user_id} has {len(previous_conversations)} previous conversations (is_first={is_first})")
            return is_first
            
        except Exception as e:
            logger.error(f"Error checking if first conversation: {e}")
            return True  # Default to first conversation on error
    
    async def _is_first_user_message_in_conversation(self, conversation_id: str) -> bool:
        """
        Check if this is the first user message in the current conversation.
        
        Args:
            conversation_id: Current conversation ID
            
        Returns:
            True if this is the first user message in this conversation
        """
        try:
            if not self.conversation_storage:
                return True
            
            # Get the conversation
            conversation = await self.conversation_storage.get_conversation(conversation_id)
            logger.info(f"Loaded conversation {conversation_id} for first message check, data: {conversation}")
            if not conversation:
                return True
            
            # Check if there are any user messages
            # Note: We check for <= 1 because the current message may already be persisted in storage
            # when this check runs. So 0 or 1 messages both indicate this is the first user message.
            messages = conversation.get('messages', [])
            user_messages = [msg for msg in messages if msg.get('role') == 'user']
            
            is_first = len(user_messages) <= 1
            logger.info(f"Conversation {conversation_id} has {len(user_messages)} user messages (is_first={is_first})")
            return is_first
            
        except Exception as e:
            logger.error(f"Error checking if first user message: {e}")
            return True  # Default to first message on error
    # ============================================================================
    # PRIVATE METHODS - Context Loading
    # ============================================================================
    
    async def _load_basic_user_context(self, user_context: Dict[str, Any]):
        """
        Load basic profile and goals for returning users at conversation start.
        Makes a single request to context manager for essential information.
        
        Args:
            user_context: User context including user_id
        """
        try:
            user_id = user_context.get('user_id')
            if not user_id or not self.context_manager_agent:
                logger.warning("Cannot load context: missing user_id or context_manager_agent")
                return
            
            logger.info(f"Loading basic profile and goals for user: {user_id}")
            
            # Request basic profile and goals from context manager
            basic_query = "Please provide the user's basic profile (name, role, preferences) and their main goals or content plans."
            context_info = await self._request_context_from_manager(
                query=basic_query,
                reasoning="Loading basic user context for returning user at conversation start",
                user_context=user_context
            )
            
            # Add to conversation history as system message
            cached_context = f"""=== USER CONTEXT (Auto-loaded) ===

{context_info}

=== End of User Context ===

This basic context was automatically retrieved for this returning user. You can request additional specific details if needed using the manage_context tool."""
            
            self.add_to_history("system", cached_context)
            logger.info("Basic user context successfully loaded")
            
        except Exception as e:
            logger.error(f"Error loading basic user context: {e}")
            # Don't fail the conversation if context loading fails
    
    async def _request_context_from_manager(self, query: str, reasoning: str, user_context: Dict[str, Any]) -> str:
        """
        Request context from the context manager agent.
        
        Args:
            query: The context query to ask
            reasoning: Explanation for why context is needed
            user_context: Full user context including user_id, conversation_id, message_id, session_id
            
        Returns:
            Context information as string
        """
        try:
            if not self.context_manager_agent:
                return "Context manager not available."
            
            context_message = f"Request for context: {query}\nReasoning: {reasoning}"
            
            # Pass full user_context to ensure proper agent call logging
            result = await self.context_manager_agent.process_message(
                user_message=context_message,
                user_context=user_context
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error requesting context from manager: {e}")
            return f"Error retrieving context: {str(e)}"
    
    async def _prefetch_and_cache_user_context(self, user_context: Dict[str, Any]):
        """
        Proactively fetch user's complete context at conversation start.
        Makes a single comprehensive request to avoid duplicate calls.
        Adds context as a system message so it's available throughout the conversation.
        
        Args:
            user_context: User context including user_id
        """
        try:
            user_id = user_context.get('user_id')
            if not user_id or not self.context_manager_agent:
                logger.warning("Cannot prefetch context: missing user_id or context_manager_agent")
                return
            
            logger.info(f"Prefetching user context for user: {user_id}")
            
            # Make a single comprehensive request instead of two separate ones
            # This avoids duplicate context manager calls
            comprehensive_query = "Please provide the user's complete profile (demographics, location, language, preferences) and their main interests, goals, and content plans."
            context_info = await self._request_context_from_manager(
                query=comprehensive_query,
                reasoning="Loading complete user context for personalized assistance and planning",
                user_context=user_context
            )
            
            # Add to conversation history as system message
            cached_context = f"""=== USER CONTEXT (Auto-loaded) ===

{context_info}

=== End of User Context ===

This context was automatically retrieved from the user's history and is available for this entire conversation. You do NOT need to fetch it again unless you need additional specific information not covered above."""
            
            self.add_to_history("system", cached_context)
            
            # Add explicit instruction to prevent redundant context requests
            self.add_to_history("system", 
                "IMPORTANT: The user's complete profile and goals are now loaded above in the cached context. "
                "Do NOT use the request_user_context tool unless you need SPECIFIC additional information that is clearly NOT covered in the auto-loaded context. "
                "If the cached context answers the user's needs, proceed directly without making context retrieval calls."
            )
            logger.info("User context successfully cached in conversation")
            
        except Exception as e:
            logger.error(f"Error prefetching user context: {e}")
            # Don't fail the conversation if prefetch fails
    
    # ============================================================================
    # PRIVATE METHODS - Tool Generation (OpenAI)
    # ============================================================================
    
    async def _generate_with_tools_openai(self):
        """Generate response with tool support for OpenAI"""
        # Only include tools if enabled
        kwargs = {
            "messages": self.conversation_history,
        }
        
        if self.enable_openai_tools:
            # Only filter out context retrieval tool for first-time conversations
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

        # Log tool calls
        tool_calls_data = [{
            "call_id": tc.id,
            "name": tc.function.name,
            "arguments": json.loads(tc.function.arguments),
            "timestamp": datetime.now(timezone.utc).isoformat()
        } for tc in tool_calls]
        
        try:
            await agent_call_logger.update_tool_calls(self._current_log_id, tool_calls_data)
            logger.info(f"[PLANNER] Logged {len(tool_calls)} tool calls")
        except Exception as e:
            logger.error(f"[PLANNER] Failed to log tool calls: {e}")

        # Increment tool calls counter
        self.metadata["tool_calls_count"] += len(tool_calls)

        for tool_call in tool_calls:
            tool_name = tool_call.function.name
            tool_input = json.loads(tool_call.function.arguments)

            # Track tool usage by type
            tools_by_type = self.metadata["tools_by_type"]
            tools_by_type[tool_name] = tools_by_type.get(tool_name, 0) + 1

            logger.info(f"Executing tool: {tool_name} (total: {tools_by_type[tool_name]})")
            
            if tool_name == "manage_tasks":
                try:
                    user_id = getattr(self, '_current_user_id', None)
                    conversation_id = getattr(self, '_current_conversation_id', None)
                    if not user_id:
                        raise ValueError("No user_id available for task management")
                    
                    if not self.task_manager_agent:
                        raise ValueError("Task manager agent not available")
                    
                    # Extract natural language request
                    request = tool_input.get('request', '')
                    if not request:
                        raise ValueError("No request provided for task management")
                    
                    # Delegate to task manager agent with natural language request
                    logger.info(f"[PLANNER] Delegating to task manager: {request[:100]}...")
                    user_context = {
                        'user_id': user_id,
                        'conversation_id': conversation_id,
                        'message_id': self._current_message_id  # Pass message_id for tracking
                    }
                    task_result = await self.task_manager_agent.process_message(
                        user_message=request,
                        user_context=user_context
                    )
                    logger.info(f"[PLANNER] Task manager completed delegation")
                    results.append(task_result)
                except Exception as e:
                    logger.error(f"Error executing manage_tasks tool: {e}")
                    results.append(f"Error managing tasks: {str(e)}")
            elif tool_name == "manage_context":
                try:
                    user_id = getattr(self, '_current_user_id', None)
                    if not user_id:
                        raise ValueError("No user_id available for context management")
                    
                    action = tool_input.get('action')
                    context_result = await self._manage_context_tool(action, tool_input, user_id)
                    results.append(context_result)
                except Exception as e:
                    logger.error(f"Error executing manage_context tool: {e}")
                    results.append(f"Error managing context: {str(e)}")
            else:
                logger.warning(f"Unknown tool: {tool_name}")
                results.append(f"Unknown tool: {tool_name}")
        
        # Log tool results
        tool_results_data = [{
            "call_id": tc.id,
            "result": result[:500] if isinstance(result, str) else str(result)[:500],  # Truncate large results
            "success": "Error" not in str(result),
            "timestamp": datetime.now(timezone.utc).isoformat()
        } for tc, result in zip(tool_calls, results)]
        
        try:
            await agent_call_logger.update_tool_results(self._current_log_id, tool_results_data)
            logger.info(f"[PLANNER] Logged {len(results)} tool results")
        except Exception as e:
            logger.error(f"[PLANNER] Failed to log tool results: {e}")

        return results

    async def _manage_context_tool(self, action: str, tool_input: Dict[str, Any], user_id: str) -> str:
        """
        Handler for manage_context tool. Routes to ContextManagerAgent for execution.
        """
        try:
            if action == "save":
                logger.debug(f"Saving user context for user: {user_id}")
                summary = tool_input.get("summary", "")
                if not summary:
                    return "Error: summary is required for 'save' action"
                
                context_message = f"Save the following information about the user: {summary}"
            elif action == "request":
                logger.debug(f"Requesting additional context for user: {user_id}")
                query = tool_input.get("query", "")
                if not query:
                    return "Error: query is required for 'request' action"
                reasoning = tool_input.get("reasoning", "")
                context_message = f"Request for additional context: {query}" + (f"\nReasoning: {reasoning}" if reasoning else "")
            elif action == "retrieve":
                logger.debug(f"Retrieving context file for user: {user_id}")
                filename = tool_input.get("filename", "INDEX.md")
                context_message = f"Retrieve the context file: {filename}"
            elif action == "list":
                logger.debug(f"Listing context files for user: {user_id}")
                context_message = "List all context files"
            else:
                return f"Unknown action: {action}"
            
            # Delegate to context manager agent with full user context
            user_context = {
                'user_id': user_id,
                'conversation_id': self._current_conversation_id,
                'message_id': self._current_message_id,
                'session_id': self.metadata.get('session_id')
            }
            result = await self.context_manager_agent.process_message(
                user_message=context_message,
                user_context=user_context
            )
            logger.debug(f"Context manager response: {result}")
            return result
        except Exception as e:
            logger.error(f"Error managing context: {e}")
            return f"Error managing context: {str(e)}"
    
    # ============================================================================
    # PRIVATE METHODS - Task Search
    # ============================================================================
    
    async def _search_tasks_tool(self, tool_input: Dict[str, Any]) -> str:
        """
        Handler for search_tasks tool. Searches and retrieves tasks from the database.
        
        Args:
            tool_input: Dict with optional 'keywords', 'status_filter', 'priority_filter'
            
        Returns:
            Formatted string with search results
        """
        import asyncpg
        from config.settings import Settings
        
        try:
            action = tool_input.get("action", "").lower()
            keywords = tool_input.get("keywords", "").strip()
            status_filter = tool_input.get("status_filter", "").strip()
            priority_filter = tool_input.get("priority_filter", "").strip()
            
            settings = Settings()
            db_url = settings.DATABASE_URL
            conn = await asyncpg.connect(db_url)
            
            try:
                if action == "get_all":
                    # Get all tasks
                    query = """
                        SELECT id, title, description, status, priority, 
                               "estimatedHours", "aiGenerated", "createdAt", "updatedAt"
                        FROM "Task"
                        ORDER BY "createdAt" DESC
                        LIMIT 100
                    """
                    params = []
                    
                elif action == "search":
                    if not keywords:
                        return "Error: 'keywords' parameter is required for 'search' action."
                    
                    # Build dynamic query with filters
                    where_clauses = [
                        "(LOWER(title) LIKE LOWER($1) OR LOWER(description) LIKE LOWER($1))"
                    ]
                    params = [f"%{keywords}%"]
                    param_count = 2
                    
                    if status_filter:
                        where_clauses.append(f"status = ${param_count}")
                        params.append(status_filter)
                        param_count += 1
                    
                    if priority_filter:
                        where_clauses.append(f'priority = ${param_count}::"Priority"')
                        params.append(priority_filter)
                        param_count += 1
                    
                    where_clause = " AND ".join(where_clauses)
                    
                    query = f"""
                        SELECT id, title, description, status, priority, 
                               "estimatedHours", "aiGenerated", "createdAt", "updatedAt"
                        FROM "Task"
                        WHERE {where_clause}
                        ORDER BY "createdAt" DESC
                        LIMIT 50
                    """
                else:
                    return f"Error: Invalid action '{action}'. Use 'search' or 'get_all'."
                
                # Execute query
                tasks = await conn.fetch(query, *params)
                
                # If search returned no results and action was search, fallback to get_all
                if not tasks and action == "search":
                    logger.info(f"No tasks found for keywords '{keywords}'. Falling back to get_all.")
                    query = """
                        SELECT id, title, description, status, priority, 
                               "estimatedHours", "aiGenerated", "createdAt", "updatedAt"
                        FROM "Task"
                        ORDER BY "createdAt" DESC
                        LIMIT 100
                    """
                    tasks = await conn.fetch(query)
                    result_text = f"No tasks found matching '{keywords}'. Returning all available tasks ({len(tasks)} total):\n\n"
                else:
                    if not tasks:
                        return "No tasks found matching your criteria."
                    result_text = f"Found {len(tasks)} task(s):\n\n"
                
                # Format results
                for task in tasks:
                    result_text += f"**[{task['status']}] {task['title']}** (Priority: {task['priority']})\n"
                    result_text += f"  ID: {task['id']}\n"
                    if task['description']:
                        desc = task['description'][:200] + "..." if len(task['description']) > 200 else task['description']
                        result_text += f"  Description: {desc}\n"
                    if task['estimatedHours']:
                        result_text += f"  Estimated: {task['estimatedHours']} hours\n"
                    result_text += f"  Created: {task['createdAt'].strftime('%Y-%m-%d')}\n\n"
                
                logger.info(f"Task search completed: found {len(tasks)} tasks")
                return result_text
                
            finally:
                await conn.close()
                
        except Exception as e:
            logger.error(f"Error in search_tasks tool: {e}")
            return f"Error searching tasks: {str(e)}"