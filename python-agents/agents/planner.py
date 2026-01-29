"""
Planning Agent
Generates content project plans and task breakdowns
"""
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import asyncio
import json
import traceback
from agents.base import BaseAgent
from agents.tools import RedisStorageTool
from config.prompts import (
    PLANNING_SYSTEM_PROMPT
)
from utils.logger import logger
from storage.agent_call_log import agent_call_logger


class PlanningAgent(BaseAgent):
    """Agent for content planning and task generation"""
    
    def __init__(self, model_client, enable_openai_tools: bool = True, context_manager_agent=None, task_manager_agent=None, conversation_storage=None, redis_client=None):
        """
        Initialize planning agent with tool support for OpenAI.
        
        Args:
            model_client: LLM client (OpenAI)
            enable_openai_tools: Whether to enable tool usage for OpenAI models (default: True)
            context_manager_agent: Context manager agent instance for saving user context
            task_manager_agent: Task manager agent instance for delegating task operations
            conversation_storage: Conversation storage instance for checking conversation history
            redis_client: Redis client for temporary storage of intermediate data
        """
        super().__init__(model_client, "planning")
        self.enable_openai_tools = enable_openai_tools
        self.context_manager_agent = context_manager_agent
        self.task_manager_agent = task_manager_agent
        self.conversation_storage = conversation_storage
        
        # Initialize Redis storage tool
        self.redis_tool = RedisStorageTool(redis_client) if redis_client else None
        
        self.is_first_conversation = False
        self._context_cached = False  # Track if context already cached in this session
        self._current_user_id = None
        self._current_user_name = None
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
                    "name": "manage_user_tasks",
                    "description": "Delegate task management operations to the UserTaskManager agent. Supports: creating tasks (with initial notes), searching tasks, updating task fields, adding notes to existing tasks, retrieving task details and managing projects. Use 'add notes' for appending notes to tasks. Cannot handle large number of tasks at once; for bulk operations, break into smaller batches or use subtasks. you can use redis_storage to store intermediate task lists or data if needed.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "request": {
                                "type": "string",
                                "description": "Natural language request describing the task operation. Examples: 'Create 5 tasks for video production', 'Search for tasks about editing', 'Update task X status to completed', 'Add a note to task Y saying...', 'Get task Z details'"
                            }
                        },
                        "required": ["request"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "manage_user_context",
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
            },
            {
                "type": "function",
                "function": {
                    "name": "delegate_to_agents",
                    "description": "Break a complex task into smaller independent subtasks and delegate to child executor agents for parallel processing. Each subtask will be executed by an independent executor agent instance. Use this for complex tasks that can be parallelized.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "parent_task_description": {
                                "type": "string",
                                "description": "Description of the main/parent task to be broken down"
                            },
                            "subtasks": {
                                "type": "array",
                                "description": "List of subtasks to execute in parallel",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "id": {
                                            "type": "string",
                                            "description": "Unique identifier for this subtask (e.g., 'subtask_1', 'research_competitors')"
                                        },
                                        "description": {
                                            "type": "string",
                                            "description": "Clear description of what this subtask should accomplish"
                                        },
                                        "goal": {
                                            "type": "string",
                                            "description": "Specific goal or expected output for this subtask"
                                        },
                                        "context": {
                                            "type": "object",
                                            "description": "Additional context or data needed for this subtask",
                                            "additionalProperties": True
                                        }
                                    },
                                    "required": ["id", "description", "goal"]
                                }
                            },
                            "wait_for_completion": {
                                "type": "boolean",
                                "description": "Whether to wait for all subtasks to complete before responding (default: true)"
                            }
                        },
                        "required": ["parent_task_description", "subtasks"]
                    }
                }
            }
        ]
        
        # Initialize with comprehensive system prompt (no user name available yet)
        self._initialize_system_prompt()
    
    def get_available_tools(self) -> list:
        """
        Get list of available tools, including dynamically added tools like redis_storage.
        
        Returns:
            List of tool definitions in OpenAI format
        """
        tools = self.tools_openai.copy()
        
        # Add redis_storage tool if available
        if self.redis_tool and self.redis_tool.is_available():
            tools.append(self.redis_tool.get_tool_definition())
        
        return tools

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
    
    def _initialize_system_prompt(self, user_name: str | None = None):
        """Initialize the agent with system prompts and instructions"""
        # Add personalized greeting if user name is available
        if user_name:
            greeting = f"You are talking to {user_name}."
            self.add_to_history("system", greeting)
        
        self.add_to_history("system", PLANNING_SYSTEM_PROMPT)
       
        
    
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

        # Store user_id, user_name, and conversation_id for tool execution
        user_name = None
        if user_context and 'user_id' in user_context:
            self._current_user_id = user_context['user_id']
            user_name = user_context.get('user_name')
            self._current_user_name = user_name  # Store as instance variable for tool access
            self._current_conversation_id = user_context.get('conversation_id')
            self._current_message_id = user_context.get('message_id')
        
        # Reset tool tracking for this message
        self._tool_calls_log = []
        self._tool_results_log = []
        self._tool_calls_detailed = []  # New: detailed tool execution tracking
        
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

            # Add user name greeting at the start if conversation history exists and no greeting yet
            if user_name and self.conversation_history:
                # Check if first message is already a user greeting
                first_msg = self.conversation_history[0] if len(self.conversation_history) > 0 else None
                has_greeting = first_msg and first_msg.get("role") == "system" and "talking to" in first_msg.get("content", "").lower()
                
                if not has_greeting:
                    # Insert greeting at the beginning
                    greeting = f"You are talking to {user_name}."
                    self.conversation_history.insert(0, {"role": "system", "content": greeting})
                    logger.info(f"Added user greeting to conversation history for {user_name}")

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
                    
                    # Track tool calls for logging
                    for tc in message.tool_calls:
                        self._tool_calls_log.append({
                            "id": tc.id,
                            "type": tc.type,
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
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
                    
                    # Execute tools (this blocks until all tools complete)
                    # Log what we're executing
                    tool_names = [tc.function.name for tc in message.tool_calls]
                    logger.info(f"Executing {len(message.tool_calls)} tools: {', '.join(tool_names)}...")
                    tool_results = await self._execute_tools_openai(message.tool_calls)
                    logger.info(f"All {len(message.tool_calls)} tools completed")
                    
                    # Track tool results for logging
                    self._tool_results_log.extend(tool_results)
                    
                    # Add tool results (MUST immediately follow assistant message with tool_calls)
                    for tool_call, result in zip(message.tool_calls, tool_results):
                        self.add_to_history("tool", result, tool_call.id)
                    
                    # Now add system message after tool results (optional, for guidance)
                    self.add_to_history("system",
                        f"All {len(tool_results)} tool(s) have finished executing. "
                        f"Review the tool results above and generate your final response based on these results."
                    )
                    
                    # Get follow-up response WITH tools context
                    # Prepare tools for follow-up (filter if needed)
                    tools = self.get_available_tools()
                    if self.is_first_conversation:
                        tools = [tool for tool in tools 
                                if tool["function"]["name"] != "request_user_context"]
                    
                    # Loop to handle potential multi-turn tool calling
                    max_tool_iterations = 5  # Prevent infinite loops
                    iteration_count = 0
                    
                    while iteration_count < max_tool_iterations:
                        iteration_count += 1
                        logger.info(f"[PLANNER] Follow-up completion iteration {iteration_count}/{max_tool_iterations}")
                        
                        follow_up_response = await self.model_client.generate_completion(
                            messages=self.conversation_history,
                            tools=tools,
                        )
                        
                        # Check if response has tool calls (handle both string and ChatCompletion object)
                        if isinstance(follow_up_response, str):
                            # String response = no more tool calls
                            follow_up_text = follow_up_response
                            break
                        else:
                            # ChatCompletion object - check for tool calls
                            follow_up_message = follow_up_response.choices[0].message
                            
                            # If the LLM wants to make more tool calls, execute them
                            if hasattr(follow_up_message, 'tool_calls') and follow_up_message.tool_calls:
                                logger.warning(f"[PLANNER] Follow-up response contains {len(follow_up_message.tool_calls)} additional tool call(s): {[tc.function.name for tc in follow_up_message.tool_calls]}")
                                logger.warning(f"[PLANNER] This indicates a potential issue - follow-up should provide final text, not request more tools")
                                
                                # Track these tool calls
                                for tc in follow_up_message.tool_calls:
                                    self._tool_calls_log.append({
                                        "id": tc.id,
                                        "type": tc.type,
                                        "function": {
                                            "name": tc.function.name,
                                            "arguments": tc.function.arguments
                                        }
                                    })
                                
                                # Add assistant message with tool calls to history
                                self.add_to_history("assistant", {
                                    "content": follow_up_message.content,
                                    "tool_calls": [{
                                        "id": tc.id,
                                        "type": tc.type,
                                        "function": {
                                            "name": tc.function.name,
                                            "arguments": tc.function.arguments
                                        }
                                    } for tc in follow_up_message.tool_calls]
                                })
                                
                                # Execute these additional tools
                                logger.info(f"[PLANNER] Executing {len(follow_up_message.tool_calls)} additional tool(s) from follow-up response...")
                                additional_results = await self._execute_tools_openai(follow_up_message.tool_calls)
                                logger.info(f"[PLANNER] Additional tools completed: {[r[:100] for r in additional_results]}")
                                
                                # Track results
                                self._tool_results_log.extend(additional_results)
                                
                                # Add tool results to history
                                for tool_call, result in zip(follow_up_message.tool_calls, additional_results):
                                    self.add_to_history("tool", result, tool_call.id)
                                
                                # Add guidance for next iteration
                                self.add_to_history("system",
                                    f"The {len(additional_results)} additional tool(s) have completed. "
                                    f"Review all tool results and provide your FINAL response to the user."
                                )
                                
                                # Continue loop to get next response
                                continue
                            else:
                                # No tool calls - extract text content
                                follow_up_text = follow_up_message.content
                                break
                    
                    # Check if we hit max iterations
                    if iteration_count >= max_tool_iterations:
                        logger.error(f"[PLANNER] Hit maximum tool iteration limit ({max_tool_iterations}). Forcing completion.")
                        follow_up_text = "I've processed your request with multiple tool operations. Please let me know if you need any clarifications or adjustments."
                    
                    # Handle null/empty responses (can happen after timeouts)
                    if not follow_up_text or follow_up_text.strip() == "":
                        logger.warning(f"[PLANNER] Empty follow-up response detected after {iteration_count} iteration(s). Tool results: {[str(r)[:100] for r in tool_results]}")
                        # Check if any tool had a timeout
                        has_timeout = any("TOOL TIMEOUT" in str(r) for r in tool_results)
                        if has_timeout:
                            follow_up_text = (
                                "The task management operation is taking longer than expected and may still be processing in the background. "
                                "You can check the task list to see if changes have been applied, or try a more specific request. "
                                "For large operations, consider breaking them into smaller batches."
                            )
                        else:
                            follow_up_text = "I've completed processing your request. Please let me know if you need anything else."
                    
                    self.add_to_history("assistant", follow_up_text)
                    
                    # COMPLETE AGENT CALL LOGGING
                    try:
                        await agent_call_logger.complete_agent_call(
                            log_id=self._current_log_id,
                            output_message=follow_up_text,
                            tool_calls=self._tool_calls_log if self._tool_calls_log else None,
                            tool_results=self._tool_results_log if self._tool_results_log else None,
                            tool_calls_detailed=self._tool_calls_detailed if hasattr(self, '_tool_calls_detailed') and self._tool_calls_detailed else None,
                            metadata={
                                "tool_calls_made": len(self._tool_calls_log),
                                "is_first_conversation": self.is_first_conversation,
                                "context_cached": self._context_cached,
                                "final_history_length": len(self.conversation_history)
                            }
                        )
                        logger.info(f"[PLANNER] Completed agent call log: {self._current_log_id}")
                    except Exception as log_error:
                        logger.error(f"[PLANNER] Failed to complete agent call logging: {log_error}")
                    
                    return follow_up_text
                else:
                    # Regular text response
                    self.add_to_history("assistant", message.content)
                    
                    # COMPLETE AGENT CALL LOGGING
                    try:
                        await agent_call_logger.complete_agent_call(
                            log_id=self._current_log_id,
                            output_message=message.content,
                            tool_calls=None,
                            tool_results=None,
                            tool_calls_detailed=None,
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
                        tool_calls_detailed=None,
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
            #logger.info(f"Loaded conversation {conversation_id} for first message check, data: {conversation}")
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
            basic_query = "Please provide the user's basic profile (name, role, preferences) and their main goals or content plans. If not found, describe this user in 2-3 sentences based on available information."
            context_info = await self._request_context_from_manager(
                query=basic_query,
                reasoning="Loading basic user context for returning user at conversation start",
                user_context=user_context
            )
            
            # Add to conversation history as system message
            cached_context = f"""=== USER CONTEXT (Auto-loaded) ===

{context_info}

=== End of User Context ===

This basic context was automatically retrieved for this returning user. You can request additional specific details if needed using the manage_user_context tool."""
            
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
            tools = self.get_available_tools()
            if self.is_first_conversation:
                tools = [tool for tool in self.get_available_tools() 
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
        import traceback
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
            
            # Track detailed execution
            detailed_call = {
                "tool_call_id": tool_call.id,
                "name": tool_name,
                "input": tool_input,
                "output": None,
                "exception": None,
                "started_at": datetime.now(timezone.utc).isoformat(),
                "completed_at": None,
                "duration_ms": None,
                "success": False
            }

            # Track tool usage by type
            tools_by_type = self.metadata["tools_by_type"]
            tools_by_type[tool_name] = tools_by_type.get(tool_name, 0) + 1

            logger.info(f"Executing tool: {tool_name} (total: {tools_by_type[tool_name]})")
            
            # Execute tool and track detailed results
            tool_start_time = datetime.now(timezone.utc)
            tool_result = None
            tool_exception = None
            
            if tool_name == "manage_user_tasks":
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
                    # Delegate to task manager with a timeout to avoid hanging
                    # Increased timeout for complex operations like closing duplicate tasks
                    timeout_seconds = 600
                    logger.info(f"[PLANNER] Starting task manager delegation (timeout: {timeout_seconds}s)...")
                    start_time = datetime.now(timezone.utc)
                    
                    try:
                        task_result = await asyncio.wait_for(
                            self.task_manager_agent.process_message(
                                user_message=request,
                                user_context=user_context
                            ),
                            timeout=timeout_seconds
                        )
                        elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
                        logger.info(f"[PLANNER] Task manager completed successfully in {elapsed:.2f}s")
                        
                        # Parse JSON response from task manager
                        try:
                            task_response = json.loads(task_result) if isinstance(task_result, str) else task_result
                            # Extract message and status for LLM context
                            message = task_response.get('message', str(task_result))
                            status = task_response.get('status', 'unknown')
                            # Build human-readable summary for LLM
                            task_result_str = f"[Task Manager - {status.upper()}] {message}"
                            if task_response.get('error'):
                                task_result_str += f"\nError: {task_response['error']}"
                            if task_response.get('data'):
                                # Include relevant data counts for LLM context
                                data = task_response['data']
                                if 'created_count' in data:
                                    task_result_str += f"\nCreated {data['created_count']} items"
                                if 'updated_count' in data:
                                    task_result_str += f"\nUpdated {data['updated_count']} items"
                                if 'total_count' in data:
                                    task_result_str += f"\nFound {data['total_count']} items"
                            logger.info(f"[PLANNER] Task manager response parsed: {task_result_str}")
                            results.append(task_result_str)
                        except (json.JSONDecodeError, TypeError) as parse_error:
                            logger.warning(f"[PLANNER] Failed to parse task manager JSON response: {parse_error}, using raw response")
                            tool_result = str(task_result)
                            results.append(tool_result)
                        
                    except asyncio.TimeoutError:
                        elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
                        # Record a timeout and return a helpful message
                        self.metadata.setdefault('task_manager_timeouts', 0)
                        self.metadata['task_manager_timeouts'] += 1
                        logger.error(f"[PLANNER] Task manager timed out after {elapsed:.2f}s (limit: {timeout_seconds}s)")
                        logger.error(f"[PLANNER] WARNING: Task manager agent may still be running. Check agent_call_log table for orphaned IN_PROGRESS records.")
                        task_result = (
                            f"TOOL TIMEOUT: The task management operation did not complete within {timeout_seconds} seconds ({elapsed:.0f}s elapsed). "
                            f"The task manager may still be processing your request in the background. "
                            f"\n\nSuggested actions:\n"
                            f"- Wait a few minutes and check if tasks were updated\n"
                            f"- Break your request into smaller, more specific operations\n"
                            f"- For bulk operations, process tasks in batches of 5-10 at a time"
                        )
                        tool_exception = f"TimeoutError: Task manager timed out after {elapsed:.0f}s"
                        tool_result = task_result
                        results.append(task_result)
                    except Exception as e:
                        elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
                        logger.error(f"[PLANNER] Exception delegating to task manager after {elapsed:.2f}s: {e}", exc_info=True)
                        task_result = f"TOOL ERROR: Failed to execute task management: {str(e)}"
                        tool_exception = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
                        tool_result = task_result
                        results.append(task_result)
                except Exception as e:
                    logger.error(f"Error executing manage_user_tasks tool: {e}")
                    error_msg = f"Error managing tasks: {str(e)}"
                    tool_exception = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
                    tool_result = error_msg
                    results.append(error_msg)
            elif tool_name == "manage_user_context":
                try:
                    user_id = getattr(self, '_current_user_id', None)
                    if not user_id:
                        raise ValueError("No user_id available for context management")
                    
                    action = tool_input.get('action')
                    context_result = await self._manage_context_tool(action, tool_input, user_id)
                    tool_result = context_result
                    results.append(context_result)
                except Exception as e:
                    logger.error(f"Error executing manage_user_context tool: {e}")
                    error_msg = f"Error managing context: {str(e)}"
                    tool_exception = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
                    tool_result = error_msg
                    results.append(error_msg)
            elif tool_name == "redis_storage":
                try:
                    user_id = getattr(self, '_current_user_id', None)
                    if not user_id:
                        raise ValueError("No user_id available for Redis storage")
                    
                    if not self.redis_tool:
                        error_msg = "Redis storage tool not available. Please configure Redis connection."
                        results.append(error_msg)
                        tool_result = error_msg
                        tool_exception = "RedisNotConfiguredError: Redis client not available"
                    else:
                        redis_result = await self.redis_tool.execute(tool_input, user_id, agent_type="planner")
                        tool_result = redis_result
                        results.append(redis_result)
                except Exception as e:
                    logger.error(f"Error executing redis_storage tool: {e}")
                    error_msg = f"Error with Redis storage: {str(e)}"
                    tool_exception = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
                    tool_result = error_msg
                    results.append(error_msg)
            elif tool_name == "delegate_to_agents":
                try:
                    user_id = getattr(self, '_current_user_id', None)
                    conversation_id = getattr(self, '_current_conversation_id', None)
                    if not user_id:
                        raise ValueError("No user_id available for subtask execution")
                    
                    subtask_result = await self._execute_delegate_to_agents(tool_input, user_id, conversation_id)
                    tool_result = subtask_result
                    results.append(subtask_result)
                except Exception as e:
                    logger.error(f"Error executing delegate_to_agents tool: {e}")
                    logger.error(traceback.format_exc())
                    error_msg = f"Error delegating to agents: {str(e)}"
                    tool_exception = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
                    tool_result = error_msg
                    results.append(error_msg)
            else:
                logger.warning(f"Unknown tool: {tool_name}")
                error_msg = f"Unknown tool: {tool_name}"
                tool_exception = f"UnknownToolError: {tool_name}"
                tool_result = error_msg
                results.append(error_msg)
            
            # Complete detailed tracking for this tool call
            tool_end_time = datetime.now(timezone.utc)
            detailed_call["completed_at"] = tool_end_time.isoformat()
            detailed_call["duration_ms"] = int((tool_end_time - tool_start_time).total_seconds() * 1000)
            detailed_call["output"] = tool_result
            detailed_call["exception"] = tool_exception
            detailed_call["success"] = tool_exception is None
            self._tool_calls_detailed.append(detailed_call)
        
        # Log tool results
        tool_results_data = [{
            "call_id": tc.id,
            "result": result[:500] if isinstance(result, str) else str(result)[:500],  # Truncate large results
            "success": "Error" not in str(result),
            "timestamp": datetime.now(timezone.utc).isoformat()
        } for tc, result in zip(tool_calls, results)]
        
        try:
            await agent_call_logger.update_tool_results(self._current_log_id, tool_results_data)
            # Also update detailed tool calls
            if hasattr(self, '_tool_calls_detailed') and self._tool_calls_detailed:
                await agent_call_logger.update_tool_calls_detailed(self._current_log_id, self._tool_calls_detailed)
                logger.info(f"[PLANNER] Logged {len(results)} tool results and {len(self._tool_calls_detailed)} detailed records")
            else:
                logger.info(f"[PLANNER] Logged {len(results)} tool results")
        except Exception as e:
            logger.error(f"[PLANNER] Failed to log tool results: {e}")

        return results

    async def _manage_context_tool(self, action: str, tool_input: Dict[str, Any], user_id: str) -> str:
        """
        Handler for manage_user_context tool. Routes to ContextManagerAgent for execution.
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
                'user_name': self._current_user_name,  # Include user name for context
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
    
    
    
    # ============================================================================
    # PRIVATE METHODS - Redis Storage
    # ============================================================================
    # Redis storage is now handled by RedisStorageTool in agents/tools/redis_storage.py

    async def _execute_delegate_to_agents(
        self, 
        tool_input: Dict[str, Any], 
        user_id: str,
        conversation_id: Optional[str] = None
    ) -> str:
        """
        Break a task into subtasks and delegate to executor agents.
        
        Args:
            tool_input: Dict with 'parent_task_description', 'subtasks', and optional 'wait_for_completion'
            user_id: User identifier
            conversation_id: Optional conversation identifier
            
        Returns:
            Result summary of subtask execution
        """
        try:
            from agents.executor import ExecutorAgent
            from models.factory import create_model_client
            
            parent_description = tool_input.get("parent_task_description", "")
            subtasks = tool_input.get("subtasks", [])
            wait_for_completion = tool_input.get("wait_for_completion", True)
            
            if not subtasks:
                return "Error: No subtasks provided. Please specify at least one subtask."
            
            # Generate a unique parent task ID for this batch
            parent_task_id = f"parent_{datetime.now(timezone.utc).timestamp()}"
            
            logger.info(f"[PLANNER] Breaking into {len(subtasks)} subtasks for parent: {parent_task_id}")
            
            # Store subtask contexts in Redis
            for subtask in subtasks:
                subtask_id = subtask.get("id")
                if not subtask_id:
                    continue
                
                subtask_context = {
                    "id": subtask_id,
                    "description": subtask.get("description", ""),
                    "goal": subtask.get("goal", ""),
                    "context": subtask.get("context", {}),
                    "task_type": subtask.get("context", {}).get("task_type", "general"),
                    "parent_task_id": parent_task_id,
                    "parent_description": parent_description,
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
                
                # Store in Redis
                key = f"subtask:{parent_task_id}:{subtask_id}:{user_id}"
                await self.redis_tool.redis_client.set(
                    key, 
                    json.dumps(subtask_context),
                    ex=3600  # Expire after 1 hour
                )
                logger.info(f"[PLANNER] Stored context for subtask: {subtask_id}")
            
            # Create executor agents and launch subtask executions
            executor_tasks = []
            executor_agents = []
            
            for subtask in subtasks:
                subtask_id = subtask.get("id")
                if not subtask_id:
                    continue
                
                # Create a new executor agent for each subtask
                executor_model = create_model_client(
                    model=getattr(self.model_client, 'model', 'gpt-4o-mini')
                )
                
                executor = ExecutorAgent(
                    model_client=executor_model,
                    redis_client=self.redis_tool.redis_client if self.redis_tool else None,
                    task_manager_agent=self.task_manager_agent,
                    executor_id=f"executor_{subtask_id}_{datetime.now(timezone.utc).timestamp()}"
                )
                
                executor_agents.append(executor)
                
                # Launch subtask execution
                task = executor.execute_subtask(
                    subtask_id=subtask_id,
                    parent_task_id=parent_task_id,
                    user_id=user_id,
                    conversation_id=conversation_id
                )
                executor_tasks.append(task)
                
                logger.info(f"[PLANNER] Launched executor for subtask: {subtask_id}")
            
            if not executor_tasks:
                return "Error: No valid subtasks to execute."
            
            # Wait for completion if requested
            if wait_for_completion:
                logger.info(f"[PLANNER] Waiting for {len(executor_tasks)} subtasks to complete...")
                
                try:
                    results = await asyncio.gather(*executor_tasks, return_exceptions=True)
                    
                    # Process results
                    completed = 0
                    failed = 0
                    outputs = []
                    
                    for i, result in enumerate(results):
                        if isinstance(result, Exception):
                            failed += 1
                            logger.error(f"[PLANNER] Subtask {i} failed with exception: {result}")
                        elif isinstance(result, dict):
                            if result.get("success"):
                                completed += 1
                                outputs.append({
                                    "subtask_id": result.get("subtask_id"),
                                    "executor_id": result.get("executor_id"),
                                    "output": result.get("output", "")[:500]  # Truncate for summary
                                })
                            else:
                                failed += 1
                        else:
                            failed += 1
                    
                    # Build summary response
                    summary = f"""Subtask Execution Complete:
- Parent Task: {parent_description}
- Total Subtasks: {len(subtasks)}
- Completed: {completed}
- Failed: {failed}

Results:
"""
                    for output in outputs:
                        summary += f"\n**{output['subtask_id']}** (by {output['executor_id']}):\n{output['output']}\n"
                    
                    # Store aggregated results in Redis for later retrieval
                    results_key = f"subtask_results:{parent_task_id}:{user_id}"
                    await self.redis_tool.redis_client.set(
                        results_key,
                        json.dumps({
                            "parent_task_id": parent_task_id,
                            "parent_description": parent_description,
                            "total_subtasks": len(subtasks),
                            "completed": completed,
                            "failed": failed,
                            "results": outputs,
                            "completed_at": datetime.now(timezone.utc).isoformat()
                        }),
                        ex=7200  # Keep results for 2 hours
                    )
                    
                    logger.info(f"[PLANNER] All subtasks completed. Completed: {completed}, Failed: {failed}")
                    return summary
                    
                except Exception as e:
                    logger.error(f"[PLANNER] Error waiting for subtasks: {e}")
                    logger.error(traceback.format_exc())
                    return f"Error executing subtasks: {str(e)}"
            else:
                # Don't wait - return immediately
                response = f"""Launched {len(executor_tasks)} subtasks for execution:
- Parent Task: {parent_description}
- Subtasks: {', '.join([s.get('id', 'unknown') for s in subtasks])}

Subtasks are executing in the background. You can check their status in Redis using the parent task ID: {parent_task_id}
"""
                logger.info(f"[PLANNER] Launched {len(executor_tasks)} subtasks without waiting")
                return response
                
        except Exception as e:
            logger.error(f"[PLANNER] Error in delegate_to_agents: {e}")
            logger.error(traceback.format_exc())
            return f"Error breaking into subtasks: {str(e)}"
